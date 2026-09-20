"""끝까지 검증: 실제 MCP 클라이언트 → 이 서버(stdio) → 블렌더 수신기(소켓) → 이미지.

블렌더가 켜져 있고 수신기(N 패널 → BlenderMCP → 서버 시작)가 켜진 상태에서 실행한다.
  uv run python scripts/e2e_socket.py
"""

from __future__ import annotations

import asyncio
import os
import socket
import sys
import time
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

PROJECT = str(Path(__file__).resolve().parent.parent)
HOST = os.environ.get("BLENDER_FX_HOST", "localhost")
PORT = int(os.environ.get("BLENDER_FX_PORT", "9876"))

STEPS = [
    ("doctor", {}),
    ("ping_blender", {}),
    ("make_demo_building", {"floors": 3, "style": "windows", "ground": "asphalt"}),
    ("set_ground", {"material": "grass"}),
    ("camera", {"preset": "low"}),
    ("snapshot", {"name": "e2e_before"}),
    ("destroy", {"target": "Building", "pieces": 60, "frames": 48, "glue": "medium", "preview_frames": 3}),
    ("list_objects", {}),
    ("restore", {"name": "e2e_before"}),
    ("list_objects", {}),
    ("list_snapshots", {}),
]


def wait_port(timeout: float = 90.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with socket.create_connection((HOST, PORT), timeout=1.0):
                return True
        except OSError:
            time.sleep(1.0)
    return False


async def main() -> int:
    if not wait_port():
        print(f"수신기 포트({HOST}:{PORT})가 안 열립니다. 블렌더와 BlenderMCP 서버를 켜세요.")
        return 1
    params = StdioServerParameters(command="uv", args=["--directory", PROJECT, "run", "blender-fx-mcp"])
    failures = 0
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()
            tools = await s.list_tools()
            print("tools:", [t.name for t in tools.tools])
            for name, args in STEPS:
                t0 = time.time()
                res = await s.call_tool(name, args, read_timeout_seconds=600)
                texts = [c.text for c in res.content if getattr(c, "type", "") == "text"]
                images = [c for c in res.content if getattr(c, "type", "") == "image"]
                is_error = bool(getattr(res, "is_error", getattr(res, "isError", False)))
                bad = is_error or any(t.startswith("실패") for t in texts)
                failures += int(bad)
                print(f"== {name} ({time.time() - t0:.1f}s) {'실패' if bad else '성공'} | 이미지 {len(images)}장")
                for t in texts:
                    print("   ", t[:400])
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
