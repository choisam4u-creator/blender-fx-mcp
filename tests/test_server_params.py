# 명령 → 레시피 파라미터 변환, 오류 메시지, 소켓 응답 처리 단위 테스트. 블렌더 없이 돈다.
import json
import socket
import threading

import pytest

from blender_fx_mcp import bridge, server
from blender_fx_mcp.bridge import BlenderError


@pytest.fixture
def calls(monkeypatch, tmp_path):
    """run_recipe 를 가로채 (레시피, 파라미터)를 기록하고 실패 결과를 돌려준다."""
    seen = []
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.delenv("BLENDER_FX_LANG", raising=False)

    def fake_run_python(code, timeout=None):
        first = code.split("\n", 1)[0]
        params = eval(first[len("PARAMS = "):])  # build_code 가 repr 로 넣은 dict
        body = code.split("\n", 1)[1]
        recipe = next(n for n in server.RECIPES.glob("*.py")
                      if n.stem != "_common" and body.endswith(n.read_text(encoding="utf-8") + "\n"))
        seen.append((recipe.stem, params))
        return 'FX_RESULT {"ok": false, "error": "멈춤"}'

    monkeypatch.setattr(server.bridge, "run_python", fake_run_python)
    return seen


# ---------- run_recipe ----------

def test_run_recipe_drops_none_and_sets_lang(calls):
    with pytest.raises(BlenderError):
        server.run_recipe("list_objects", {"a": None, "b": 0, "c": False})
    _, params = calls[0]
    assert params == {"b": 0, "c": False, "_lang": "ko"}


def test_run_recipe_error_includes_traceback(monkeypatch):
    monkeypatch.setattr(server.bridge, "run_python",
                        lambda code, timeout=None: 'FX_RESULT ' + json.dumps(
                            {"ok": False, "error": "대상 없음", "traceback": "Traceback: X"}))
    with pytest.raises(BlenderError) as e:
        server.run_recipe("list_objects", {})
    assert str(e.value) == "대상 없음\nTraceback: X"


def test_run_recipe_error_without_reason(monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    monkeypatch.setattr(server.bridge, "run_python", lambda code, timeout=None: 'FX_RESULT {"ok": false}')
    with pytest.raises(BlenderError, match="no reason given"):
        server.run_recipe("list_objects", {})


def test_parse_result_empty_output_message(monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    with pytest.raises(BlenderError, match=r"\(empty\)"):
        server.parse_result("   \n")


def test_build_code_unknown_recipe():
    with pytest.raises(FileNotFoundError):
        server.build_code("no_such_recipe", {})


# ---------- 도구 → 파라미터 변환 ----------

def test_destroy_sentinels_become_preset(calls):
    out = server.destroy("Building")
    assert out.startswith("실패: 멈춤")
    recipe, p = calls[0]
    assert recipe == "destroy"
    # density 0, friction/bounce 음수는 "프리셋 그대로" → 아예 보내지 않는다
    assert "density" not in p and "friction" not in p and "bounce" not in p
    assert p["target"] == "Building" and p["pieces"] == 120 and p["repair"] is True


def test_destroy_overrides_are_sent(calls):
    server.destroy("B", density=900.0, friction=0.0, bounce=0.2)
    _, p = calls[0]
    assert p["density"] == 900.0 and p["friction"] == 0.0 and p["bounce"] == 0.2


def test_explode_with_target_fractures_first(calls):
    server.explode(target="Tower", burst_frame=1)
    recipe, p = calls[0]
    assert recipe == "destroy"
    assert p["impact"] == "none" and p["hold_until"] == 1  # burst_frame-1 이 0 이 되지 않게
    assert p["pattern"] == "radial"


def test_explode_without_target_skips_destroy(calls, tmp_path):
    server.explode(at=[0.0, 0.0, 1.0])
    recipe, p = calls[0]
    assert recipe == "explode"
    assert "target" not in p and p["at"] == [0.0, 0.0, 1.0]
    assert p["cache_dir"] == str(tmp_path / "cache_fluid")


def test_set_render_zero_means_unchanged(calls):
    server.set_render()
    recipe, p = calls[0]
    assert recipe == "set_render"
    for k in ("samples", "width", "height", "fps", "view_transform", "look", "motion_blur"):
        assert k not in p


def test_inspect_mesh_decimate_zero_dropped(calls):
    server.inspect_mesh("M")
    assert calls[0] == ("inspect_mesh", {"target": "M", "_lang": "ko"})


def test_snapshot_name_is_sanitized(calls, tmp_path):
    server.snapshot("../나쁜 이름/x")
    _, p = calls[0]
    path = p["path"]
    assert path.startswith(str(tmp_path / "snapshots")) and path.endswith(".blend")
    assert "/" not in path[len(str(tmp_path / "snapshots")) + 1:]


def test_restore_reports_auto_save_failure(calls):
    out = server.restore("before")
    # 자동 저장(snapshot) 시도 후 restore 시도, 둘 다 실패 → restore 실패만 보고
    assert [c[0] for c in calls] == ["snapshot", "restore"]
    assert out.startswith("실패:")


def test_list_snapshots_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    assert server.list_snapshots().startswith("No snapshots yet")


def test_new_run_dir_label_is_safe(monkeypatch, tmp_path):
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    d = server.new_run_dir("a/b c" + "x" * 100)
    assert d.parent == tmp_path and "/" not in d.name and d.is_dir()


# ---------- 소켓 응답 처리 ----------

def _serve_once(reply: bytes, chunks: int = 1):
    """한 번만 응답하는 가짜 수신기. reply 를 chunks 조각으로 나눠 보낸다."""
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)

    def run():
        conn, _ = srv.accept()
        with conn:
            conn.recv(65536)
            step = max(1, len(reply) // chunks)
            for i in range(0, len(reply), step):
                conn.sendall(reply[i:i + step])
        srv.close()

    threading.Thread(target=run, daemon=True).start()
    return srv.getsockname()[1]


@pytest.fixture
def receiver(monkeypatch):
    def start(reply: bytes, chunks: int = 1):
        monkeypatch.setenv("BLENDER_FX_HOST", "127.0.0.1")
        monkeypatch.setenv("BLENDER_FX_PORT", str(_serve_once(reply, chunks)))
    return start


def test_bridge_success_split_response(receiver):
    receiver(json.dumps({"status": "success", "result": {"result": "FX_RESULT {}"}}).encode(), chunks=4)
    assert bridge.run_python("x", timeout=5) == "FX_RESULT {}"


def test_bridge_error_status(receiver, monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    receiver(json.dumps({"status": "error", "message": "boom"}).encode())
    with pytest.raises(BlenderError, match="Blender error: boom"):
        bridge.send_command("execute_code", timeout=5)


def test_bridge_empty_response(receiver):
    receiver(b"")
    with pytest.raises(BlenderError, match="빈 응답"):
        bridge.send_command("ping", timeout=5)


def test_bridge_ping_false_without_pong(receiver):
    receiver(json.dumps({"status": "success", "result": {}}).encode())
    assert bridge.ping() is False
