# SPDX-License-Identifier: MIT
"""렌더 결과(PNG 폴더·mp4)를 바로 여는 OS별 명령 한 줄. 첫 렌더 뒤 경로만 보이면 무엇으로 볼지 모른다."""

from __future__ import annotations

import shlex
import sys

from .i18n import t


def open_command(path: str, platform: str | None = None) -> str:
    """path 를 기본 앱(폴더면 파일 관리자)으로 여는 명령. 경로는 그 셸에 맞게 따옴표로 감싼다."""
    platform = platform or sys.platform
    if platform.startswith("win"):
        # start 는 첫 따옴표 인자를 창 제목으로 읽어 빈 제목 "" 를 먼저 준다. cmd 경로에는 " 가 올 수 없다
        return f'start "" "{path}"'
    return f"{'open' if platform == 'darwin' else 'xdg-open'} {shlex.quote(path)}"


def open_line(path: str, platform: str | None = None) -> str:
    """결과 문장 끝에 붙이는 줄(앞에 줄바꿈 포함)."""
    cmd = open_command(path, platform)
    return t(f"\n결과 보기: {cmd}", f"\nOpen it: {cmd}")
