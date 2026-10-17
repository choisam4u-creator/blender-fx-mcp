# SPDX-License-Identifier: MIT
"""레시피 오류 문장 → 해결법 절(docs/troubleshooting.md 앵커) 대응표를 만든다. 블렌더 없이 돈다.

  uv run python scripts/gen_help_index.py           # src/blender_fx_mcp/help_index.py 가 문서·레시피와 같은지 점검(다르면 종료 코드 1)
  uv run python scripts/gen_help_index.py --write   # 대응표를 새로 씀(문서에 절을 더하거나 레시피 오류 문장을 바꾼 뒤)

레시피의 raise FxError(L(한, 영)) 마다 첫 문장의 가장 긴 고정 조각(열쇠)을 뽑고, 문서에서 그 열쇠가 처음 나오는 절의 앵커를 짝짓는다.
서버는 레시피 오류에 이 표로 "해결법: …#절" 을 붙인다. 문서에 없는 열쇠는 표에 넣지 않는다(tests/test_troubleshooting.py 가 따로 지킨다).
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "troubleshooting.md"
RECIPES = ROOT / "src" / "blender_fx_mcp" / "recipes"
OUT = ROOT / "src" / "blender_fx_mcp" / "help_index.py"


def fixed_parts(node):
    """문자열(또는 f-string)의 고정 조각들. 값 자리 {…} 에서 끊는다."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.JoinedStr):
        parts, cur = [], ""
        for v in node.values:
            if isinstance(v, ast.Constant):
                cur += v.value
            else:
                parts.append(cur)
                cur = ""
        return parts + [cur]
    return []


def key(node, min_len):
    """첫 문장(마침표·물음표 앞)의 가장 긴 고정 조각. 따옴표·빈칸·괄호를 다듬는다. 너무 짧으면 None."""
    best = ""
    for part in fixed_parts(node):
        part = re.split(r"(?<=[.?])\s", part, maxsplit=1)[0]
        best = max(best, part, key=len)
        if re.search(r"[.?]\s", part) or part.endswith((".", "?")):
            break  # 첫 문장이 끝났다
    best = best.strip(" '\"()[]:").rstrip(".")
    return best if len(best) >= min_len else None


def recipe_errors():
    """[(파일, 줄, 한 열쇠, 영 열쇠)] — 레시피의 모든 raise FxError(L(한, 영))."""
    out = []
    for path in sorted(RECIPES.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "FxError" and node.args
                    and isinstance(node.args[0], ast.Call) and getattr(node.args[0].func, "id", None) == "L"):
                ko, en = node.args[0].args[:2]
                out.append((path.name, node.lineno, key(ko, 5), key(en, 8)))
    return out


def anchor(title: str) -> str:
    """GitHub 가 ## 제목에서 만드는 앵커(소문자, 문장부호 빼기, 빈칸 → -)."""
    return re.sub(r"[^\w\- ]", "", title.strip().lower()).replace(" ", "-")


def section_of(doc: str, phrase: str) -> str | None:
    """문서에서 phrase 가 처음 나오는 ## 절의 앵커. 머리말(첫 ## 앞)이나 없으면 None."""
    pos = doc.find(phrase)
    if pos < 0:
        return None
    titles = re.findall(r"^## (.+)$", doc[:pos], re.M)
    return anchor(titles[-1]) if titles else None


def build() -> dict[str, str]:
    """열쇠 → 앵커. 긴 열쇠부터(짧은 열쇠가 긴 문장 안에 들어 있어도 긴 쪽이 이긴다)."""
    doc = DOC.read_text(encoding="utf-8")
    index = {}
    for _f, _line, ko, en in recipe_errors():
        for k in (ko, en):
            sec = section_of(doc, k) if k else None
            if sec:
                index[k] = sec
    return dict(sorted(index.items(), key=lambda kv: (-len(kv[0]), kv[0])))


def render(index: dict[str, str]) -> str:
    rows = "\n".join(f"    {k!r}: {v!r}," for k, v in index.items())
    return ("# SPDX-License-Identifier: MIT\n"
            "# 자동 생성: uv run python scripts/gen_help_index.py --write (손으로 고치지 않는다)\n"
            "# 레시피 오류 문장의 고정 조각 → docs/troubleshooting.md 절 앵커. 긴 조각부터 맞춘다.\n"
            f"RECIPE_HELP = {{\n{rows}\n}}\n")


def main(argv: list[str]) -> int:
    index = build()
    want = render(index)
    if argv == ["--write"]:
        OUT.write_text(want, encoding="utf-8")
        print(f"썼습니다: {OUT.relative_to(ROOT)} (열쇠 {len(index)}개)")
        return 0
    if argv:
        print("쓰는 법: gen_help_index.py [--write]", file=sys.stderr)
        return 2
    if OUT.exists() and OUT.read_text(encoding="utf-8") == want:
        print("help_index.py 가 문서·레시피와 같습니다.")
        return 0
    print("help_index.py 가 문서·레시피와 다릅니다. uv run python scripts/gen_help_index.py --write 로 새로 쓰세요.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
