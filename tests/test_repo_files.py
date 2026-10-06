# 저장소 안내 파일(이슈 양식 등) 점검. 블렌더 없이 돈다.
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / ".github" / "ISSUE_TEMPLATE"


@pytest.mark.parametrize("name", ["bug_report.md", "feature_request.md"])
def test_issue_template_front_matter(name):
    text = (TEMPLATES / name).read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, f"{name}: 맨 위 --- 머리말이 없음"
    keys = {line.split(":", 1)[0] for line in m.group(1).splitlines() if ":" in line}
    assert {"name", "about"} <= keys


def test_bug_template_asks_for_repro_info():
    text = (TEMPLATES / "bug_report.md").read_text(encoding="utf-8")
    for needed in ("blender-fx-doctor", "Blender version", "BLENDER_FX_LANG"):
        assert needed in text


def test_issue_config_links():
    text = (TEMPLATES / "config.yml").read_text(encoding="utf-8")
    assert re.search(r"^blank_issues_enabled: (true|false)$", text, re.M)
    urls = re.findall(r"^\s+url: (\S+)$", text, re.M)
    assert urls and all(u.startswith("https://github.com/choisam4u-creator/blender-fx-mcp/") for u in urls)
    # 링크가 저장소 안 파일을 가리키면 그 파일이 있어야 한다
    for u in urls:
        if "/blob/main/" in u:
            assert (ROOT / u.split("/blob/main/", 1)[1]).is_file(), u


def test_security_policy_has_private_reporting_and_port_warning():
    text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert "/security/advisories/new" in text
    assert "9876" in text and "BLENDER_FX_HOST" in text


def test_security_port_matches_bridge_default(monkeypatch):
    from blender_fx_mcp import bridge
    monkeypatch.delenv("BLENDER_FX_PORT", raising=False)
    monkeypatch.delenv("BLENDER_FX_HOST", raising=False)
    text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert f"{bridge.host()}:{bridge.port()}" in text


def test_code_of_conduct_present():
    text = (ROOT / "CODE_OF_CONDUCT.md").read_text(encoding="utf-8")
    assert "Contributor Covenant" in text and "2.1" in text


def _server_tools():
    src = (ROOT / "src" / "blender_fx_mcp" / "server.py").read_text(encoding="utf-8")
    return re.findall(r"@mcp\.tool\(\)\s*\ndef (\w+)\(", src)


def _readme_section(title):
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    m = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    assert m, f"README 에 '## {title}' 절이 없음"
    return m.group(1)


@pytest.mark.parametrize("title", ["도구 목록", "English"])
def test_readme_tool_tables_cover_every_tool(title):
    """README 의 도구 표(한국어·영어)에 server.py 의 MCP 도구가 빠짐없이 있어야 한다."""
    tools = _server_tools()
    assert len(tools) >= 30
    section = _readme_section(title)
    listed = set(re.findall(r"^\| (.+?) \|", section, re.M))
    names = {n for cell in listed for n in re.findall(r"`(\w+)`", cell)}
    missing = [t for t in tools if t not in names]
    assert not missing, f"README '{title}' 표에 없는 도구: {missing}"


def test_readme_english_section_is_self_contained():
    """해외 사용자가 한국어 없이 설치·첫 명령까지 갈 수 있어야 한다."""
    section = _readme_section("English")
    assert not re.search(r"[가-힣]", section), "영어 절에 한글이 섞여 있음"
    for needed in ("blender-fx-doctor", "claude mcp add", "BLENDER_FX_LANG=en", "Connect to MCP server", "SECURITY.md"):
        assert needed in section, needed
    assert "(#english)" in (ROOT / "README.md").read_text(encoding="utf-8")


def test_dependabot_watches_uv_and_actions():
    """의존성(uv.lock)과 워크플로 액션 판이 주 1회 갱신 PR 로 들어와야 한다."""
    text = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    assert re.search(r"^version: 2$", text, re.M)
    ecosystems = re.findall(r'package-ecosystem: "([^"]+)"', text)
    assert set(ecosystems) == {"uv", "github-actions"}
    assert text.count('interval: "weekly"') == len(ecosystems)
    assert (ROOT / "uv.lock").is_file()


def test_pull_request_template_matches_contributing():
    """PR 양식의 확인 칸이 CONTRIBUTING 절차(ruff·pytest·한/영 문장·README 도구 표)를 빠뜨리지 않아야 한다."""
    text = (ROOT / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    for cmd in ("uvx ruff check .", "uv run pytest -q"):
        assert cmd in text and cmd in contributing, cmd
    for needed in ("L(", "t(", "run_guarded(main)", "STEPS", "## 도구 목록", "## English", "app_only", "CHANGELOG.md"):
        assert needed in text, needed
    assert len(re.findall(r"^- \[ \] ", text, re.M)) >= 6


def _badges():
    head = (ROOT / "README.md").read_text(encoding="utf-8").split("\n> ", 1)[0]
    return re.findall(r"\[!\[([^\]]*)\]\(([^)]+)\)\]\(([^)]+)\)", head)


def test_readme_badges_match_repo():
    """README 맨 위 배지가 실제 워크플로·라이선스·지원 파이썬 판과 맞아야 한다."""
    badges = _badges()
    assert len(badges) >= 3, "README 첫 화면에 배지(CI·라이선스·Python)가 없음"
    workflows = ROOT / ".github" / "workflows"
    for alt, img, link in badges:
        m = re.search(r"/actions/workflows/([\w.-]+\.yml)/badge\.svg", img)
        if m:
            assert (workflows / m.group(1)).is_file(), m.group(1)
            assert img.startswith("https://github.com/choisam4u-creator/blender-fx-mcp/")
            assert link.endswith(f"/actions/workflows/{m.group(1)}")
        elif not link.startswith("http"):
            assert (ROOT / link).is_file(), link
    alts = " ".join(a for a, _, _ in badges)
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    lic = re.search(r'^license = "([^"]+)"$', pyproject, re.M).group(1)
    assert lic in alts and lic in (ROOT / "LICENSE").read_text(encoding="utf-8")
    vers = re.findall(r"Programming Language :: Python :: (3\.\d+)\"", pyproject)
    assert f"{vers[0]}–{vers[-1]}" in alts, f"Python 배지가 분류자 {vers[0]}–{vers[-1]} 와 다름"


def test_ci_reports_server_coverage_without_recipes():
    """CI 서버 시험이 커버리지를 내고, 블렌더 안에서만 도는 레시피는 측정에서 빠져야 한다."""
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert re.search(r"pytest .*--cov .*markdown-append:\$GITHUB_STEP_SUMMARY", ci)
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "pytest-cov" in pyproject
    assert re.search(r'^omit = \[.*recipes/\*.*\]$', pyproject, re.M)
    # CI 가 돌리는 시험 파일이 모두 실제로 있어야 한다
    for name in re.findall(r"tests/(test_\w+\.py)", ci):
        assert (ROOT / "tests" / name).is_file(), name


def test_coverage_artifacts_are_ignored():
    """`pytest --cov` 가 남기는 .coverage 는 기기마다 다른 SQLite 파일이라 저장소에 들어가면 안 된다."""
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".coverage" in ignored and "htmlcov/" in ignored
