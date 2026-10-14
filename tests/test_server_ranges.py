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
    """레시피가 자르는 범위는 레시피와 비교하고, 서버에서만 막는 범위(렌더 크기)는 따로 적어 둔다."""
    every = {(r, n) for r, d in server.RANGES.items() for n in d}
    assert every == set(RECIPE_SIDE) | server.SERVER_ONLY_RANGES
    assert not set(RECIPE_SIDE) & server.SERVER_ONLY_RANGES


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
    "render_preview": ["render"],
    "render_video": ["render_video"],
    "set_timing": ["set_timing"],
    "set_physics": ["set_physics"],
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
    (lambda: server.set_render(width=-1920), "width -1920 is out of range. Allowed: 16 ~ 7680. 1280×720"),
    (lambda: server.render_preview(width=-640), "width -640 is out of range. Allowed: 16 ~ 7680."),
    (lambda: server.render_preview(height=8), "height 8 is out of range."),
    (lambda: server.render_video(width=15360, height=8640), "width 15360 is out of range. Allowed: 16 ~ 7680."),
    (lambda: server.render_video(height=10000), "0 uses the set_render size"),
    (lambda: server.set_render(fps=-24), "fps -24 is out of range. Allowed: 1 ~ 240. 24 (film look), 30"),
    (lambda: server.render_video(fps=1000), "fps 1000 is out of range. Allowed: 1 ~ 240."),
    (lambda: server.render_video(frame_start=-10), "frame_start -10 is out of range. Allowed: 1 ~ 1048574. Frame numbers"),
    (lambda: server.render_video(frame_end=-1), "frame_end -1 is out of range."),
    (lambda: server.set_timing(fps=-30), "fps -30 is out of range."),
    (lambda: server.set_timing(frame_start=-5), "frame_start -5 is out of range."),
    (lambda: server.set_timing(frame_end=2_000_000), "frame_end 2000000 is out of range."),
    (lambda: server.set_timing(slow_from=-3, slow_to=40), "slow_from -3 is out of range."),
    (lambda: server.set_physics(fps=500), "fps 500 is out of range. Allowed: 1 ~ 240."),
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
        low = {n: lo for n, (lo, hi) in names.items()}
        high = {n: (hi if hi is not None else lo * 100) for n, (lo, hi) in names.items()}
        for first, second, equal_ok in server.ORDERS.get(recipe, []):
            if not equal_ok:  # 끝이 시작보다 커야 하는 쌍(slow_from < slow_to)은 경계에서 한 칸 띄운다
                low[second] += 1
                high[first] -= 1
        server.run_recipe(recipe, low)
        server.run_recipe(recipe, high)
    # 0 → None 으로 바뀌는 자동 값, 숫자가 아닌 값(레시피가 알아서 다룸)은 막지 않는다
    server.run_recipe("emit", {"resolution": None, "frames": 72})
    server.run_recipe("destroy", {"focus": True})
    assert len(sent) == 2 * len(server.RANGES) + 2


@pytest.mark.parametrize("bad", [dict(resolution=500), dict(frames=3), dict(material="titanium"), dict(pieces=5000)])
def test_explode_checks_every_argument_before_fracturing(monkeypatch, tmp_path, bad):
    """폭발은 조각내기(destroy) → 굽기(explode) 두 단계다. 굽기 인자가 틀렸으면 조각내기 전에 멈춰야 장면이 반쯤 바뀌지 않는다."""
    from blender_fx_mcp import bridge, server
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    monkeypatch.setattr(bridge, "run_python", lambda code, timeout=None: pytest.fail("블렌더로 보내면 안 됨"))
    out = server.explode(target="Building", **bad)
    out = out if isinstance(out, str) else out[0]
    assert out.startswith("Failed: ") and next(iter(bad)) in out, out


@pytest.mark.parametrize("call", [
    "destroy(target='Building', time_scale=float('inf'))",
    "destroy(target='Building', impact_power=float('nan'))",
    "water(mode='drop', at=[0.0, float('nan'), 1.0])",
    "wind(strength=float('-inf'))",
])
def test_nan_and_inf_are_refused_before_blender(monkeypatch, tmp_path, call):
    """nan·inf 는 블렌더로 보내는 코드에서 NameError('inf' 정의 안 됨)가 되어 원인 모를 오류가 났다. 서버가 미리 막는다."""
    from blender_fx_mcp import bridge, server
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    monkeypatch.setattr(bridge, "run_python", lambda code, timeout=None: pytest.fail("블렌더로 보내면 안 됨"))
    out = eval(call, vars(server))
    out = out if isinstance(out, str) else out[0]
    assert out.startswith("Failed: ") and "must be a finite number" in out, out


@pytest.mark.parametrize("lang,expect", [
    ("ko", "fps 값 -24 은(는) 범위 밖입니다. 가능한 범위: 1 ~ 240. 24(영화 느낌)·30(보통 영상)·60(부드러운 움직임) 권장. 0 이면"),
    ("en", "fps -24 is out of range. Allowed: 1 ~ 240. 24 (film look), 30 (regular video) or 60 (smooth motion) recommended; 0 keeps"),
])
def test_fps_error_says_what_to_use_in_both_languages(no_blender, monkeypatch, lang, expect):
    """fps 는 레시피가 자르지 않아 음수가 블렌더까지 갔다. 권장 값(24·30·60)과 0 의 뜻을 한/영으로 알려 준다."""
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    assert expect in server.set_render(fps=-24)


def test_valid_fps_and_frames_reach_blender(monkeypatch, tmp_path):
    """흔한 값(24·30·60, 프레임 1~250)과 0(그대로)은 막지 않는다."""
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    sent = []
    monkeypatch.setattr(bridge, "run_python", lambda code, timeout=None: sent.append(code) or 'FX_RESULT {"ok": false, "error": "x"}')
    for fps in (0, 24, 30, 60, 240):
        server.set_render(fps=fps)
        server.set_physics(fps=fps)
    server.set_timing(frame_start=1, frame_end=250, fps=30, slow_from=40, slow_to=60)
    server.render_video(frame_start=1, frame_end=48, fps=60)
    assert len(sent) == 12


@pytest.mark.parametrize("call,expect", [
    (lambda: server.set_timing(frame_start=100, frame_end=50),
     "frame_end(50) must be at least frame_start(100). The scene was not changed. Swap the two values (frame_start=50, frame_end=100)"),
    (lambda: server.set_timing(slow_from=40, slow_to=40), "slow_to(40) must be greater than slow_from(40)."),
    (lambda: server.set_timing(fps=30, slow_from=60, slow_to=20), "Swap the two values (slow_from=20, slow_to=60)"),
    (lambda: server.render_video(frame_start=48, frame_end=1), "frame_end(1) must be at least frame_start(48)."),
])
def test_reversed_pairs_stop_before_blender(no_blender, monkeypatch, call, expect):
    """레시피는 frame_start·fps 를 먼저 넣은 뒤 순서 오류를 내 장면이 반쯤 바뀐 채 남았다. 서버가 보내기 전에 막는다."""
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    assert expect in call()


def test_reversed_pair_message_in_korean(no_blender, monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "ko")
    text = server.set_timing(frame_start=100, frame_end=50)
    assert "frame_end(50) 는 frame_start(100) 보다 같거나 커야 합니다. 장면은 바꾸지 않았습니다." in text
    assert "frame_start=50, frame_end=100 처럼 두 값을 바꿔 다시 시키세요." in text


def test_ordered_or_one_sided_pairs_reach_blender(monkeypatch, tmp_path):
    """같은 프레임(1프레임 길이)·한쪽만 준 값은 막지 않는다(한쪽만이면 블렌더가 다른 쪽을 따라 옮긴다)."""
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    sent = []
    monkeypatch.setattr(bridge, "run_python", lambda code, timeout=None: sent.append(code) or 'FX_RESULT {"ok": false, "error": "x"}')
    server.set_timing(frame_start=10, frame_end=10)
    server.set_timing(frame_start=500)
    server.set_timing(slow_to=5)
    server.render_video(frame_start=12, frame_end=12)
    assert len(sent) == 4


def test_every_order_pair_names_real_arguments():
    for recipe, pairs in server.ORDERS.items():
        tool = getattr(server, recipe)
        names = set(inspect.signature(tool).parameters)
        for first, second, _ in pairs:
            assert {first, second} <= names, (recipe, first, second)


@pytest.mark.parametrize("call", [
    lambda: server.cloth_flag(at=[1.0, 2.0]),
    lambda: server.fire(at=[0.0, 0.0, 0.0, 1.0]),
    lambda: server.explode(at=[1.0]),
    lambda: server.water(domain_at=[0.0, 0.0]),
])
def test_points_need_three_numbers_before_blender(monkeypatch, tmp_path, call):
    """[x, y, z] 가 아닌 위치는 블렌더에 보내기 전에 막는다(레시피가 옛 깃발을 지운 뒤 IndexError 로 멈추던 것)."""
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    monkeypatch.setattr(bridge, "run_python", lambda code, timeout=None: pytest.fail("블렌더로 보내면 안 됨"))
    out = call()
    out = out if isinstance(out, str) else out[0]
    assert out.startswith("Failed: Give ") and "three numbers [x, y, z]" in out and "The scene was not changed." in out, out


def test_points_korean(monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "ko")
    with pytest.raises(bridge.BlenderError, match=r"at 은\(는\) \[x, y, z\] 숫자 세 개로 주세요\(지금 \[1, 2\]\)"):
        server.check_points({"at": [1, 2]})
    server.check_points({"at": [1, 2, 3], "domain_at": None})  # 맞으면 조용히
