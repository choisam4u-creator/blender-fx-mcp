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
    ("demo_scene", "style"): lambda: _not_in_literal("demo_scene.py", "style"),
    ("demo_scene", "ground"): lambda: _module_constant("_common.py", "GROUND_MATERIALS"),
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


# ---------- 도구 설명(docstring)의 값 목록 ----------
# AI 는 도구 설명만 보고 값을 고른다. 설명에 적힌 값과 서버가 받는 값이 어긋나면 바로 오류가 난다.
# 도구 → 그 도구가 고정 목록 인자를 넘기는 레시피
TOOL_RECIPE = {
    "make_demo_building": "demo_scene",
    "destroy": "destroy",
    "explode": "destroy",
    "water": "water",
    "particles": "particles",
    "set_ground": "set_ground",
    "set_look": "set_look",
    "camera": "camera",
    "render_preview": "render",
    "render_video": "render_video",
}


def _tool_functions() -> dict[str, ast.FunctionDef]:
    tree = ast.parse(Path(server.__file__).read_text(encoding="utf-8"))
    return {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}


def _documented_values(doc: str, name: str) -> tuple[str, ...] | None:
    """설명에서 `name: a / b(설명) / c` 로 시작하는 줄의 값들. 괄호 속은 빼고, 각 칸의 첫 영어 낱말을 값으로 본다."""
    import re
    for line in doc.splitlines():
        line = re.sub(r"\([^)]*\)", "", line).strip()
        if line.startswith(f"{name}:"):
            values = []
            for part in line[len(name) + 1:].split("/"):
                m = re.search(r"[a-z][a-z_]*", part)
                assert m, f"{name} 줄의 '{part}' 칸에 값이 없음"
                values.append(m.group(0))
            return tuple(values)
    return None


def _cases():
    funcs = _tool_functions()
    for tool, recipe in TOOL_RECIPE.items():
        params = {a.arg for a in funcs[tool].args.args}
        for name in server.CHOICES[recipe]:
            if name in params:
                yield tool, recipe, name


@pytest.mark.parametrize("tool,recipe,name", list(_cases()), ids=lambda v: v if isinstance(v, str) else "")
def test_docstring_lists_exactly_the_allowed_values(tool, recipe, name):
    doc = ast.get_docstring(_tool_functions()[tool])
    documented = _documented_values(doc, name)
    assert documented is not None, f"{tool} 설명에 `{name}: a / b / c` 줄이 없음"
    allowed = server.CHOICES[recipe][name]
    assert set(documented) == set(allowed), (
        f"{tool}.{name}: 설명에만 있음 {sorted(set(documented) - set(allowed))}, "
        f"설명에 빠짐 {sorted(set(allowed) - set(documented))}")
    assert len(documented) == len(set(documented)), f"{tool}.{name}: 설명에 같은 값이 두 번"


def test_every_tool_with_choice_args_is_checked():
    """CHOICES 레시피로 가는 도구가 새로 생기면 TOOL_RECIPE 에도 넣게 한다."""
    import re
    src = Path(server.__file__).read_text(encoding="utf-8")
    funcs = _tool_functions()
    for name, fn in funcs.items():
        if not any(getattr(d, "func", None) is not None and getattr(d.func, "attr", "") == "tool"
                   for d in fn.decorator_list):
            continue
        body = ast.get_source_segment(src, fn)
        called = set(re.findall(r'run_recipe\("(\w+)"', body))
        params = {a.arg for a in fn.args.args}
        for recipe in called & set(server.CHOICES):
            if params & set(server.CHOICES[recipe]):
                assert name in TOOL_RECIPE, f"{name} 도구가 {recipe} 고정 목록 인자를 받는데 설명 검사 목록에 없음"
