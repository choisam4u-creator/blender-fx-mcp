# 명령 → 레시피 파라미터 변환, 오류 메시지, 소켓 응답 처리 단위 테스트. 블렌더 없이 돈다.
import json
import socket
import threading

import pytest

from conftest import tool_text
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
    assert tool_text(server.list_snapshots()).startswith("No snapshots yet")


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


def test_bridge_trailing_data_after_object_is_ignored(receiver):
    """응답 객체 뒤에 군더더기(줄바꿈·다른 JSON)가 붙어도 첫 객체를 쓴다(전에는 연결이 닫힐 때까지 기다려 '빈 응답')."""
    receiver(json.dumps({"status": "success", "result": {"result": "ok"}}).encode() + b'\n{"x": 1}')
    assert bridge.run_python("x", timeout=5) == "ok"


@pytest.mark.parametrize("reply, words", [
    (b'{"status": "success", "res', ["cut off", "26 bytes"]),       # 응답 도중 끊김
    (b"[1, 2]", ["unexpected response"]),                            # JSON 객체가 아님
])
def test_bridge_truncated_or_odd_reply_is_explained(receiver, monkeypatch, reply, words):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    receiver(reply)
    with pytest.raises(BlenderError) as ei:
        bridge.send_command("execute_code", timeout=5)
    assert all(w in str(ei.value) for w in words), str(ei.value)


def test_bridge_reset_after_connect_is_not_install_advice(monkeypatch):
    """연결 뒤 끊김(블렌더가 굽다가 죽음)은 '연결할 수 없음·애드온 설치'가 아니라 끊김으로 알린다."""
    class Dropped:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def settimeout(self, v):
            pass

        def sendall(self, data):
            pass

        def recv(self, n):
            raise ConnectionResetError("reset by peer")

    monkeypatch.setattr(bridge.socket, "create_connection", lambda *a, **k: Dropped())
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    with pytest.raises(BlenderError) as ei:
        bridge.send_command("execute_code", timeout=5)
    msg = str(ei.value)
    assert "dropped during the command (ConnectionResetError)" in msg and "Install" not in msg and "restore" in msg


@pytest.mark.parametrize("name, value", [
    ("BLENDER_FX_TIMEOUT", "0"), ("BLENDER_FX_TIMEOUT", "-5"), ("BLENDER_FX_TIMEOUT", "ten"),
    ("BLENDER_FX_TIMEOUT", "nan"), ("BLENDER_FX_PORT", "abc"), ("BLENDER_FX_PORT", "70000"),
])
def test_bad_env_number_gives_one_clear_error(monkeypatch, name, value):
    """잘못된 숫자 환경변수는 모든 도구에서 같은 한 문장(고칠 곳)으로. 전에는 0 이면 '애드온 설치'로, 글자면 예외가 새어 나갔다."""
    monkeypatch.setenv(name, value)
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    monkeypatch.setattr(bridge.socket, "create_connection", lambda *a, **k: pytest.fail("연결하면 안 됨"))
    with pytest.raises(BlenderError) as ei:
        bridge.send_command("ping")
    assert f"{name}={value!r} is not valid" in str(ei.value)
    out = server.list_objects()  # 도구는 예외 대신 실패 문장
    assert out.startswith("Failed: ") and name in out
    assert bridge.port() in (bridge.DEFAULT_PORT,) or name != "BLENDER_FX_PORT"  # 화면 표시는 기본값으로 버팀
    assert bridge.default_timeout() == 600.0 or name != "BLENDER_FX_TIMEOUT"


def test_large_reply_is_fast(receiver):
    """수 MB 응답을 조각마다 처음부터 다시 풀지 않는다(전에는 20MB 에 5초)."""
    import time
    big = "x" * 8_000_000
    receiver(json.dumps({"status": "success", "result": {"result": big}}).encode(), chunks=200)
    start = time.monotonic()
    assert bridge.run_python("x", timeout=10) == big
    assert time.monotonic() - start < 3


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


def test_decode_waits_for_rest_of_multibyte_character():
    """여러 바이트 글자(한글 등)가 조각 경계에서 반쯤 오면 아직 덜 온 것으로 보고 기다린다."""
    whole = json.dumps({"status": "success", "result": {"result": "완료"}}, ensure_ascii=False).encode("utf-8")
    cut = whole.index("완".encode()) + 1  # 첫 글자 3바이트 중 1바이트까지만
    assert bridge._decode(whole[:cut]) is None
    assert bridge._decode(whole)["result"]["result"] == "완료"


# ---------- 미리보기 크기(set_render 를 따름) ----------

def _preview_size():
    """render.py 레시피의 preview_size 만 꺼내 블렌더 없이 부른다(레시피 파일은 bpy 를 앞에 붙여야 돈다)."""
    import ast

    src = (server.RECIPES / "render.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name == "preview_size")
            or (isinstance(n, ast.Assign) and n.targets[0].id == "PREVIEW_LONG_SIDE")]
    ns: dict = {}
    exec(compile(ast.Module(body=keep, type_ignores=[]), "render.py", "exec"), ns)
    return ns["preview_size"]


@pytest.mark.parametrize(("width", "height", "user_res", "expect"), [
    (0, 0, None, (640, 360)),  # 정한 적 없으면 예전과 같은 640×360
    (0, 0, (1920, 1080), (640, 360)),
    (0, 0, (1080, 1920), (360, 640)),  # 세로 영상: 긴 변 640, 비율 그대로
    (0, 0, (1000, 1000), (640, 640)),
    (0, 0, (2048, 858), (640, 268)),  # 시네마스코프
    (0, 0, (320, 180), (320, 180)),  # 640 보다 작으면 키우지 않음
    (800, 0, (1080, 1920), (800, 1422)),  # 하나만 주면 나머지는 비율로
    (0, 300, None, (533, 300)),
    (400, 300, (1080, 1920), (400, 300)),  # 둘 다 주면 그대로
])
def test_preview_size_follows_set_render(width, height, user_res, expect):
    assert _preview_size()(width, height, user_res) == expect


def test_render_preview_sends_no_size_unless_given(calls):
    """크기를 안 주면 레시피가 장면 크기로 정하도록 width/height 를 보내지 않는다(전에는 늘 640×360 을 보냄)."""
    server.render_preview(frames=[1])
    server.render_preview(frames=[1], width=320)
    (_, first), (_, second) = calls
    assert "width" not in first and "height" not in first, first
    assert second["width"] == 320 and "height" not in second, second
