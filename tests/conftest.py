# `pip install bpy` 로 받은 bpy 모듈(Linux, 5.0.1 · 4.5.14 LTS · 4.2.23 LTS 모두 같음)은 블렌더 앱과 달리 일부 기능이 깨져 있다.
#  - Mantaflow(연기·불·물·먼지): 파이썬 바인딩에 `LevelsetGrid.setConst` 가 없어 프로세스가 중단된다
#  (리지드바디 접착 세그폴트는 bpy 결함이 아니라 레시피 쪽 원인이었다 — 활성 객체 없이 constraint_add 를 불러서. 2026-10-05 수정)
# 그래서 BLENDER_FX_BLENDER 가 bpy 를 설치한 파이썬이면 `app_only` 표시 시험(유체 5개)만 건너뛴다.
# 블렌더 앱으로는 전부 돈다(GitHub Actions 에서는 손으로 돌리는 app-tests 작업). BLENDER_FX_FORCE_ALL=1 이면 bpy 로도 전부 돌린다(원인 조사용).
import os

import pytest

from blender_fx_mcp.headless import find_blender, is_bpy_python


def pytest_collection_modifyitems(config, items):
    blender = find_blender()
    if not blender or not is_bpy_python(blender) or os.environ.get("BLENDER_FX_FORCE_ALL") == "1":
        return
    skip = pytest.mark.skip(reason="bpy 모듈에서 깨지는 기능(유체)이라 건너뜀 — 블렌더 앱에서는 돈다")
    for item in items:
        if "app_only" in item.keywords:
            item.add_marker(skip)
