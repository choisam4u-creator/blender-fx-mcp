"""README 도구 표 점검·초안. 블렌더 없이 돈다.

  uv run python scripts/gen_tool_table.py           # README 표와 서버가 어긋난 곳(빠진 도구·틀린 값 목록)을 알려 줌
  uv run python scripts/gen_tool_table.py --draft   # 도구 설명(docstring)으로 만든 한/영 표 행 초안을 출력

README 표는 사람이 다듬은 설명(인자·쓰임새)이라 통째로 생성하지 않는다. 새 도구를 넣을 때 --draft 의 행을 복사해 다듬고,
표에 `a/b/c` 처럼 적은 값 목록은 서버의 CHOICES 와 같아야 한다(값이 늘거나 줄면 이 스크립트와 시험이 짚는다).
"""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from blender_fx_mcp import server  # noqa: E402

# 도구 → 고정 목록을 검사하는 레시피 이름(server.CHOICES 의 키)
TOOL_RECIPE = {
    "destroy": "destroy", "explode": "destroy", "water": "water", "splash": "water",
    "make_demo_building": "demo_scene", "particles": "particles", "set_ground": "set_ground",
    "set_look": "set_look", "camera": "camera", "render_preview": "render", "render_video": "render_video",
}
SLASH_LIST = re.compile(r"(?<![\w./])([a-z]+(?:/[a-z]+){2,})(?![\w/])")


def tool_docs() -> dict[str, tuple[str, str]]:
    """도구 이름 → (영어 첫 줄, 한국어 둘째 줄)."""
    out = {}
    for tool in asyncio.run(server.mcp.list_tools()):
        lines = [line.strip() for line in (tool.description or "").strip().splitlines() if line.strip()]
        out[tool.name] = (lines[0], lines[1] if len(lines) > 1 else lines[0])
    return out


def readme_rows(section: str) -> dict[str, str]:
    """README 의 절('## 도구 목록' 또는 '### Tools') 표에서 도구 이름 → 설명 칸. `a` / `b` 처럼 묶인 행은 각각."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    body = text.split(section + "\n", 1)[1]
    body = re.split(r"^#{2,3} ", body, maxsplit=1, flags=re.M)[0]
    rows = {}
    for names, desc in re.findall(r"^\| ((?:`\w+`(?: / )?)+) \| (.+) \|$", body, re.M):
        for name in re.findall(r"`(\w+)`", names):
            rows[name] = desc
    return rows


def problems() -> list[str]:
    tools = tool_docs()
    out = []
    for section in ("## 도구 목록", "### Tools"):
        rows = readme_rows(section)
        for name in tools:
            if name not in rows:
                out.append(f"{section}: `{name}` 행이 없음(--draft 로 초안을 만드세요)")
        for name in rows:
            if name not in tools:
                out.append(f"{section}: `{name}` 은 서버에 없는 도구")
        for name, desc in rows.items():
            if name not in TOOL_RECIPE:  # 고정 목록 인자가 없는 도구(파일 형식 목록 등은 검사하지 않음)
                continue
            allowed = server.CHOICES[TOOL_RECIPE[name]]
            for listed in SLASH_LIST.findall(desc):
                values = set(listed.split("/"))
                if not any(values == set(v) for v in allowed.values()):
                    out.append(f"{section}: `{name}` 의 값 목록 {listed} 이 서버 허용 값과 다름: "
                               + "; ".join(f"{k}={'/'.join(v)}" for k, v in allowed.items()))
    return out


def draft() -> str:
    tools = tool_docs()
    ko = "\n".join(f"| `{name}` | {k} |" for name, (_, k) in tools.items())
    en = "\n".join(f"| `{name}` | {e} |" for name, (e, _) in tools.items())
    return f"## 도구 목록 (초안)\n\n{ko}\n\n### Tools (draft)\n\n{en}"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--draft"]:
        print(draft())
        return 0
    if argv:
        print("사용법 / usage: gen_tool_table.py [--draft]", file=sys.stderr)
        return 2
    found = problems()
    for line in found:
        print(f"[X ] {line}")
    print("README 도구 표가 서버와 같습니다 / README tool tables match the server" if not found
          else f"{len(found)}곳을 고치세요 / fix {len(found)} place(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
