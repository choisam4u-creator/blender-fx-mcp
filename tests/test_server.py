# 서버 쪽 단위 테스트. 블렌더 없이 돈다.
import asyncio

import pytest

from blender_fx_mcp import bridge
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
    monkeypatch.setenv("BLENDER_FX_PORT", "1")  # 수신기 없음 → 연결 항목만 실패해야 한다
    checks = run_checks()
    by_name = {c["name"]: c for c in checks}
    assert by_name["python"]["ok"] and by_name["mcp 라이브러리"]["ok"]
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
    monkeypatch.setenv("BLENDER_FX_PORT", "1")
    with pytest.raises(BlenderError, match="연결할 수 없습니다"):
        bridge.run_python("print(1)", timeout=2)
