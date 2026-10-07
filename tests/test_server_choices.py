# 고정 목록 인자(impact·material·liquid·kind·preset·quality 등)의 서버 쪽 미리 검사. 블렌더 없이 돈다.
# 서버 목록(server.CHOICES)이 레시피 파일의 목록과 같은지, 틀린 값이 블렌더로 가기 전에 막히는지 본다.
import ast
from pathlib import Path

import pytest

from blender_fx_mcp import bridge, server

RECIPES = Path(server.__file__).parent / "recipes"


def _module_constant(file: str, name: str) -> tuple[str, ...]:
    """레시피 파일 맨 위의 NAME = {...} / (...) 에서 키나 원소(문자열)를 순서대로."""
    tree = ast.parse((RECIPES / file).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(tg, "id", None) == name for tg in node.targets):
            value = node.value
            items = value.keys if isinstance(value, ast.Dict) else value.elts
            return tuple(ast.literal_eval(k) for k in items)
    raise AssertionError(f"{file} 에 {name} 이 없음")


def _not_in_literal(file: str, var: str) -> tuple[str, ...]:
    """레시피 안의 `if var not in ("a", "b")` 에서 튜플 원소."""
    tree = ast.parse((RECIPES / file).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id == var
                and isinstance(node.ops[0], ast.NotIn) and isinstance(node.comparators[0], ast.Tuple)):
            return tuple(ast.literal_eval(node.comparators[0]))
    raise AssertionError(f"{file} 에 `{var} not in (...)` 가 없음")


RECIPE_SIDE = {
    ("destroy", "impact"): lambda: _module_constant("destroy.py", "SIDES"),
    ("destroy", "material"): lambda: _module_constant("destroy.py", "MATERIALS"),
    ("destroy", "pattern"): lambda: _module_constant("destroy.py", "PATTERNS"),
    ("destroy", "dust"): lambda: _module_constant("destroy.py", "DUST_LEVELS"),
    ("destroy", "glue"): lambda: _module_constant("destroy.py", "GLUE_LEVELS"),
    ("destroy", "collision"): lambda: _module_constant("destroy.py", "COLLISIONS"),
    ("destroy", "interior"): lambda: ("auto", "none") + _module_constant("destroy.py", "MATERIALS"),
    ("water", "mode"): lambda: _module_constant("water.py", "MODES"),
    ("water", "shape"): lambda: _module_constant("water.py", "SHAPES"),
    ("water", "liquid"): lambda: _module_constant("water.py", "LIQUIDS"),
    ("particles", "kind"): lambda: _module_constant("particles.py", "KINDS"),
    ("emit", "kind"): lambda: _not_in_literal("emit.py", "kind"),
    ("set_ground", "material"): lambda: _module_constant("_common.py", "GROUND_MATERIALS"),
    ("set_look", "preset"): lambda: _module_constant("set_look.py", "LOOKS"),
    ("set_look", "sky"): lambda: _not_in_literal("set_look.py", "sky_mode"),
    ("camera", "preset"): lambda: _module_constant("camera.py", "PRESETS"),
}


def test_every_server_choice_has_a_recipe_source():
    pairs = {(r, n) for r, d in server.CHOICES.items() for n in d}
    assert pairs - {("render", "quality"), ("render_video", "quality")} == set(RECIPE_SIDE)


@pytest.mark.parametrize("key", sorted(RECIPE_SIDE), ids=lambda k: f"{k[0]}.{k[1]}")
def test_server_list_matches_recipe(key):
    recipe, name = key
    assert server.CHOICES[recipe][name] == RECIPE_SIDE[key](), "레시피 목록이 바뀌면 server.CHOICES 도 고친다"


def test_quality_values_are_the_ones_render_understands():
    common = (RECIPES / "_common.py").read_text(encoding="utf-8")
    start = common.index("def apply_render_quality")
    body = common[start:common.index("\ndef ", start + 1)]
    for q in server.CHOICES["render"]["quality"]:
        assert q in body
    assert server.CHOICES["render"]["quality"] == server.CHOICES["render_video"]["quality"]


@pytest.fixture
def no_blender(monkeypatch):
    """블렌더로 가면 시험 실패. 검사가 소켓보다 먼저인지 확인한다."""
    def boom(*a, **k):
        raise AssertionError("검사 전에 블렌더로 보냄")
    monkeypatch.setattr(bridge, "run_python", boom)


@pytest.mark.parametrize("lang,expect", [
    ("ko", "material 값 'concret' 은(는) 쓸 수 없습니다. 가능한 값: concrete / brick"),
    ("en", "material 'concret' is not allowed. Choose one of: concrete / brick"),
])
def test_typo_is_caught_before_blender_with_suggestion(no_blender, monkeypatch, lang, expect):
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    out = server.destroy(target="Building", material="concret")
    assert expect in out
    assert ("혹시 'concrete' 인가요?" if lang == "ko" else "Did you mean 'concrete'?") in out


def test_case_and_space_still_suggest(no_blender, monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    assert "Did you mean 'honey'?" in server.water(liquid=" Honey")


def test_no_suggestion_when_nothing_is_close(no_blender, monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    out = server.particles(kind="zzzz")
    assert "Choose one of: rain / snow / sparks / ash." in out and "Did you mean" not in out


@pytest.mark.parametrize("call", [
    lambda: server.explode(target="Building", glue="stron"),      # explode 안의 destroy 단계
    lambda: server.set_look(preset="sunst"),
    lambda: server.set_look(sky="procedual"),
    lambda: server.camera(preset="close-up"),
    lambda: server.set_ground(material="gras"),
    lambda: server.render_preview(quality="hight"),
    lambda: server.render_video(quality="fnal"),
    lambda: server.destroy(target="B", impact="lft"),
    lambda: server.destroy(target="B", interior="wod"),
])
def test_each_tool_checks_before_blender(no_blender, monkeypatch, tmp_path, call):
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", "ko")
    out = call()
    out = out if isinstance(out, str) else out[0]
    assert out.startswith("실패: ") and "가능한 값" in out


def test_valid_values_reach_blender(monkeypatch):
    sent = []
    monkeypatch.setattr(bridge, "run_python", lambda code, timeout=None: sent.append(code) or 'FX_RESULT {"ok": true}')
    for recipe, names in server.CHOICES.items():
        server.run_recipe(recipe, {n: allowed[-1] for n, allowed in names.items()})
    assert len(sent) == len(server.CHOICES)


def test_none_and_unlisted_recipes_pass(monkeypatch):
    monkeypatch.setattr(bridge, "run_python", lambda code, timeout=None: 'FX_RESULT {"ok": true}')
    assert server.run_recipe("destroy", {"target": "B", "material": None})["ok"]
    assert server.run_recipe("list_objects", {"anything": "x"})["ok"]
