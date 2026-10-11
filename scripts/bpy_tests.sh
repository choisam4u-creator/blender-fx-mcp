#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# 블렌더 앱 없이 `pip install bpy` 로 레시피 시험을 돌린다(Linux 클라우드 회차·CI 의 recipe-tests-bpy 작업과 같은 방법).
# 개발용 .venv 를 건드리지 않게 따로 가상환경(.venv-bpy)을 만든다. 유체(`app_only`) 시험은 tests/conftest.py 가 건너뛴다.
#
#   scripts/bpy_tests.sh                       # 전체 시험
#   scripts/bpy_tests.sh tests/test_recipes_v06.py -k shatter   # pytest 인자를 그대로 넘김
#
# 필요한 것: uv, Linux x86_64, libEGL(소프트웨어 Mesa). 없으면 설치 명령을 알려 주고 멈춘다.
set -euo pipefail

BPY_VERSION="5.0.1"
PYTHON_VERSION="3.11"
VENV=".venv-bpy"

cd "$(dirname "$0")/.."

if ! command -v uv >/dev/null 2>&1; then
  echo "uv 가 없습니다: https://docs.astral.sh/uv/ 에서 설치하세요." >&2
  exit 2
fi

if [ "$(uname -s)" != "Linux" ]; then
  echo "이 스크립트는 Linux 전용입니다(bpy 휠·libEGL). Mac 에서는 블렌더 앱으로 'uv run pytest -q'." >&2
  exit 2
fi

if ! ldconfig -p 2>/dev/null | grep -q 'libEGL\.so\.1'; then
  echo "libEGL 이 없어 bpy 가 렌더하지 못합니다. 먼저 설치하세요:" >&2
  echo "  sudo apt-get install -y libxi6 libxxf86vm1 libxfixes3 libxrender1 libgl1 libsm6 libxkbcommon0 libegl1 libegl-mesa0 libgl1-mesa-dri" >&2
  exit 2
fi

export UV_PROJECT_ENVIRONMENT="$VENV"
uv python install "$PYTHON_VERSION" >/dev/null
uv sync --group dev --python "$PYTHON_VERSION" --quiet
if ! "$VENV/bin/python" -c "import bpy, sys; sys.exit(bpy.app.version_string.split()[0] != '$BPY_VERSION')" 2>/dev/null; then
  uv pip install --python "$VENV/bin/python" "bpy==$BPY_VERSION"
fi

BLENDER_FX_BLENDER="$PWD/$VENV/bin/python" exec uv run --no-sync pytest -q "$@"
