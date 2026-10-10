# MCP 프롬프트(first_demo·undo_last) 시험. 클라이언트의 `/` 메뉴에 뜨고, 문장이 실제 도구 이름만 쓰는지 본다. 블렌더 없이 돈다.
import asyncio
import re

import pytest

from blender_fx_mcp import server


def _prompts():
    return {p.name: p for p in asyncio.run(server.mcp.list_prompts())}


def _text(name, args=None):
    res = asyncio.run(server.mcp.get_prompt(name, args or {}))
    assert len(res.messages) == 1 and res.messages[0].role == "user"
    return res.messages[0].content.text


def _tools():
    return {t.name for t in asyncio.run(server.mcp.list_tools())}


def test_prompts_are_listed_with_title():
    ps = _prompts()
    assert set(ps) == {"first_demo", "undo_last"}
    for p in ps.values():
        # 제목·설명은 서버를 띄울 때의 언어(한/영 짝은 test_server_messages 가 점검)
        assert len(p.title) >= 8 and len(p.description) >= 20, p
    args = {a.name: a for a in ps["first_demo"].arguments}
    assert set(args) == {"impact", "material"} and not any(a.required for a in args.values())
    # 인자 설명의 값 목록 = 서버가 받는 값(CHOICES)
    for name, a in args.items():
        assert a.description.split(" / ") == list(server.CHOICES["destroy"][name])
    assert ps["undo_last"].arguments in (None, [])


@pytest.mark.parametrize("lang", ["ko", "en"])
@pytest.mark.parametrize("name", ["first_demo", "undo_last"])
def test_prompt_follows_language_and_names_real_tools(monkeypatch, lang, name):
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    text = _text(name)
    assert bool(re.search(r"[가-힣]", text)) is (lang == "ko"), text
    # 문장 속 snake_case 단어와 단계 머리 단어 중 도구처럼 보이는 것은 모두 실제 도구여야 한다
    words = set(re.findall(r"\b[a-z]+(?:_[a-z]+)+\b", text)) - {"before_demo", "before_restore"}
    words |= {w for w in re.findall(r"\b(doctor|snapshot|restore|destroy)\b", text)}
    assert words and words <= _tools(), words - _tools()


def test_first_demo_order_and_arguments(monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    text = _text("first_demo", {"impact": "top", "material": "glass"})
    order = ["ping_blender", "make_demo_building", "snapshot", "destroy", "render_preview"]
    pos = [text.index(w) for w in order]
    assert pos == sorted(pos), "README 첫 명령 예시와 같은 순서: 연결 → 건물 → 저장 → 붕괴 → 미리보기"
    assert "impact=top, material=glass" in text and "target=Building" in text
    # make_demo_building 기본 이름과 destroy 대상이 같아야 문장 그대로 돈다
    import inspect
    assert inspect.signature(server.make_demo_building).parameters["name"].default == "Building"
    assert "restore before_demo" in text


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_first_demo_wrong_argument_shows_allowed_values(monkeypatch, lang):
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    text = _text("first_demo", {"impact": "lft"})
    assert "left / right" in text and "'left'" in text
    assert "make_demo_building" not in text


def test_undo_last_confirms_before_restore(monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    text = _text("undo_last")
    assert text.index("list_snapshots") < text.index("ask me once") < text.index("call restore")
    assert "other than before_restore" in text


def test_readme_mentions_prompts():
    from pathlib import Path
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    ko, en = readme.split("\n## English\n", 1)
    for part in (ko, en):
        assert "/first_demo" in part and "/undo_last" in part
