# 긴 도구(굽기·렌더) 동안 MCP 진행 알림이 가는지, 공식 클라이언트(메모리 연결)로 확인한다. 블렌더 없이 돈다.
import json
import time

import anyio
import pytest
from mcp import Client

from blender_fx_mcp import bridge, server


def _slow_receiver(seconds):
    def run_python(code, timeout=None):
        time.sleep(seconds)
        res = dict(ok=True, path="/x/fx_scene.blend", size_bytes=1_000_000, note="")
        return "FX_RESULT " + json.dumps(res)
    return run_python


async def _call(name, args, with_progress):
    seen = []

    async def on_progress(progress, total, message):
        seen.append((progress, total, message))

    async with Client(server.mcp) as client:
        result = await client.call_tool(name, args, progress_callback=on_progress if with_progress else None)
    return result, seen


@pytest.mark.parametrize("lang, word", [("ko", "블렌더에서 작업 중"), ("en", "working in Blender")])
def test_long_tool_sends_progress(monkeypatch, tmp_path, lang, word):
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    monkeypatch.setattr(server, "PROGRESS_EVERY", 0.05)
    monkeypatch.setattr(bridge, "run_python", _slow_receiver(0.4))
    result, seen = anyio.run(_call, "save_blend", {"name": "fx_scene"}, True)
    assert not result.is_error, result
    assert len(seen) >= 3, seen
    assert all(word in m and m.startswith("save_blend") for _, _, m in seen)
    assert [p for p, _, _ in seen] == sorted(p for p, _, _ in seen)  # 걸린 초는 줄지 않는다


def test_no_progress_without_token_or_for_quick_tools(monkeypatch, tmp_path):
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setattr(server, "PROGRESS_EVERY", 0.05)
    monkeypatch.setattr(bridge, "run_python", _slow_receiver(0.2))
    result, seen = anyio.run(_call, "save_blend", {"name": "a"}, False)  # progressToken 없음 → 조용
    assert not result.is_error and seen == []

    def quick(code, timeout=None):
        time.sleep(0.2)
        return "FX_RESULT " + json.dumps(dict(ok=True, objects=[]))

    monkeypatch.setattr(bridge, "run_python", quick)
    result, seen = anyio.run(_call, "list_objects", {}, True)  # 짧은 도구(timeout 없음)는 알림 없음
    assert not result.is_error and seen == []


def test_progress_thread_stops_and_outside_mcp_is_noop(monkeypatch, tmp_path):
    import threading

    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setattr(server, "PROGRESS_EVERY", 0.05)
    monkeypatch.setattr(bridge, "run_python", _slow_receiver(0.2))
    anyio.run(_call, "save_blend", {"name": "b"}, True)
    assert not [th for th in threading.enumerate() if th.name == "blender-fx-progress"]
    with server._progress("x"):  # MCP 호출 밖(스크립트·시험)에서는 아무 일도 없음
        pass
    assert "저장 완료" in server.save_blend("c") or "Saved" in server.save_blend("c")
