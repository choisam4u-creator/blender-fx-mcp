# SPDX-License-Identifier: MIT
"""블렌더 창 없이 터미널에서 첫 렌더까지(저장소에서 돌리는 껍데기). 본체는 패키지의 blender_fx_mcp.first_render 이고,
PyPI 로 설치했으면 저장소 없이 `uvx --from blender-fx-mcp blender-fx-first-render` 로 같은 것을 돌린다.
From the terminal to a first render (a wrapper for a checkout). The code lives in blender_fx_mcp.first_render;
without a checkout run the same thing with `uvx --from blender-fx-mcp blender-fx-first-render`.

    uv run python examples/first_render.py                  # 이 저장소의 서버 / the server in this checkout
    uv run python examples/first_render.py uvx blender-fx-mcp

ping_blender → snapshot → make_demo_building → destroy → render_preview 를 차례로 부르고 PNG 경로와 여는 명령을 출력한다.
Connect 가 안 되면 종료 코드 2, 도구가 실패하면 1(마지막 줄에 신고 방법). 시작 전 장면은 스냅샷 first_render_before.
"""

from blender_fx_mcp.first_render import *  # noqa: F403 — 시험과 사용자가 예제 모듈에서 바로 쓰는 이름들
from blender_fx_mcp.first_render import main

if __name__ == "__main__":
    main()
