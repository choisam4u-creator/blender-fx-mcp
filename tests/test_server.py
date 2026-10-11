# 서버 쪽 단위 테스트. 블렌더 없이 돈다.
import asyncio

import pytest

from blender_fx_mcp import __version__, bridge, server
from blender_fx_mcp.bridge import BlenderError
from blender_fx_mcp.server import build_code, mcp, parse_result


def test_tools_registered():
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert {
        "ping_blender", "list_objects", "make_demo_building", "destroy", "explode", "splash",
        "render_preview", "render_video", "save_blend", "reset_destroy", "doctor",
        "import_model", "export_model", "camera", "camera_shake", "set_look", "set_timing", "clear_caches",
        "fire", "smoke", "particles", "wind", "ocean", "cloth_flag",
        "snapshot", "restore", "list_snapshots", "set_ground",
        "water", "inspect_mesh", "set_physics", "set_render",
    } <= names



def _annotations():
    return {t.name: t.annotations for t in asyncio.run(mcp.list_tools())}


def test_every_tool_has_annotations():
    for name, a in _annotations().items():
        assert a is not None, f"{name}: annotations 없음"
        # 셋 다 직접 정해야 한다(빠지면 클라이언트가 기본값 destructive=True 로 본다)
        assert None not in (a.read_only_hint, a.destructive_hint, a.idempotent_hint), name
        assert a.open_world_hint is False, name
        assert not (a.read_only_hint and a.destructive_hint), name


@pytest.mark.parametrize("name", ["restore", "clear_caches", "reset_destroy", "export_model", "snapshot", "clear_snapshots"])
def test_hard_to_undo_tools_are_destructive(name):
    a = _annotations()[name]
    assert a.destructive_hint is True and a.read_only_hint is False


@pytest.mark.parametrize("name", ["doctor", "ping_blender", "list_objects", "inspect_mesh", "list_snapshots"])
def test_query_tools_are_read_only(name):
    assert _annotations()[name].read_only_hint is True


def test_annotations_reach_the_wire():
    # MCP 로 나갈 때 camelCase 키(readOnlyHint 등)로 바뀌는지
    tool = next(t for t in asyncio.run(mcp.list_tools()) if t.name == "restore")
    wire = tool.model_dump(by_alias=True, exclude_none=True)["annotations"]
    assert wire["destructiveHint"] is True and wire["readOnlyHint"] is False

def test_language_switch(monkeypatch):
    from blender_fx_mcp.i18n import t
    monkeypatch.delenv("BLENDER_FX_LANG", raising=False)
    assert t("한국어", "English") == "한국어"
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    assert t("한국어", "English") == "English"
    monkeypatch.setenv("BLENDER_FX_LANG", "en-US")
    assert t("한국어", "English") == "English"


def test_recipe_params_carry_language(monkeypatch):
    from blender_fx_mcp import server
    seen = {}
    monkeypatch.setenv("BLENDER_FX_LANG", "en")

    def fake(code, timeout=None):
        seen["code"] = code
        return 'FX_RESULT {"ok": true}'

    monkeypatch.setattr(server.bridge, "run_python", fake)
    server.run_recipe("list_objects", {})
    assert "'_lang': 'en'" in seen["code"]


def test_english_failure_message(monkeypatch):
    from blender_fx_mcp import server
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    monkeypatch.setenv("BLENDER_FX_PORT", "1")
    out = server.ping_blender()
    assert out.startswith("Failed:") and "Cannot connect to Blender" in out


def test_doctor_runs_without_blender(monkeypatch):
    from blender_fx_mcp.doctor import format_report, run_checks
    monkeypatch.setenv("BLENDER_FX_LANG", "ko")  # 한국어 기대값: 셸·다른 시험의 en 에 기대지 않는다
    monkeypatch.setenv("BLENDER_FX_PORT", "1")  # 수신기 없음 → 연결 항목만 실패해야 한다
    checks = run_checks()
    by_name = {c["name"]: c for c in checks}
    assert by_name["python"]["ok"] and by_name["mcp 라이브러리"]["ok"]
    assert by_name["blender-fx-mcp"]["detail"] == __version__
    assert by_name["수신기 연결"]["ok"] is False
    assert "확인 필요" in format_report(checks)


def test_build_code_prepends_params():
    code = build_code("destroy", {"target": "X", "pieces": 3})
    assert code.startswith("PARAMS = {'target': 'X', 'pieces': 3}\n")
    assert "def main()" in code and "run_guarded(main)" in code


def test_parse_result_takes_last_line():
    out = 'junk\nFX_RESULT {"ok": true, "a": 1}\nmore\nFX_RESULT {"ok": true, "a": 2}\n'
    assert parse_result(out)["a"] == 2


def test_parse_result_missing():
    with pytest.raises(BlenderError, match="FX_RESULT"):
        parse_result("nothing here")


def test_bridge_connection_refused(monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "ko")
    monkeypatch.setenv("BLENDER_FX_PORT", "1")
    with pytest.raises(BlenderError, match="연결할 수 없습니다"):
        bridge.run_python("print(1)", timeout=2)


# ---- 블렌더 판 ----

@pytest.mark.parametrize("lang", ["ko", "en"])
@pytest.mark.parametrize("version,warns", [("5.2.0 LTS", False), ("5.2", False), ("4.2.3 LTS", True), ("5.3.0 Alpha", True)])
def test_ping_blender_shows_version_and_warns_off_support(monkeypatch, lang, version, warns):
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    monkeypatch.setattr(bridge, "ping", lambda: True)
    monkeypatch.setattr(bridge, "run_python", lambda code, timeout=None: f"noise\n{version}\n")
    out = server.ping_blender()
    assert out.startswith("연결됨 (" if lang == "ko" else "Connected (") and f"Blender {version})" in out, out
    assert (bridge.SUPPORTED_BLENDER + " LTS" in out) is warns, out


def test_ping_blender_without_version_still_connected(monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    monkeypatch.setattr(bridge, "ping", lambda: True)

    def no(code, timeout=None):
        raise BlenderError("Blender error: execute_code is off")

    monkeypatch.setattr(bridge, "run_python", no)
    assert server.ping_blender() == f"Connected ({bridge.host()}:{bridge.port()})"


def test_doctor_connection_line_has_version(monkeypatch, tmp_path):
    from blender_fx_mcp import doctor
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setattr(bridge, "ping", lambda: True)
    monkeypatch.setattr(bridge, "run_python", lambda code, timeout=None: "4.2.3 LTS\n")
    conn = next(c for c in doctor.run_checks() if c["id"] == "connection")
    assert conn["ok"] and "Blender 4.2.3 LTS" in conn["detail"] and "not a tested version" in conn["detail"]


def test_supported_blender_matches_support_md():
    import re
    from pathlib import Path
    support = (Path(__file__).resolve().parents[1] / "SUPPORT.md").read_text(encoding="utf-8")
    supported = re.search(r"^\| 블렌더 / Blender \| ([\d.]+) LTS \| 지원", support, re.M).group(1)
    assert bridge.SUPPORTED_BLENDER == supported


class _Stdin:
    def __init__(self, tty):
        self.tty = tty

    def isatty(self):
        return self.tty


@pytest.mark.parametrize("lang,head", [("ko", "멈춘 것이 아닙니다"), ("en", "It is not frozen")])
def test_terminal_launch_prints_hint_to_stderr(monkeypatch, capsys, lang, head):
    # 터미널에서 서버 명령을 직접 치면 아무 출력 없이 멈춘 듯 보인다 → stderr 로 등록·점검·끝내기 안내(stdout 은 MCP 전용)
    import sys
    from blender_fx_mcp.doctor import SERVER_CMD
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    monkeypatch.setattr(sys, "stdin", _Stdin(True))
    ran = []
    monkeypatch.setattr(server.mcp, "run", lambda *a, **k: ran.append(1))
    server.main()
    out, err = capsys.readouterr()
    assert ran == [1] and out == ""
    assert head in err and "claude mcp add -s user blender-fx" in err and SERVER_CMD in err
    assert "blender-fx-doctor" in err and "Ctrl+C" in err


def test_client_launch_prints_nothing(monkeypatch, capsys):
    import sys
    monkeypatch.setattr(sys, "stdin", _Stdin(False))
    monkeypatch.setattr(server.mcp, "run", lambda *a, **k: None)
    server.main()
    assert capsys.readouterr() == ("", "")


def test_piped_server_stays_quiet():
    # 실제 프로세스: 클라이언트처럼 파이프로 띄우면(입력 즉시 끝) 안내 없이 끝나야 한다
    import subprocess
    import sys
    p = subprocess.run([sys.executable, "-m", "blender_fx_mcp.server"], input=b"", capture_output=True, timeout=60)
    assert "Ctrl+C" not in p.stderr.decode("utf-8", "replace")
    assert p.stdout == b""
