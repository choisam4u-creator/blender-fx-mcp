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
