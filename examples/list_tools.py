# SPDX-License-Identifier: MIT
"""blender-fx-mcp 서버를 공식 `mcp` 파이썬 클라이언트로 띄워 도구 목록과 ping_blender 결과를 출력한다.
Launch the blender-fx-mcp server over stdio with the official `mcp` Python client, list its tools and call ping_blender.

    uv run python examples/list_tools.py                  # 이 저장소의 서버 / the server in this checkout
    uv run python examples/list_tools.py uvx --from git+https://github.com/choisam4u-creator/blender-fx-mcp blender-fx-mcp

블렌더가 꺼져 있어도 돈다. 그때 ping_blender 는 연결 실패 문장을 돌려준다(예외가 아님).
Works without Blender: ping_blender then returns the connection failure message instead of raising.
자기 MCP 클라이언트를 짤 때 출발점으로 복사해 쓰면 된다. / Copy it as a starting point for your own MCP client.
"""

import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def server_params(argv: list[str]) -> StdioServerParameters:
    # 인자가 없으면 지금 파이썬으로 이 저장소의 서버 모듈을 띄운다. 있으면 그 명령을 그대로 쓴다.
    command, *args = argv or [sys.executable, "-m", "blender_fx_mcp.server"]
    # 서버는 BLENDER_FX_LANG·BLENDER_FX_PORT 등을 환경변수로 읽는다. 지금 환경을 그대로 넘긴다.
    return StdioServerParameters(command=command, args=args, env=dict(os.environ))


async def run(params: StdioServerParameters) -> tuple[list[str], str]:
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            result = await session.call_tool("ping_blender", {})
            text = "".join(c.text for c in result.content if c.type == "text")
            return [tool.name for tool in tools], text


def main() -> None:
    names, ping = asyncio.run(run(server_params(sys.argv[1:])))
    print(f"도구 {len(names)}개 / {len(names)} tools")
    for name in names:
        print(f"  {name}")
    print(f"ping_blender: {ping}")


if __name__ == "__main__":
    main()
