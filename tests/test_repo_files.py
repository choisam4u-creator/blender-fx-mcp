# 저장소 안내 파일(이슈 양식 등) 점검. 블렌더 없이 돈다.
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / ".github" / "ISSUE_TEMPLATE"


@pytest.mark.parametrize("name", ["feature_request.md"])
def test_issue_template_front_matter(name):
    text = (TEMPLATES / name).read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, f"{name}: 맨 위 --- 머리말이 없음"
    keys = {line.split(":", 1)[0] for line in m.group(1).splitlines() if ":" in line}
    assert {"name", "about"} <= keys


def _bug_form():
    # PyYAML 없이 읽는다: 이 양식은 `  - type:` 로 칸을 나누는 고정 모양만 쓴다.
    text = (TEMPLATES / "bug_report.yml").read_text(encoding="utf-8")
    head, _, body = text.partition("\nbody:\n")
    blocks = re.split(r"^  - type: ", body, flags=re.M)[1:]
    fields = {}
    for b in blocks:
        kind = b.split("\n", 1)[0].strip()
        m = re.search(r"^    id: ([\w-]+)$", b, re.M)
        if kind == "markdown":
            continue
        assert m, f"{kind} 칸에 id 가 없음"
        req = re.search(r"^      required: (true|false)$", b, re.M)
        fields[m.group(1)] = (kind, req and req.group(1) == "true", b)
    return text, head, fields


def test_bug_form_is_the_only_bug_template():
    # .md 와 .yml 이 같이 있으면 GitHub 가 두 양식을 다 보여 준다
    assert (TEMPLATES / "bug_report.yml").is_file()
    assert not (TEMPLATES / "bug_report.md").exists()


def test_bug_form_header():
    text, head, _ = _bug_form()
    assert "\t" not in text, "YAML 에 탭 문자"
    for key in ("name", "description", "labels"):
        assert re.search(rf"^{key}: \S", head, re.M), key
    assert re.search(r'^labels: \["bug"\]$', head, re.M)


def test_bug_form_required_fields():
    _, _, fields = _bug_form()
    required = {k for k, (_, req, _) in fields.items() if req}
    assert {"doctor", "blender-version", "os", "client", "repro", "actual"} <= required
    assert len(fields) == len(set(fields)), "id 중복"
    for k, (kind, _, b) in fields.items():
        assert kind in {"input", "textarea", "dropdown", "checkboxes"}, (k, kind)
        assert re.search(r"^      label: \S", b, re.M), f"{k}: label 없음"
        if kind == "dropdown":
            assert re.search(r"^      options:\n(        - .+\n)+", b, re.M), f"{k}: options 없음"


def test_bug_form_asks_for_repro_info():
    text, _, fields = _bug_form()
    for needed in ("blender-fx-doctor", "Blender version", "BLENDER_FX_LANG", "SECURITY.md"):
        assert needed in text
    langs = re.findall(r"^        - (\w+)$", fields["lang"][2], re.M)
    assert langs == ["ko", "en"]  # i18n.t 가 고르는 두 언어


def test_bug_form_labels_are_bilingual():
    _, _, fields = _bug_form()
    for k, (_, _, b) in fields.items():
        label = re.search(r"^      label: (.+)$", b, re.M).group(1)
        if k != "os":
            assert " / " in label, f"{k}: 한/영 label 이 아님 ({label})"


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


def test_coverage_artifacts_are_ignored():
    """`pytest --cov` 가 남기는 .coverage 는 기기마다 다른 SQLite 파일이라 저장소에 들어가면 안 된다."""
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".coverage" in ignored and "htmlcov/" in ignored


@pytest.mark.parametrize("path", sorted((ROOT / ".github" / "workflows").glob("*.yml")), ids=lambda p: p.name)
def test_workflow_top_level_permissions_read_only(path):
    text = path.read_text(encoding="utf-8")
    # 최상위(들여쓰기 없는) permissions 가 jobs 보다 먼저 있고, 쓰기 권한이 없어야 한다
    m = re.search(r"^permissions:\n((?:[ \t]+.*\n)+)", text, re.M)
    assert m, f"{path.name}: 최상위 permissions 가 없음"
    assert text.index("\npermissions:") < text.index("\njobs:")
    assert "contents: read" in m.group(1)
    assert "write" not in text, f"{path.name}: write 권한이 있음"


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
