# SPDX-License-Identifier: MIT
"""출력 폴더의 디스크 여유. 물·연기 굽기(Mantaflow) 캐시는 수 GB 라 굽다가 디스크가 차면 원인 모를 실패가 남는다."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

DOCTOR_WARN_BYTES = 5 * 1024**3  # doctor 가 경고하는 여유(굽기 몇 번 분량)
BAKE_MIN_BYTES = 1 * 1024**3  # 이보다 적으면 굽기 도구를 블렌더에 보내기 전에 멈춘다


def free_bytes(path: str | os.PathLike) -> int | None:
    """path(없으면 가장 가까운 있는 상위 폴더)가 있는 디스크의 남은 바이트. 알 수 없으면 None."""
    p = Path(path).expanduser()
    while not p.exists() and p.parent != p:
        p = p.parent
    try:
        return shutil.disk_usage(p).free
    except OSError:
        return None


def folder_bytes(path: str | os.PathLike) -> int:
    """폴더 안 파일 크기의 합. 읽을 수 없는 파일은 건너뛴다."""
    total = 0
    for dirpath, _, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(dirpath, name))
            except OSError:
                pass
    return total


def gb(n: int) -> str:
    return f"{n / 1024**3:.1f}GB"
