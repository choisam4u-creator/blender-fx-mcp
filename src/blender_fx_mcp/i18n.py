# SPDX-License-Identifier: MIT
"""메시지 언어. BLENDER_FX_LANG 이 있으면 그것(en 으로 시작하면 영어, 아니면 한국어).
없으면 로캘(LC_ALL → LC_MESSAGES → LANG 중 처음 값이 있는 것)이 ko 면 한국어, 다른 언어면 영어.
로캘이 비었거나 C/POSIX 면(창 앱이 띄운 서버에서 흔함) 한국어."""

from __future__ import annotations

import os


LOCALE_VARS = ("LC_ALL", "LC_MESSAGES", "LANG")


def _from_locale() -> tuple[str, str]:
    """(언어, 근거 환경변수). POSIX 규칙대로 값이 있는 첫 변수만 본다."""
    for var in LOCALE_VARS:
        value = os.environ.get(var, "").strip()
        if value:
            code = value.split(".")[0].split("@")[0].split("_")[0].lower()
            if code in ("c", "posix"):
                return "ko", "default"
            return ("ko" if code == "ko" else "en"), var
    return "ko", "default"


def lang_source() -> str:
    """언어를 정한 근거: "BLENDER_FX_LANG", 로캘 변수 이름, 또는 "default"."""
    if os.environ.get("BLENDER_FX_LANG", "").strip():
        return "BLENDER_FX_LANG"
    return _from_locale()[1]


def lang() -> str:
    explicit = os.environ.get("BLENDER_FX_LANG", "").strip().lower()
    return explicit or _from_locale()[0]


def is_en() -> bool:
    return lang().startswith("en")


def t(ko: str, en: str) -> str:
    """사용자에게 보여줄 문장을 언어에 맞게 고른다."""
    return en if is_en() else ko
