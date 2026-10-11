# 저장소의 모든 마크다운 문서에서 상대 링크와 `#앵커`가 실제 파일·제목을 가리키는지 한 번에 본다. 블렌더 없이 돈다.
# (Mac 시험의 첫 FAIL 이 README 의 깨진 링크였다. 문서별 시험은 일부 링크만 본다.)
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CODE_BLOCK = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`\n]*`")
COMMENT = re.compile(r"<!--.*?-->", re.S)


def github_slug(heading: str) -> str:
    """GitHub 의 제목 앵커 규칙: 링크·강조 기호를 걷어 내고 소문자, 글자·숫자·`_`·`-`·공백만 남겨 공백을 `-` 로(한글 유지)."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)
    text = re.sub(r"[`*]", "", text).strip().lower()
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def anchors(path: Path) -> set[str]:
    out, seen = set(), {}
    for heading in re.findall(r"^#{1,6} (.+?)\s*#*$", CODE_BLOCK.sub("", path.read_text(encoding="utf-8")), re.M):
        slug = github_slug(heading)
        n = seen.get(slug, 0)
        out.add(slug if n == 0 else f"{slug}-{n}")  # 같은 제목이 또 나오면 -1, -2
        seen[slug] = n + 1
    return out


def markdown_files() -> list[Path]:
    if shutil.which("git") and (ROOT / ".git").exists():
        names = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True)
        return [ROOT / n for n in names.stdout.split()]
    return sorted(p for p in ROOT.rglob("*.md") if ".venv" not in p.parts)


def test_github_slug_rules():
    assert github_slug("Security, contributing, license") == "security-contributing-license"
    assert github_slug("나머지 도구 한 줄 예시") == "나머지-도구-한-줄-예시"
    assert github_slug("1. \"창문 있는 건물\"") == "1-창문-있는-건물"
    assert github_slug("`blender-fx-doctor` 출력 / doctor output") == "blender-fx-doctor-출력--doctor-output"


@pytest.mark.parametrize("doc", markdown_files(), ids=lambda p: str(p.relative_to(ROOT)))
def test_relative_links_and_anchors_exist(doc):
    text = INLINE_CODE.sub("", COMMENT.sub("", CODE_BLOCK.sub("", doc.read_text(encoding="utf-8"))))
    broken = []
    for link in re.findall(r"\]\(([^)\s]+)\)", text):
        if re.match(r"[a-z][a-z0-9+.-]*:", link):  # http:, mailto: 등 바깥 주소는 보지 않는다
            continue
        path, _, frag = link.partition("#")
        target = (doc.parent / path).resolve() if path else doc
        if not target.exists():
            broken.append(f"{link} (파일 없음)")
        elif frag and target.suffix == ".md" and frag not in anchors(target):
            broken.append(f"{link} (제목 #{frag} 없음)")
    assert not broken, f"{doc.relative_to(ROOT)} 의 깨진 링크: {broken}"
