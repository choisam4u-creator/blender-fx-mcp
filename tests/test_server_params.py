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


@pytest.mark.parametrize("env,expect_destroy,expect_video", [
    (None, 1800.0, 3600.0),          # 기본값(600)은 굽기 도구의 하한보다 작다
    ("2400", 2400.0, 3600.0),        # 늘리면 굽기 도구도 따라간다
    ("7200", 7200.0, 7200.0),
])
def test_long_tools_honor_timeout_env(monkeypatch, tmp_path, env, expect_destroy, expect_video):
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    if env is None:
        monkeypatch.delenv("BLENDER_FX_TIMEOUT", raising=False)
    else:
        monkeypatch.setenv("BLENDER_FX_TIMEOUT", env)
    seen = []

    def fake_run_python(code, timeout=None):
        seen.append(timeout)
        return 'FX_RESULT {"ok": false, "error": "stop"}'

    monkeypatch.setattr(server.bridge, "run_python", fake_run_python)
    server.destroy(target="Building")
    server.render_video()
    assert seen == [expect_destroy, expect_video]


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


def test_restore_reports_auto_save_failure(calls, tmp_path):
    (tmp_path / "snapshots").mkdir(exist_ok=True)
    (tmp_path / "snapshots" / "before.blend").write_bytes(b"x")
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


def test_bridge_empty_response(receiver, monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "ko")
    receiver(b"")
    with pytest.raises(BlenderError, match="빈 응답"):
        bridge.send_command("ping", timeout=5)


@pytest.mark.parametrize("lang, words", [("ko", ["2초", "BLENDER_FX_TIMEOUT"]), ("en", ["2 s", "BLENDER_FX_TIMEOUT"])])
def test_bridge_timeout_names_seconds_and_env(monkeypatch, lang, words):
    """연결은 되는데 답이 없으면, 기다린 초와 늘리는 방법(BLENDER_FX_TIMEOUT)을 알려 준다."""
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)  # 받아만 두고 답하지 않는다
    monkeypatch.setenv("BLENDER_FX_HOST", "127.0.0.1")
    monkeypatch.setenv("BLENDER_FX_PORT", str(srv.getsockname()[1]))
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    try:
        with pytest.raises(BlenderError) as ei:
            bridge.send_command("execute_code", timeout=1.6)
    finally:
        srv.close()
    for w in words:
        assert w in str(ei.value)


def test_bridge_connect_timeout_is_connection_error(monkeypatch):
    """연결 자체가 시간 초과면(닿지 않는 주소) BLENDER_FX_TIMEOUT 이 아니라 연결 안내를 낸다."""
    def no_route(*a, **k):
        raise socket.timeout("timed out")
    monkeypatch.setattr(bridge.socket, "create_connection", no_route)
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    with pytest.raises(BlenderError) as ei:
        bridge.send_command("ping", timeout=600)
    msg = str(ei.value)
    assert "Cannot connect to Blender" in msg and "BLENDER_FX_TIMEOUT" not in msg and "600" not in msg


def test_bridge_ping_false_without_pong(receiver):
    receiver(json.dumps({"status": "success", "result": {}}).encode())
    assert bridge.ping() is False


# ---- headless: 블렌더 앱과 bpy 파이썬 구분 ----

def test_blender_command_app_vs_bpy_python():
    from blender_fx_mcp.headless import blender_command, is_bpy_python

    assert not is_bpy_python("/Applications/Blender.app/Contents/MacOS/Blender")
    assert is_bpy_python("/opt/venv/bin/python3.11")
    assert blender_command("/usr/bin/blender", "s.py") == [
        "/usr/bin/blender", "--background", "--factory-startup", "--python", "s.py"]
    assert blender_command("/opt/venv/bin/python", "s.py") == ["/opt/venv/bin/python", "s.py"]


def test_exit_reason_names_signals():
    from blender_fx_mcp.headless import _exit_reason

    assert _exit_reason(0) == "0"
    assert "세그폴트" in _exit_reason(-11)
    assert "SIGABRT" in _exit_reason(-6)
    assert "시그널" in _exit_reason(-15)


def test_run_steps_error_names_stuck_step(monkeypatch, tmp_path):
    """블렌더가 중간에 죽으면 어느 단계에서 멈췄는지와 종료 이유를 알려 준다."""
    import subprocess

    from blender_fx_mcp import headless

    fake = subprocess.CompletedProcess([], -11, stdout='FX_RESULT {"ok": true}\n', stderr="")
    monkeypatch.setattr(headless.subprocess, "run", lambda *a, **k: fake)
    with pytest.raises(RuntimeError) as e:
        headless.run_steps([("demo_scene", {}), ("destroy", {"target": "Building"})], blender="/usr/bin/blender")
    msg = str(e.value)
    assert "2번째 단계 'destroy'" in msg and "세그폴트" in msg
