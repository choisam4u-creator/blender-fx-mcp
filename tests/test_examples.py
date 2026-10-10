# examples/ 의 클라이언트 연결 설정이 읽히고, 실제 진입점·저장소 주소와 맞는지 점검. 블렌더 없이 돈다.
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples"
REPO = "git+https://github.com/choisam4u-creator/blender-fx-mcp"


def _entry_points():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = re.search(r"^\[project\.scripts\]\n(.*?)(?=^\[)", text, re.S | re.M).group(1)
    return dict(re.findall(r'^([\w-]+) = "([^"]+)"$', block, re.M))


def _check_server(server):
    assert server["command"] == "uvx"
    args = server["args"]
    assert args[:2] == ["--from", REPO]
    assert args[-1] in _entry_points() and args[-1] == "blender-fx-mcp"
    assert server["env"]["BLENDER_FX_LANG"] in ("ko", "en")


@pytest.mark.parametrize("name", ["claude_desktop_config.json", "cursor-mcp.json"])
def test_json_examples(name):
    data = json.loads((EX / name).read_text(encoding="utf-8"))
    assert list(data) == ["mcpServers"]
    _check_server(data["mcpServers"]["blender-fx"])


def test_codex_example():
    tomllib = pytest.importorskip("tomllib")  # 3.11+
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
    out = capsys.readouterr().out.splitlines()
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
    assert [n for n, _ in example.STEPS] == ["make_demo_building", "destroy", "render_preview"]
    # destroy 대상 = make_demo_building 이 만드는 기본 이름
    assert example.STEPS[1][1]["target"] == inspect.signature(server.make_demo_building).parameters["name"].default


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


@pytest.mark.parametrize("fail, code", [("", 0), ("destroy", 1)])
def test_first_render_success_and_tool_failure(monkeypatch, capsys, tmp_path, fail, code):
    """가짜 서버로 성공 갈래(PNG 경로 출력)와 도구 실패 갈래(오류 문장 출력, 종료 코드 1, 렌더 안 부름)를 확인한다."""
    import asyncio
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
    out = capsys.readouterr().out.splitlines()
    assert got == code
    if fail:
        assert out[-1].startswith("destroy: Failed: ") and not any(x.startswith("render_preview") for x in out)
    else:
        assert out[-3:] == ["2 PNG files:", f"  {folder / 'frame_0001.png'}", f"  {folder / 'frame_0072.png'}"]


def test_first_render_is_documented():
    readme = (EX / "README.md").read_text(encoding="utf-8")
    assert "[`first_render.py`](first_render.py)" in readme
    assert "uv run python examples/first_render.py" in readme
    assert "uv run python examples/first_render.py" in (EX / "first_render.py").read_text(encoding="utf-8")
