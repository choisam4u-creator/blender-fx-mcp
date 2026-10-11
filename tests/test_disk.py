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
    assert "2.0GB" in c["detail"] and "5.0GB" in c["detail"] and "clear_caches" in c["fix"]
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
    assert e.value.code == 0 and "[- ] output folder free space" in out and "(optional) Ask the AI to run clear_caches" in out


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
