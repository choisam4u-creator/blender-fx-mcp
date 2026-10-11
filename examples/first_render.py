# SPDX-License-Identifier: MIT
"""블렌더 창 없이 터미널에서 첫 렌더까지: 서버를 공식 `mcp` 파이썬 클라이언트로 띄워
ping_blender → make_demo_building → destroy → render_preview 를 차례로 부르고 미리보기 PNG 경로를 출력한다.
From the terminal to a first render: start the server with the official `mcp` Python client, call
ping_blender → make_demo_building → destroy → render_preview in order and print the preview PNG paths.

    uv run python examples/first_render.py                  # 이 저장소의 서버 / the server in this checkout
    uv run python examples/first_render.py uvx --from git+https://github.com/choisam4u-creator/blender-fx-mcp blender-fx-mcp

블렌더를 켜고 BlenderMCP 탭에서 Connect 를 눌러 둔 뒤 돌린다. 연결이 안 되면 다음 할 일을 출력하고 종료 코드 2.
Open Blender and click Connect in the BlenderMCP tab first. If it cannot connect, it prints the next steps and exits with code 2.
도구가 실패하면 그 오류 문장(무엇을 바꾸면 되는지 들어 있음)을 출력하고 종료 코드 1. 장면에 'Building' 이 하나 더해진다.
If a tool fails it prints the error (which says what to change) and exits with code 1. It adds a 'Building' to the scene.
시작 전에 지금 장면을 스냅샷 first_render_before 로 저장하고, 끝에 되돌리는 방법을 출력한다.
The current scene is saved first as snapshot first_render_before, and the way back is printed at the end.
단계마다 `[2/5] make_demo_building …` 진행 줄과 걸린 초를 출력한다(붕괴·렌더는 수십 초 걸릴 수 있음).
Each step prints a `[2/5] make_demo_building …` progress line and the seconds it took (collapse and render can take tens of seconds).
"""

import asyncio
import os
import sys
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

FAILED = ("실패: ", "Failed: ")  # 서버 도구가 실패하면 돌려주는 문장 머리
BEFORE = "first_render_before"
STEPS = [
    ("snapshot", {"name": BEFORE}),  # 사용자가 하던 장면을 먼저 저장(실패하면 아무것도 바꾸지 않고 멈춘다)
    ("make_demo_building", {}),
    ("destroy", {"target": "Building", "impact": "left", "material": "concrete", "pieces": 80}),
    ("render_preview", {"frame_count": 3}),
]


def en() -> bool:
    return os.environ.get("BLENDER_FX_LANG", "ko").strip().lower().startswith("en")


def server_params(argv: list[str]) -> StdioServerParameters:
    # 인자가 없으면 지금 파이썬으로 이 저장소의 서버 모듈을 띄운다. 있으면 그 명령을 그대로 쓴다(list_tools.py 와 같음).
    command, *args = argv or [sys.executable, "-m", "blender_fx_mcp.server"]
    return StdioServerParameters(command=command, args=args, env=dict(os.environ))


def text_of(result) -> str:
    return "".join(c.text for c in result.content if c.type == "text")


def undo_line() -> str:
    return (f"원래 장면으로: AI 에게 'restore {BEFORE}' 라고 하거나 /undo_last 를 고르세요." if not en() else
            f"To go back: ask your AI to 'restore {BEFORE}' or pick /undo_last.")


def png_paths(render_text: str) -> list[str]:
    """render_preview 문장의 '→ <폴더>' 에서 PNG 를 찾는다. 서버와 같은 컴퓨터일 때만 보인다."""
    if "→ " not in render_text:
        return []
    folder = render_text.rsplit("→ ", 1)[1].split(" (")[0].strip()
    return sorted(str(p) for p in Path(folder).glob("*.png"))


def progress(i: int, name: str) -> str:
    """단계를 부르기 전에 찍는 줄. 붕괴·렌더는 수십 초 걸려, 아무 출력이 없으면 멈춘 줄 안다."""
    total = len(STEPS) + 1  # ping_blender 포함
    return f"[{i}/{total}] {name} …" + (" (기다리는 중)" if not en() else " (waiting)")


async def call(session: ClientSession, i: int, name: str, args: dict):
    """진행 줄 → 도구 호출 → '이름 (걸린 초): 결과' 줄. (결과, 문장) 을 돌려준다."""
    print(progress(i, name), flush=True)
    start = time.monotonic()
    result = await session.call_tool(name, args)
    text = text_of(result)
    print(f"{name} ({time.monotonic() - start:.1f}s): {text}", flush=True)
    return result, text


async def run(params: StdioServerParameters) -> int:
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            _, ping = await call(session, 1, "ping_blender", {})
            if ping.startswith(FAILED):
                # 연결 실패 문장에 원인별 다음 한 단계가 들어 있다. 더 자세한 점검은 doctor
                print("다음 할 일: 위 안내대로 한 뒤 다시 돌리세요. 전체 점검: uv run blender-fx-doctor" if not en() else
                      "Next: follow the step above and run this again. Full check: uv run blender-fx-doctor")
                return 2
            text = ""
            for i, (name, args) in enumerate(STEPS):
                result, text = await call(session, i + 2, name, args)
                if result.is_error or text.startswith(FAILED):
                    if i:  # 스냅샷 뒤에 실패했으면 장면이 바뀌었을 수 있다
                        print(undo_line())
                    return 1
            paths = png_paths(text)
            print(("PNG {n}개:" if not en() else "{n} PNG files:").format(n=len(paths)))
            for p in paths:
                print(f"  {p}")
            print(undo_line())
            return 0


def main() -> None:
    sys.exit(asyncio.run(run(server_params(sys.argv[1:]))))


if __name__ == "__main__":
    main()
