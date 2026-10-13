# SPDX-License-Identifier: MIT
"""CHANGELOG 의 한 판 절을 GitHub 릴리스 본문으로 출력한다. 출시 절차 8단계에서 손 복사 대신 쓴다.

  uv run python scripts/release_notes.py v0.7.0 > notes.md
  uv run python scripts/release_notes.py --draft v0.8.0   # 아직 날짜가 없는(미출시) 절을 미리 읽기
  gh release create v0.7.0 --notes-file notes.md      # 사람이 Mac 에서(쓰기 권한이 필요해 자동 게시는 하지 않는다)

영어 요약(**English summary**)을 먼저, 그다음 한국어 상세를 낸다. 절 맨 앞의 관리자용 메모(버전을 어디서 올렸는지 등)는 뺀다.
없는 판이나 아직 날짜가 없는(미출시) 판이면 이유를 stderr 에 쓰고 종료 코드 1(`--draft` 면 미출시 판도 맨 위에 초안 표시를 달아 낸다).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEADING = re.compile(r"^## \[?(\d+\.\d+\.\d+)\]? (?:—|-) (.+)$", re.M)
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
PYPI = "https://pypi.org/project/blender-fx-mcp/{version}/"


def section(text: str, version: str) -> tuple[str, str] | None:
    """(날짜, 본문). 그 판 절이 없으면 None."""
    heads = list(HEADING.finditer(text))
    for i, m in enumerate(heads):
        if m.group(1) == version:
            end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
            return m.group(2).strip(), text[m.end():end].strip()
    return None


DRAFT = "> 초안 / Draft — 아직 출시되지 않은 판입니다(CHANGELOG: {when}). / This version is not released yet.\n\n"


def notes(text: str, version: str, draft: bool = False) -> str:
    found = section(text, version)
    if found is None:
        raise LookupError(f"CHANGELOG.md 에 {version} 절이 없습니다 / no {version} section in CHANGELOG.md")
    when, body = found
    released = bool(DATE.fullmatch(when))
    if not released and not draft:
        raise LookupError(f"{version} 은 아직 출시 날짜가 없습니다({when}). 미리 보려면 --draft "
                          f"/ {version} has no release date yet; use --draft to preview")
    start = body.find("**English summary**")
    if start < 0:
        raise LookupError(f"{version} 절에 '**English summary**' 가 없습니다 / no English summary in {version}")
    body = body[start:].strip()
    if not released:  # 아직 PyPI 에 없으니 설치 줄은 빼고 초안 표시
        return DRAFT.format(when=when) + body + "\n"
    footer = f"PyPI: {PYPI.format(version=version)} · `uvx blender-fx-mcp@{version}`"
    return f"{body}\n\n---\n\n{footer}\n"


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    draft = "--draft" in argv
    if draft:
        argv.remove("--draft")
    if len(argv) != 1 or not re.fullmatch(r"v?\d+\.\d+\.\d+", argv[0]):
        print("사용법 / usage: release_notes.py [--draft] vX.Y.Z", file=sys.stderr)
        return 2
    version = argv[0].lstrip("v")
    try:
        sys.stdout.write(notes((root / "CHANGELOG.md").read_text(encoding="utf-8"), version, draft))
    except LookupError as e:
        print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
