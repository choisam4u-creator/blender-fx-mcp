# SPDX-License-Identifier: MIT
"""출력 폴더의 디스크 여유. 물·연기 굽기(Mantaflow) 캐시는 수 GB 라 굽다가 디스크가 차면 원인 모를 실패가 남는다."""

from __future__ import annotations

import glob
import os
import shutil
from pathlib import Path

DOCTOR_WARN_BYTES = 5 * 1024**3  # doctor 가 경고하는 여유(굽기 몇 번 분량)
BAKE_MIN_BYTES = 1 * 1024**3  # 이보다 적으면 굽기 도구를 블렌더에 보내기 전에 멈춘다
SNAPSHOT_KEEP = 5  # clear_snapshots 가 기본으로 남기는 개수


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



def old_snapshots(d: str | os.PathLike, keep: int = SNAPSHOT_KEEP) -> list[list[Path]]:
    """clear_snapshots 가 지울 스냅샷: 최근 keep 개와 before_restore 를 뺀 나머지(새것 → 오래된 것 순서).
    스냅샷마다 [.blend, 블렌더가 남긴 이전 판 .blend1 …] 묶음. doctor 의 "지울 수 있는 양" 도 이 규칙으로 센다."""
    d = Path(d)
    files = sorted((f for f in d.glob("*.blend") if f.stem != "before_restore"),
                   key=lambda f: f.stat().st_mtime, reverse=True)
    return [[f, *sorted(d.glob(f"{glob.escape(f.stem)}.blend[0-9]*"))] for f in files[keep:]]


def usage_groups(root: str | os.PathLike) -> list[tuple[str, int, int]]:
    """출력 폴더를 지울 수 있는 단위로 묶은 (묶음, 바이트, 개수), 큰 것부터. 빈 묶음은 뺀다.
    caches: 구운 캐시(cache_* 폴더, clear_caches), snapshots: clear_snapshots 가 기본값으로 실제로 지울 스냅샷만,
    runs: 렌더·미리보기 등 날짜 이름 폴더(손으로), files: 출력 폴더 바로 아래 파일(내보낸 모델 등, 손으로)."""
    sizes = {"caches": [0, 0], "snapshots": [0, 0], "runs": [0, 0], "files": [0, 0]}
    try:
        entries = list(os.scandir(root))
    except OSError:
        return []
    for e in entries:
        try:
            if not e.is_dir(follow_symlinks=False):
                key, n, c = "files", e.stat(follow_symlinks=False).st_size, 1
            elif e.name == "snapshots":
                old = old_snapshots(e.path)
                key, n, c = "snapshots", sum(f.stat().st_size for group in old for f in group), len(old)
            else:
                key, n, c = ("caches" if e.name.startswith("cache_") else "runs"), folder_bytes(e.path), 1
        except OSError:
            continue
        sizes[key][0] += n
        sizes[key][1] += c
    return sorted(((k, b, c) for k, (b, c) in sizes.items() if b), key=lambda x: -x[1])
