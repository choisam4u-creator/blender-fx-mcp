# server.json.example 이 공식 MCP 레지스트리 형식(2025-12-11 스키마)과 이 저장소 상태에 맞는지 본다.
# 네트워크 없이 도는 점검만 한다. 스키마 전체 검증은 docs/registry.md 의 명령으로.
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SERVER = json.loads((ROOT / "server.json.example").read_text(encoding="utf-8"))
PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def _project_version() -> str:
    return re.search(r'^version = "([^"]+)"', PYPROJECT, re.M).group(1)


def _keys(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield path + k, k
            yield from _keys(v, path + k + ".")
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v, path)


def test_required_fields_and_limits():
    for k in ("name", "description", "version"):
        assert SERVER.get(k), k
    assert re.fullmatch(r"[a-zA-Z0-9.-]+/[a-zA-Z0-9._-]+", SERVER["name"])
    assert len(SERVER["description"]) <= 100
    assert len(SERVER.get("title", "")) <= 100
    for pkg in SERVER["packages"]:
        for k in ("registryType", "identifier", "transport"):
            assert k in pkg, k


def test_keys_are_camel_case():
    # 2025-09-29 스키마부터 snake_case(registry_type 등)는 받지 않는다
    bad = [p for p, k in _keys(SERVER) if "_" in k and k not in ("_meta",)]
    assert bad == [], bad


def test_versions_match_pyproject():
    v = _project_version()
    assert SERVER["version"] == v
    for pkg in SERVER["packages"]:
        assert pkg["version"] == v
        assert pkg["identifier"] == "blender-fx-mcp"


def test_readme_has_mcp_name_for_pypi_verification():
    # 레지스트리는 PyPI 패키지 설명(README)에서 이 줄을 찾아 소유를 확인한다
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"mcp-name: {SERVER['name']}" in readme


def test_env_vars_are_used_by_code():
    src = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "src").rglob("*.py"))
    for pkg in SERVER["packages"]:
        for env in pkg.get("environmentVariables", []):
            assert env["name"] in src, env["name"]


def test_package_version_matches_pyproject():
    from blender_fx_mcp import __version__

    assert __version__ == _project_version()


def _pyproject():
    tomllib = pytest.importorskip("tomllib")  # 3.11+
    return tomllib.loads(PYPROJECT)["project"]


def test_project_urls_point_to_repo():
    """PyPI·레지스트리 페이지에서 이슈·보안 신고·변경 기록 경로가 바로 보여야 한다."""
    urls = _pyproject()["urls"]
    for k in ("Homepage", "Issues", "Changelog", "Security"):
        assert urls.get(k, "").startswith("https://github.com/choisam4u-creator/blender-fx-mcp"), k
    assert urls["Homepage"].rstrip("/") == SERVER["repository"]["url"].rstrip("/")
    for u in urls.values():
        if "/blob/main/" in u:
            assert (ROOT / u.split("/blob/main/", 1)[1]).is_file(), u
    assert (ROOT / "SECURITY.md").is_file()


def test_python_classifiers_match_requires_python():
    proj = _pyproject()
    low = tuple(int(x) for x in re.search(r">=\s*3\.(\d+)", proj["requires-python"]).groups())
    minors = sorted(int(m) for c in proj["classifiers"]
                    for m in re.findall(r"^Programming Language :: Python :: 3\.(\d+)$", c))
    assert minors, "Python 판 분류자가 없음"
    assert minors[0] == low[0], (minors, proj["requires-python"])
    assert minors == list(range(minors[0], minors[-1] + 1)), f"빠진 판이 있음: {minors}"
    assert "License :: " not in " ".join(proj["classifiers"]), "license = 'MIT' 와 License 분류자를 같이 쓰면 빌드가 거부한다"


def test_ci_matrix_covers_every_classifier():
    """분류자에 적은 파이썬 판은 CI 가 모두 실제로 돌려 봐야 한다(Mac 실측 환경이 3.13)."""
    proj = _pyproject()
    minors = sorted(int(m) for c in proj["classifiers"]
                    for m in re.findall(r"^Programming Language :: Python :: 3\.(\d+)$", c))
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    m = re.search(r"^\s+python: \[(.*?)\]$", ci, re.M)
    assert m, "ci.yml 에 python 행렬이 없음"
    tested = sorted(int(v) for v in re.findall(r'"3\.(\d+)"', m.group(1)))
    assert tested == minors, f"분류자 {minors} 와 CI 행렬 {tested} 이 다름"
