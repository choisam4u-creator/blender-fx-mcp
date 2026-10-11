# 출력 폴더 디스크 여유: doctor 의 선택 항목과 굽기 전 멈춤. 블렌더 없이 돈다.
import pytest

from blender_fx_mcp import bridge, disk, doctor, server


def test_free_bytes_walks_up_to_existing_folder(monkeypatch, tmp_path):
    assert disk.free_bytes(tmp_path) > 0
    # 두 번 재면 그사이 다른 프로세스가 디스크를 써서 값이 달라질 수 있다(CI 러너). 어느 폴더를 재는지로 확인한다
    asked = []
    real = disk.shutil.disk_usage
    monkeypatch.setattr(disk.shutil, "disk_usage", lambda p: asked.append(p) or real(p))
    assert disk.free_bytes(tmp_path / "없는" / "폴더") > 0
    assert asked == [tmp_path]
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "x.bin").write_bytes(b"0" * 1000)
    (tmp_path / "y.bin").write_bytes(b"0" * 24)
    assert disk.folder_bytes(tmp_path) == 1024
    assert disk.gb(3 * 1024**3) == "3.0GB"


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_doctor_space_check(monkeypatch, tmp_path, lang):
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    (tmp_path / "c.bin").write_bytes(b"0" * 2048)
    monkeypatch.setattr(disk, "free_bytes", lambda p: 2 * 1024**3)
    c = doctor._space_check(str(tmp_path))
    assert c["id"] == "space" and c["optional"] and not c["ok"]
    assert "2.0GB" in c["detail"] and "5.0GB" in c["detail"]
    # 출력 폴더가 작으면 지워도 소용없다고 말한다(엉뚱한 clear_caches 를 권하지 않음)
    assert "clear_caches" not in c["fix"] and "BLENDER_FX_OUT" in c["fix"]
    assert ("작아서 지워도 소용없음" if lang == "ko" else "clearing it will not help") in c["fix"]
    monkeypatch.setattr(disk, "free_bytes", lambda p: 50 * 1024**3)
    c = doctor._space_check(str(tmp_path))
    assert c["ok"] and c["fix"] == "" and "50.0GB" in c["detail"]
    monkeypatch.setattr(disk, "free_bytes", lambda p: None)
    assert doctor._space_check(str(tmp_path))["ok"]  # 알 수 없으면 경고하지 않음


def test_low_space_is_optional_next_step_not_failure(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    monkeypatch.setattr(disk, "free_bytes", lambda p: 1024**3)
    checks = [doctor._check("python", True, "3.11", "python"), doctor._space_check(str(tmp_path))]
    monkeypatch.setattr(doctor, "run_checks", lambda: checks)
    with pytest.raises(SystemExit) as e:
        doctor.main([])
    out = capsys.readouterr().out
    assert e.value.code == 0 and "[- ] output folder free space" in out and "(optional) The output folder is small" in out


def _fill(root, name, n):
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "f.bin").write_bytes(b"0" * n)


def _snapshots(root, sizes):
    """sizes 순서대로 오래된 → 새 스냅샷(이름 s0, s1, …)과 before_restore 하나."""
    import os
    d = root / "snapshots"
    d.mkdir(parents=True, exist_ok=True)
    for i, n in enumerate(sizes):
        f = d / f"s{i}.blend"
        f.write_bytes(b"0" * n)
        os.utime(f, (1_000_000 + i, 1_000_000 + i))
    (d / "before_restore.blend").write_bytes(b"0" * 7777)
    return d


def test_usage_groups(tmp_path):
    _fill(tmp_path, "cache_fluid", 3000)
    _fill(tmp_path, "cache_emit", 1000)
    d = _snapshots(tmp_path, [300, 200, 1, 1, 1, 1, 1])  # 오래된 2개만 지울 수 있음(최근 5개·before_restore 남김)
    (d / "s0.blend1").write_bytes(b"0" * 50)  # 지울 스냅샷의 이전 판도 함께 센다
    _fill(tmp_path, "20261011-101010_render_final", 2000)
    _fill(tmp_path, "20261011-101011_preview", 10)
    (tmp_path / "tower.glb").write_bytes(b"0" * 900)  # export_model 이 출력 폴더 바로 아래에 쓰는 파일
    (tmp_path / "loose.png").write_bytes(b"0" * 5)
    assert disk.usage_groups(tmp_path) == [("caches", 4000, 2), ("runs", 2010, 2), ("files", 905, 2), ("snapshots", 550, 2)]
    assert [g[0].name for g in disk.old_snapshots(d)] == ["s1.blend", "s0.blend"]
    assert disk.usage_groups(tmp_path / "없음") == []
    (tmp_path / "empty").mkdir()
    assert disk.usage_groups(tmp_path / "empty") == []


def test_snapshots_that_clear_snapshots_keeps_are_not_reclaimable(tmp_path):
    """스냅샷이 최근 5개뿐이면(아무리 커도) clear_snapshots 가 아무것도 못 지우니 doctor 도 권하지 않는다."""
    _snapshots(tmp_path, [10**6] * 5)
    assert disk.usage_groups(tmp_path) == []


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_low_space_names_biggest_groups_and_their_tools(monkeypatch, tmp_path, lang):
    """여유가 5GB 아래면 큰 묶음(캐시·스냅샷·렌더 결과·낱 파일)과 크기, 그 묶음을 지우는 방법을 큰 것부터 짝지어 말한다."""
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    monkeypatch.setattr(disk, "free_bytes", lambda p: 2 * 1024**3)
    monkeypatch.setattr(doctor, "GROUP_MIN_BYTES", 1000)
    _fill(tmp_path, "cache_liquid", 9000)
    _snapshots(tmp_path, [3000, 3000, 1, 1, 1, 1, 1])
    _fill(tmp_path, "20261011-101010_render_final", 3000)
    _fill(tmp_path, "20261011-101011_preview", 10)
    (tmp_path / "tower.glb").write_bytes(b"0" * 1500)
    c = doctor._space_check(str(tmp_path))
    labels = (["구운 캐시(cache_*)", "스냅샷(snapshots)", "렌더·미리보기 결과", "폴더 바로 아래 파일"] if lang == "ko"
              else ["baked caches (cache_*)", "snapshots", "render and preview results", "loose files"])
    pos = [c["detail"].index(label) for label in labels]
    assert pos == sorted(pos), c["detail"]  # 큰 것부터
    fixes = (["clear_caches", "오래된 스냅샷 2개", "날짜 이름 폴더(2개)", "파일 1개"] if lang == "ko"
             else ["clear_caches", "delete 2 old snapshots", "date-named folders (2)", "the 1 files"])
    tools = [c["fix"].index(x) for x in fixes]
    assert tools == sorted(tools), c["fix"]  # 고칠 방법도 같은 순서, 지울 수 있는 개수와 함께
    assert c["fix"].endswith("BLENDER_FX_OUT 을 여유 있는 디스크의 폴더로 지정" if lang == "ko"
                             else "point BLENDER_FX_OUT to a folder on a disk with more space")
    assert (f"최근 {server.SNAPSHOT_KEEP}개" if lang == "ko" else f"newest {server.SNAPSHOT_KEEP}") in c["fix"]
    monkeypatch.setattr(doctor, "GROUP_MIN_BYTES", 6000)  # 작은 묶음은 빼고 캐시·스냅샷만
    c = doctor._space_check(str(tmp_path))
    assert "clear_caches" in c["fix"] and "clear_snapshots" in c["fix"] and "(2" not in c["fix"]


@pytest.mark.parametrize("call", [
    'water(mode="drop")', 'splash(target="Building")', 'fire(target="Building")', 'smoke(at=[0, 0, 1])',
    'explode(target="Building")',
])
def test_bake_tools_stop_before_blender_when_disk_is_full(monkeypatch, tmp_path, call):
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", "ko")
    monkeypatch.setattr(disk, "free_bytes", lambda p: 300 * 1024**2)
    sent = []
    monkeypatch.setattr(bridge, "run_python", lambda code, timeout=None: sent.append(code) or "")
    out = eval(call, vars(server))
    out = out if isinstance(out, str) else out[0]
    assert not sent, f"{call}: 디스크가 부족한데 블렌더로 보냄(explode 는 조각내기도 하면 안 됨)"
    assert "디스크 여유가 0.3GB 뿐이라 굽기를 시작하지 않았습니다" in out and "clear_caches" in out, out


def test_enough_space_and_clear_caches_still_run(monkeypatch, tmp_path):
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setattr(disk, "free_bytes", lambda p: 300 * 1024**2)
    sent = []

    def fake(code, timeout=None):
        sent.append(code)
        raise bridge.BlenderError("reached")

    monkeypatch.setattr(bridge, "run_python", fake)
    server.clear_caches()  # 공간을 비우는 도구는 막지 않는다
    assert sent and "'cache_dirs'" in sent[0].splitlines()[0]
    monkeypatch.setattr(disk, "free_bytes", lambda p: 20 * 1024**3)
    sent.clear()
    server.water(mode="drop")
    assert sent and "'cache_dir'" in sent[-1].splitlines()[0]


def test_disk_helpers_survive_os_errors(monkeypatch, tmp_path):
    """디스크를 읽다 권한·경쟁 오류가 나도 doctor·굽기 전 점검이 예외로 죽지 않는다."""
    import os
    import shutil

    def denied(*a, **k):
        raise PermissionError("denied")

    monkeypatch.setattr(shutil, "disk_usage", denied)
    assert disk.free_bytes(tmp_path) is None  # 모르면 None → 경고·차단하지 않음
    monkeypatch.undo()
    (tmp_path / "a.bin").write_bytes(b"0" * 10)
    (tmp_path / "b.bin").write_bytes(b"0" * 5)
    real = os.path.getsize
    monkeypatch.setattr(os.path, "getsize", lambda p: denied() if p.endswith("a.bin") else real(p))
    assert disk.folder_bytes(tmp_path) == 5  # 읽을 수 없는 파일은 건너뜀


def test_usage_groups_skips_unreadable_entries(monkeypatch, tmp_path):
    (tmp_path / "cache_fluid").mkdir()
    (tmp_path / "cache_fluid" / "x.vdb").write_bytes(b"0" * 300)
    (tmp_path / "20261011-120000_render").mkdir()
    (tmp_path / "20261011-120000_render" / "f.png").write_bytes(b"0" * 50)
    real = disk.folder_bytes
    monkeypatch.setattr(disk, "folder_bytes", lambda p: (_ for _ in ()).throw(OSError("gone")) if "cache_" in str(p) else real(p))
    groups = {g[0]: g for g in disk.usage_groups(tmp_path)}
    assert "caches" not in groups and groups["runs"][1] == 50  # 사라진 폴더는 건너뛰고 나머지는 센다
