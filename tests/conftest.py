# `pip install bpy` 로 받은 bpy 모듈은 Mantaflow(연기·불·물·먼지) 파이썬 바인딩이 깨져 있다
# (bpy 5.0.1, Linux 에서 `LevelsetGrid.setConst` 없음 → 프로세스 중단). 그래서 BLENDER_FX_BLENDER 가
# bpy 를 설치한 파이썬이면 `fluid` 표시가 붙은 시험만 건너뛴다. 블렌더 앱으로는 전부 돈다.
import pytest

from blender_fx_mcp.headless import find_blender, is_bpy_python


def pytest_collection_modifyitems(config, items):
    blender = find_blender()
    if not blender or not is_bpy_python(blender):
        return
    skip = pytest.mark.skip(reason="bpy 모듈의 Mantaflow 가 깨져 있어 건너뜀(블렌더 앱에서는 돈다)")
    for item in items:
        if "fluid" in item.keywords:
            item.add_marker(skip)
