# 출력 폴더 디스크 여유: doctor 의 선택 항목과 굽기 전 멈춤. 블렌더 없이 돈다.
import pytest

from blender_fx_mcp import bridge, disk, doctor, server


def test_free_bytes_walks_up_to_existing_folder(tmp_path):
    assert disk.free_bytes(tmp_path / "없는" / "폴더") == disk.free_bytes(tmp_path) > 0
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


def test_usage_groups(tmp_path):
    _fill(tmp_path, "cache_fluid", 3000)
    _fill(tmp_path, "cache_emit", 1000)
    _fill(tmp_path, "snapshots", 500)
    _fill(tmp_path, "20261011-101010_render_final", 2000)
    _fill(tmp_path, "20261011-101011_preview", 10)
    (tmp_path / "loose.png").write_bytes(b"0" * 5)
    assert disk.usage_groups(tmp_path) == [("caches", 4000, 2), ("runs", 2015, 3), ("snapshots", 500, 1)]
    assert disk.usage_groups(tmp_path / "없음") == []
    (tmp_path / "empty").mkdir()
    assert disk.usage_groups(tmp_path / "empty") == []


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_low_space_names_biggest_groups_and_their_tools(monkeypatch, tmp_path, lang):
    """여유가 5GB 아래면 큰 묶음(캐시·스냅샷·렌더 결과)과 크기, 그 묶음을 지우는 도구를 큰 것부터 짝지어 말한다."""
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    monkeypatch.setattr(disk, "free_bytes", lambda p: 2 * 1024**3)
    monkeypatch.setattr(doctor, "GROUP_MIN_BYTES", 1000)
    _fill(tmp_path, "snapshots", 5000)
    _fill(tmp_path, "cache_liquid", 9000)
    _fill(tmp_path, "20261011-101010_render_final", 3000)
    _fill(tmp_path, "20261011-101011_preview", 10)
    c = doctor._space_check(str(tmp_path))
    labels = (["구운 캐시(cache_*)", "스냅샷(snapshots)", "렌더·미리보기 결과"] if lang == "ko"
              else ["baked caches (cache_*)", "snapshots", "render and preview results"])
    pos = [c["detail"].index(label) for label in labels]
    assert pos == sorted(pos), c["detail"]  # 큰 것부터
    tools = [c["fix"].index(x) for x in ("clear_caches", "clear_snapshots", "(2")]
    assert tools == sorted(tools), c["fix"]  # 고칠 방법도 같은 순서, 렌더 결과는 폴더 수와 함께 손으로
    assert c["fix"].endswith("BLENDER_FX_OUT 을 여유 있는 디스크의 폴더로 지정" if lang == "ko"
                             else "point BLENDER_FX_OUT to a folder on a disk with more space")
    assert (f"최근 {server.SNAPSHOT_KEEP}개" if lang == "ko" else f"newest {server.SNAPSHOT_KEEP}") in c["fix"]
    monkeypatch.setattr(doctor, "GROUP_MIN_BYTES", 6000)  # 작은 묶음은 빼고 캐시만
    c = doctor._space_check(str(tmp_path))
    assert "clear_caches" in c["fix"] and "clear_snapshots" not in c["fix"] and "(2" not in c["fix"]


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
