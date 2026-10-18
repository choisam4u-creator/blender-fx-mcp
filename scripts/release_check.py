# SPDX-License-Identifier: MIT
"""출시 전 점검. 버전·CHANGELOG·server.json·빌드 결과가 서로 맞는지 한 번에 본다.

  uv run python scripts/release_check.py           # 파일만 점검 (몇 초)
  uv run python scripts/release_check.py --build   # uv build 로 휠을 만들어 METADATA 까지
  uv run python scripts/release_check.py --dist dist   # 이미 만든 휠·sdist 의 METADATA 만 (CI 패키징 점검)
  uv run python scripts/release_check.py --tag v0.7.0  # 파일 점검 + 밀 태그가 pyproject 판과 같은지 (release.yml 과 같은 규칙)

파일 점검에는 해결법 대응표(`gen_help_index.py`)와 `scripts/lint.sh --print` 가 CI lint 단계와 같은지,
Mac 실측(`docs/test-reports/latest.md`)이 PASS 이고 30일 안인지도 든다.
`--dist` 는 판 번호·CHANGELOG 의 "미출시" 점검을 하지 않아 출시 전 PR 에서도 통과한다.
실패한 줄마다 고칠 곳을 적는다. 모두 통과하면 종료 코드 0, 하나라도 실패하면 1.
태그·PyPI·레지스트리 등록은 하지 않는다(그 순서는 docs/registry.md).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# CHANGELOG 의 판 절 제목: "## [0.7.0] - 2026-10-11"(Keep a Changelog), 옛 "## 0.6.3 — 2026-09-21", 또는 "## 0.8.0 — 미출시 (준비 중)"
HEADING = re.compile(r"^## \[?(\d+\.\d+\.\d+)\]? (?:—|-) (.+)$", re.M)
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
# PyPI 가 받는 Metadata-Version. hatchling 은 2026-10 기준 2.5 를 쓰며, 2.5 를 받는 twine 은 7.0.0 부터다(6.x check 는 거부).
# 새 판이 나와 빌드가 그 판을 쓰면 PyPI·twine 지원을 확인한 뒤 여기 더한다.
METADATA_VERSIONS = ("2.1", "2.2", "2.3", "2.4", "2.5")


def project_version(root: Path) -> str:
    m = re.search(r'^version = "([^"]+)"', (root / "pyproject.toml").read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else ""


def project_urls(root: Path) -> dict[str, str]:
    """pyproject.toml 의 [project.urls] (tomllib 없이 정규식으로 읽는다. 시험이 tomllib 결과와 같은지 본다)."""
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
        out.append((False, "CHANGELOG.md 에 '## [X.Y.Z] - 날짜' 절이 없음 → 맨 위에 이번 판 절을 만든다"))
    else:
        top, when = m.group(1), m.group(2).strip()
        out.append((top == version, f"CHANGELOG.md 맨 위 절 판 = {top}"
                    + ("" if top == version else f" → pyproject 판({version})과 다름. 버전 네 곳을 {top} 로 올리거나 절 제목을 고친다")))
        dated = bool(DATE.fullmatch(when))
        out.append((dated, f"CHANGELOG.md 맨 위 절 날짜 = {when}"
                    + ("" if dated else " → 아직 미출시. 제목의 '미출시 …' 를 출시 날짜(YYYY-MM-DD)로 바꾼다")))
        if top in [h for h, _ in HEADING.findall(changelog)[1:]]:
            out.append((False, f"CHANGELOG.md 에 {top} 절이 두 번 있음 → 하나로 합친다"))

        if dated:  # 출시하면 지원 판 표에서 지난 판(PyPI 최신이라 함께 지원하던 것)을 뺀다
            out += check_supported(root, version)

    readme = (root / "README.md").read_text(encoding="utf-8")
    name = server.get("name", "")
    ok = f"mcp-name: {name}" in readme
    out.append((ok, f"README.md 의 mcp-name 줄({name})" + ("" if ok else " → 레지스트리 소유 확인용 줄을 README 맨 위에 넣는다")))
    out += check_generated(root)
    out += check_mac_report(root)
    return out


MAC_REPORT = Path("docs") / "test-reports" / "latest.md"
MAC_REPORT_DAYS = 30  # 실제 블렌더로 돌린 결과가 이보다 오래면 출시 전에 다시


def check_mac_report(root: Path, today: date | None = None) -> list[tuple[bool, str]]:
    """Mac 에서 실제 블렌더로 돌린 결과(latest.md)가 PASS 이고 MAC_REPORT_DAYS 일 안인지. 클라우드·CI 는 블렌더 앱이 없어
    이 결과만이 앱에서 도는지의 근거다. 파일이 없는 저장소(시험용 복사본)는 건너뛴다."""
    path = root / MAC_REPORT
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    when = re.search(r"^- 날짜: (\d{4}-\d{2}-\d{2})", text, re.M)
    verdict = re.search(r"^- 종합: \**(PASS|FAIL)\b", text, re.M)
    again = " → Mac 에서 `uv run python scripts/mac_report.py` 를 다시 돌려 latest.md 를 새로 쓰고 커밋한다"
    if not when or not verdict:
        return [(False, f"{MAC_REPORT.as_posix()}: '- 날짜:'·'- 종합:' 줄을 못 읽음" + again)]
    age = ((today or date.today()) - date.fromisoformat(when.group(1))).days
    ok = verdict.group(1) == "PASS" and age <= MAC_REPORT_DAYS
    why = []
    if verdict.group(1) != "PASS":
        why.append("FAIL 항목을 먼저 고친 뒤")
    if age > MAC_REPORT_DAYS:
        why.append(f"{MAC_REPORT_DAYS}일 넘음")
    return [(ok, f"Mac 실측(latest.md) = {verdict.group(1)}, {when.group(1)}({age}일 전)"
             + ("" if ok else f" ({', '.join(why)})" + again))]


def ci_lint_commands(root: Path) -> list[str]:
    """ci.yml lint 잡의 ruff·actionlint·zizmor 단계 명령(tests/test_lint_script.py 와 같은 읽기)."""
    ci = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    lint = ci.split("\n  lint:\n", 1)[-1].split("\n  server-tests:", 1)[0]
    return [c for c in re.findall(r"^      - run: (.*)$", lint, re.M) if re.search(r"\b(ruff|actionlint|zizmor)\b", c)]


def check_generated(root: Path) -> list[tuple[bool, str]]:
    """만든 파일·명령이 원본과 같은지: 해결법 대응표(gen_help_index.py), scripts/lint.sh --print = CI lint 단계.
    둘 다 pytest 도 지키지만 출시 절차는 이 스크립트 하나만 돌리므로 여기서도 본다. 스크립트가 없는 저장소(시험용 복사본)는 건너뛴다."""
    out: list[tuple[bool, str]] = []
    gen = root / "scripts" / "gen_help_index.py"
    if gen.is_file():
        r = subprocess.run([sys.executable, str(gen)], cwd=root, capture_output=True, text=True, check=False)
        out.append((r.returncode == 0, "해결법 대응표(src/blender_fx_mcp/help_index.py) = 문서·레시피·서버 오류 문장"
                    + ("" if r.returncode == 0 else " → 다름. `uv run python scripts/gen_help_index.py --write` 로 새로 쓰고 커밋한다")))
    lint = root / "scripts" / "lint.sh"
    if lint.is_file():
        bash = shutil.which("bash")
        if bash is None:
            out.append((True, "scripts/lint.sh --print: bash 가 없어 건너뜀(macOS·Linux 에서 다시 돌린다)"))
        else:
            r = subprocess.run([bash, str(lint), "--print"], cwd=root, capture_output=True, text=True, check=False)
            got, want = r.stdout.splitlines(), ci_lint_commands(root)
            ok = r.returncode == 0 and got == want
            hint = (f" → 다름. lint.sh: {got or r.stderr.strip()} / ci.yml: {want}. CONTRIBUTING 의 판 표와 ci.yml lint 단계의 판을 맞춘다"
                    if not ok else "")
            out.append((ok, f"scripts/lint.sh --print = CI lint 단계({len(want)}개)" + hint))
    return out


def supported_series(root: Path) -> dict[str, list[str]]:
    """SECURITY.md 에서 보안 수정 '예' 인 판 계열, SUPPORT.md 의 blender-fx-mcp 줄 판 계열(예: ["0.8", "0.7"])."""
    sec = (root / "SECURITY.md").read_text(encoding="utf-8")
    sup = (root / "SUPPORT.md").read_text(encoding="utf-8")
    return {"SECURITY.md": re.findall(r"^\| (\d+\.\d+)\.x[^|]*\| 예", sec, re.M),
            "SUPPORT.md": re.findall(r"^\| blender-fx-mcp \| (\d+\.\d+)\.x", sup, re.M)}


def check_supported(root: Path, version: str) -> list[tuple[bool, str]]:
    """출시한 판의 계열 하나만 지원 판으로 남았는지. 출시 전에는 PyPI 최신 판도 함께 적어 두므로 출시 때 정리한다."""
    series = ".".join(version.split(".")[:2])
    out = []
    for name, got in supported_series(root).items():
        ok = got == [series]
        out.append((ok, f"{name} 지원 판 = {', '.join(s + '.x' for s in got) or '(없음)'}"
                    + ("" if ok else f" → 출시했으니 지원 판 줄을 {series}.x 하나로 정리한다(지난 판 줄은 지운다)")))
    return out


def check_tag(tag: str, version: str) -> list[tuple[bool, str]]:
    """태그는 'v' + pyproject 판이어야 한다. release.yml 의 build 잡도 이 함수로 본다(규칙이 한 곳)."""
    want = f"v{version}"
    if tag == want:
        return [(True, f"태그 {tag} = pyproject 판 {version}")]
    if tag == version:
        hint = f"앞에 v 가 빠짐 → {want} 로 단다(release.yml 은 v* 태그에만 돈다)"
    else:
        hint = (f"pyproject 판({version})과 다름 → 버전 네 곳을 {tag.lstrip('v')} 로 올린 커밋에 태그를 달거나, "
                f"태그를 {want} 로 고친다. 이미 밀었으면 `git push --delete origin {tag}` 뒤 다시")
    return [(False, f"태그 {tag or '(빈 값)'}: {hint}")]


def project_license(root: Path) -> str:
    m = re.search(r'^license = "([^"]+)"', (root / "pyproject.toml").read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else ""


def read_metadata(dist: Path) -> str | None:
    """휠의 .dist-info/METADATA 또는 sdist 의 PKG-INFO. 없으면 None."""
    # Windows 체크아웃(core.autocrlf)에서 만든 패키지는 README 가 CRLF 로 들어간다. README.md 와 비교할 수 있게 LF 로 맞춘다.
    if dist.suffix == ".whl":
        with zipfile.ZipFile(dist) as z:
            name = next((n for n in z.namelist() if n.endswith(".dist-info/METADATA")), None)
            return z.read(name).decode("utf-8").replace("\r\n", "\n") if name else None
    with tarfile.open(dist) as t:
        member = next((m for m in t.getmembers() if m.name.count("/") == 1 and m.name.endswith("/PKG-INFO")), None)
        f = t.extractfile(member) if member else None
        return f.read().decode("utf-8").replace("\r\n", "\n") if f else None


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
    """PyPI 가 받고 화면에 필요한 것: Metadata-Version, License-Expression, 마크다운 README 본문, 레지스트리용 mcp-name 줄."""
    out: list[tuple[bool, str]] = []
    m = re.search(r"^Metadata-Version: (.+)$", meta, re.M)
    mv = m.group(1).strip() if m else "(없음)"
    ok = mv in METADATA_VERSIONS
    out.append((ok, f"{label} Metadata-Version = {mv}" + ("" if ok else
                f" → PyPI 가 받는지 모름(허용: {', '.join(METADATA_VERSIONS)}). [build-system] 의 hatchling 판을 확인")))
    m = re.search(r"^License-Expression: (.+)$", meta, re.M)
    got = m.group(1).strip() if m else "(없음)"
    out.append((got == license, f"{label} METADATA License-Expression = {got}"
                + ("" if got == license else f" → pyproject 의 license(\"{license}\")와 다름")))
    m = re.search(r"^Description-Content-Type: (.+)$", meta, re.M)
    ctype = m.group(1).strip() if m else "(없음)"
    ok = ctype.startswith("text/markdown")
    out.append((ok, f"{label} README 형식 = {ctype}" + ("" if ok else " → pyproject 의 readme 가 README.md 인지 확인")))
    _head, sep, body = meta.partition("\n\n")
    first = readme.strip().splitlines()[0] if readme.strip() else ""
    ok = bool(sep) and bool(first) and body.lstrip().startswith(first)
    out.append((ok, f"{label} README 본문" + ("" if ok else " → 패키지 설명에 README.md 가 들어가지 않음(pyproject 의 readme 확인)")))
    ok = "mcp-name: " in body
    out.append((ok, f"{label} README 의 mcp-name 줄" + ("" if ok else " → 레지스트리가 소유를 확인하지 못함. README 맨 위에 넣는다")))
    return out


def check_license_files(dist: Path, label: str) -> list[tuple[bool, str]]:
    """배포물만 받은 사람도 라이선스 본문을 보게: 휠은 .dist-info/licenses/LICENSE, sdist 는 LICENSE 와 제3자 라이선스 표."""
    if dist.suffix == ".whl":
        with zipfile.ZipFile(dist) as z:
            names = z.namelist()
        need = {"LICENSE": any(n.endswith(".dist-info/licenses/LICENSE") for n in names)}
    else:
        with tarfile.open(dist) as t:
            names = ["/".join(n.split("/")[1:]) for n in t.getnames()]
        need = {"LICENSE": "LICENSE" in names, "docs/third-party-licenses.md": "docs/third-party-licenses.md" in names}
    return [(ok, f"{label} 에 {name} 포함" + ("" if ok else " → pyproject 의 license-files·sdist 포함 목록 확인"))
            for name, ok in need.items()]


def check_wheel(wheel: Path, version: str, urls: dict[str, str]) -> list[tuple[bool, str]]:
    """휠 METADATA 의 판과 Project-URL 이 pyproject 와 같은지."""
    meta = read_metadata(wheel)
    if meta is None:
        return [(False, f"{wheel.name} 안에 METADATA 가 없음 → 빌드 설정([build-system]) 확인")]
    return check_metadata(meta, "휠", version, urls)


def check_dist(dist_dir: Path, root: Path) -> list[tuple[bool, str]]:
    """이미 만든 휠·sdist 를 모두 점검한다(판·Project-URL·라이선스·README·라이선스 파일)."""
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
            out += check_license_files(dist, label)
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
    if "--tag" in argv:
        i = argv.index("--tag")
        if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
            print("FAIL --tag 뒤에 밀 태그를 적는다 (예: --tag v0.7.0)")
            return 1
        results += check_tag(argv[i + 1], project_version(root))
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
