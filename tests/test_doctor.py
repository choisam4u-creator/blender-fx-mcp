# doctor.py 의 실패 갈래 시험. 사용자가 가장 먼저 돌리는 명령이라 실패 안내가 깨지지 않게 한다. 블렌더 없이 돈다.
import json
import stat
import sys
from pathlib import Path

import pytest

from blender_fx_mcp import __version__, bridge, doctor

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="가짜 블렌더가 /bin/sh 스크립트")


@pytest.fixture
def env(monkeypatch, tmp_path):
    """집 폴더·출력 폴더를 tmp 로, 수신기는 응답하는 것으로, 블렌더는 없는 것으로 시작한다."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path / "out"))
    monkeypatch.setenv("BLENDER_FX_LANG", "ko")
    monkeypatch.setattr(bridge, "ping", lambda: None)
    monkeypatch.setattr(doctor, "find_blender", lambda: None)
    return tmp_path


def _by_name(checks):
    return {c["name"]: c for c in checks}


def _fake_blender(tmp_path: Path, body: str) -> str:
    exe = tmp_path / "blender"
    exe.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
    return str(exe)


def test_order_and_version_first(env):
    names = [c["name"] for c in doctor.run_checks()]
    assert names[:2] == ["python", "blender-fx-mcp"]
    assert names[-1] == "출력 폴더"


@posix_only
def test_blender_version_line(env, monkeypatch):
    exe = _fake_blender(env, 'echo "Blender 5.2.0 LTS"\necho "build date"')
    monkeypatch.setattr(doctor, "find_blender", lambda: exe)
    c = _by_name(doctor.run_checks())["블렌더 실행 파일"]
    assert c["ok"] and c["detail"] == f"{exe} — Blender 5.2.0 LTS"


@posix_only
def test_blender_prints_nothing(env, monkeypatch):
    exe = _fake_blender(env, "exit 0")
    monkeypatch.setattr(doctor, "find_blender", lambda: exe)
    assert _by_name(doctor.run_checks())["블렌더 실행 파일"]["detail"].endswith("버전 출력 없음")


def test_blender_fails_to_run(env, monkeypatch):
    missing = str(env / "지워진-blender")
    monkeypatch.setattr(doctor, "find_blender", lambda: missing)
    c = _by_name(doctor.run_checks())["블렌더 실행 파일"]
    assert c["ok"]  # 경로는 찾았으니 OK, 대신 실행 실패를 적는다
    assert c["detail"].startswith(missing) and "실행 실패" in c["detail"]


@posix_only
def test_blender_hangs_is_reported(env, monkeypatch):
    exe = _fake_blender(env, "sleep 5")
    monkeypatch.setattr(doctor, "find_blender", lambda: exe)
    real_run = doctor.subprocess.run
    monkeypatch.setattr(doctor.subprocess, "run", lambda *a, **k: real_run(*a, **{**k, "timeout": 0.3}))
    assert "실행 실패" in _by_name(doctor.run_checks())["블렌더 실행 파일"]["detail"]


def test_blender_missing_tells_env_var(env, monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    c = _by_name(doctor.run_checks())["Blender executable"]
    assert not c["ok"] and "BLENDER_FX_BLENDER" in c["detail"]


def test_addon_missing_and_found(env):
    name = "수신기 애드온 파일(blender-mcp)"
    c = _by_name(doctor.run_checks())[name]
    assert not c["ok"] and "ahujasid/blender-mcp" in c["detail"]

    addon = env / "home" / ".config" / "blender" / "5.2" / "scripts" / "addons" / "blender_mcp.py"
    addon.parent.mkdir(parents=True)
    addon.write_text("")
    c = _by_name(doctor.run_checks())[name]
    assert c["ok"] and c["detail"] == str(addon)


def test_receiver_down_shows_bridge_message(env, monkeypatch):
    def down():
        raise bridge.BlenderError("연결할 수 없습니다(가짜)")
    monkeypatch.setattr(bridge, "ping", down)
    c = _by_name(doctor.run_checks())["수신기 연결"]
    assert not c["ok"] and c["detail"] == "연결할 수 없습니다(가짜)"


def test_receiver_up(env, monkeypatch):
    monkeypatch.setenv("BLENDER_FX_PORT", "9999")
    c = _by_name(doctor.run_checks())["수신기 연결"]
    assert c["ok"] and c["detail"].endswith(":9999 응답함")


def test_output_folder_not_writable(env, monkeypatch):
    blocker = env / "파일"
    blocker.write_text("폴더가 아님")
    monkeypatch.setenv("BLENDER_FX_OUT", str(blocker / "out"))
    c = _by_name(doctor.run_checks())["출력 폴더"]
    assert not c["ok"] and c["detail"].startswith(f"{blocker / 'out'} 에 쓸 수 없음")


def test_output_folder_ok_leaves_no_test_file(env):
    c = _by_name(doctor.run_checks())["출력 폴더"]
    assert c["ok"] and list(Path(c["detail"]).iterdir()) == []


def test_uv_missing(env, monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda _: None)
    c = _by_name(doctor.run_checks())["uv"]
    assert not c["ok"] and "brew install uv" in c["detail"]


def test_mcp_missing(env, monkeypatch):
    def gone(_):
        raise doctor.metadata.PackageNotFoundError("mcp")
    monkeypatch.setattr(doctor.metadata, "version", gone)
    c = _by_name(doctor.run_checks())["mcp 라이브러리"]
    assert not c["ok"] and c["detail"].startswith("설치 안 됨")


# ---- 보고서와 종료 코드 ----

def test_report_all_ok_and_attention_line(env, monkeypatch):
    ok = [doctor._check("a", True, "x")]
    assert doctor.format_report(ok).splitlines() == ["[OK] a: x", "모두 정상입니다."]
    bad = ok + [doctor._check("b", False, "y")]
    lines = doctor.format_report(bad).splitlines()
    assert lines[1] == "[X ] b: y"
    assert lines[-1].startswith("확인 필요: b. 해결법: ") and bridge.TROUBLESHOOTING_URL in lines[-1]


@pytest.mark.parametrize("failing,code", [
    (None, 0),               # 모두 정상
    ("connection", 0),       # 블렌더를 안 켠 것은 치명적이지 않다
    ("blender", 0),
    ("python", 1),
    ("mcp", 1),
])
@pytest.mark.parametrize("lang", ["ko", "en"])
def test_main_exit_code(monkeypatch, capsys, failing, code, lang):
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    names = {"python": "python", "mcp": "mcp 라이브러리" if lang == "ko" else "mcp library",
             "connection": "수신기 연결", "blender": "블렌더 실행 파일"}
    checks = [doctor._check(n, key != failing, "d", key) for key, n in names.items()]
    monkeypatch.setattr(doctor, "run_checks", lambda: checks)
    with pytest.raises(SystemExit) as e:
        doctor.main([])
    assert e.value.code == code
    assert "[OK] python: d" in capsys.readouterr().out or failing == "python"


# ---- --json ----

def _fake_checks(monkeypatch, tmp_path, lang):
    """실제 run_checks 를 블렌더·수신기 없이 돌린다(블렌더 못 찾음, 연결 실패)."""
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setattr(doctor, "find_blender", lambda: None)
    monkeypatch.setattr(doctor, "ADDON_GLOBS", [])

    def refused():
        raise bridge.BlenderError("refused")

    monkeypatch.setattr(bridge, "ping", refused)


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_json_matches_text_report(monkeypatch, capsys, tmp_path, lang):
    """--json 과 줄 출력이 같은 항목·같은 결과여야 하고, id 는 언어와 상관없이 같아야 한다."""
    _fake_checks(monkeypatch, tmp_path, lang)
    with pytest.raises(SystemExit) as e:
        doctor.main([])
    text_code, text = e.value.code, capsys.readouterr().out.splitlines()
    with pytest.raises(SystemExit) as e:
        doctor.main(["--json"])
    assert e.value.code == text_code
    data = json.loads(capsys.readouterr().out)
    rows = text[:-1]
    assert len(data["checks"]) == len(rows)
    for c, row in zip(data["checks"], rows):
        assert row == f"[{'OK' if c['ok'] else 'X '}] {c['name']}: {c['detail']}"
    assert [c["id"] for c in data["checks"]] == [
        "python", "blender-fx-mcp", "mcp", "uv", "blender", "addon", "connection", "output"]
    assert data["failed"] == [c["id"] for c in data["checks"] if not c["ok"]]
    assert {"blender", "addon", "connection"} <= set(data["failed"])
    assert data["ok"] is False and data["help"] == bridge.TROUBLESHOOTING_URL and data["help"] in text[-1]
    assert data["lang"] == lang and data["blender"] is None
    assert data["blender_fx_mcp"] == __version__
    assert (data["host"], data["port"]) == (bridge.host(), bridge.port())


def test_json_all_ok_has_no_help(monkeypatch, capsys):
    monkeypatch.setattr(doctor, "run_checks", lambda: [doctor._check("python", True, "3.11", "python")])
    monkeypatch.setattr(doctor, "find_blender", lambda: "/opt/blender/blender")
    with pytest.raises(SystemExit) as e:
        doctor.main(["--json"])
    data = json.loads(capsys.readouterr().out)
    assert e.value.code == 0
    assert data["ok"] is True and data["failed"] == [] and data["help"] is None
    assert data["blender"] == "/opt/blender/blender"


def test_unknown_option_is_rejected(capsys):
    with pytest.raises(SystemExit) as e:
        doctor.main(["--jsn"])
    assert e.value.code == 2 and "--jsn" in capsys.readouterr().err
