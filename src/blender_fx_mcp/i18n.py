"""메시지 언어. 환경변수 BLENDER_FX_LANG 이 en 으로 시작하면 영어, 아니면 한국어."""

from __future__ import annotations

import os


def lang() -> str:
    return os.environ.get("BLENDER_FX_LANG", "ko").strip().lower()


def is_en() -> bool:
    return lang().startswith("en")


def t(ko: str, en: str) -> str:
    """사용자에게 보여줄 문장을 언어에 맞게 고른다."""
    return en if is_en() else ko
