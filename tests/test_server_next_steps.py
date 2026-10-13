# 서버 쪽 오류(bridge·server 의 BlenderError)가 한/영 모두 "다음 할 일"을 말하는지. 블렌더 없이 돈다.
# 레시피 오류(FxError)는 tests/test_recipe_next_steps.py 가 본다. 연결·경로 오류가 가장 흔해 서버 쪽도 같은 규칙을 지킨다.
import ast
import json
import re
from pathlib import Path

import pytest

from blender_fx_mcp import bridge, server
from test_recipe_messages import _text
from test_recipe_next_steps import EN_MARKERS, MARKERS, _tools_and_args
import test_server_params

FILES = [bridge.__file__, server.__file__]
receiver = test_server_params.receiver  # 가짜 수신기 픽스처

# 서버 문장에만 있는 표지: 해결법 링크(그 절이 할 일을 말한다)·신고 안내
SERVER_MARKERS = (*MARKERS, "해결법:", "신고해 주세요")
SERVER_EN_MARKERS = (*EN_MARKERS, "help:", "fix ", "try ", "report it", "save ")


def _t_pairs():
    """`BlenderError(t(ko, en))` 와 BlenderError 로 쓰이는 문장 함수(_missing_snapshot)의 `t(ko, en)` 들."""
    for path in FILES:
        tree = ast.parse(Path(path).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_missing_snapshot":
                for ret in ast.walk(node):
                    if isinstance(ret, ast.Return) and isinstance(ret.value, ast.Call):
                        yield f"{path.rsplit('/', 1)[-1]}:{ret.lineno}", ret.value
            if not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "BlenderError" and node.args):
                continue
            arg = node.args[0]
            if isinstance(arg, ast.BinOp):  # t(...) + 꼬리(parse_result 의 출력 끝부분)
                arg = arg.left
            if isinstance(arg, ast.Call) and getattr(arg.func, "id", None) == "t":
                yield f"{path.rsplit('/', 1)[-1]}:{node.lineno}", arg


PAIRS = list(_t_pairs())


def test_server_error_sentences_found():
    """bridge·server 에 BlenderError(t(...)) 가 이만큼은 있어야 시험이 제대로 훑은 것이다."""
    assert len(PAIRS) >= 18


@pytest.mark.parametrize("where,call", PAIRS, ids=[w for w, _ in PAIRS])
def test_server_error_says_what_to_do_next(where, call):
    ko, en = _text(call.args[0]), _text(call.args[1])
    assert any(m in ko for m in SERVER_MARKERS), f"{where} 한국어 문장에 다음 할 일이 없음: {ko[:80]!r}"
    assert any(m in en.lower() for m in SERVER_EN_MARKERS), f"{where} 영어 문장에 다음 할 일이 없음: {en[:80]!r}"


def test_server_errors_name_real_tools_and_arguments():
    """오류가 말하는 snake_case 이름은 실제 도구·인자이거나 환경변수·파일 이름이어야 AI 가 그대로 부를 수 있다."""
    tools, args = _tools_and_args()
    known = tools | args | {"before_restore", "blender_mcp", "my_model"}
    bad = []
    for where, call in PAIRS:
        for word in re.findall(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b", _text(call.args[0]) + " " + _text(call.args[1])):
            if word not in known:
                bad.append(f"{where} {word}")
    assert not bad, f"없는 도구·인자 이름: {bad}"


@pytest.mark.parametrize("recipe,name,lo,hi", [(r, n, lo, hi) for r, d in server.RANGES.items() for n, (lo, hi) in d.items()])
@pytest.mark.parametrize("lang", ["ko", "en"])
def test_every_range_error_has_a_recommendation(monkeypatch, recipe, name, lo, hi, lang):
    """범위 밖 숫자는 '가능한 범위' 만이 아니라 권장 값(다음에 줄 값)도 말한다."""
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    with pytest.raises(bridge.BlenderError) as e:
        server.check_ranges(recipe, {name: lo - 1})
    msg = str(e.value)
    assert server._range_hint(name), f"{name} 에 권장 값 안내가 없음"
    assert msg.endswith(server._range_hint(name)), msg


@pytest.mark.parametrize("lang,marker", [("ko", "가능한 값"), ("en", "Choose one of")])
def test_choice_error_lists_values_and_closest(monkeypatch, lang, marker):
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    recipe, names = next(iter(server.CHOICES.items()))
    name, allowed = next(iter(names.items()))
    with pytest.raises(bridge.BlenderError) as e:
        server.check_choices(recipe, {name: allowed[0] + "x"})
    assert marker in str(e.value) and allowed[0] in str(e.value)


@pytest.mark.parametrize("lang,expect", [
    ("ko", "블렌더 오류: boom. 버그일 수 있습니다. uvx --from blender-fx-mcp blender-fx-doctor --issue 결과를 붙여 신고해 주세요."),
    ("en", "Blender error: boom. This may be a bug; please report it with the output of uvx --from blender-fx-mcp blender-fx-doctor --issue."),
])
def test_receiver_error_says_how_to_report(receiver, monkeypatch, lang, expect):
    """수신기가 코드를 실행하다 실패(레시피 오류가 아님)하면 버그일 가능성이 커 신고 방법을 알려 준다."""
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    receiver(json.dumps({"status": "error", "message": "boom"}).encode())
    with pytest.raises(bridge.BlenderError) as e:
        bridge.send_command("execute_code", timeout=5)
    assert str(e.value).startswith(expect) and "#empty-response-blender-error" in str(e.value)


@pytest.mark.parametrize("lang,expect", [("ko", "신고해 주세요. 출력 끝부분: boom"), ("en", "and the text below. End of output: boom")])
def test_missing_result_line_says_how_to_report(monkeypatch, lang, expect):
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    with pytest.raises(bridge.BlenderError) as e:
        server.parse_result("boom")
    assert "blender-fx-doctor --issue" in str(e.value) and str(e.value).endswith(expect)


def test_range_hint_is_empty_for_unknown_names():
    """RANGES 에 없는 이름은 안내를 붙이지 않는다(엉뚱한 권장 값을 말하지 않게)."""
    assert server._range_hint("unknown_argument") == ""
