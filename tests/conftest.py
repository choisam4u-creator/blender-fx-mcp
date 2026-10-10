# `pip install bpy` 로 받은 bpy 모듈(Linux, 5.0.1 · 4.5.14 LTS · 4.2.23 LTS 모두 같음)은 블렌더 앱과 달리 일부 기능이 깨져 있다.
#  - Mantaflow(연기·불·물·먼지): 파이썬 바인딩에 `LevelsetGrid.setConst` 가 없어 프로세스가 중단된다
#  (리지드바디 접착 세그폴트는 bpy 결함이 아니라 레시피 쪽 원인이었다 — 활성 객체 없이 constraint_add 를 불러서. 2026-10-05 수정)
# 그래서 BLENDER_FX_BLENDER 가 bpy 를 설치한 파이썬이면 `app_only` 표시 시험(유체 5개)만 건너뛴다.
# 블렌더 앱으로는 전부 돈다(GitHub Actions 에서는 손으로 돌리는 app-tests 작업). BLENDER_FX_FORCE_ALL=1 이면 bpy 로도 전부 돌린다(원인 조사용).
import os
import stat
import sys
from pathlib import Path

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


@pytest.fixture(autouse=True)
def _default_lang(monkeypatch):
    """셸의 BLENDER_FX_LANG(예: Mac 에서 en)이 시험으로 새지 않게 매 시험 기본값(한국어)에서 시작한다.
    언어가 필요한 시험은 monkeypatch.setenv 로 직접 정하고, 끝나면 monkeypatch 가 되돌린다."""
    monkeypatch.delenv("BLENDER_FX_LANG", raising=False)


def make_fake_blender(folder, body: str, name: str = "blender") -> str:
    """가짜 블렌더 실행 파일을 만든다. 본문은 파이썬이라 Linux·macOS·Windows 에서 같게 돈다.

    받은 인자는 folder/argv.txt 에(한 줄에 하나), 마지막 인자가 파일이면 그 내용을 folder/script.py 에 남긴다.
    POSIX 는 `exec` 하는 /bin/sh 감싸개(시그널로 죽으면 음수 종료 코드가 그대로 보인다), Windows 는 `.cmd` 감싸개.
    """
    folder = Path(folder)
    prelude = (
        "import pathlib, sys\n"
        "sys.stdout.reconfigure(encoding='utf-8'); sys.stderr.reconfigure(encoding='utf-8')\n"
        f"_d = pathlib.Path({str(folder)!r})\n"
        "(_d / 'argv.txt').write_text('\\n'.join(sys.argv[1:]) + '\\n', encoding='utf-8')\n"
        "if sys.argv[1:] and pathlib.Path(sys.argv[-1]).is_file():\n"
        "    (_d / 'script.py').write_text(pathlib.Path(sys.argv[-1]).read_text(encoding='utf-8'), encoding='utf-8')\n"
    )
    script = folder / f"{name}_body.py"
    script.write_text(prelude + body + "\n", encoding="utf-8")
    if sys.platform == "win32":
        exe = folder / f"{name}.cmd"
        exe.write_text(f'@echo off\r\n"{sys.executable}" "{script}" %*\r\nexit /b %ERRORLEVEL%\r\n', encoding="utf-8")
    else:
        exe = folder / name
        exe.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8")
        exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
    return str(exe)



@pytest.fixture
def fake_blender(tmp_path):
    """`fake_blender(본문, name=...)` → 가짜 블렌더 경로. 파일은 tmp_path 에 생긴다."""
    return lambda body, name="blender": make_fake_blender(tmp_path, body, name)
