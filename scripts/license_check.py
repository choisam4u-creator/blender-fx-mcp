"""런타임 의존성 라이선스 점검. `uv.lock` 에서 blender-fx-mcp 가 끌어오는 패키지를 모두 모아(추가 기능·플랫폼 조건 포함)
MIT 프로젝트와 함께 배포해도 되는 허용 목록 안인지, `docs/third-party-licenses.md` 표와 같은지 본다.

  uv run python scripts/license_check.py

설치된 패키지는 실제 메타데이터(License-Expression → License 분류자 → License 칸)로 확인하고,
이 환경에 설치되지 않은 패키지(다른 OS·파이썬 판 전용)는 표의 값만 허용 목록과 대조한다. Python 3.11+(tomllib).
"""

from __future__ import annotations

import re
import sys
import tomllib
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "docs" / "third-party-licenses.md"

# MIT 와 함께 배포·재배포해도 되는 허용적(permissive) 라이선스. 카피레프트(GPL·LGPL·AGPL)는 넣지 않는다.
ALLOWED = {"MIT", "MIT-0", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0", "ISC", "PSF-2.0", "MPL-2.0", "Unlicense", "0BSD"}

# 옛 License 분류자·자유 문장을 SPDX 이름으로
CLASSIFIERS = {
    "License :: OSI Approved :: MIT License": "MIT",
    "License :: OSI Approved :: BSD License": "BSD-3-Clause",
    "License :: OSI Approved :: Apache Software License": "Apache-2.0",
    "License :: OSI Approved :: ISC License (ISCL)": "ISC",
    "License :: OSI Approved :: Python Software Foundation License": "PSF-2.0",
    "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
}


def runtime_packages(lock_path: Path = ROOT / "uv.lock") -> list[str]:
    """blender-fx-mcp 에서 출발해 dependencies 와 요청된 extra 를 따라간 패키지 이름(자기 자신 제외)."""
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    packages = {p["name"]: p for p in lock["package"]}
    seen: set[str] = set()
    todo: list[tuple[str, tuple[str, ...]]] = [("blender-fx-mcp", ())]
    while todo:
        name, extras = todo.pop()
        key = f"{name}[{','.join(extras)}]"
        if key in seen:
            continue
        seen.add(key)
        pkg = packages[name]
        deps = list(pkg.get("dependencies", []))
        for extra in extras:
            deps += pkg.get("optional-dependencies", {}).get(extra, [])
        todo += [(d["name"], tuple(d.get("extra", ()))) for d in deps]
    return sorted({k.split("[")[0] for k in seen} - {"blender-fx-mcp"})


def installed_license(name: str) -> str | None:
    """설치돼 있으면 SPDX 식 라이선스, 아니면 None. 알 수 없으면 '?'."""
    try:
        meta = metadata.metadata(name)
    except metadata.PackageNotFoundError:
        return None
    if meta.get("License-Expression"):
        return meta["License-Expression"].strip()
    for c in meta.get_all("Classifier") or []:
        if c in CLASSIFIERS:
            return CLASSIFIERS[c]
    text = (meta.get("License") or "").strip()
    return text if text in ALLOWED else "?"


def expression_allowed(expr: str) -> bool:
    """`A OR B` 는 하나만, `A AND B` 는 모두 허용 목록이면 통과."""
    if " OR " in expr:
        return any(expression_allowed(part) for part in expr.strip("()").split(" OR "))
    return all(part.strip("() ") in ALLOWED for part in expr.split(" AND "))


def table_licenses(path: Path | None = None) -> dict[str, str]:
    text = (path or TABLE).read_text(encoding="utf-8")
    rows = re.findall(r"^\| `([\w.-]+)` \| `([^`]+)` \|", text, re.M)
    return dict(rows)


def check() -> list[tuple[bool, str]]:
    table = table_licenses()
    packages = runtime_packages()
    out = []
    for name in packages:
        documented = table.get(name)
        actual = installed_license(name)
        if documented is None:
            out.append((False, f"{name}: docs/third-party-licenses.md 표에 없음 / missing from the table"))
        elif actual is not None and actual != documented:
            out.append((False, f"{name}: 설치본은 {actual}, 표는 {documented} / installed {actual}, table {documented}"))
        elif not expression_allowed(documented):
            out.append((False, f"{name}: {documented} 은 허용 목록 밖 / not in the allowed list"))
        else:
            where = "" if actual is not None else " (이 환경에 설치 안 됨, 표 값으로 확인 / not installed here)"
            out.append((True, f"{name}: {documented}{where}"))
    for name in sorted(set(table) - set(packages)):
        out.append((False, f"{name}: 표에 있지만 이제 의존성이 아님 / in the table but no longer a dependency"))
    return out


def main() -> int:
    results = check()
    for ok, line in results:
        print(f"[{'OK' if ok else 'X '}] {line}")
    bad = sum(not ok for ok, _ in results)
    print(f"{len(results) - bad}/{len(results)} OK" + ("" if not bad else " — docs/third-party-licenses.md 를 고치세요"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
