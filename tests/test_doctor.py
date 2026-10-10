# doctor.py 의 실패 갈래 시험. 사용자가 가장 먼저 돌리는 명령이라 실패 안내가 깨지지 않게 한다. 블렌더 없이 돈다.
import json
from pathlib import Path

import pytest

from blender_fx_mcp import __version__, bridge, doctor

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


def test_order_and_version_first(env):
    names = [c["name"] for c in doctor.run_checks()]
    assert names[:2] == ["python", "blender-fx-mcp"]
    assert names[-1] == "출력 폴더"


def test_blender_version_line(env, monkeypatch, fake_blender):
    exe = fake_blender('print("Blender 5.2.0 LTS")\nprint("build date")')
    monkeypatch.setattr(doctor, "find_blender", lambda: exe)
    c = _by_name(doctor.run_checks())["블렌더 실행 파일"]
    assert c["ok"] and c["detail"] == f"{exe} — Blender 5.2.0 LTS"


def test_blender_prints_nothing(env, monkeypatch, fake_blender):
    exe = fake_blender("sys.exit(0)")
    monkeypatch.setattr(doctor, "find_blender", lambda: exe)
    assert _by_name(doctor.run_checks())["블렌더 실행 파일"]["detail"].endswith("버전 출력 없음")


def test_blender_fails_to_run(env, monkeypatch):
    missing = str(env / "지워진-blender")
    monkeypatch.setattr(doctor, "find_blender", lambda: missing)
    c = _by_name(doctor.run_checks())["블렌더 실행 파일"]
    assert c["ok"]  # 경로는 찾았으니 OK, 대신 실행 실패를 적는다
    assert c["detail"].startswith(missing) and "실행 실패" in c["detail"]


def test_blender_hangs_is_reported(env, monkeypatch, fake_blender):
    exe = fake_blender("import time\ntime.sleep(2)")
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
    blocker.write_text("폴더가 아님", encoding="utf-8")
    monkeypatch.setenv("BLENDER_FX_OUT", str(blocker / "out"))
    c = _by_name(doctor.run_checks())["출력 폴더"]
    assert not c["ok"] and c["detail"].startswith(f"{blocker / 'out'} 에 쓸 수 없음")


def test_output_folder_ok_leaves_no_test_file(env):
    c = _by_name(doctor.run_checks())["출력 폴더"]
    assert c["ok"] and list(Path(c["detail"]).iterdir()) == []


@pytest.mark.parametrize("plat,cmd", [
    ("darwin", "brew install uv"),
    ("linux", "curl -LsSf https://astral.sh/uv/install.sh | sh"),
    ("win32", "irm https://astral.sh/uv/install.ps1 | iex"),
])
def test_uv_missing_gives_install_command_for_this_os(env, monkeypatch, plat, cmd):
    monkeypatch.setattr(doctor.shutil, "which", lambda _: None)
    monkeypatch.setattr(doctor.sys, "platform", plat)
    c = _by_name(doctor.run_checks())["uv"]
    assert not c["ok"] and cmd in c["detail"] and cmd in c["fix"]


def test_blender_missing_is_optional_not_attention(env):
    """블렌더 실행 파일은 헤드리스 시험에만 필요하다. 못 찾아도 X 가 아니라 `-` 이고, 다음 할 일에 들어가지 않는다."""
    checks = doctor.run_checks()
    c = _by_name(checks)["블렌더 실행 파일"]
    assert not c["ok"] and c["optional"] and "필요 없음" in c["detail"]
    report = doctor.format_report(checks)
    assert f"[- ] 블렌더 실행 파일: {c['detail']}" in report.splitlines()
    assert "블렌더 실행 파일" not in report.splitlines()[-4]  # 확인 필요 줄


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_report_numbers_next_steps_in_install_order(env, monkeypatch, lang):
    """실패한 필수 항목마다 다음 할 일을 설치 순서대로 번호를 매겨 보여 준다(문서를 한 번 더 열지 않게)."""
    import re
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    monkeypatch.setattr(doctor.shutil, "which", lambda _: None)

    def refused():
        raise bridge.BlenderError("refused")
    monkeypatch.setattr(bridge, "ping", refused)
    checks = doctor.run_checks()
    lines = doctor.format_report(checks).splitlines()
    head = lines.index(next(x for x in lines if x.startswith(("확인 필요:", "Needs attention:"))))
    steps = lines[head + 1:-1]
    assert [s.split(".", 1)[0].strip() for s in steps] == ["1", "2", "3"]
    assert "uv" in steps[0] and "addon.py" in steps[1] and "Connect to MCP server" in steps[2]
    assert "Install from Disk" in steps[1]
    assert lines[-1].endswith(bridge.TROUBLESHOOTING_URL)
    if lang == "en":
        assert not re.search(r"[가-힣]", "\n".join(lines[head:])), lines[head:]


def test_connect_step_mentions_port_only_when_changed(env, monkeypatch):
    def refused():
        raise bridge.BlenderError("refused")
    monkeypatch.setattr(bridge, "ping", refused)
    assert "BLENDER_FX_PORT" not in _by_name(doctor.run_checks())["수신기 연결"]["fix"]
    monkeypatch.setenv("BLENDER_FX_PORT", "9999")
    fix = _by_name(doctor.run_checks())["수신기 연결"]["fix"]
    assert "BLENDER_FX_PORT" in fix and "9999" in fix


def test_fix_is_empty_when_ok(env):
    for c in doctor.run_checks():
        if c["ok"]:
            assert c["fix"] == "", c
        elif not c["optional"]:
            assert c["fix"], f"{c['id']}: 실패했는데 다음 할 일이 없음"


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
    assert lines[2:] == ["확인 필요: b. 다음 할 일:", "  1. y", f"해결법: {bridge.TROUBLESHOOTING_URL}"]
    with_fix = ok + [doctor._check("b", False, "y", fix="고치는 법")]
    assert doctor.format_report(with_fix).splitlines()[3] == "  1. 고치는 법"


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
    monkeypatch.setattr(bridge, "ADDON_GLOBS", [])

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
    rows = text[:len(data["checks"])]
    for c, row in zip(data["checks"], rows):
        assert row == f"[{doctor.mark(c)}] {c['name']}: {c['detail']}"
    assert [c["id"] for c in data["checks"]] == [
        "python", "blender-fx-mcp", "mcp", "uv", "blender", "addon", "connection", "output"]
    assert data["failed"] == [c["id"] for c in data["checks"] if not c["ok"] and not c["optional"]]
    assert {"addon", "connection"} <= set(data["failed"]) and "blender" not in data["failed"]
    assert next(c for c in data["checks"] if c["id"] == "blender")["optional"] is True
    assert all(c["fix"] for c in data["checks"] if c["id"] in data["failed"])
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


# ---- README 준비 단계 = doctor 순서 ----

def _setup_steps(section: str):
    """README 절에서 `<!-- setup-steps: … -->` 표지 뒤 번호 목록의 `[OK] 이름` 들을 차례로 모은다."""
    import re
    m = re.search(r"<!-- setup-steps: ([\w, ]+) -->\n(.*?)\n\n", section, re.S)
    assert m, "README 준비 단계 표지(<!-- setup-steps: … -->)가 없음"
    ids = [x.strip() for x in m.group(1).split(",")]
    oks = re.findall(r"→ `\[OK\] ([^`]+)`", m.group(2))
    return ids, oks


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_readme_setup_steps_follow_doctor_order(env, monkeypatch, lang):
    """첫 화면의 준비 단계가 doctor 필수 항목(uv → 애드온 → 연결) 순서와 같고, 단계마다 doctor 의 줄 이름을 그대로 쓴다."""
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    ko, en = readme.split("\n## English\n", 1)
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    checks = doctor.run_checks()
    ids, oks = _setup_steps(ko if lang == "ko" else en)
    required = [c["id"] for c in checks if not c["optional"] and c["id"] in ids]
    assert ids == required, f"README 단계 {ids} ≠ doctor 순서 {required}"
    names = {c["id"]: c["name"] for c in checks}
    assert oks == [names[i] for i in ids], f"{lang}: README 의 [OK] 이름 {oks} ≠ doctor {[names[i] for i in ids]}"
    # 순서 시험이 doctor 의 '다음 할 일' 번호와도 맞는지: 모두 실패하면 이 순서로 번호가 매겨진다
    order = [c["id"] for c in doctor.failed([dict(c, ok=False) for c in checks])]
    assert [i for i in order if i in ids] == ids
