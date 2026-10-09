# scripts/release_check.py(출시 전 점검) 시험. 블렌더 없이 돈다.
import importlib.util
import re
import shutil
import tarfile
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
              "CITATION.cff"):
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


def _fails(results):
    return [line for ok, line in results if not ok]


def test_current_repo_state():
    """준비 중(맨 위 절이 '미출시', 버전은 아직 이전 판)이면 정확히 '판 다름'과 '미출시' 두 줄만 실패하고,
    출시 순서를 마친 뒤(날짜가 붙음)에는 모두 통과해야 한다."""
    fails = _fails(rc.check_files(ROOT))
    top_version, when = rc.HEADING.search((ROOT / "CHANGELOG.md").read_text(encoding="utf-8")).groups()
    if rc.DATE.fullmatch(when.strip()):
        assert fails == []
        return
    assert top_version != rc.project_version(ROOT), "미출시 절인데 버전을 이미 올렸으면 날짜도 붙인다"
    assert len(fails) == 2, fails
    assert "CHANGELOG.md 맨 위 절 판" in fails[0] and "pyproject 판" in fails[0]
    assert "미출시" in fails[1] and "YYYY-MM-DD" in fails[1]


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
    tomllib = pytest.importorskip("tomllib")
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
    pytest.importorskip("tomllib")  # 3.11+
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
    assert {"mcp", "typer", "rich", "pywin32", "exceptiongroup"} <= set(packages)
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
