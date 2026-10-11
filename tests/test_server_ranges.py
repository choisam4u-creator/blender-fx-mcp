# 숫자 인자(pieces·resolution·frames·focus·samples) 범위의 서버 쪽 미리 검사. 블렌더 없이 돈다.
# 레시피는 범위 밖 값을 조용히 잘라 쓴다. 서버 범위(server.RANGES)가 그 자르는 값과 같은지,
# 범위 밖 값이 블렌더로 가기 전에 막히는지, 도구 기본값이 범위 안인지 본다.
import ast
import inspect
from pathlib import Path

import pytest

from blender_fx_mcp import bridge, server

RECIPES = Path(server.__file__).parent / "recipes"


def _clamp(file: str, var: str) -> tuple[float, float | None]:
    """레시피의 `var = max(LO, min(..., HI))` 또는 `var = max(LO, ...)` 에서 (LO, HI)."""
    tree = ast.parse((RECIPES / file).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                and getattr(node.targets[0], "id", None) == var):
            continue
        call = node.value
        if not (isinstance(call, ast.Call) and getattr(call.func, "id", None) == "max"
                and isinstance(call.args[0], ast.Constant)):
            continue
        lo, inner = call.args[0].value, call.args[1]
        hi = None
        if (isinstance(inner, ast.Call) and getattr(inner.func, "id", None) == "min"
                and isinstance(inner.args[1], ast.Constant)):
            hi = inner.args[1].value
        return lo, hi
    raise AssertionError(f"{file} 에 `{var} = max(...)` 가 없음")


RECIPE_SIDE = {
    ("destroy", "pieces"): lambda: _clamp("destroy.py", "pieces"),
    ("destroy", "frames"): lambda: _clamp("destroy.py", "frames"),
    ("destroy", "focus"): lambda: _clamp("_common.py", "focus"),
    ("explode", "frames"): lambda: _clamp("explode.py", "frames"),
    ("explode", "resolution"): lambda: _clamp("explode.py", "resolution"),
    ("water", "frames"): lambda: _clamp("water.py", "frames"),
    ("water", "resolution"): lambda: _clamp("water.py", "resolution"),
    ("emit", "frames"): lambda: _clamp("emit.py", "frames"),
    ("emit", "resolution"): lambda: _clamp("emit.py", "resolution"),
    ("particles", "frames"): lambda: _clamp("particles.py", "frames"),
    ("set_render", "samples"): lambda: _clamp("set_render.py", "n"),
}


def test_every_server_range_has_a_recipe_source():
    assert {(r, n) for r, d in server.RANGES.items() for n in d} == set(RECIPE_SIDE)


@pytest.mark.parametrize("key", sorted(RECIPE_SIDE), ids=lambda k: f"{k[0]}.{k[1]}")
def test_server_range_matches_recipe_clamp(key):
    recipe, name = key
    assert server.RANGES[recipe][name] == RECIPE_SIDE[key](), "레시피가 자르는 값이 바뀌면 server.RANGES 도 고친다"


# 도구 → 그 도구가 숫자 인자를 넘기는 레시피들
TOOL_RECIPES = {
    "destroy": ["destroy"],
    "explode": ["destroy", "explode"],
    "water": ["water"],
    "fire": ["emit"],
    "smoke": ["emit"],
    "particles": ["particles"],
    "set_render": ["set_render"],
}


@pytest.mark.parametrize("tool", sorted(TOOL_RECIPES))
def test_tool_defaults_are_in_range(tool):
    """기본값은 범위 안이거나 0(서버가 None 으로 바꿔 레시피 기본값을 쓰게 함)이어야 한다."""
    sig = inspect.signature(getattr(server, tool))
    for recipe in TOOL_RECIPES[tool]:
        for name, (lo, hi) in server.RANGES[recipe].items():
            if name not in sig.parameters:
                continue
            d = sig.parameters[name].default
            assert d == 0 or (lo <= d and (hi is None or d <= hi)), f"{tool}.{name} 기본값 {d} 이 범위 {lo}~{hi} 밖"


@pytest.fixture
def no_blender(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("검사 전에 블렌더로 보냄")
    monkeypatch.setattr(bridge, "run_python", boom)


@pytest.mark.parametrize("lang,expect", [
    ("ko", "resolution 값 2000 은(는) 범위 밖입니다. 가능한 범위: 16 ~ 320. 32 빠름 / 64 보통 / 128 고화질."),
    ("en", "resolution 2000 is out of range. Allowed: 16 ~ 320. 32 fast / 64 normal / 128 high quality;"),
])
def test_out_of_range_is_caught_before_blender(no_blender, monkeypatch, lang, expect):
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    assert expect in server.water(resolution=2000)


@pytest.mark.parametrize("call,text", [
    (lambda: server.destroy(target="B", pieces=5000), "pieces 5000 is out of range. Allowed: 2 ~ 1500. 50-400"),
    (lambda: server.destroy(target="B", pieces=1), "Allowed: 2 ~ 1500."),
    (lambda: server.destroy(target="B", focus=1.5), "focus 1.5 is out of range. Allowed: 0.0 ~ 1.0."),
    (lambda: server.destroy(target="B", frames=5), "frames 5 is out of range. Allowed: at least 12."),
    (lambda: server.explode(target="B", pieces=9999), "pieces 9999"),          # explode 안의 destroy 단계
    (lambda: server.explode(at=[0, 0, 0], resolution=300), "Allowed: 16 ~ 256."),
    (lambda: server.fire(at=[0, 0, 0], resolution=1000), "Allowed: 16 ~ 256."),
    (lambda: server.smoke(at=[0, 0, 0], resolution=8), "resolution 8"),
    (lambda: server.particles(frames=3), "frames 3"),
    (lambda: server.set_render(samples=-4), "samples -4 is out of range. Allowed: at least 1."),
])
def test_each_tool_checks_ranges_before_blender(no_blender, monkeypatch, tmp_path, call, text):
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    out = call()
    out = out if isinstance(out, str) else out[0]
    assert out.startswith("Failed: ") and text in out


def test_boundaries_and_auto_values_reach_blender(monkeypatch):
    sent = []
    monkeypatch.setattr(bridge, "run_python", lambda code, timeout=None: sent.append(code) or 'FX_RESULT {"ok": true}')
    for recipe, names in server.RANGES.items():
        server.run_recipe(recipe, {n: lo for n, (lo, hi) in names.items()})
        server.run_recipe(recipe, {n: (hi if hi is not None else lo * 100) for n, (lo, hi) in names.items()})
    # 0 → None 으로 바뀌는 자동 값, 숫자가 아닌 값(레시피가 알아서 다룸)은 막지 않는다
    server.run_recipe("emit", {"resolution": None, "frames": 72})
    server.run_recipe("destroy", {"focus": True})
    assert len(sent) == 2 * len(server.RANGES) + 2
