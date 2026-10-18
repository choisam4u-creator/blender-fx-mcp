# scripts/release_check.py(출시 전 점검) 시험. 블렌더 없이 돈다.
import importlib.util
import re
import shutil
import subprocess
import tarfile
import tomllib
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("release_check", ROOT / "scripts" / "release_check.py")
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)


@pytest.fixture
def repo(tmp_path):
    """점검에 쓰는 파일만 복사한 가짜 저장소."""
    for f in ("pyproject.toml", "server.json.example", "CHANGELOG.md", "README.md", "src/blender_fx_mcp/__init__.py",
              "CITATION.cff", "SECURITY.md", "SUPPORT.md"):
        (tmp_path / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / f, tmp_path / f)
    return tmp_path


def _release(root: Path, version: str = "9.9.9", date: str = "2026-12-01") -> None:
    """출시 순서대로 버전 네 곳과 CHANGELOG 맨 위 절을 맞춘다."""
    old = rc.project_version(root)
    for f in ("pyproject.toml", "server.json.example", "src/blender_fx_mcp/__init__.py", "CITATION.cff"):
        p = root / f
        p.write_text(p.read_text(encoding="utf-8").replace(f'"{old}"', f'"{version}"'), encoding="utf-8")
    cl = root / "CHANGELOG.md"
    text = cl.read_text(encoding="utf-8")
    m = rc.HEADING.search(text)
    cl.write_text(text[:m.start()] + f"## {version} — {date}" + text[m.end():], encoding="utf-8")
    _support_only(root, version)


def _support_only(root: Path, version: str) -> None:
    """출시 순서의 '지원 판 표 정리': blender-fx-mcp 판 줄을 새 판 계열 하나로."""
    series = ".".join(version.split(".")[:2])
    for f, row in (("SECURITY.md", f"| {series}.x (최신 / latest) | 예 / yes |"),
                   ("SUPPORT.md", f"| blender-fx-mcp | {series}.x (최신 / latest) | 버그·보안 수정 / bug and security fixes |")):
        p = root / f
        lines = p.read_text(encoding="utf-8").splitlines()
        pick = (lambda x: re.match(r"\| \d+\.\d+\.x", x)) if f == "SECURITY.md" else (lambda x: x.startswith("| blender-fx-mcp |"))
        first = next(i for i, x in enumerate(lines) if pick(x))
        lines = [x for i, x in enumerate(lines) if i == first or not pick(x)]
        lines[first] = row
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fails(results):
    return [line for ok, line in results if not ok]


def test_current_repo_state():
    """준비 중(맨 위 절이 '미출시', 버전은 아직 이전 판)이면 정확히 '판 다름'과 '미출시' 두 줄만,
    판을 올리고 날짜만 기다리면 '미출시' 한 줄만 실패하고, 출시 순서를 마친 뒤(날짜가 붙음)에는 모두 통과해야 한다."""
    fails = _fails(rc.check_files(ROOT))
    # Mac 실측 줄은 저장소 진행이 아니라 Mac 에서 마지막으로 돌린 때를 따른다(따로 시험). 여기서는 한 줄 있는지만
    assert sum(f.startswith("Mac 실측(latest.md)") for f in fails) <= 1
    fails = [f for f in fails if not f.startswith("Mac 실측(latest.md)")]
    top_version, when = rc.HEADING.search((ROOT / "CHANGELOG.md").read_text(encoding="utf-8")).groups()
    if rc.DATE.fullmatch(when.strip()):
        assert fails == []
        return
    if top_version == rc.project_version(ROOT):  # 판은 올렸고 출시 날짜만 기다림: '미출시' 한 줄만
        assert len(fails) == 1 and "미출시" in fails[0] and "YYYY-MM-DD" in fails[0], fails
        return
    assert len(fails) == 2, fails
    assert "CHANGELOG.md 맨 위 절 판" in fails[0] and "pyproject 판" in fails[0]
    assert "미출시" in fails[1] and "YYYY-MM-DD" in fails[1]


def test_release_requires_support_tables_trimmed(repo):
    """출시 전에는 PyPI 최신 판(0.7.x)도 지원으로 적어 둔다. 출시(날짜를 붙임)한 뒤에도 그대로면 정리하라고 알린다."""
    assert rc.supported_series(ROOT)["SECURITY.md"][:1] == [".".join(rc.project_version(ROOT).split(".")[:2])]
    _release(repo)
    for f, row in (("SECURITY.md", "| 9.8.x (PyPI 최신 / latest on PyPI) | 예 — 9.9.0 이 나올 때까지 / yes |"),
                   ("SUPPORT.md", "| blender-fx-mcp | 9.8.x (PyPI) | 버그·보안 수정 |")):
        p = repo / f
        text = p.read_text(encoding="utf-8")
        anchor = "| 9.9.x (최신 / latest) | 예 / yes |" if f == "SECURITY.md" else "| blender-fx-mcp | 9.9.x"
        i = text.index(anchor)
        j = text.index("\n", i) + 1
        p.write_text(text[:j] + row + "\n" + text[j:], encoding="utf-8")
    fails = _fails(rc.check_files(repo))
    assert len(fails) == 2, fails
    assert all("9.9.x, 9.8.x" in f and "9.9.x 하나로 정리" in f for f in fails), fails


def test_released_state_passes(repo, capsys):
    _release(repo)
    assert _fails(rc.check_files(repo)) == []
    assert rc.main([], root=repo) == 0
    assert "출시 준비 완료" in capsys.readouterr().out


@pytest.mark.parametrize("path,label", [
    ("src/blender_fx_mcp/__init__.py", "__init__.py __version__ = 0.0.1 → 9.9.9 로 고친다"),
    ("server.json.example", "server.json.example version = 0.0.1 → 9.9.9 로 고친다"),
    ("CITATION.cff", "CITATION.cff version = 0.0.1 → 9.9.9 로 고친다"),
])
def test_version_mismatch_names_the_file(repo, path, label):
    _release(repo)
    p = repo / path
    p.write_text(p.read_text(encoding="utf-8").replace('"9.9.9"', '"0.0.1"', 1), encoding="utf-8")
    assert any(label in line for line in _fails(rc.check_files(repo)))


def test_duplicate_changelog_section(repo):
    _release(repo)
    cl = repo / "CHANGELOG.md"
    cl.write_text(cl.read_text(encoding="utf-8") + "\n## 9.9.9 — 2026-11-01\n", encoding="utf-8")
    assert any("두 번" in line for line in _fails(rc.check_files(repo)))


def test_missing_mcp_name_and_changelog_heading(repo):
    _release(repo)
    (repo / "README.md").write_text("# x\n", encoding="utf-8")
    (repo / "CHANGELOG.md").write_text("# 변경 이력\n", encoding="utf-8")
    fails = _fails(rc.check_files(repo))
    assert any("mcp-name" in line for line in fails)
    assert any("절이 없음" in line for line in fails)


def test_project_urls_read_without_tomllib():
    urls = rc.project_urls(ROOT)
    assert set(urls) == {"Homepage", "Documentation", "Issues", "Changelog", "Security"}
    assert urls == tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["urls"]


def _wheel(tmp_path, meta: str, license_file: bool = True) -> Path:
    w = tmp_path / "x-1.0-py3-none-any.whl"
    with zipfile.ZipFile(w, "w") as z:
        z.writestr("x-1.0.dist-info/METADATA", meta)
        if license_file:
            z.writestr("x-1.0.dist-info/licenses/LICENSE", "MIT License")
    return w


def test_wheel_metadata_checked(tmp_path):
    urls = {"Homepage": "https://h", "Issues": "https://i"}
    good = _wheel(tmp_path, "Metadata-Version: 2.4\nName: x\nVersion: 1.0\n"
                            "Project-URL: Homepage, https://h\nProject-URL: Issues, https://i\n")
    assert _fails(rc.check_wheel(good, "1.0", urls)) == []
    bad = _wheel(tmp_path, "Metadata-Version: 2.4\nName: x\nVersion: 0.9\nProject-URL: Homepage, https://h\n")
    fails = _fails(rc.check_wheel(bad, "1.0", urls))
    assert any("Version = 0.9" in line for line in fails) and any("Issues" in line for line in fails)


def test_wheel_without_metadata(tmp_path):
    w = tmp_path / "empty.whl"
    with zipfile.ZipFile(w, "w") as z:
        z.writestr("x/__init__.py", "")
    assert "METADATA 가 없음" in _fails(rc.check_wheel(w, "1.0", {}))[0]


def test_build_failure_is_reported(repo, monkeypatch, capsys):
    _release(repo)

    def no_uv(root, dest):
        raise FileNotFoundError("uv")
    monkeypatch.setattr(rc, "build_wheel", no_uv)
    assert rc.main(["--build"], root=repo) == 1
    assert "FAIL uv build 실패" in capsys.readouterr().out


def test_build_checks_wheel(repo, monkeypatch, tmp_path, capsys):
    """--build 는 만든 휠을 check_wheel 로 넘긴다(실제 빌드 대신 가짜 휠)."""
    _release(repo)
    urls = rc.project_urls(repo)
    meta = "Version: 9.9.9\n" + "".join(f"Project-URL: {k}, {v}\n" for k, v in urls.items())
    monkeypatch.setattr(rc, "build_wheel", lambda root, dest: _wheel(tmp_path, meta))
    assert rc.main(["--build"], root=repo) == 0
    assert "OK   휠 METADATA Version = 9.9.9" in capsys.readouterr().out


def _meta(root: Path, **override) -> str:
    """pyproject·README 와 맞는 METADATA. override 로 한 줄씩 깨뜨린다."""
    fields = {
        "Metadata-Version": "2.5",
        "Version": rc.project_version(root),
        "License-Expression": rc.project_license(root),
        "Description-Content-Type": "text/markdown",
    }
    fields.update(override)
    head = "".join(f"{k}: {v}\n" for k, v in fields.items() if v is not None)
    head += "".join(f"Project-URL: {k}, {v}\n" for k, v in rc.project_urls(root).items())
    return head + "\n" + (root / "README.md").read_text(encoding="utf-8")


def _sdist(path: Path, meta: str, extra=("LICENSE", "docs/third-party-licenses.md")) -> Path:
    src = path.parent / "pkginfo"
    src.write_text(meta, encoding="utf-8")
    with tarfile.open(path, "w:gz") as t:
        t.add(src, arcname="blender_fx_mcp-1.0/PKG-INFO")
        for name in extra:
            t.add(src, arcname=f"blender_fx_mcp-1.0/{name}")
    return path


def test_dist_passes_on_unreleased_repo(repo, tmp_path, capsys):
    """--dist 는 '미출시' 판 점검을 하지 않아 지금 저장소에서도 통과해야 한다(CI 패키징 점검)."""
    dist = tmp_path / "dist"
    dist.mkdir()
    meta = _meta(repo)
    _wheel(dist, meta)
    _sdist(dist / "x-1.0.tar.gz", meta)
    assert rc.main(["--dist", str(dist)], root=repo) == 0
    out = capsys.readouterr().out
    assert "패키지 점검 통과" in out and "sdist x-1.0.tar.gz README 의 mcp-name 줄" in out


@pytest.mark.parametrize("override, expect", [
    ({"Version": "0.0.1"}, "Version = 0.0.1"),
    ({"License-Expression": "GPL-3.0"}, "License-Expression = GPL-3.0"),
    ({"License-Expression": None}, "License-Expression = (없음)"),
    ({"Description-Content-Type": "text/x-rst"}, "README 형식 = text/x-rst"),
    ({"Metadata-Version": "3.0"}, "Metadata-Version = 3.0"),
    ({"Metadata-Version": "2.0"}, "Metadata-Version = 2.0"),
    ({"Metadata-Version": None}, "Metadata-Version = (없음)"),
])
def test_dist_metadata_errors_name_the_field(repo, tmp_path, override, expect):
    dist = tmp_path / "dist"
    dist.mkdir()
    _wheel(dist, _meta(repo, **override))
    _sdist(dist / "x-1.0.tar.gz", _meta(repo))
    fails = _fails(rc.check_dist(dist, repo))
    assert len(fails) == 1 and expect in fails[0] and fails[0].startswith("휠 ")


def test_dist_readme_missing_from_description(repo, tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    meta = _meta(repo).split("\n\n", 1)[0] + "\n\nsomething else\n"
    _sdist(dist / "x-1.0.tar.gz", meta)
    _wheel(dist, _meta(repo))
    fails = _fails(rc.check_dist(dist, repo))
    assert any("README 본문" in f for f in fails) and any("mcp-name" in f for f in fails)
    assert all(f.startswith("sdist ") for f in fails)


def test_dist_missing_files_and_metadata(repo, tmp_path, capsys):
    empty = tmp_path / "empty"
    empty.mkdir()
    fails = _fails(rc.check_dist(empty, repo))
    assert len(fails) == 2 and all("uv build" in f for f in fails)
    broken = tmp_path / "broken"
    broken.mkdir()
    with zipfile.ZipFile(broken / "x-1.0-py3-none-any.whl", "w") as z:
        z.writestr("x/__init__.py", "")
    with tarfile.open(broken / "x-1.0.tar.gz", "w:gz"):
        pass
    fails = _fails(rc.check_dist(broken, repo))
    assert len(fails) == 2 and all("METADATA 가 없음" in f for f in fails)
    assert rc.main(["--dist"], root=repo) == 1
    assert "--dist 뒤에" in capsys.readouterr().out


def test_ci_checks_built_packages():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "uv build\n" in ci
    assert ci.index("uv build\n") < ci.index("release_check.py --dist dist")


def test_metadata_versions_cover_current_build():
    """허용 목록이 PyPI 가 받는 판(2.1~)이고, 지금 빌드 백엔드가 쓰는 2.5 를 포함한다.
    2.5 를 받는 twine 이 7.0.0 부터라 CI·registry.md 가 그 판 이상의 twine 을 쓰는지도 본다."""
    assert rc.METADATA_VERSIONS[0] == "2.1" and "2.5" in rc.METADATA_VERSIONS
    for path in (ROOT / ".github" / "workflows" / "ci.yml", ROOT / "docs" / "registry.md"):
        found = re.findall(r"twine@(\d+)\.\d+\.\d+ check", path.read_text(encoding="utf-8"))
        assert found and all(int(major) >= 7 for major in found), path.name


# ---------- scripts/license_check.py ----------

def _license_check():
    import importlib.util

    spec = importlib.util.spec_from_file_location("license_check", ROOT / "scripts" / "license_check.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_license_check_passes_on_this_lock():
    lc = _license_check()
    results = lc.check()
    assert results and all(ok for ok, _ in results), [line for ok, line in results if not ok]
    packages = lc.runtime_packages()
    # extra(`mcp[cli]` → typer·rich)와 플랫폼 조건 패키지까지 따라가는지
    assert {"mcp", "typer", "rich", "pywin32"} <= set(packages)
    assert "pytest" not in packages and "blender-fx-mcp" not in packages, "개발 의존성·자기 자신은 빼야 함"


def test_license_expression_rules():
    lc = _license_check()
    assert lc.expression_allowed("MIT")
    assert lc.expression_allowed("Apache-2.0 OR BSD-3-Clause")
    assert lc.expression_allowed("GPL-3.0-only OR MIT")
    assert not lc.expression_allowed("GPL-3.0-only")
    assert not lc.expression_allowed("MIT AND LGPL-2.1-or-later")
    assert not lc.expression_allowed("?")
    assert not any(x in lc.ALLOWED for x in ("GPL-3.0-only", "LGPL-3.0-only", "AGPL-3.0-only"))


def test_license_check_reports_table_drift(monkeypatch, tmp_path):
    lc = _license_check()
    table = (ROOT / "docs" / "third-party-licenses.md").read_text(encoding="utf-8")
    broken = table.replace("| `rich` | `MIT` |", "| `rich` | `GPL-3.0-only` |").replace("| `typer` |", "| `typerx` |")
    (tmp_path / "t.md").write_text(broken, encoding="utf-8")
    monkeypatch.setattr(lc, "TABLE", tmp_path / "t.md")
    bad = [line for ok, line in lc.check() if not ok]
    assert any(line.startswith("rich: 설치본은 MIT, 표는 GPL-3.0-only") for line in bad), bad
    assert any(line.startswith("typer: docs/third-party-licenses.md 표에 없음") for line in bad), bad
    assert any(line.startswith("typerx: 표에 있지만") for line in bad), bad
    assert lc.main() == 1


def test_license_doc_is_linked_and_run_in_ci():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.count("(docs/third-party-licenses.md)") >= 2, "README 한/영 라이선스 절에서 링크"
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "uv run python scripts/license_check.py" in ci.split("server-tests:")[0], "lint 작업에서 돌아야 함"
    doc = (ROOT / "docs" / "third-party-licenses.md").read_text(encoding="utf-8")
    english = doc.split("## English", 1)[1].split("## 표 / Table", 1)[0]
    assert not re.search(r"[가-힣]", english)
    lc = _license_check()
    for spdx in sorted(lc.ALLOWED):  # 문서의 허용 목록 = 스크립트의 허용 목록
        assert doc.count(f"`{spdx}`") >= 2, spdx


def test_dist_accepts_crlf_metadata(repo, tmp_path):
    """Windows 체크아웃(CRLF README)에서 만든 sdist·휠도 README 본문·mcp-name 점검을 통과해야 한다."""
    dist = tmp_path / "dist"
    dist.mkdir()
    meta = _meta(repo).replace("\n", "\r\n")
    _wheel(dist, meta)
    src = tmp_path / "pkginfo-crlf"
    src.write_bytes(meta.encode("utf-8"))
    with tarfile.open(dist / "x-1.0.tar.gz", "w:gz") as t:
        for name in ("PKG-INFO", "LICENSE", "docs/third-party-licenses.md"):
            t.add(src, arcname=f"blender_fx_mcp-1.0/{name}")
    assert "\r\n" not in rc.read_metadata(dist / "x-1.0.tar.gz")
    assert rc.main(["--dist", str(dist)], root=repo) == 0


def test_dist_requires_license_files(repo, tmp_path):
    """휠에 LICENSE, sdist 에 LICENSE·제3자 라이선스 표가 없으면 실패하고 무엇이 빠졌는지 말해야 한다."""
    dist = tmp_path / "dist"
    dist.mkdir()
    meta = _meta(repo)
    _wheel(dist, meta, license_file=False)
    _sdist(dist / "x-1.0.tar.gz", meta, extra=("LICENSE",))
    fails = [line for ok, line in rc.check_dist(dist, repo) if not ok]
    assert fails == ["휠 x-1.0-py3-none-any.whl 에 LICENSE 포함 → pyproject 의 license-files·sdist 포함 목록 확인",
                     "sdist x-1.0.tar.gz 에 docs/third-party-licenses.md 포함 → pyproject 의 license-files·sdist 포함 목록 확인"]


def test_tag_matches_version():
    """release.yml 과 Mac 이 같은 규칙: 태그는 'v' + pyproject 판."""
    assert _fails(rc.check_tag("v9.9.9", "9.9.9")) == []
    missing_v = _fails(rc.check_tag("9.9.9", "9.9.9"))
    assert len(missing_v) == 1 and "v 가 빠짐" in missing_v[0] and "v9.9.9" in missing_v[0]
    other = _fails(rc.check_tag("v9.9.8", "9.9.9"))
    assert len(other) == 1 and "pyproject 판(9.9.9)과 다름" in other[0] and "git push --delete origin v9.9.8" in other[0]


def test_main_with_tag(repo, capsys):
    _release(repo)
    assert rc.main(["--tag", "v9.9.9"], root=repo) == 0
    assert "OK   태그 v9.9.9 = pyproject 판 9.9.9" in capsys.readouterr().out
    assert rc.main(["--tag", "v1.0.0"], root=repo) == 1
    assert "고칠 곳 1개" in capsys.readouterr().out
    assert rc.main(["--tag"], root=repo) == 1
    assert "--tag 뒤에 밀 태그" in capsys.readouterr().out


# ---------- scripts/release_notes.py ----------

def _release_notes():
    spec = importlib.util.spec_from_file_location("release_notes", ROOT / "scripts" / "release_notes.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_notes_for_released_version(capsys):
    rn = _release_notes()
    assert rn.main(["v0.7.0"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("**English summary**")
    assert out.index("*Fixes*") < out.index("**고침**"), "영어 요약이 한국어 상세보다 먼저"
    assert "버전 네 곳(`pyproject.toml`·" not in out, "절 맨 앞 관리자용 메모가 들어감"
    assert "## [0.6.3]" not in out and "0.6.3 —" not in out, "다음 절까지 들어감"
    assert out.rstrip().endswith("`uvx blender-fx-mcp@0.7.0`") and "pypi.org/project/blender-fx-mcp/0.7.0/" in out
    assert rn.main(["0.7.0"]) == 0 and capsys.readouterr().out == out  # v 없이도 같다


@pytest.mark.parametrize("arg, code, says", [
    ("v9.9.9", 1, "no 9.9.9 section"), ("v0.8.0", 1, "use --draft"), ("latest", 2, "usage"),
])
def test_release_notes_refuses_missing_or_unreleased(capsys, arg, code, says):
    assert _release_notes().main([arg]) == code
    captured = capsys.readouterr()
    assert captured.out == "" and says in captured.err


def test_release_procedure_uses_release_notes_script():
    text = (ROOT / "docs" / "maintenance.md").read_text(encoding="utf-8")
    assert text.count("scripts/release_notes.py vX.Y.Z") >= 2, "출시 절차 한/영 8단계가 이 명령을 써야 함"


def test_release_notes_draft_previews_unreleased(capsys):
    rn = _release_notes()
    assert rn.main(["--draft", "v0.8.0"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("> 초안 / Draft") and "**English summary**" in out
    assert "pypi.org" not in out and "uvx blender-fx-mcp@" not in out, "아직 PyPI 에 없는 판에 설치 줄"
    assert "## [0.7.0]" not in out
    assert rn.main(["v0.7.0", "--draft"]) == 0  # 출시된 판은 --draft 여도 평소와 같다
    assert capsys.readouterr().out.rstrip().endswith("`uvx blender-fx-mcp@0.7.0`")


# ---------- scripts/mac_report.py ----------

def _mac_report():
    spec = importlib.util.spec_from_file_location("mac_report", ROOT / "scripts" / "mac_report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mac_report_reads_the_commands_in_cloud_notes():
    mr = _mac_report()
    cmds = mr.mac_commands((ROOT / "docs" / "test-reports" / "CLOUD-NOTES.md").read_text(encoding="utf-8"))
    assert 1 <= len(cmds) <= 5 and all(cmd and not cmd.startswith("#") for cmd, _ in cmds), cmds
    assert all(note for _, note in cmds), "명령마다 '확인할 것' 주석"


def test_mac_report_writes_latest_md(tmp_path, monkeypatch, capsys):
    """가짜 명령 셋(통과·실패·주석)으로 돌려 latest.md 모양·종료 코드·집 폴더 가리기를 본다."""
    import sys
    mr = _mac_report()
    home = str(tmp_path / "home" / "sam")
    monkeypatch.setattr(mr, "mask_home", lambda text: text.replace(home, "~"))
    monkeypatch.setattr(mr, "blender_version", lambda: "Blender 5.2.0 LTS")
    py = sys.executable
    notes = tmp_path / "NOTES.md"
    notes.write_text(f"""# 기록

## 맥에서 돌릴 명령 (블렌더 필요)

```sh
"{py}" -c "print('3 passed in 1.0s')"     # 통과해야 함
"{py}" -c "import sys; print('{home}/x'); sys.exit(1)"   # 실패 예시
```
""", encoding="utf-8")
    out = tmp_path / "latest.md"
    assert mr.main(["--notes", str(notes), "--out", str(out), "--timeout", "60"]) == 1
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# Mac 시험 결과 (최신)") and "**FAIL** — 1개 실패" in text
    assert "| PASS (" in text and "3 passed in 1.0s" in text
    assert "| 통과해야 함 |" in text and "## 실패 핵심" in text and "~/x" in text and home not in text
    assert mr.main(["--notes", str(notes), "--dry-run"]) == 0
    assert capsys.readouterr().out.count("print(") >= 2


def test_mac_report_without_command_block(tmp_path):
    notes = tmp_path / "n.md"
    notes.write_text("# 비어 있음\n", encoding="utf-8")
    assert _mac_report().main(["--notes", str(notes), "--dry-run"]) == 2


# ---------- scripts/triage_report.py ----------

def _triage():
    spec = importlib.util.spec_from_file_location("triage_report", ROOT / "scripts" / "triage_report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SINCE = "2026-09-16"   # now(2026-10-16) 에서 CI_LOOKBACK_DAYS(30) 전


def _ci_data(repo="o/r", runs=None, jobs=None, issues=()):
    """CI 칸용 가짜 응답: 기본 브랜치 main, 열린 PR #3(fix-typo). runs = {브랜치: [실행…]}, jobs = {실행 id: [잡…]}."""
    runs = runs or {}
    data = {f"repos/{repo}": [{"default_branch": "main"}],
            f"repos/{repo}/pulls?state=open&per_page=100": [{"number": 3, "head": {"ref": "fix-typo"}}],
            f"repos/{repo}/issues?state=open&per_page=100": list(issues)}
    for branch in ("main", "fix-typo"):
        data[f"repos/{repo}/actions/runs?branch={branch}&status=completed&created=%3E%3D{SINCE}&per_page=100"] = [
            {"total_count": len(runs.get(branch, [])), "workflow_runs": runs.get(branch, [])}]
    for run_id, js in (jobs or {}).items():
        data[f"repos/{repo}/actions/runs/{run_id}/jobs?per_page=100"] = [{"jobs": js}]
    return data


def _run(run_id, name, conclusion, created):
    return {"id": run_id, "name": name, "conclusion": conclusion, "created_at": created, "html_url": f"https://x/runs/{run_id}"}


def _fake_github(repo="o/r"):
    """열린 것 다섯: 늦은 버그(답 없음), 제때 답한 질문, 늦게 답한 PR(리뷰), 봇 PR, 관리자가 연 PR."""
    me, maint, bot = {"login": "user1", "type": "User"}, {"login": "maint", "type": "User"}, {"login": "dependabot[bot]", "type": "Bot"}
    data = {
        f"repos/{repo}/issues?state=open&per_page=100": [
            {"number": 1, "title": "crash | on render", "user": me, "labels": [{"name": "bug"}], "created_at": "2026-10-01T00:00:00Z"},
            {"number": 2, "title": "how to?", "user": me, "labels": [{"name": "question"}], "created_at": "2026-10-01T00:00:00Z"},
            {"number": 3, "title": "fix typo", "user": me, "labels": [], "created_at": "2026-09-01T00:00:00Z", "pull_request": {}},
            {"number": 4, "title": "bump x", "user": bot, "labels": [], "created_at": "2026-09-01T00:00:00Z", "pull_request": {}},
            {"number": 5, "title": "own work", "user": maint, "author_association": "OWNER", "labels": [],
             "created_at": "2026-09-01T00:00:00Z", "pull_request": {}},
        ],
        # 1: 글쓴이 본인 댓글·봇 댓글은 답이 아니다
        f"repos/{repo}/issues/1/comments?per_page=100": [{"user": me, "created_at": "2026-10-02T00:00:00Z"},
                                                          {"user": bot, "created_at": "2026-10-02T00:00:00Z"}],
        f"repos/{repo}/issues/2/comments?per_page=100": [{"user": maint, "created_at": "2026-10-03T12:00:00Z"}],
        f"repos/{repo}/issues/3/comments?per_page=100": [],
        f"repos/{repo}/pulls/3/reviews?per_page=100": [{"user": maint, "submitted_at": "2026-09-21T00:00:00Z"}],
        f"repos/{repo}/issues/4/comments?per_page=100": [],
        f"repos/{repo}/pulls/4/reviews?per_page=100": [],
        f"repos/{repo}/issues/5/comments?per_page=100": [],
        f"repos/{repo}/pulls/5/reviews?per_page=100": [],
    }
    green = {"main": [_run(1, "ci", "success", "2026-10-15T00:00:00Z")]}
    data = {**_ci_data(repo, green), **data}
    return lambda path: data[path]


def test_triage_report_flags_only_items_past_the_support_target(capsys):
    from datetime import datetime, timezone
    tr = _triage()
    now = datetime(2026, 10, 16, tzinfo=timezone.utc)
    rows = {r["number"]: r for r in tr.triage("o/r", _fake_github(), now)}
    assert set(rows) == {1, 2, 3}, "봇·관리자가 연 것은 기본으로 뺀다"
    assert rows[1]["target"] == 7 and rows[1]["reply_days"] is None and rows[1]["late"]
    assert rows[2]["target"] == 14 and rows[2]["reply_days"] == 2.5 and not rows[2]["late"]
    assert rows[3]["kind"] == "PR" and rows[3]["reply_days"] == 20.0 and rows[3]["late"], "리뷰도 첫 답, 14일 넘김"
    assert {r["number"] for r in tr.triage("o/r", _fake_github(), now, include_bots=True, include_own=True)} == {1, 2, 3, 4, 5}

    assert tr.main(["--repo", "o/r"], api=_fake_github(), now=now) == 1
    out = capsys.readouterr().out
    assert "3개 중" in out and "2 of 3" in out and "| 1 | issue | crash \\| on render | bug | 7일 / d | 없음 / none ⚠ |" in out
    assert "how to?" not in out, "목표 안인 것은 --all 일 때만"
    assert tr.main(["--repo", "o/r", "--all"], api=_fake_github(), now=now) == 1 and "how to?" in capsys.readouterr().out
    assert "CI: 기본 브랜치·열린 PR 의 최신 실행이 모두 초록" in out


def test_triage_report_ci_section_flags_long_red_runs(capsys):
    from datetime import datetime, timezone
    tr = _triage()
    now = datetime(2026, 10, 16, tzinfo=timezone.utc)
    runs = {
        # main 의 ci: 10/12 부터 연달아 빨강(4일째) → ⚠. triage 는 초록이라 표에 없음. 그 전 초록은 빨개진 때를 끊는다
        "main": [_run(11, "ci", "failure", "2026-10-15T00:00:00Z"), _run(9, "triage", "success", "2026-10-14T00:00:00Z"),
                 _run(10, "ci", "failure", "2026-10-12T00:00:00Z"), _run(8, "ci", "success", "2026-10-10T00:00:00Z")],
        # PR #3: 반나절 빨강 → 표에는 있지만 ⚠ 아님
        "fix-typo": [_run(21, "ci", "timed_out", "2026-10-15T12:00:00Z"), _run(20, "ci", "success", "2026-10-15T06:00:00Z")],
    }
    jobs = {11: [{"name": "lint", "conclusion": "failure"}, {"name": "server-tests (3.13)", "conclusion": "success"}],
            21: [{"name": "server-tests | os", "conclusion": "timed_out"}]}
    data = _ci_data(runs=runs, jobs=jobs)
    rows = tr.ci_status("o/r", data.__getitem__, now)
    assert [(r["branch"], r["pr"], r["workflow"], r["red_days"], r["jobs"], r["late"]) for r in rows] == [
        ("main", None, "ci", 4.0, ["lint"], True), ("fix-typo", 3, "ci", 0.5, ["server-tests | os"], False)]

    assert tr.main(["--repo", "o/r"], api=data.__getitem__, now=now) == 1, "이슈는 없어도 3일 넘게 빨간 CI 가 있으면 1"
    out = capsys.readouterr().out
    assert "빨간 워크플로 2개, 3일 넘은 것 1개" in out
    assert "| main | ci | 4.0일 / d ⚠ | lint | https://x/runs/11 |" in out
    assert "| fix-typo (PR #3) | ci | 0.5일 / d | server-tests \\| os | https://x/runs/21 |" in out
    assert out.index("| main |") < out.index("| fix-typo"), "오래 빨간 것부터"

    short = _ci_data(runs={"fix-typo": runs["fix-typo"]}, jobs=jobs)
    assert tr.main(["--repo", "o/r"], api=short.__getitem__, now=now) == 0, "3일 안의 빨강은 표에만"
    capsys.readouterr()
    assert tr.main(["--repo", "o/r", "--no-ci"], api=lambda p: [] if "issues" in p else 1 / 0, now=now) == 0, "--no-ci 는 CI 를 묻지 않음"
    assert "CI:" not in capsys.readouterr().out


def test_triage_report_ci_section_reads_real_rest_shapes(capsys):
    """GitHub REST 문서의 실제 응답 모양(workflow_runs[]·jobs[] 의 모든 칸, 쪽 나눔, 재실행 run_attempt)을 고정 자료로.
    취소된 실행(새 push 로 concurrency 취소)·포크 PR 승인 대기(action_required)는 건강을 말하지 않아 건너뛴다:
    빨간 main 위에 취소된 실행 하나가 있어도 빨강으로, 건너뛴(skipped) 잡은 실패 잡이 아니다."""
    import json
    from datetime import datetime, timezone
    tr = _triage()
    fixture = json.loads((ROOT / "tests" / "fixtures" / "github_actions_rest.json").read_text(encoding="utf-8"))
    data = _ci_data(runs={}, jobs={})
    for branch, pages in fixture["runs"].items():
        data[f"repos/o/r/actions/runs?branch={branch}&status=completed&created=%3E%3D{SINCE}&per_page=100"] = pages
    for run_id, pages in fixture["jobs"].items():
        data[f"repos/o/r/actions/runs/{run_id}/jobs?per_page=100"] = pages
    data["repos/o/r/pulls?state=open&per_page=100"] = fixture["pulls"]
    now = datetime(2026, 10, 16, tzinfo=timezone.utc)
    rows = tr.ci_status("o/r", data.__getitem__, now)
    assert [(r["branch"], r["pr"], r["workflow"], r["red_days"], r["jobs"], r["late"]) for r in rows] == [
        ("main", None, "ci", 4.0, ["lint"], True)], rows
    assert rows[0]["url"] == "https://github.com/octo-org/octo-repo/actions/runs/30433641"  # 취소된 것이 아닌 마지막 빨간 실행
    assert tr.main(["--repo", "o/r"], api=data.__getitem__, now=now) == 1
    out = capsys.readouterr().out
    assert "| main | ci | 4.0일 / d ⚠ | lint | https://github.com/octo-org/octo-repo/actions/runs/30433641 |" in out
    assert "fix-typo" not in out.split("CI:", 1)[1], "승인 대기 실행 아래 마지막 결과는 초록"
    assert tr.NO_SIGNAL.isdisjoint(tr.RED)


def test_triage_report_ci_marks_runs_green_only_after_rerun(capsys):
    """재실행해서야 초록이 된 실행은 목록 API 에 마지막 시도(초록)만 와 표에서 사라진다. 앞 시도(attempts/N-1)가 빨가면 '흔들림' 줄로.
    REST 칸 이름 그대로(run_attempt·head_sha·previous_attempt_url). 앞 시도도 초록(그냥 다시 돌린 것)이면 흔들림이 아니다. 종료 코드는 그대로."""
    from datetime import datetime, timezone
    tr = _triage()
    now = datetime(2026, 10, 16, tzinfo=timezone.utc)

    def rerun(run_id, name, created, attempt):
        return {**_run(run_id, name, "success", created), "run_attempt": attempt, "head_sha": "acb5820",
                "previous_attempt_url": f"https://api.github.com/repos/o/r/actions/runs/{run_id}/attempts/{attempt - 1}"}
    runs = {"main": [rerun(31, "ci", "2026-10-15T00:00:00Z", 2), rerun(30, "ci", "2026-10-10T00:00:00Z", 3),
                     rerun(29, "triage", "2026-10-14T00:00:00Z", 2)],
            "fix-typo": [rerun(41, "ci", "2026-10-15T00:00:00Z", 2)]}
    data = _ci_data(runs=runs)
    data.update({"repos/o/r/actions/runs/31/attempts/1": [{"id": 31, "run_attempt": 1, "conclusion": "failure"}],
                 "repos/o/r/actions/runs/30/attempts/2": [{"id": 30, "run_attempt": 2, "conclusion": "timed_out"}],
                 "repos/o/r/actions/runs/29/attempts/1": [{"id": 29, "run_attempt": 1, "conclusion": "success"}],
                 "repos/o/r/actions/runs/41/attempts/1": [{"id": 41, "run_attempt": 1, "conclusion": "failure"}]})
    rows = tr.ci_status("o/r", data.__getitem__, now)
    assert [(r["branch"], r["pr"], r["workflow"], r["flaky"], r["url"], r["late"]) for r in rows] == [
        ("main", None, "ci", 2, "https://x/runs/31", False), ("fix-typo", 3, "ci", 1, "https://x/runs/41", False)]
    assert tr.main(["--repo", "o/r"], api=data.__getitem__, now=now) == 0, "흔들림은 고칠 거리지만 빨간 CI 는 아님"
    out = capsys.readouterr().out.split("CI:", 1)[1]
    assert "모두 초록" in out and "triage" not in out
    assert "흔들림 / Flaky: main · ci — 재실행해서 초록 2번(최근 30일)" in out and out.rstrip().endswith("fix the test: https://x/runs/41")
    # 빨간 표가 있을 때는 표 아래 빈 줄 뒤에
    data[next(k for k in data if "branch=main" in k)][0]["workflow_runs"].insert(0, _run(32, "lint", "failure", "2026-10-15T06:00:00Z"))
    data["repos/o/r/actions/runs/32/jobs?per_page=100"] = [{"jobs": [{"name": "lint", "conclusion": "failure"}]}]
    text = tr.format_ci(tr.ci_status("o/r", data.__getitem__, now))
    assert "빨간 워크플로 1개" in text and "| main | lint |" in text and text.index("| main | lint |") < text.index("\n\n흔들림 / Flaky: main")


def test_maintenance_has_red_ci_response_rule():
    """maintenance 한/영에 빨간 CI 대응 절: triage 표의 3일(CI_RED_DAYS)과 같은 일수, 그 주에 고치거나 이슈로 남김."""
    tr = _triage()
    text = (ROOT / "docs" / "maintenance.md").read_text(encoding="utf-8")
    ko = text.split("### 빨간 CI 대응", 1)[1].split("\n#", 1)[0]
    en = text.split("### Responding to red CI", 1)[1].split("\n#", 1)[0]
    assert f"{tr.CI_RED_DAYS}일" in ko and "이슈" in ko and "triage_report.py" in ko
    assert f"{tr.CI_RED_DAYS} days" in en and "issue" in en and "triage_report.py" in en
    assert "cancelled" in ko and "cancelled" in en  # 취소된 실행은 세지 않는다는 것도
    assert "흔들림" in ko and "Flaky" in en  # 재실행해서 초록이면 표 아래 줄로 남는다는 것도


def test_triage_report_without_gh_says_what_to_do(monkeypatch, capsys):
    tr = _triage()
    monkeypatch.setattr(tr.shutil, "which", lambda name: None)
    assert tr.main([]) == 2
    err = capsys.readouterr().err
    assert "brew install gh" in err and "gh auth login" in err and "https://cli.github.com" in err


def test_triage_report_reads_paginated_gh_output(monkeypatch):
    tr = _triage()
    monkeypatch.setattr(tr.shutil, "which", lambda name: "/usr/bin/gh")
    done = subprocess.CompletedProcess([], 0, stdout='[{"a": 1}]\n[{"a": 2}, {"a": 3}]\n', stderr="")
    monkeypatch.setattr(tr.subprocess, "run", lambda *a, **k: done)
    assert tr.gh_api("x") == [{"a": 1}, {"a": 2}, {"a": 3}]
    monkeypatch.setattr(tr.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 1, "", "HTTP 401: Bad credentials"))
    with pytest.raises(tr.GhError, match="HTTP 401"):
        tr.gh_api("x")


def test_triage_targets_match_support_md():
    tr = _triage()
    support = (ROOT / "SUPPORT.md").read_text(encoding="utf-8")
    assert f"보안 신고 / Security report | {tr.TARGET_DAYS['security']}일 안" in support
    assert f"버그 / Bug | {tr.TARGET_DAYS['bug']}일 안" in support
    assert f"질문·기능 요청 / Question, feature | {tr.OTHER_DAYS}일 안" in support
    assert tr.target_days(["bug", "question"]) == 7 and tr.target_days([]) == 14


# ---- 만든 파일·명령이 원본과 같은지(출시 절차는 release_check 하나만 돌린다) ----

MAC_PASS = "# Mac 시험 결과 (최신)\n\n- 날짜: 2026-10-10\n- 시험한 브랜치: `main` (커밋 abc1234)\n- 종합: **PASS**\n"


@pytest.mark.parametrize("text, today, ok, words", [
    (MAC_PASS, "2026-11-09", True, ["= PASS, 2026-10-10(30일 전)"]),
    (MAC_PASS, "2026-11-10", False, ["31일 전", "30일 넘음", "scripts/mac_report.py"]),
    (MAC_PASS.replace("**PASS**", "**FAIL** — 1개 실패"), "2026-10-11", False, ["= FAIL", "FAIL 항목을 먼저 고친 뒤", "scripts/mac_report.py"]),
    (MAC_PASS.replace("**PASS**", "**FAIL**"), "2026-12-01", False, ["FAIL 항목을 먼저 고친 뒤, 30일 넘음"]),
    ("# 손으로 쓴 메모\n", "2026-10-11", False, ["'- 날짜:'·'- 종합:' 줄을 못 읽음", "scripts/mac_report.py"]),
])
def test_mac_report_must_be_recent_pass(tmp_path, text, today, ok, words):
    """출시 전 실제 블렌더 결과를 보는 단계: latest.md 가 PASS 이고 30일 안이어야 통과, 아니면 다시 돌릴 명령을 말한다."""
    from datetime import date
    path = tmp_path / rc.MAC_REPORT
    path.parent.mkdir(parents=True)
    path.write_text(text, encoding="utf-8")
    [(got, line)] = rc.check_mac_report(tmp_path, date.fromisoformat(today))
    assert got is ok and all(w in line for w in words), line
    assert ("scripts/mac_report.py" in line) is (not ok)


def test_mac_report_line_reads_what_mac_report_writes(tmp_path):
    """mac_report.py 가 쓰는 머리(날짜·종합)를 release_check 가 그대로 읽는다(한쪽만 바뀌면 여기서 잡힘). 파일이 없으면 건너뜀."""
    from datetime import date
    assert rc.check_mac_report(tmp_path) == []
    spec = importlib.util.spec_from_file_location("mac_report", ROOT / "scripts" / "mac_report.py")
    mr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mr)
    path = tmp_path / rc.MAC_REPORT
    path.parent.mkdir(parents=True)
    for results, verdict in (([("uv run pytest -q", "", True, 1.0, "1 passed")], True),
                             ([("uv run pytest -q", "", False, 1.0, "1 failed")], False)):
        path.write_text(mr.report(results, "2026-10-17", "main", "abc1234", "macOS"), encoding="utf-8")
        [(ok, line)] = rc.check_mac_report(tmp_path, date(2026, 10, 18))
        assert ok is verdict and "2026-10-17(1일 전)" in line, line


def test_generated_checks_pass_on_this_repo(monkeypatch):
    """이 저장소에서는 해결법 대응표·lint.sh --print 점검이 둘 다 통과한다(Windows 는 bash 없이 건너뜀 줄)."""
    import sys
    if sys.platform == "win32":
        monkeypatch.setattr(rc.shutil, "which", lambda _: None)
    results = rc.check_generated(ROOT)
    assert [ok for ok, _ in results] == [True, True], results
    assert results[0][1].startswith("해결법 대응표") and results[1][1].startswith("scripts/lint.sh --print")
    assert results in [rc.check_files(ROOT)[-3:-1]]  # 파일 점검(출시 절차의 한 명령)에 들어 있다(마지막 줄은 Mac 실측)


def test_generated_check_catches_stale_help_index(tmp_path):
    """대응표가 문서·레시피와 다르면 FAIL 과 고치는 명령."""
    for rel in ("scripts/gen_help_index.py", "docs/troubleshooting.md", "src/blender_fx_mcp/server.py"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, tmp_path / rel)
    shutil.copytree(ROOT / "src" / "blender_fx_mcp" / "recipes", tmp_path / "src" / "blender_fx_mcp" / "recipes")
    out = tmp_path / "src" / "blender_fx_mcp" / "help_index.py"
    shutil.copy(ROOT / "src" / "blender_fx_mcp" / "help_index.py", out)
    assert rc.check_generated(tmp_path) == [(True, "해결법 대응표(src/blender_fx_mcp/help_index.py) = 문서·레시피·서버 오류 문장")]
    out.write_text(out.read_text(encoding="utf-8").replace("#", "#stale-", 1), encoding="utf-8")
    [(ok, line)] = rc.check_generated(tmp_path)
    assert not ok and "gen_help_index.py --write" in line


def test_generated_check_catches_lint_drift(monkeypatch, tmp_path):
    """lint.sh --print 가 ci.yml lint 단계와 다르면 FAIL 과 양쪽 명령·고칠 곳. bash 가 없으면 건너뜀 줄(실패 아님)."""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "lint.sh").write_text("# 내용은 쓰지 않음(subprocess.run 을 가짜로)\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    shutil.copy(ROOT / ".github" / "workflows" / "ci.yml", tmp_path / ".github" / "workflows" / "ci.yml")
    want = rc.ci_lint_commands(tmp_path)
    assert len(want) == 3 and want[0].startswith("uvx ruff@")

    def fake_run(printed):
        return lambda *a, **k: subprocess.CompletedProcess(a[0], 0, stdout="".join(c + "\n" for c in printed), stderr="")

    monkeypatch.setattr(rc.shutil, "which", lambda _: "/bin/bash")
    monkeypatch.setattr(rc.subprocess, "run", fake_run(want))
    assert rc.check_generated(tmp_path) == [(True, "scripts/lint.sh --print = CI lint 단계(3개)")]
    monkeypatch.setattr(rc.subprocess, "run", fake_run(["uvx ruff@0.0.1 check ."] + want[1:]))
    [(ok, line)] = rc.check_generated(tmp_path)
    assert not ok and "ruff@0.0.1" in line and want[0] in line and "CONTRIBUTING" in line
    monkeypatch.setattr(rc.shutil, "which", lambda _: None)
    [(ok, line)] = rc.check_generated(tmp_path)
    assert ok and "건너뜀" in line


@pytest.mark.parametrize("exit_code, stderr", [(0, ""), (1, ""), (2, "진단: 입력을 확인하세요")])
def test_generated_check_utf8_pipes(tmp_path, monkeypatch, exit_code, stderr):
    """부모 기본 읽기와 자식 출력을 cp1252로 모의해 한글·실패 진단을 보존한다."""
    monkeypatch.setenv("PYTHONIOENCODING", "cp1252")
    monkeypatch.setattr(subprocess, "_text_encoding", lambda: "cp1252")
    gen = tmp_path / "scripts" / "gen_help_index.py"
    gen.parent.mkdir()
    gen.write_text(
        "import sys\n"
        "print('대응표 확인')\n"
        f"print({stderr!r}, file=sys.stderr)\n"
        f"sys.exit({exit_code})\n", encoding="utf-8",
    )
    [(ok, line)] = rc.check_generated(tmp_path)
    assert ok == (exit_code == 0)
    if exit_code:
        assert "gen_help_index.py --write" in line
    if stderr:
        assert stderr in line
