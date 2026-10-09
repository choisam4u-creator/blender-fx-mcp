# 저장소 안내 파일(이슈 양식 등) 점검. 블렌더 없이 돈다.
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / ".github" / "ISSUE_TEMPLATE"


FORMS = {"bug_report.yml": "bug", "feature_request.yml": "enhancement"}


def _form(name):
    # PyYAML 없이 읽는다: 이 양식들은 `  - type:` 로 칸을 나누는 고정 모양만 쓴다.
    text = (TEMPLATES / name).read_text(encoding="utf-8")
    head, _, body = text.partition("\nbody:\n")
    blocks = re.split(r"^  - type: ", body, flags=re.M)[1:]
    fields = {}
    for b in blocks:
        kind = b.split("\n", 1)[0].strip()
        m = re.search(r"^    id: ([\w-]+)$", b, re.M)
        if kind == "markdown":
            continue
        assert m, f"{name}: {kind} 칸에 id 가 없음"
        assert m.group(1) not in fields, f"{name}: id 중복 {m.group(1)}"
        req = re.search(r"^      required: (true|false)$", b, re.M)
        fields[m.group(1)] = (kind, req and req.group(1) == "true", b)
    return text, head, fields


def _bug_form():
    return _form("bug_report.yml")


def test_issue_templates_are_forms_only():
    # .md 와 .yml 이 같이 있으면 GitHub 가 두 양식을 다 보여 준다. 양식은 모두 YAML 폼으로 받는다.
    assert sorted(p.name for p in TEMPLATES.glob("*.md")) == []
    assert sorted(p.name for p in TEMPLATES.glob("*.yml") if p.name != "config.yml") == sorted(FORMS)


@pytest.mark.parametrize("name", sorted(FORMS))
def test_form_header(name):
    text, head, _ = _form(name)
    assert "\t" not in text, "YAML 에 탭 문자"
    for key in ("name", "description", "labels"):
        assert re.search(rf"^{key}: \S", head, re.M), key
    assert re.search(rf'^labels: \["{FORMS[name]}"\]$', head, re.M)
    assert " / " in re.search(r"^name: (.+)$", head, re.M).group(1), "한/영 이름이 아님"


@pytest.mark.parametrize("name", sorted(FORMS))
def test_form_fields_are_well_formed_and_bilingual(name):
    _, _, fields = _form(name)
    assert any(req for _, req, _ in fields.values()), "필수 칸이 하나도 없음"
    for k, (kind, _, b) in fields.items():
        assert kind in {"input", "textarea", "dropdown", "checkboxes"}, (k, kind)
        label = re.search(r"^      label: (.+)$", b, re.M)
        assert label, f"{k}: label 없음"
        if k != "os":
            assert " / " in label.group(1), f"{k}: 한/영 label 이 아님 ({label.group(1)})"
        if kind == "dropdown":
            assert re.search(r"^      options:\n(        - .+\n)+", b, re.M), f"{k}: options 없음"


def test_bug_form_required_fields():
    _, _, fields = _bug_form()
    required = {k for k, (_, req, _) in fields.items() if req}
    assert {"doctor", "blender-version", "os", "client", "repro", "actual"} <= required


def test_feature_form_required_fields():
    text, _, fields = _form("feature_request.yml")
    required = {k for k, (_, req, _) in fields.items() if req}
    assert {"goal", "prompt", "workaround"} <= required
    assert "docs/recipes.md" in text
    support = (ROOT / "SUPPORT.md").read_text(encoding="utf-8")
    assert "issues/new?template=feature_request.yml" in support


def test_bug_form_asks_for_repro_info():
    text, _, fields = _bug_form()
    for needed in ("blender-fx-doctor", "Blender version", "BLENDER_FX_LANG", "SECURITY.md"):
        assert needed in text
    # --json 안내는 doctor 칸 안에, 실제로 있는 옵션이어야 한다
    assert "`--json`" in fields["doctor"][2]
    assert '"--json"' in (ROOT / "src" / "blender_fx_mcp" / "doctor.py").read_text(encoding="utf-8")
    langs = re.findall(r"^        - (\w+)$", fields["lang"][2], re.M)
    assert langs == ["ko", "en"]  # i18n.t 가 고르는 두 언어


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
    return re.findall(r"@mcp\.tool\([^)]*\)\s*\ndef (\w+)\(", src)


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


def _ignored(text):
    return set(re.findall(r"--ignore=tests/(test_\w+\.py)", text))


def test_ci_runs_every_test_file_except_blender_only_recipes():
    """CI 서버 시험은 파일을 손으로 적지 않고, 블렌더가 있어야 하는 레시피 시험 파일만 뺀다(새 시험 파일이 CI 에서 빠지지 않게)."""
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    run = next(line for line in ci.splitlines() if "--cov " in line)
    assert re.search(r"pytest -q tests --ignore=", run), "CI 는 tests/ 전체를 돌리고 --ignore 로만 빼야 함"
    listed = set(re.findall(r"tests/(test_\w+\.py)", run)) - _ignored(run)
    assert not listed, f"CI 가 시험 파일을 손으로 적음: {sorted(listed)}"
    blender_only = {
        p.name for p in (ROOT / "tests").glob("test_*.py")
        if re.search(r"^pytestmark = pytest\.mark\.skipif\(BLENDER is None", p.read_text(encoding="utf-8"), re.M)
    }
    assert blender_only, "블렌더 전용 시험 파일을 찾지 못함"
    assert _ignored(run) == blender_only, (
        f"CI 가 빼는 파일 {sorted(_ignored(run))} 과 블렌더 전용 시험 파일 {sorted(blender_only)} 이 다름"
    )


def test_contributing_coverage_command_matches_ci():
    """CONTRIBUTING 의 커버리지 명령(한/영)이 CI 와 같은 파일을 빼야 한다."""
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    run = next(line for line in ci.splitlines() if "--cov " in line)
    text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if "--cov" in line and "pytest" in line]
    assert len(lines) >= 2, "CONTRIBUTING 에 한/영 커버리지 명령이 모두 있어야 함"
    for line in lines:
        assert "pytest -q tests --ignore=" in line, line
        assert _ignored(line) == _ignored(run), f"CONTRIBUTING 의 --ignore 목록이 ci.yml 과 다름: {line[:80]}"


def test_coverage_artifacts_are_ignored():
    """`pytest --cov` 가 남기는 .coverage 는 기기마다 다른 SQLite 파일이라 저장소에 들어가면 안 된다."""
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".coverage" in ignored and "htmlcov/" in ignored


# 작업(job) 단위로만, 이 목록의 쓰기 권한만 허용한다. 나머지 워크플로는 write 가 한 글자도 없어야 한다.
JOB_WRITE_PERMISSIONS = {
    "stale.yml": {"issues: write"},
    "scorecard.yml": {"security-events: write", "id-token: write"},
}


@pytest.mark.parametrize("path", sorted((ROOT / ".github" / "workflows").glob("*.yml")), ids=lambda p: p.name)
def test_workflow_top_level_permissions_read_only(path):
    text = path.read_text(encoding="utf-8")
    # 최상위(들여쓰기 없는) permissions 가 jobs 보다 먼저 있고, 쓰기 권한이 없어야 한다
    m = re.search(r"^permissions:\n((?:[ \t]+.*\n)+)", text, re.M)
    assert m, f"{path.name}: 최상위 permissions 가 없음"
    assert text.index("\npermissions:") < text.index("\njobs:")
    assert "contents: read" in m.group(1) and "write" not in m.group(1)
    allowed = JOB_WRITE_PERMISSIONS.get(path.name, set())
    writes = re.findall(r"^\s+([\w-]+: write)$", text, re.M)
    assert set(writes) == allowed and len(writes) == len(allowed), f"{path.name}: 허용 밖 write 권한 {writes}"
    assert text.count("write") == len(writes), f"{path.name}: permissions 밖에 write 가 있음"
    for perm in writes:  # 쓰기 권한은 작업 안 permissions 블록에만
        block = re.search(r"^    permissions:\n((?:      .*\n)+)", text, re.M)
        assert block and perm in block.group(1), f"{path.name}: {perm} 이 작업 단위 permissions 에 없음"


@pytest.mark.parametrize("path", sorted((ROOT / ".github" / "workflows").glob("*.yml")), ids=lambda p: p.name)
def test_workflow_actions_pinned_to_sha(path):
    """외부 액션은 40자 커밋 SHA 로 고정하고 판 주석을 단다(OpenSSF Scorecard Pinned-Dependencies).
    태그는 옮겨질 수 있다. dependabot 은 SHA 와 판 주석을 함께 올린다."""
    uses = re.findall(r"^\s*-?\s*uses:\s*(.+)$", path.read_text(encoding="utf-8"), re.M)
    assert uses, f"{path.name}: uses 가 없음"
    for u in uses:
        if u.startswith("./"):  # 저장소 안 액션은 고정 대상이 아님
            continue
        assert re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40} # v\d+(\.\d+){0,2}", u.strip()), \
            f"{path.name}: SHA 고정 아님 또는 판 주석 없음: {u}"


# ---------- docs/architecture.md ----------
ARCH = ROOT / "docs" / "architecture.md"


def test_architecture_paths_exist():
    """구조 문서에 적은 파일 경로가 모두 저장소에 있어야 한다(파일이 옮겨지면 문서도 고친다)."""
    text = ARCH.read_text(encoding="utf-8")
    paths = set(re.findall(r"(?:src|scripts|tests|docs)/[\w./*-]+\.(?:py|md)", text))
    assert len(paths) >= 8
    missing = sorted(p for p in paths if "*" not in p and not (ROOT / p).exists())
    assert not missing, f"architecture.md 에 있지만 저장소에 없는 파일: {missing}"


def test_architecture_names_exist_in_code():
    """그림에 적은 함수·상수 이름이 실제 코드에 있어야 한다."""
    from blender_fx_mcp import bridge, server
    for name in ("check_choices", "check_ranges", "build_code", "parse_result", "CHOICES", "RANGES"):
        assert hasattr(server, name), name
    assert hasattr(bridge, "run_python")
    common = (ROOT / "src/blender_fx_mcp/recipes/_common.py").read_text(encoding="utf-8")
    for name in ("def run_guarded", "def L(", "class FxError", '"FX_RESULT "'):
        assert name in common, name
    assert '"execute_code"' in (ROOT / "src/blender_fx_mcp/bridge.py").read_text(encoding="utf-8")
    assert "app_only" in (ROOT / "tests/conftest.py").read_text(encoding="utf-8")


def test_architecture_tool_count_matches_server():
    import asyncio

    from blender_fx_mcp import server
    count = len(asyncio.run(server.mcp.list_tools()))
    text = ARCH.read_text(encoding="utf-8")
    assert f"도구 {count}개" in text and f"{count} tools" in text


def test_architecture_has_both_languages_and_is_linked():
    text = ARCH.read_text(encoding="utf-8")
    assert "## 한국어" in text and "## English" in text
    english = text[text.index("## English"):]
    assert not re.search(r"[가-힣]", english), "영어 절에 한글"
    for doc in ("README.md", "CONTRIBUTING.md"):
        assert "docs/architecture.md" in (ROOT / doc).read_text(encoding="utf-8"), f"{doc} 에서 링크 없음"


def test_issue_template_links_point_to_existing_forms():
    # 문서의 `issues/new?template=...` 링크가 지운 양식(.md)을 가리키지 않게
    for path in [ROOT / "README.md", ROOT / "CONTRIBUTING.md", *ROOT.glob("*.md"), *(ROOT / "docs").glob("*.md")]:
        for name in re.findall(r"issues/new\?template=([\w.-]+)", path.read_text(encoding="utf-8")):
            assert (TEMPLATES / name).is_file(), f"{path.name}: 없는 양식 {name}"


def _support_rows():
    text = (ROOT / "SUPPORT.md").read_text(encoding="utf-8")
    part = text.split("## 지원하는 판", 1)[1]
    return text, [[c.strip() for c in line.strip("|").split("|")] for line in part.splitlines()
                  if line.startswith("| ") and not line.startswith("| 대상")]


def test_support_python_versions_match_classifiers_and_ci():
    _, rows = _support_rows()
    py = next(r for r in rows if r[0].startswith("파이썬"))
    listed = [int(m) for m in re.findall(r"3\.(\d+)", py[1])]
    proj = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    classifiers = [int(m) for m in re.findall(r'"Programming Language :: Python :: 3\.(\d+)"', proj)]
    assert listed == classifiers, (listed, classifiers)
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    matrix = re.search(r"^\s+python: \[(.*?)\]$", ci, re.M).group(1)
    in_ci = [int(m) for m in re.findall(r'"3\.(\d+)"', matrix)]
    said = [int(m) for m in re.findall(r"3\.(\d+)", py[2].split("/")[0])]
    assert said == in_ci, f"SUPPORT.md 는 CI 가 {said} 를 돈다고 하지만 ci.yml 은 {in_ci}"


def test_support_blender_versions_match_ci_and_readme():
    _, rows = _support_rows()
    blender = [r for r in rows if r[0].startswith("블렌더")]
    main = re.match(r"(\d+\.\d+)", blender[0][1]).group(1)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"블렌더 {main}" in readme and f"Blender {main}" in readme
    app = (ROOT / ".github" / "workflows" / "app-tests.yml").read_text(encoding="utf-8")
    assert re.search(rf'default: "{re.escape(main)}\.\d+"', app), "app-tests 기본 블렌더 판이 SUPPORT.md 와 다름"
    bpy = re.search(r"`bpy` (\d+\.\d+\.\d+)", blender[1][1]).group(1)
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert f"bpy=={bpy}" in ci, f"ci.yml 의 bpy 판이 SUPPORT.md({bpy})와 다름"


def test_support_package_line_matches_version_and_security():
    _, rows = _support_rows()
    pkg = next(r for r in rows if r[0] == "blender-fx-mcp")
    series = re.match(r"(\d+\.\d+)\.x", pkg[1]).group(1)
    proj = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert re.search(rf'^version = "{re.escape(series)}\.\d+"', proj, re.M)
    assert f"| {series}.x" in (ROOT / "SECURITY.md").read_text(encoding="utf-8")


def test_support_links_and_reply_target():
    text, _ = _support_rows()
    for rel in re.findall(r"\]\(((?!https?:)[^)#]+)\)", text):
        assert (ROOT / rel).is_file(), rel
    sec = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert "7일 안" in sec and "| 보안 신고 / Security report | 7일 안" in text, "보안 응답 목표가 SECURITY.md 와 다름"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.count("(SUPPORT.md)") >= 2, "README 한/영 절에서 SUPPORT.md 링크"


def _recipe_sections():
    text = (ROOT / "docs" / "recipes.md").read_text(encoding="utf-8")
    ko, _, en = text.partition("\n## English\n")
    assert en, "docs/recipes.md 에 '## English' 절이 없음"

    def examples(part, level):
        heads = re.split(rf"^{level} (\d+)\. ", part, flags=re.M)[1:]
        return {int(n): re.findall(r"^\| \d+ \| `([^`]+)` \|$", body, re.M) for n, body in zip(heads[::2], heads[1::2])}

    return ko, en, examples(ko, "##"), examples(en, "###")


def test_recipes_english_section_mirrors_korean():
    _, _, ko, en = _recipe_sections()
    assert sorted(ko) == sorted(en) == list(range(1, len(ko) + 1)), (sorted(ko), sorted(en))
    for n in ko:
        assert ko[n] and ko[n] == en[n], f"예시 {n}: 한/영 도구 호출이 다름\n{ko[n]}\n{en[n]}"


def test_recipes_calls_use_real_tools_and_args():
    import ast
    import inspect

    from blender_fx_mcp import server
    _, _, ko, _ = _recipe_sections()
    for n, calls in ko.items():
        for call in calls:
            node = ast.parse(call.replace("…", "x"), mode="eval").body
            fn = getattr(server, node.func.id, None)
            assert callable(fn), f"예시 {n}: 없는 도구 {node.func.id}"
            params = inspect.signature(fn).parameters
            for kw in node.keywords:
                assert kw.arg in params, f"예시 {n}: {node.func.id} 에 없는 인자 {kw.arg}"


def test_recipes_english_has_no_hangul_and_is_linked():
    _, en, _, _ = _recipe_sections()
    assert not re.search(r"[가-힣]", en), "영어 절에 한글"
    text = (ROOT / "docs" / "recipes.md").read_text(encoding="utf-8")
    assert "](#english)" in text.split("\n## ", 1)[0], "맨 위에 영어 절 링크"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    english = readme.split("\n## English", 1)[1]
    assert "](docs/recipes.md#english)" in english


def test_recipes_calls_pass_server_checks(monkeypatch, tmp_path):
    # 문서의 인자가 서버의 목록·범위 검사를 통과해 실제로 블렌더까지 가는지(예시를 그대로 따라 하면 오류가 나지 않게)
    from blender_fx_mcp import bridge, server
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", "ko")
    _, _, ko, _ = _recipe_sections()
    for n, calls in ko.items():
        for call in calls:
            sent = []

            def reached(code, timeout=None, sent=sent):
                sent.append(code)
                raise bridge.BlenderError("여기까지 오면 통과")  # 결과 처리는 test_server_tools 몫

            monkeypatch.setattr(bridge, "run_python", reached)
            out = eval(call.replace("…/model.glb", str(tmp_path / "model.glb")), vars(server))
            out = out if isinstance(out, str) else out[0]
            assert sent, f"예시 {n}: {call} 이 블렌더로 가기 전에 막힘: {out}"


def _changelog_sections():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    parts = re.split(r"^## (\d+\.\d+\.\d+) — (.+)$", text, flags=re.M)
    return [(parts[i], parts[i + 1].strip(), parts[i + 2]) for i in range(1, len(parts), 3)]


def _english_summary(body):
    m = re.search(r"^\*\*English summary\*\*\n(.*?)(?=^\*\*[^*\n]+\*\*$|\Z)", body, re.S | re.M)
    return m and m.group(1)


def test_changelog_unreleased_sections_have_english_summary():
    """해외 사용자·심사자도 릴리스 노트를 읽을 수 있게: 0.7.0 부터(미출시 절은 반드시) 영어 요약이 있어야 한다."""
    checked = 0
    for version, when, body in _changelog_sections():
        unreleased = not re.fullmatch(r"\d{4}-\d{2}-\d{2}", when)
        if not unreleased and tuple(map(int, version.split("."))) < (0, 7, 0):
            continue
        summary = _english_summary(body)
        assert summary, f"{version}: '**English summary**' 절이 없음"
        assert not re.search(r"[가-힣]", summary), f"{version}: 영어 요약에 한글이 섞임"
        for part in ("Fixes", "Tests and CI", "Docs"):
            m = re.search(rf"^\*{part}\*\n((?:- .*\n(?:  .*\n)*)+)", summary, re.M)
            assert m, f"{version}: 영어 요약에 *{part}* 목록이 없음"
            assert 1 <= len(re.findall(r"^- ", m.group(1), re.M)) <= 6, f"{version} {part}: 1~6줄로 요약"
        checked += 1
    assert checked >= 1


def test_changelog_english_summary_before_korean_details():
    # 요약이 한국어 상세 목록보다 앞에 있어야 첫 화면에서 보인다
    version, _, body = _changelog_sections()[0]
    assert body.index("**English summary**") < body.index("**고침**"), version


def _contributing_section(title, end):
    text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    start = text.index(title)
    return text[start:text.index(end, start + len(title))]


HANGUL_RE = re.compile(r"[가-힣]")
GOOD_FIRST_KO = ("## 처음 기여하기 좋은 일", "### Good first contributions")
GOOD_FIRST_EN = ("### Good first contributions", "\n## 규칙")


@pytest.mark.parametrize("bounds", [GOOD_FIRST_KO, GOOD_FIRST_EN])
def test_good_first_paths_and_commands_exist(bounds):
    """'처음 기여하기 좋은 일' 표의 파일·시험 명령이 실제로 있어야 새 기여자가 길을 잃지 않는다."""
    sec = _contributing_section(*bounds)
    paths = set(re.findall(r"`((?:src|docs|tests)/[\w./-]+)`", sec)) | set(re.findall(r"(tests/\w+\.py)", sec))
    assert len(paths) >= 8, paths
    for p in paths:
        assert (ROOT / p).is_file(), p
    commands = re.findall(r"`(uv run pytest -q [^`]+)`", sec)
    assert len(commands) >= 4
    for cmd in commands:
        files = re.findall(r"tests/\w+\.py", cmd)
        assert files, cmd
        k = re.search(r"-k (\w+)", cmd)
        if k:
            # -k 로 고른 이름의 시험이 그 파일에 실제로 있어야 한다(0개 선택은 통과처럼 보인다)
            assert any(re.search(rf"def test_\w*{k.group(1)}", (ROOT / f).read_text(encoding="utf-8")) for f in files), cmd
    # 표에 적은 상수·도구 이름이 코드에 있는지
    server = (ROOT / "src/blender_fx_mcp/server.py").read_text(encoding="utf-8")
    common = (ROOT / "src/blender_fx_mcp/recipes/_common.py").read_text(encoding="utf-8")
    assert "GROUND_MATERIALS = {" in common and "CHOICES:" in server
    assert "def set_ground(" in server and "def make_demo_building(" in server


def test_good_first_labels_match_support():
    ko = _contributing_section(*GOOD_FIRST_KO)
    en = _contributing_section(*GOOD_FIRST_EN)
    support = (ROOT / "SUPPORT.md").read_text(encoding="utf-8")
    for label in ("good first issue", "needs-info"):
        assert f"`{label}`" in ko and f"`{label}`" in en, label
    assert "`needs-info`" in support and "30" in support
    assert "30일" in ko and "30 days" in en
    assert not HANGUL_RE.search(en), "영어 절에 한글이 섞임"
    # 영어 첫 문단에서 이 절로 가는 링크
    assert "(#good-first-contributions)" in (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8").split("\n## ")[0]



def test_ci_has_coverage_floor_matching_contributing():
    """CI 커버리지 하한이 있고, CONTRIBUTING(한/영)이 같은 수치를 말해야 한다."""
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    m = re.search(r"--cov-fail-under=(\d+)", ci)
    assert m, "ci.yml 에 --cov-fail-under 하한이 없음"
    floor = int(m.group(1))
    assert 90 <= floor <= 100, floor
    text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert f"**{floor}% 아래면 실패**" in text, "CONTRIBUTING 한국어 절의 하한이 ci.yml 과 다름"
    assert f"{floor}% floor" in text, "CONTRIBUTING 영어 절의 하한이 ci.yml 과 다름"
    assert text.count(f"--cov-fail-under={floor}") >= 2


MAINT = ROOT / "docs" / "maintenance.md"


def test_maintenance_has_both_languages_and_is_linked():
    text = MAINT.read_text(encoding="utf-8")
    assert "## 한국어" in text and "## English" in text
    korean, english = text.split("## English")
    assert not re.search(r"[가-힣]", english), "maintenance.md 영어 절에 한글"
    assert korean.count("### ") == english.count("### "), "한/영 소절 수가 다름"
    for doc in ("README.md", "SUPPORT.md"):
        assert "docs/maintenance.md" in (ROOT / doc).read_text(encoding="utf-8"), f"{doc} 에서 링크 없음"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.count("docs/maintenance.md") >= 2, "README 한/영 절 모두에서 링크"


def test_maintenance_links_exist():
    text = MAINT.read_text(encoding="utf-8")
    links = re.findall(r"\]\(([^)#]+)\)", text)
    assert links
    for link in links:
        assert (MAINT.parent / link).resolve().is_file(), link


def test_maintenance_matches_support_and_labels():
    """응답 일수·라벨·needs-info 마감이 SUPPORT.md·CONTRIBUTING 과 같아야 한다."""
    text = MAINT.read_text(encoding="utf-8")
    support = (ROOT / "SUPPORT.md").read_text(encoding="utf-8")
    for days in re.findall(r"(\d+)일 안", support):
        assert f"{days}일 안" in text and f"within {days} days" in text, days
    m = re.search(r"(\d+)일 동안 답이 없으면", support)
    assert m and f"{m.group(1)}일 동안 답이 없으면" in text and f"{m.group(1)} days without a reply" in text
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    for label in ("needs-info", "good first issue"):
        assert text.count(f"`{label}`") >= 2, label
        assert label in support or label in contributing, label


def test_maintenance_matches_dependabot_and_python():
    """dependabot 의 커밋 접두어·생태계, 가장 낮은 파이썬 판이 문서와 같아야 한다."""
    text = MAINT.read_text(encoding="utf-8")
    bot = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    for eco, prefix in re.findall(r'package-ecosystem: "([\w-]+)".*?prefix: "(\w+)"', bot, re.S):
        assert f"**`{prefix}`(" in text and f"**`{prefix}` (" in text, prefix
        assert eco in text, eco
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for job in ("server-tests", "recipe-tests-bpy"):
        assert f"{job}:" in ci, job
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    lowest = re.findall(r"Programming Language :: Python :: (3\.\d+)\"", pyproject)[0]
    assert f"지금 가장 낮은 {lowest}" in text and f"The lowest version today, {lowest}" in text


BPY_SCRIPT = ROOT / "scripts" / "bpy_tests.sh"


def test_bpy_script_matches_ci_bpy_job():
    # 클라우드에서 쓰는 bpy 시험 스크립트가 CI 의 recipe-tests-bpy 작업과 같은 판·패키지를 쓰는지.
    script = BPY_SCRIPT.read_text(encoding="utf-8")
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    job = ci.split("recipe-tests-bpy:", 1)[1]
    bpy = re.search(r'^BPY_VERSION="([\d.]+)"', script, re.M).group(1)
    py = re.search(r'^PYTHON_VERSION="([\d.]+)"', script, re.M).group(1)
    assert f"bpy=={bpy}" in job
    assert f"uv python install {py}" in job
    ci_pkgs = set(re.search(r"apt-get install -y ([^\n]+)", job).group(1).split())
    script_pkgs = set(re.search(r"apt-get install -y ([^\"\n]+)", script).group(1).split())
    assert script_pkgs == ci_pkgs


def test_bpy_script_is_runnable_and_documented():
    assert BPY_SCRIPT.stat().st_mode & 0o111, "실행 권한이 없음(chmod +x)"
    assert BPY_SCRIPT.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash\n")
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").split()
    assert ".venv-bpy/" in ignored
    assert "scripts/bpy_tests.sh" in (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")


def _minor_list(text):
    return sorted({int(m) for m in re.findall(r"3\.(\d+)", text)})


def test_python_version_range_is_the_same_everywhere():
    """지원 파이썬 판(가장 낮은 판·가장 높은 판)이 적힌 곳을 한 번에 본다.
    3.10 을 뺄 때 분류자만 고치면 나머지 어긋난 곳을 모두 짚는다(maintenance.md 의 EOL 정리 기준)."""
    proj = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    classifiers = sorted(int(m) for m in re.findall(r'"Programming Language :: Python :: 3\.(\d+)"', proj))
    low, high = classifiers[0], classifiers[-1]
    assert classifiers == list(range(low, high + 1)), f"분류자에 빠진 판: {classifiers}"
    found = {}
    found["pyproject requires-python"] = int(re.search(r'^requires-python = ">=3\.(\d+)"', proj, re.M).group(1))
    found["pyproject ruff target-version"] = int(re.search(r'^target-version = "py3(\d+)"', proj, re.M).group(1))
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    found["uv.lock requires-python"] = int(re.search(r'^requires-python = ">=3\.(\d+)"', lock, re.M).group(1))
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    matrix = _minor_list(re.search(r"^\s+python: \[(.*?)\]$", ci, re.M).group(1))
    found["ci.yml 행렬 최저"] = matrix[0]
    support = next(r for r in _support_rows()[1] if r[0].startswith("파이썬"))
    found["SUPPORT.md 표 최저"] = _minor_list(support[1])[0]
    badge = re.search(r"badge/python-3\.(\d+)%E2%80%933\.(\d+)-", (ROOT / "README.md").read_text(encoding="utf-8"))
    found["README 배지 최저"] = int(badge.group(1))
    arch = ARCH.read_text(encoding="utf-8")
    for line in re.findall(r"^.*CI server-tests.*$", arch, re.M):
        found[f"architecture.md: {line.strip()[:30]}"] = _minor_list(line)[0]
    maint = (ROOT / "docs" / "maintenance.md").read_text(encoding="utf-8")
    found["maintenance.md 한국어"] = int(re.search(r"지금 가장 낮은 3\.(\d+)", maint).group(1))
    found["maintenance.md 영어"] = int(re.search(r"The lowest version today, 3\.(\d+)", maint).group(1))
    wrong = {k: f"3.{v}" for k, v in found.items() if v != low}
    assert not wrong, f"가장 낮은 판이 분류자(3.{low})와 다른 곳: {wrong}"
    assert matrix[-1] == high and _minor_list(support[1])[-1] == high and int(badge.group(2)) == high, \
        f"가장 높은 판(3.{high})이 CI 행렬·SUPPORT 표·README 배지 중 어딘가와 다름"


LABELS = ROOT / ".github" / "labels.yml"
LABEL_RE = re.compile(r'^- name: "([^"]+)"\n  color: "([0-9a-f]{6})"\n  description: "([^"]+)"$', re.M)


def _labels():
    text = LABELS.read_text(encoding="utf-8")
    found = LABEL_RE.findall(text)
    assert len(found) == text.count("- name:"), "labels.yml 의 항목 모양이 다름(name·color·description 순서)"
    return {name: (color, desc) for name, color, desc in found}


def test_labels_file_is_well_formed():
    labels = _labels()
    assert len(labels) == LABELS.read_text(encoding="utf-8").count("- name:"), "라벨 이름 중복"
    for name, (_, desc) in labels.items():
        assert len(desc) <= 100, f"{name}: GitHub 라벨 설명은 100자까지"
        ko, sep, en = desc.partition(" / ")
        assert sep and HANGUL_RE.search(ko) and en and not HANGUL_RE.search(en), f"{name}: 설명이 '한국어 / English' 가 아님"


def _used_labels():
    used = {}
    for name in FORMS:
        m = re.search(r"^labels: \[(.*)\]$", (TEMPLATES / name).read_text(encoding="utf-8"), re.M)
        used.update({lab: name for lab in re.findall(r'"([^"]+)"', m.group(1))})
    bot = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    for line in re.findall(r"^    labels: \[(.*)\]$", bot, re.M):
        used.update({lab: "dependabot.yml" for lab in re.findall(r'"([^"]+)"', line)})
    stale = (ROOT / ".github" / "workflows" / "stale.yml").read_text(encoding="utf-8")
    for key in ("only-labels", "stale-issue-label"):
        used[re.search(rf'^          {key}: "([^"]+)"$', stale, re.M).group(1)] = "stale.yml"
    pattern = re.compile(
        r"`([a-z][a-z -]+)` ?(?:라벨|label)|(?:labell?ed|[Ll]abel|as) `([a-z][a-z -]+)`|^- `([a-z][a-z -]+)` —", re.M
    )
    for doc in ("CONTRIBUTING.md", "SUPPORT.md", "docs/maintenance.md"):
        for m in pattern.finditer((ROOT / doc).read_text(encoding="utf-8")):
            used[next(g for g in m.groups() if g)] = doc
    return used


def test_every_used_label_is_defined():
    """양식·dependabot·문서가 말하는 라벨이 모두 labels.yml 에 있어야 한다(저장소에 실제로 만들 목록)."""
    labels = _labels()
    used = _used_labels()
    for need in ("bug", "enhancement", "needs-info", "good first issue", "dependencies"):
        assert need in used, f"{need} 을 쓰는 곳을 찾지 못함(찾는 규칙이 깨졌는지 확인)"
    missing = {lab: where for lab, where in used.items() if lab not in labels}
    assert not missing, f"labels.yml 에 없는 라벨: {missing}"
    # dependabot 은 labels 를 적지 않으면 기본 라벨(생태계 이름 등)을 붙인다
    bot = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    assert bot.count("    labels: [") == bot.count("package-ecosystem:")


def test_maintenance_label_commands_match_labels_file():
    """maintenance.md 의 `gh label create` 명령이 labels.yml 과 같은 이름·색·설명이어야 한다."""
    text = MAINT.read_text(encoding="utf-8")
    cmds = re.findall(r'^gh label create "([^"]+)" --color (\w+) --description "([^"]+)" --force$', text, re.M)
    assert {n: (c, d) for n, c, d in cmds} == _labels()
    assert len(cmds) == text.count("gh label create \"")
    assert ".github/labels.yml" in text.split("## English")[1]


def test_stale_workflow_matches_needs_info_deadline():
    """needs-info 자동 닫기의 일수 합이 SUPPORT·maintenance.md 의 마감과 같고, PR·다른 이슈는 건드리지 않아야 한다."""
    text = (ROOT / ".github" / "workflows" / "stale.yml").read_text(encoding="utf-8")
    opt = dict(re.findall(r"^          ([\w-]+): (-?\d+)$", text, re.M))
    support = (ROOT / "SUPPORT.md").read_text(encoding="utf-8")
    deadline = int(re.search(r"(\d+)일 동안 답이 없으면", support).group(1))
    stale, close = int(opt["days-before-stale"]), int(opt["days-before-close"])
    assert stale + close == deadline and close > 0
    assert opt["days-before-pr-stale"] == opt["days-before-pr-close"] == "-1"
    assert re.search(r'^          only-labels: "needs-info"$', text, re.M)
    # 안내 문장의 일수가 설정과 같고 한/영 모두 있는지
    assert f"{stale}일" in text and f"{close}일" in text and f"{deadline}일" in text
    assert f"{stale} days" in text and f"{close} days" in text and f"{deadline} days" in text
    maint = MAINT.read_text(encoding="utf-8")
    assert maint.count(".github/workflows/stale.yml") >= 2
    assert f"{stale}일 조용하면" in maint and f"after {stale} quiet days" in maint
    assert re.search(r"^  schedule:\n    - cron: ", text, re.M)


def test_scorecard_workflow_and_badge():
    """Scorecard 작업이 기본 브랜치에서 결과를 공개하고, README 배지가 이 저장소의 점수를 가리켜야 한다."""
    text = (ROOT / ".github" / "workflows" / "scorecard.yml").read_text(encoding="utf-8")
    assert re.search(r"^  push:\n    branches: \[main\]$", text, re.M)
    assert re.search(r"^  schedule:\n    - cron: ", text, re.M)
    assert "pull_request" not in text, "Scorecard 는 PR 에서 결과를 공개할 수 없다"
    assert "publish_results: true" in text and "persist-credentials: false" in text
    assert "ossf/scorecard-action@" in text and "codeql-action/upload-sarif@" in text
    job = re.search(r"^    permissions:\n((?:      .*\n)+)", text, re.M).group(1)
    perms = set(re.findall(r"^      ([\w-]+: \w+)$", job, re.M))
    assert perms == {"contents: read", "actions: read", "security-events: write", "id-token: write"}, perms
    repo = "github.com/choisam4u-creator/blender-fx-mcp"
    badges = {alt: (img, link) for alt, img, link in _badges()}
    img, link = badges["OpenSSF Scorecard"]
    assert img == f"https://api.scorecard.dev/projects/{repo}/badge"
    assert link == f"https://scorecard.dev/viewer/?uri={repo}"


ONE_LINE_KO = "## 나머지 도구 한 줄 예시"
ONE_LINE_EN = "### Every other tool in one line"
ONE_LINE_ROW = re.compile(r'^\| "[^"]+" \| `([^`]+)` \| .+ \|$', re.M)


def _one_line_calls():
    text = (ROOT / "docs" / "recipes.md").read_text(encoding="utf-8")
    ko = text.split(ONE_LINE_KO, 1)[1].split("\n## ", 1)[0]
    en = text.split(ONE_LINE_EN, 1)[1].split("\n### ", 1)[0]
    return ONE_LINE_ROW.findall(ko), ONE_LINE_ROW.findall(en)


def test_every_tool_has_a_recipes_example():
    """32개 도구가 docs/recipes.md 의 예시(번호 예시 또는 한 줄 예시)에 한 번은 나와야 한다. 한/영 표는 같은 호출."""
    import ast
    import asyncio

    from blender_fx_mcp import server
    ko, en = _one_line_calls()
    assert ko and ko == en, "한 줄 예시의 한/영 호출이 다름"
    _, _, numbered, _ = _recipe_sections()
    calls = [c for cs in numbered.values() for c in cs] + ko
    used = {ast.parse(c.replace("…", "x"), mode="eval").body.func.id for c in calls}
    tools = {tool.name for tool in asyncio.run(server.mcp.list_tools())}
    assert tools - used == set(), f"예시가 없는 도구: {sorted(tools - used)}"
    assert used <= tools, f"없는 도구: {sorted(used - tools)}"
    one_line = [ast.parse(c.replace("…", "x"), mode="eval").body.func.id for c in ko]
    assert len(one_line) == len(set(one_line)), "한 줄 예시에 같은 도구가 두 번"
    # 위 번호 예시에 이미 나온 도구는 한 줄 예시에 다시 적지 않는다
    assert not set(one_line) & {ast.parse(c.replace("…", "x"), mode="eval").body.func.id
                                for cs in numbered.values() for c in cs}
    text = (ROOT / "docs" / "recipes.md").read_text(encoding="utf-8")
    assert f"{len(tools)}개 도구" in text and f"{len(tools)} tools" in text


def test_one_line_examples_pass_server_checks(monkeypatch, tmp_path):
    """한 줄 예시를 그대로 불러도 서버의 목록·범위·경로 검사에 막히지 않고 블렌더까지 가야 한다."""
    import ast

    from blender_fx_mcp import bridge, server
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", "ko")

    def reached(*args, **kwargs):
        raise bridge.BlenderError("여기까지 오면 통과")

    monkeypatch.setattr(bridge, "run_python", reached)
    monkeypatch.setattr(bridge, "ping", reached)
    local = {"doctor", "list_snapshots"}  # 블렌더에 묻지 않고 이 컴퓨터에서 답하는 도구
    ko, _ = _one_line_calls()
    for call in ko:
        name = ast.parse(call.replace("…", "x"), mode="eval").body.func.id
        out = eval(call.replace("…/", f"{tmp_path}/"), vars(server))
        out = out if isinstance(out, str) else out[0]
        if name in local:
            assert out and not out.startswith("실패"), call
        else:
            assert out == "실패: 여기까지 오면 통과", f"{call} 이 블렌더로 가기 전에 막힘: {out}"
