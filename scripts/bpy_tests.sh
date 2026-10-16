#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# 블렌더 앱 없이 `pip install bpy` 로 레시피 시험을 돌린다(Linux 클라우드 회차·CI 의 recipe-tests-bpy 작업과 같은 방법).
# 개발용 .venv 를 건드리지 않게 따로 가상환경(.venv-bpy)을 만든다. 유체(`app_only`) 시험은 tests/conftest.py 가 건너뛴다.
#
#   scripts/bpy_tests.sh                       # 전체 시험
#   scripts/bpy_tests.sh tests/test_recipes_v06.py -k shatter   # pytest 인자를 그대로 넘김
#   BPY_WHEEL=~/Downloads/bpy-5.0.1-cp311-cp311-manylinux_2_28_x86_64.whl scripts/bpy_tests.sh   # 이미 받은 휠로(내려받기 없이)
#
# bpy 휠은 처음 한 번 크게 받는다(Linux 휠 356MB, 2026-10-16 클라우드 실측은 아래 BPY_NOTICE). 두 번째부터는 uv 캐시에서 깔려 빠르다.
# BPY_WHEEL 은 파일 이름이 bpy-<BPY_VERSION>- 로 시작해야 한다(CI 와 같은 판).
#
# 필요한 것: uv, Linux x86_64, libEGL(소프트웨어 Mesa). 없으면 설치 명령을 알려 주고 멈춘다.
set -euo pipefail

BPY_VERSION="5.0.1"
PYTHON_VERSION="3.11"
VENV=".venv-bpy"
BPY_NOTICE="내려받기 356MB·설치 뒤 약 1GB, 클라우드 컨테이너에서 받기 약 3분·깔기 12초, 느린 망에서는 20분 넘게"

if [ -n "${BPY_WHEEL:-}" ]; then
  if [ ! -f "$BPY_WHEEL" ]; then
    echo "BPY_WHEEL 파일이 없습니다: $BPY_WHEEL — 휠의 전체 경로로 다시 주거나, BPY_WHEEL 을 빼고 돌리면 PyPI 에서 받습니다." >&2
    exit 2
  fi
  case "$(basename "$BPY_WHEEL")" in
    "bpy-$BPY_VERSION-"*.whl) ;;
    *)
      echo "BPY_WHEEL 이 bpy $BPY_VERSION 휠이 아닙니다: $(basename "$BPY_WHEEL") — CI 와 같은 판인 bpy-$BPY_VERSION-…whl 을 주세요(https://pypi.org/project/bpy/$BPY_VERSION/#files)." >&2
      exit 2
      ;;
  esac
  BPY_WHEEL="$(cd "$(dirname "$BPY_WHEEL")" && pwd)/$(basename "$BPY_WHEEL")"
fi

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
  if [ -n "${BPY_WHEEL:-}" ]; then
    echo "bpy $BPY_VERSION 를 받은 휠에서 설치합니다: $BPY_WHEEL" >&2
    uv pip install --python "$VENV/bin/python" "$BPY_WHEEL"
  else
    echo "bpy $BPY_VERSION 를 받습니다($BPY_NOTICE). 처음엔 오래 걸려도 멈춘 것이 아닙니다." >&2
    echo "  이미 받은 휠이 있으면: BPY_WHEEL=휠경로 scripts/bpy_tests.sh" >&2
    uv pip install --python "$VENV/bin/python" "bpy==$BPY_VERSION"
  fi
fi

BLENDER_FX_BLENDER="$PWD/$VENV/bin/python" exec uv run --no-sync pytest -q "$@"
