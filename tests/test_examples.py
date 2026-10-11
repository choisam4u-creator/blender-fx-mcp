# examples/ 의 클라이언트 연결 설정이 읽히고, 실제 진입점·저장소 주소와 맞는지 점검. 블렌더 없이 돈다.
import json
import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples"
PACKAGE = "blender-fx-mcp"  # PyPI 이름(0.7.0 부터 PyPI 에 있음). git+ 주소는 미출시 main 을 시험할 때만


def _entry_points():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = re.search(r"^\[project\.scripts\]\n(.*?)(?=^\[)", text, re.S | re.M).group(1)
    return dict(re.findall(r'^([\w-]+) = "([^"]+)"$', block, re.M))


def _project_name():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^name = "([^"]+)"', text, re.M).group(1)


def _check_server(server):
    assert server["command"] == "uvx"
    args = server["args"]
    # uvx <패키지> 는 같은 이름의 진입점을 띄운다: PyPI 패키지 이름 = 서버 진입점
    assert args == [PACKAGE], args
    assert args[-1] in _entry_points() and _project_name() == PACKAGE
    assert server["env"]["BLENDER_FX_LANG"] in ("ko", "en")


@pytest.mark.parametrize("name", ["claude_desktop_config.json", "cursor-mcp.json"])
def test_json_examples(name):
    data = json.loads((EX / name).read_text(encoding="utf-8"))
    assert list(data) == ["mcpServers"]
    _check_server(data["mcpServers"]["blender-fx"])


def test_codex_example():
    data = tomllib.loads((EX / "codex-config.toml").read_text(encoding="utf-8"))
    server = data["mcp_servers"]["blender_fx"]
    _check_server(server)
    # 굽기·렌더 도구는 최소 1800초(render_video 3600초)를 기다린다. 클라이언트가 먼저 끊으면 안 된다
    assert server["tool_timeout_sec"] >= 3600


def test_has_english_example():
    langs = {json.loads((EX / n).read_text(encoding="utf-8"))["mcpServers"]["blender-fx"]["env"]["BLENDER_FX_LANG"]
             for n in ("claude_desktop_config.json", "cursor-mcp.json")}
    assert "en" in langs


def test_examples_readme_links_every_file_and_is_linked_from_readme():
    index = (EX / "README.md").read_text(encoding="utf-8")
    files = sorted(p.name for p in EX.iterdir() if p.is_file() and p.name != "README.md")  # __pycache__ 등 폴더는 뺌
    assert files, "examples/ 가 비었음"
    for name in files:
        assert f"]({name})" in index, f"examples/README.md 에 {name} 링크가 없음"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.count("](examples/)") >= 2, "README 한국어·영어 설치 절 모두 examples/ 로 이어져야 함"


def _load_list_tools():
    import importlib.util

    spec = importlib.util.spec_from_file_location("list_tools_example", EX / "list_tools.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("lang, prefix", [("ko", "실패: "), ("en", "Failed: ")])
def test_list_tools_example_runs_without_blender(monkeypatch, lang, prefix):
    """예제가 서버를 stdio 로 띄워 서버와 같은 도구 목록을 받고, 블렌더가 없으면 ping 이 실패 문장을 돌려주는지."""
    import asyncio
    import socket

    from blender_fx_mcp import server

    with socket.socket() as s:  # 아무도 듣지 않는 포트
        s.bind(("localhost", 0))
        port = s.getsockname()[1]
    monkeypatch.setenv("BLENDER_FX_PORT", str(port))
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    example = _load_list_tools()
    names, ping = asyncio.run(example.run(example.server_params([])))
    assert names == [t.name for t in asyncio.run(server.mcp.list_tools())]
    assert "ping_blender" in names
    assert ping.startswith(prefix) and f"localhost:{port}" in ping


def test_list_tools_example_is_documented():
    readme = (EX / "README.md").read_text(encoding="utf-8")
    assert "[`list_tools.py`](list_tools.py)" in readme
    assert "uv run python examples/list_tools.py" in readme
    assert "uv run python examples/list_tools.py" in (EX / "list_tools.py").read_text(encoding="utf-8")


# ---- first_render.py: 터미널에서 첫 렌더까지 ----

def _load(name):
    import importlib.util

    spec = importlib.util.spec_from_file_location(f"{name}_example", EX / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _results(lines, lang):
    """진행 줄([i/n] … 기다리는 중)을 빼고, 결과 줄의 '(걸린 초)' 를 지워 비교하기 쉽게 한다."""
    import re
    wait = "(기다리는 중)" if lang == "ko" else "(waiting)"
    out = []
    for x in lines:
        if re.fullmatch(rf"\[\d+/5\] \w+ … {re.escape(wait)}", x):
            continue
        out.append(re.sub(r"^(\w+) \(\d+\.\ds\): ", r"\1: ", x))
    return out


def _closed_port():
    import socket

    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


@pytest.mark.parametrize("lang, prefix, nxt", [("ko", "ping_blender: 실패: ", "다음 할 일: "), ("en", "ping_blender: Failed: ", "Next: ")])
def test_first_render_without_blender_exits_2_with_next_steps(monkeypatch, capsys, lang, prefix, nxt):
    """블렌더가 없으면 연결 실패 문장(원인별 다음 한 단계)과 다음 할 일을 출력하고 종료 코드 2. 다른 도구는 부르지 않는다."""
    import asyncio

    port = _closed_port()
    monkeypatch.setenv("BLENDER_FX_PORT", str(port))
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    example = _load("first_render")
    code = asyncio.run(example.run(example.server_params([])))
    out = _results(capsys.readouterr().out.splitlines(), lang)
    assert code == 2
    assert out[0].startswith(prefix) and f"localhost:{port}" in out[0] and "Connect to MCP server" in out[0]
    assert out[1].startswith(nxt) and "blender-fx-doctor" in out[1] and len(out) == 2


def test_first_render_steps_are_valid_server_calls():
    """예제가 부르는 도구·인자가 실제 서버에 있고, 서버의 값 검사를 통과한다(예제가 그대로 돈다)."""
    import inspect

    from blender_fx_mcp import server

    example = _load("first_render")
    for name, args in example.STEPS:
        params = inspect.signature(getattr(server, name)).parameters
        assert set(args) <= set(params), (name, set(args) - set(params))
        recipe = {"make_demo_building": "demo_scene", "render_preview": "render"}.get(name, name)
        server.check_choices(recipe, args)
        server.check_ranges(recipe, args)
    assert [n for n, _ in example.STEPS] == ["snapshot", "make_demo_building", "destroy", "render_preview"]
    # 스냅샷 이름이 서버에서 바뀌지 않아야 안내한 restore 이름이 맞다
    import re
    assert re.sub(r"[^\w\-]+", "_", example.BEFORE)[:40] == example.BEFORE
    # destroy 대상 = make_demo_building 이 만드는 기본 이름
    assert example.STEPS[2][1]["target"] == inspect.signature(server.make_demo_building).parameters["name"].default


FAKE_SERVER = '''
import sys
from mcp.server.mcpserver import MCPServer
mcp = MCPServer("fake")
FOLDER, FAIL = sys.argv[1], sys.argv[2]
calls = []

@mcp.tool()
def ping_blender() -> str:
    return "Connected (localhost:9876, Blender 5.2.0 LTS)"

@mcp.tool()
def snapshot(name: str) -> str:
    return "Failed: disk full. Free some space." if FAIL == "snapshot" else f"Snapshot saved: {name}"

@mcp.tool()
def make_demo_building() -> str:
    return "Created 'Building'"

@mcp.tool()
def destroy(target: str, impact: str, material: str, pieces: int) -> str:
    return "Failed: pieces is too big. Try 50-400." if FAIL == "destroy" else f"{target}: {pieces} pieces"

@mcp.tool()
def render_preview(frame_count: int) -> str:
    return f"Render (BLENDER_EEVEE, 640×360): frames [1, 36, 72] → {FOLDER} (Fast preview: sky is not shown.)"

mcp.run()
'''


@pytest.mark.parametrize("fail, code", [("", 0), ("destroy", 1), ("snapshot", 1)])
def test_first_render_success_and_tool_failure(monkeypatch, capsys, tmp_path, fail, code):
    """가짜 서버로 성공 갈래(PNG 경로 출력)와 도구 실패 갈래(오류 문장 출력, 종료 코드 1, 렌더 안 부름)를 확인한다."""
    import asyncio
    import re
    import sys

    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    folder = tmp_path / "출력 폴더"  # 한글·공백 경로도 그대로
    folder.mkdir()
    for n in ("frame_0072.png", "frame_0001.png", "notes.txt"):
        (folder / n).write_bytes(b"x")
    script = tmp_path / "fake_server.py"
    script.write_text(FAKE_SERVER, encoding="utf-8")
    example = _load("first_render")
    got = asyncio.run(example.run(example.server_params([sys.executable, str(script), str(folder), fail])))
    raw = capsys.readouterr().out.splitlines()
    out = _results(raw, "en")
    assert got == code
    undo = "To go back: ask your AI to 'restore first_render_before' or pick /undo_last."
    assert out[1] == "snapshot: Snapshot saved: first_render_before" or fail == "snapshot"
    if fail == "snapshot":
        # 저장에 실패하면 장면을 건드리기 전에 멈춘다(되돌릴 곳이 없으니 되돌리기 안내도 없다)
        assert out[-1].startswith("snapshot: Failed: ") and len(out) == 2
    elif fail:
        assert out[-2:] == ["destroy: Failed: pieces is too big. Try 50-400.", undo]
        assert not any(x.startswith("render_preview") for x in out)
    else:
        assert out[-4:] == ["2 PNG files:", f"  {folder / 'frame_0001.png'}", f"  {folder / 'frame_0072.png'}", undo]
        # 단계마다 부르기 전에 진행 줄, 끝나면 걸린 초가 붙은 결과 줄
        names = ["ping_blender"] + [n for n, _ in example.STEPS]
        assert [x for x in raw if x.startswith("[")] == [f"[{i}/5] {n} … (waiting)" for i, n in enumerate(names, 1)]
        for n in names:
            i = raw.index(next(x for x in raw if x.startswith("[") and f"] {n} " in x))
            assert re.match(rf"{n} \(\d+\.\ds\): ", raw[i + 1]), raw[i + 1]


def test_first_render_is_documented():
    readme = (EX / "README.md").read_text(encoding="utf-8")
    assert "[`first_render.py`](first_render.py)" in readme
    assert "uv run python examples/first_render.py" in readme
    assert "uv run python examples/first_render.py" in (EX / "first_render.py").read_text(encoding="utf-8")


def test_first_render_progress_line_is_bilingual(monkeypatch):
    example = _load("first_render")
    monkeypatch.setenv("BLENDER_FX_LANG", "ko")
    assert example.progress(3, "destroy") == "[3/5] destroy … (기다리는 중)"
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    assert example.progress(3, "destroy") == "[3/5] destroy … (waiting)"


def test_readme_points_to_first_render_in_both_languages():
    """README 한/영 설치 절에서 first_render.py 를 찾을 수 있고, 명령이 예제 docstring 의 명령과 같다."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    doc = (EX / "first_render.py").read_text(encoding="utf-8")
    cmd = "uv run python examples/first_render.py"
    assert cmd in doc
    ko, en = readme.split("\n## English", 1)
    assert f"\n{cmd}   #" in ko.split("## 매일 쓰는 순서")[0]
    assert f"\nBLENDER_FX_LANG=en {cmd}   #" in en.split("### First command")[0]
    assert sum(cmd in x for x in readme.splitlines()) == 2
    # README 가 거는 examples/README.md 앵커가 실제 제목에서 나온다(GitHub 규칙: 소문자, 문장부호 빼기, 빈칸 → -)
    import re
    titles = re.findall(r"^#{1,6} (.+)$", (EX / "README.md").read_text(encoding="utf-8"), re.M)
    anchors = {re.sub(r"[^\w\- ]", "", x.strip().lower()).replace(" ", "-") for x in titles}
    linked = set(re.findall(r"\(examples/README\.md#([^)]+)\)", readme))
    assert linked and linked <= anchors, linked - anchors


USER_FACING = ["README.md", "docs/troubleshooting.md", "examples/README.md", "examples/first_render.py",
               "examples/list_tools.py", ".github/ISSUE_TEMPLATE/bug_report.yml",
               "src/blender_fx_mcp/doctor.py", "src/blender_fx_mcp/server.py"]


@pytest.mark.parametrize("name", USER_FACING)
def test_install_commands_use_pypi(name):
    """사용자가 따라 칠 명령은 PyPI 패키지로(git 이 없어도 되고 짧다). git+ 주소는 troubleshooting 의 '미출시 main 시험' 한 곳만."""
    text = (ROOT / name).read_text(encoding="utf-8")
    entry = _entry_points()
    cmds = re.findall(r"uvx(?: --from ([^\s`\"]+))? (blender-fx[\w-]*)", text)
    assert cmds or name == "examples/list_tools.py", f"{name}: uvx 명령을 못 찾음"
    for source, prog in cmds:
        assert prog in entry or prog == PACKAGE, f"{name}: 없는 진입점 {prog}"
        if source.startswith("git+"):
            assert name == "docs/troubleshooting.md", f"{name}: 설치 명령이 git+ 주소 → uvx {PACKAGE}"
        else:
            assert source in ("", PACKAGE), f"{name}: --from {source}"
    if name == "docs/troubleshooting.md":
        assert text.count("git+https://") == 2 and "## Still on the old version" in text  # 한/영 한 번씩


# ---- first_render.py 를 진짜 서버 + 가짜 블렌더 수신기(소켓)로 끝까지 ----

# 1×1 투명 PNG. 서버가 미리보기 이미지를 읽어 MCP 응답에 싣는다
PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")


def _fake_receiver(port_holder, calls, fail="", slow=None):
    """blender-mcp 애드온과 같은 규약(JSON 한 덩어리 요청 → JSON 응답)으로 답하는 수신기.
    execute_code 의 코드가 어느 레시피인지 레시피 파일 본문으로 알아내고, 그 레시피가 내는 FX_RESULT 를 흉내 낸다.
    render 는 PARAMS 의 out_dir 에 실제 PNG 를 만든다(예제가 그 경로를 출력하는지 보려고)."""
    import ast
    import json
    import socket
    import threading

    recipes = {p.stem: p.read_text(encoding="utf-8") for p in (ROOT / "src" / "blender_fx_mcp" / "recipes").glob("*.py")
               if not p.stem.startswith("_")}
    # 도구가 문장을 만들 때 읽는 키(레시피 실제 출력의 부분 집합)
    common = dict(ok=True, target="Building", size_m=[8, 8, 12], floors=4, style="windows", windows=24, ground="asphalt",
                  volume_m3=700.0, closed=True, pieces=80, pattern="voronoi", focus=0.5, material="concrete", impact="left",
                  frames=72, total_mass_kg=1200, glue="medium", glue_constraints=150, dust="on", moved_ratio=0.8,
                  max_fall_m=9.5, volume_kept=0.99, open_chunks=0, size_bytes=1_200_000, objects=3,
                  snapshots=["first_render_before"], path="/fake/fx_scene.blend", note="")

    def answer(req):
        if req["type"] == "ping":
            return {"pong": True}
        code = req["params"]["code"]
        if "bpy.app.version_string" in code and "PARAMS" not in code:
            return {"result": "5.2.0 LTS\n"}
        name = next(n for n, body in recipes.items() if code.rstrip().endswith(body.rstrip()))
        params = ast.literal_eval(code.splitlines()[0].split("=", 1)[1].strip())
        calls.append(name)
        if slow and name in slow:  # 굽기·저장처럼 오래 걸리는 레시피 흉내
            import time
            time.sleep(slow[name])
        if name == fail:  # 레시피가 블렌더 안에서 실패하면 emit_result(ok=False, error=…) 를 낸다
            return {"result": "FX_RESULT " + json.dumps({"ok": False, "error": "pieces is too big. Try 50-400."}) + "\n"}
        res = dict(common)
        if name == "render":
            out = Path(params["out_dir"])
            out.mkdir(parents=True, exist_ok=True)
            res.update(engine="BLENDER_EEVEE", size=[640, 360], frames=[1, 36, 72], paths=[])
            for f in res["frames"]:
                p = out / f"frame_{f:04d}.png"
                p.write_bytes(PNG)
                res["paths"].append(str(p))
        return {"result": "FX_RESULT " + json.dumps(res, ensure_ascii=False) + "\n"}

    srv = socket.socket()
    srv.bind(("localhost", 0))
    srv.listen()
    port_holder.append(srv.getsockname()[1])

    def serve():
        while True:
            try:
                conn, _ = srv.accept()
            except OSError:
                return
            with conn:
                buf = b""
                while True:
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    buf += chunk
                    try:
                        req = json.loads(buf.decode("utf-8"))
                        break
                    except ValueError:
                        continue
                else:
                    continue
                try:
                    resp = {"status": "success", "result": answer(req)}
                except Exception as e:  # 시험이 모르는 레시피면 블렌더 오류처럼 돌려 실패가 보이게
                    resp = {"status": "error", "message": f"fake receiver: {e!r}"}
                conn.sendall(json.dumps(resp).encode("utf-8"))

    threading.Thread(target=serve, daemon=True).start()
    return srv


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_first_render_end_to_end_with_fake_receiver(monkeypatch, capsys, tmp_path, lang):
    """README 의 첫 렌더 명령이 그대로 돈다: 진짜 서버(stdio) → 가짜 수신기(소켓). 5단계 진행 줄, 종료 코드 0,
    서버가 출력 폴더에 만든 PNG 경로, 되돌리는 방법. 레시피는 스냅샷 → 건물(+미리보기 렌더) → 붕괴(+렌더) → 렌더 순."""
    import asyncio
    import re

    port, calls = [], []
    srv = _fake_receiver(port, calls)
    try:
        monkeypatch.setenv("BLENDER_FX_PORT", str(port[0]))
        monkeypatch.setenv("BLENDER_FX_LANG", lang)
        monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path / "out"))
        example = _load("first_render")
        code = asyncio.run(example.run(example.server_params([])))
    finally:
        srv.close()
    raw = capsys.readouterr().out.splitlines()
    assert code == 0, "\n".join(raw)
    wait = "(기다리는 중)" if lang == "ko" else "(waiting)"
    names = ["ping_blender", "snapshot", "make_demo_building", "destroy", "render_preview"]
    assert [x for x in raw if x.startswith("[")] == [f"[{i}/5] {n} … {wait}" for i, n in enumerate(names, 1)]
    out = _results(raw, lang)
    assert out[0].startswith("ping_blender: " + ("연결됨" if lang == "ko" else "Connected")) and "5.2.0 LTS" in out[0]
    assert calls == ["snapshot", "demo_scene", "render", "destroy", "render", "render"]
    # 마지막 render_preview 의 출력 폴더(서버가 BLENDER_FX_OUT 아래 만든 날짜 폴더)의 PNG 3개
    head = "PNG 3개:" if lang == "ko" else "3 PNG files:"
    i = out.index(head)
    pngs = [x.strip() for x in out[i + 1:i + 4]]
    assert all(Path(p).is_file() and Path(p).parent.parent == tmp_path / "out" for p in pngs), pngs
    assert [Path(p).name for p in pngs] == ["frame_0001.png", "frame_0036.png", "frame_0072.png"]
    assert re.fullmatch(r"\d{8}-\d{6}_render_preview", Path(pngs[0]).parent.name), pngs[0]
    assert out[-1] == example.undo_line() and "first_render_before" in out[-1]


def test_first_render_recipe_failure_with_fake_receiver(monkeypatch, capsys, tmp_path):
    """블렌더 안에서 붕괴가 실패하면 서버의 오류 문장을 그대로 보이고, 렌더는 부르지 않고, 되돌리는 방법과 종료 코드 1."""
    import asyncio

    port, calls = [], []
    srv = _fake_receiver(port, calls, fail="destroy")
    try:
        monkeypatch.setenv("BLENDER_FX_PORT", str(port[0]))
        monkeypatch.setenv("BLENDER_FX_LANG", "en")
        monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path / "out"))
        example = _load("first_render")
        code = asyncio.run(example.run(example.server_params([])))
    finally:
        srv.close()
    out = _results(capsys.readouterr().out.splitlines(), "en")
    assert code == 1
    assert calls == ["snapshot", "demo_scene", "render", "destroy"]
    assert out[-2] == "destroy: Failed: pieces is too big. Try 50-400." and out[-1] == example.undo_line()


@pytest.mark.parametrize("lang, label", [("ko", "장면 저장 중 — "), ("en", "Saving the scene — ")])
def test_progress_notifications_over_real_stdio_server(monkeypatch, tmp_path, lang, label):
    """배포 형태 그대로(서버를 stdio 하위 프로세스로) 긴 도구의 진행 알림이 공식 클라이언트의 progress_callback 까지 오는지.
    작업 스레드 → 이벤트 루프 → stdio 경로를 메모리 연결 시험과 따로 확인한다."""
    import asyncio

    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    port, calls = [], []
    srv = _fake_receiver(port, calls, slow={"save_blend": 1.5})
    seen = []

    async def on_progress(progress, total, message):
        seen.append((progress, message))

    async def go():
        params = _load("list_tools").server_params([])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool("save_blend", {"name": "fx_scene"}, progress_callback=on_progress)

    try:
        monkeypatch.setenv("BLENDER_FX_PORT", str(port[0]))
        monkeypatch.setenv("BLENDER_FX_LANG", lang)
        monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path / "out"))
        monkeypatch.setenv("BLENDER_FX_PROGRESS_EVERY", "0.2")
        result = asyncio.run(go())
    finally:
        srv.close()
    assert not result.is_error, result
    assert calls == ["save_blend"]
    assert len(seen) >= 2, seen
    assert all(m.startswith(label) for _, m in seen), seen
    assert [p for p, _ in seen] == sorted(p for p, _ in seen)
