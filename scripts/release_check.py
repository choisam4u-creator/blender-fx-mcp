"""출시 전 점검. 버전·CHANGELOG·server.json·빌드 결과가 서로 맞는지 한 번에 본다.

  uv run python scripts/release_check.py           # 파일만 점검 (몇 초)
  uv run python scripts/release_check.py --build   # uv build 로 휠을 만들어 METADATA 까지
  uv run python scripts/release_check.py --dist dist   # 이미 만든 휠·sdist 의 METADATA 만 (CI 패키징 점검)

`--dist` 는 판 번호·CHANGELOG 의 "미출시" 점검을 하지 않아 출시 전 PR 에서도 통과한다.
실패한 줄마다 고칠 곳을 적는다. 모두 통과하면 종료 코드 0, 하나라도 실패하면 1.
태그·PyPI·레지스트리 등록은 하지 않는다(그 순서는 docs/registry.md).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# CHANGELOG 의 판 절 제목: "## 0.7.0 — 2026-10-20" 또는 "## 0.7.0 — 미출시 (준비 중)"
HEADING = re.compile(r"^## (\d+\.\d+\.\d+) — (.+)$", re.M)
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def project_version(root: Path) -> str:
    m = re.search(r'^version = "([^"]+)"', (root / "pyproject.toml").read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else ""


def project_urls(root: Path) -> dict[str, str]:
    """pyproject.toml 의 [project.urls] (3.10 에도 돌도록 tomllib 없이 읽는다)."""
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r"^\[project\.urls\]\n(.*?)(?:^\[|\Z)", text, re.M | re.S)
    if not m:
        return {}
    return dict(re.findall(r'^(\w+)\s*=\s*"([^"]+)"', m.group(1), re.M))


def check_files(root: Path) -> list[tuple[bool, str]]:
    """(통과?, 설명) 목록. 설명에는 실패 시 고칠 곳이 들어 있다."""
    out: list[tuple[bool, str]] = []
    version = project_version(root)
    out.append((bool(version), f"pyproject.toml 판: {version or '(못 찾음 — [project] 의 version 줄 확인)'}"))

    init = (root / "src" / "blender_fx_mcp" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'__version__ = "([^"]+)"', init)
    got = m.group(1) if m else "(없음)"
    out.append((got == version, f"src/blender_fx_mcp/__init__.py __version__ = {got}"
                + ("" if got == version else f" → {version} 로 고친다")))

    server = json.loads((root / "server.json.example").read_text(encoding="utf-8"))
    out.append((server.get("version") == version, f"server.json.example version = {server.get('version')}"
                + ("" if server.get("version") == version else f" → {version} 로 고친다")))
    for i, pkg in enumerate(server.get("packages", [])):
        ok = pkg.get("version") == version
        out.append((ok, f"server.json.example packages[{i}].version = {pkg.get('version')}"
                    + ("" if ok else f" → {version} 로 고친다")))

    cff = root / "CITATION.cff"
    m = re.search(r'^version: "?([^"\n]+?)"?\s*$', cff.read_text(encoding="utf-8"), re.M) if cff.is_file() else None
    got = m.group(1) if m else "(없음)"
    out.append((got == version, f"CITATION.cff version = {got}"
                + ("" if got == version else f" → {version} 로 고친다")))

    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    m = HEADING.search(changelog)
    if not m:
        out.append((False, "CHANGELOG.md 에 '## X.Y.Z — 날짜' 절이 없음 → 맨 위에 이번 판 절을 만든다"))
    else:
        top, when = m.group(1), m.group(2).strip()
        out.append((top == version, f"CHANGELOG.md 맨 위 절 판 = {top}"
                    + ("" if top == version else f" → pyproject 판({version})과 다름. 버전 네 곳을 {top} 로 올리거나 절 제목을 고친다")))
        dated = bool(DATE.fullmatch(when))
        out.append((dated, f"CHANGELOG.md 맨 위 절 날짜 = {when}"
                    + ("" if dated else " → 아직 미출시. 제목의 '미출시 …' 를 출시 날짜(YYYY-MM-DD)로 바꾼다")))
        if top in [h for h, _ in HEADING.findall(changelog)[1:]]:
            out.append((False, f"CHANGELOG.md 에 {top} 절이 두 번 있음 → 하나로 합친다"))

    readme = (root / "README.md").read_text(encoding="utf-8")
    name = server.get("name", "")
    ok = f"mcp-name: {name}" in readme
    out.append((ok, f"README.md 의 mcp-name 줄({name})" + ("" if ok else " → 레지스트리 소유 확인용 줄을 README 맨 위에 넣는다")))
    return out


def project_license(root: Path) -> str:
    m = re.search(r'^license = "([^"]+)"', (root / "pyproject.toml").read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else ""


def read_metadata(dist: Path) -> str | None:
    """휠의 .dist-info/METADATA 또는 sdist 의 PKG-INFO. 없으면 None."""
    if dist.suffix == ".whl":
        with zipfile.ZipFile(dist) as z:
            name = next((n for n in z.namelist() if n.endswith(".dist-info/METADATA")), None)
            return z.read(name).decode("utf-8") if name else None
    with tarfile.open(dist) as t:
        member = next((m for m in t.getmembers() if m.name.count("/") == 1 and m.name.endswith("/PKG-INFO")), None)
        f = t.extractfile(member) if member else None
        return f.read().decode("utf-8") if f else None


def check_metadata(meta: str, label: str, version: str, urls: dict[str, str]) -> list[tuple[bool, str]]:
    """METADATA 의 판과 Project-URL 이 pyproject 와 같은지."""
    out: list[tuple[bool, str]] = []
    m = re.search(r"^Version: (.+)$", meta, re.M)
    got = m.group(1).strip() if m else "(없음)"
    out.append((got == version, f"{label} METADATA Version = {got}"
                + ("" if got == version else f" → pyproject 판({version})과 다름")))
    found = dict(re.findall(r"^Project-URL: ([^,]+), (.+)$", meta, re.M))
    found = {k.strip().lower(): v.strip() for k, v in found.items()}
    for key, url in urls.items():
        ok = found.get(key.lower()) == url
        out.append((ok, f"{label} METADATA Project-URL {key}" + ("" if ok else f" → 없거나 다름(pyproject: {url})")))
    return out


def check_package(meta: str, label: str, license: str, readme: str) -> list[tuple[bool, str]]:
    """PyPI 화면에 필요한 것: License-Expression, 마크다운 README 본문, 레지스트리용 mcp-name 줄."""
    out: list[tuple[bool, str]] = []
    m = re.search(r"^License-Expression: (.+)$", meta, re.M)
    got = m.group(1).strip() if m else "(없음)"
    out.append((got == license, f"{label} METADATA License-Expression = {got}"
                + ("" if got == license else f" → pyproject 의 license(\"{license}\")와 다름")))
    m = re.search(r"^Description-Content-Type: (.+)$", meta, re.M)
    ctype = m.group(1).strip() if m else "(없음)"
    ok = ctype.startswith("text/markdown")
    out.append((ok, f"{label} README 형식 = {ctype}" + ("" if ok else " → pyproject 의 readme 가 README.md 인지 확인")))
    head, sep, body = meta.partition("\n\n")
    first = readme.strip().splitlines()[0] if readme.strip() else ""
    ok = bool(sep) and bool(first) and body.lstrip().startswith(first)
    out.append((ok, f"{label} README 본문" + ("" if ok else " → 패키지 설명에 README.md 가 들어가지 않음(pyproject 의 readme 확인)")))
    ok = "mcp-name: " in body
    out.append((ok, f"{label} README 의 mcp-name 줄" + ("" if ok else " → 레지스트리가 소유를 확인하지 못함. README 맨 위에 넣는다")))
    return out


def check_wheel(wheel: Path, version: str, urls: dict[str, str]) -> list[tuple[bool, str]]:
    """휠 METADATA 의 판과 Project-URL 이 pyproject 와 같은지."""
    meta = read_metadata(wheel)
    if meta is None:
        return [(False, f"{wheel.name} 안에 METADATA 가 없음 → 빌드 설정([build-system]) 확인")]
    return check_metadata(meta, "휠", version, urls)


def check_dist(dist_dir: Path, root: Path) -> list[tuple[bool, str]]:
    """이미 만든 휠·sdist 를 모두 점검한다(판·Project-URL·라이선스·README)."""
    version, urls = project_version(root), project_urls(root)
    license = project_license(root)
    readme = (root / "README.md").read_text(encoding="utf-8")
    out: list[tuple[bool, str]] = []
    for kind, pattern in (("휠", "*.whl"), ("sdist", "*.tar.gz")):
        found = sorted(dist_dir.glob(pattern))
        if not found:
            out.append((False, f"{dist_dir} 에 {kind}({pattern})가 없음 → 먼저 `uv build` 를 돌린다"))
            continue
        for dist in found:
            label = f"{kind} {dist.name}"
            meta = read_metadata(dist)
            if meta is None:
                out.append((False, f"{label} 안에 METADATA 가 없음 → 빌드 설정([build-system]) 확인"))
                continue
            out += check_metadata(meta, label, version, urls) + check_package(meta, label, license, readme)
    return out


def build_wheel(root: Path, dest: Path) -> Path:
    subprocess.run(["uv", "build", "--wheel", "--out-dir", str(dest)], cwd=root, check=True,
                   stdout=subprocess.DEVNULL)
    wheels = sorted(dest.glob("*.whl"))
    if not wheels:
        raise RuntimeError("uv build 가 휠을 만들지 않음")
    return wheels[-1]


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--dist" in argv:
        i = argv.index("--dist")
        if i + 1 >= len(argv):
            print("FAIL --dist 뒤에 휠·sdist 가 있는 폴더를 적는다 (예: --dist dist)")
            return 1
        results = check_dist(Path(argv[i + 1]), root)
        return _report(results, "패키지 점검 통과")
    results = check_files(root)
    if "--build" in argv:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                wheel = build_wheel(root, Path(tmp))
                results += check_wheel(wheel, project_version(root), project_urls(root))
            except (subprocess.CalledProcessError, RuntimeError, FileNotFoundError) as e:
                results.append((False, f"uv build 실패: {e} → `uv build` 를 직접 돌려 오류를 본다"))
    return _report(results, "출시 준비 완료")


def _report(results: list[tuple[bool, str]], done: str) -> int:
    for ok, line in results:
        print(("OK   " if ok else "FAIL ") + line)
    failed = sum(1 for ok, _ in results if not ok)
    print(f"\n{done if not failed else f'고칠 곳 {failed}개'} (점검 {len(results)}개)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
