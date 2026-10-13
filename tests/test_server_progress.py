# 긴 도구(굽기·렌더) 동안 MCP 진행 알림이 가는지, 공식 클라이언트(메모리 연결)로 확인한다. 블렌더 없이 돈다.
import json
import time

import anyio
import pytest
from mcp import Client

from blender_fx_mcp import bridge, server


def _slow_receiver(seconds, until=None):
    """seconds 만큼 일하는 척하는 수신기. until(진행 알림 목록, 개수)을 주면 알림이 그만큼 올 때까지(최대 10초) 더 기다린다.
    느린 CI 러너(macOS)에서는 0.05초 간격 알림이 0.4초 안에 2개만 오기도 해 고정 시간으로는 개수를 장담할 수 없다."""
    def run_python(code, timeout=None):
        time.sleep(seconds)
        if until:
            seen, n = until
            deadline = time.monotonic() + 10
            while len(seen) < n and time.monotonic() < deadline:
                time.sleep(0.01)
        res = dict(ok=True, path="/x/fx_scene.blend", size_bytes=1_000_000, note="")
        return "FX_RESULT " + json.dumps(res)
    return run_python


async def _call(name, args, with_progress, seen=None):
    seen = [] if seen is None else seen

    async def on_progress(progress, total, message):
        seen.append((progress, total, message))

    async with Client(server.mcp) as client:
        result = await client.call_tool(name, args, progress_callback=on_progress if with_progress else None)
    return result, seen


@pytest.mark.parametrize("lang, word", [("ko", "장면 저장 중 — "), ("en", "Saving the scene — ")])
def test_long_tool_sends_progress(monkeypatch, tmp_path, lang, word):
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    monkeypatch.setattr(server, "PROGRESS_EVERY", 0.05)
    seen = []
    monkeypatch.setattr(bridge, "run_python", _slow_receiver(0.4, until=(seen, 3)))
    result, _ = anyio.run(_call, "save_blend", {"name": "fx_scene"}, True, seen)
    assert not result.is_error, result
    assert len(seen) >= 3, seen
    assert all(m.startswith(word) and "save_blend" not in m for _, _, m in seen)  # 내부 레시피 이름 대신 사람 말
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


def test_every_recipe_has_a_progress_label(monkeypatch):
    """레시피 파일마다 진행 알림용 사람 말(한/영)이 있어야 한다. 새 레시피가 내부 이름으로 보이지 않게."""
    import re

    recipes = {p.stem for p in (server.RECIPES).glob("*.py") if not p.stem.startswith("_")}
    monkeypatch.setenv("BLENDER_FX_LANG", "ko")
    ko = server.recipe_labels()
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    en = server.recipe_labels()
    assert recipes == set(ko) == set(en), recipes ^ set(ko)
    for name in recipes:
        assert re.search(r"[가-힣]", ko[name]) and not re.search(r"[가-힣]", en[name]), name
        assert name not in (ko[name], en[name]) and "_" not in ko[name] + en[name], f"{name}: 내부 이름이 그대로"
    assert server.recipe_label("없는_레시피") == "없는_레시피"


@pytest.mark.parametrize("raw, want", [(None, 5.0), ("", 5.0), ("2", 2.0), ("0", 0.05), ("-1", 0.05), ("x", 5.0), ("nan", 5.0)])
def test_progress_every_env(raw, want):
    assert server.progress_every(raw) == want


def test_progress_thread_stops_when_notification_fails(monkeypatch, tmp_path):
    """클라이언트가 끊겨 알림이 실패해도 도구는 끝까지 돌고, 알림 스레드는 그만둔다."""
    import threading

    class BrokenCtx:
        async def report_progress(self, *a, **k):
            raise RuntimeError("client gone")

    monkeypatch.setattr(server, "PROGRESS_EVERY", 0.05)

    async def run():
        token = server._CALL.set((BrokenCtx(), anyio.lowlevel.current_token()))
        try:
            def work():
                with server._progress("x"):
                    time.sleep(0.3)
                return "done"
            return await anyio.to_thread.run_sync(work)
        finally:
            server._CALL.reset(token)

    assert anyio.run(run) == "done"
    assert not [th for th in threading.enumerate() if th.name == "blender-fx-progress"]
