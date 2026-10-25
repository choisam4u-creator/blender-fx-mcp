# uvx 로 판을 고정한 검사 도구(ruff·actionlint-py·shellcheck-py·zizmor·twine)는 uv.lock 밖이라 dependabot 이 못 본다.
# 판은 CONTRIBUTING 의 "판을 고정한 도구" 표 한 곳에 두고, 워크플로·문서 속 `도구@판` 과 판 없는 `uvx 도구` 를 여기서 막는다.
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ("ruff", "actionlint-py", "shellcheck-py", "zizmor", "twine")
# 지난 회차 기록은 그때의 판을 그대로 남긴다
HISTORY = {"docs/CLOUD-BACKLOG.md", "docs/test-reports/CLOUD-NOTES.md"}


def pinned_table():
    text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    section = text.split("## 판을 고정한 도구 / Pinned tools", 1)[1].split("\n## ", 1)[0]
    return dict(re.findall(r"^\| ([a-z][\w-]*) \| (\d+(?:\.\d+)+) \|", section, re.M))


def checked_files():
    files = [*(ROOT / ".github").rglob("*.yml"), *(ROOT / ".github").rglob("*.md"), *ROOT.glob("*.md"), *(ROOT / "docs").rglob("*.md"), *(ROOT / "scripts").glob("*")]
    return [p for p in files if p.is_file() and p.relative_to(ROOT).as_posix() not in HISTORY]


def test_table_lists_every_uvx_tool():
    assert set(pinned_table()) == set(TOOLS), f"CONTRIBUTING 의 판 표: {pinned_table()}"


def test_every_pinned_version_matches_the_table():
    table = pinned_table()
    wrong = []
    for path in checked_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for tool, version in re.findall(r"\b(" + "|".join(map(re.escape, TOOLS)) + r")(?:@|==)(\d+(?:\.\d+)+)", text):
            if version != table[tool]:
                wrong.append(f"{path.relative_to(ROOT)}: {tool}@{version} (표는 {table[tool]})")
    assert not wrong, "판이 CONTRIBUTING 표와 다름 — 표와 함께 한 번에 올리세요:\n" + "\n".join(wrong)


def test_uvx_tool_commands_are_pinned():
    # `uvx ruff check .` 처럼 판 없이 부르면 그날의 최신 판이 돌아 규칙이 저절로 바뀐다
    loose = []
    pattern = re.compile(r"uvx (?:--from )?(" + "|".join(map(re.escape, TOOLS)) + r")(?![@\w-])")
    for path in checked_files():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if pattern.search(line):
                loose.append(f"{path.relative_to(ROOT)}: {line.strip()[:100]}")
    assert not loose, "판 없는 uvx 도구 호출 — `도구@판`(CONTRIBUTING 표)으로:\n" + "\n".join(loose)


def test_ci_runs_every_table_tool_at_its_version():
    workflows = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / ".github" / "workflows").glob("*.yml"))
    for tool, version in pinned_table().items():
        assert f"{tool}@{version}" in workflows or f"{tool}=={version}" in workflows, f"표의 {tool}@{version} 를 쓰는 워크플로가 없음 — 안 쓰면 표에서 지우세요"


def test_quarterly_bump_step_is_written_down():
    text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8").split("## 판을 고정한 도구 / Pinned tools", 1)[1].split("\n## ", 1)[0]
    assert "분기마다" in text and "Once a quarter" in text
    assert "tests/test_pinned_tools.py" in text
