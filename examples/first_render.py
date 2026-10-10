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
"""

import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

FAILED = ("실패: ", "Failed: ")  # 서버 도구가 실패하면 돌려주는 문장 머리
STEPS = [
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


def png_paths(render_text: str) -> list[str]:
    """render_preview 문장의 '→ <폴더>' 에서 PNG 를 찾는다. 서버와 같은 컴퓨터일 때만 보인다."""
    if "→ " not in render_text:
        return []
    folder = render_text.rsplit("→ ", 1)[1].split(" (")[0].strip()
    return sorted(str(p) for p in Path(folder).glob("*.png"))


async def run(params: StdioServerParameters) -> int:
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            ping = text_of(await session.call_tool("ping_blender", {}))
            print(f"ping_blender: {ping}")
            if ping.startswith(FAILED):
                # 연결 실패 문장에 원인별 다음 한 단계가 들어 있다. 더 자세한 점검은 doctor
                print("다음 할 일: 위 안내대로 한 뒤 다시 돌리세요. 전체 점검: uv run blender-fx-doctor" if not en() else
                      "Next: follow the step above and run this again. Full check: uv run blender-fx-doctor")
                return 2
            text = ""
            for name, args in STEPS:
                result = await session.call_tool(name, args)
                text = text_of(result)
                print(f"{name}: {text}")
                if result.is_error or text.startswith(FAILED):
                    return 1
            paths = png_paths(text)
            print(("PNG {n}개:" if not en() else "{n} PNG files:").format(n=len(paths)))
            for p in paths:
                print(f"  {p}")
            return 0


def main() -> None:
    sys.exit(asyncio.run(run(server_params(sys.argv[1:]))))


if __name__ == "__main__":
    main()
