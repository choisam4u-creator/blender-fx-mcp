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
