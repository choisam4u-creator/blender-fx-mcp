# 레시피 오류 메시지 정적 검사. 블렌더 없이 돈다.
# 모든 `raise FxError(...)` 는 `L(한국어, 영어)` 한 쌍을 넘겨야 BLENDER_FX_LANG=en 사용자에게 영어가 나간다.
import ast
import re

import pytest

from blender_fx_mcp import server

HANGUL = re.compile(r"[가-힣ㄱ-ㆎ]")
RECIPE_FILES = sorted(server.RECIPES.glob("*.py"))


def _text(node):
    """문자열/f-문자열 노드의 고정 부분만 이어 붙인다. 문자열이 아니면 None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value for v in node.values if isinstance(v, ast.Constant))
    return None


def _is_call(node, name):
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name


def _calls(name):
    for path in RECIPE_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if _is_call(node, name):
                yield f"{path.name}:{node.lineno}", node


def test_recipe_files_found():
    assert len(RECIPE_FILES) > 20


def test_every_fxerror_uses_L_pair():
    bad = []
    count = 0
    for where, call in _calls("FxError"):
        count += 1
        ok = (len(call.args) == 1 and not call.keywords
              and _is_call(call.args[0], "L") and len(call.args[0].args) == 2)
        if not ok:
            bad.append(where)
    assert count >= 40, f"FxError 호출이 너무 적게 잡힘({count}) — 검사 방식이 깨졌는지 확인"
    assert not bad, f"L(한국어, 영어) 없이 FxError 를 던지는 곳: {bad}"


@pytest.mark.parametrize("where,call", list(_calls("L")), ids=lambda v: v if isinstance(v, str) else "")
def test_L_pair_is_korean_then_english(where, call):
    assert len(call.args) == 2 and not call.keywords, f"{where}: L() 은 (한국어, 영어) 두 인자"
    ko, en = (_text(a) for a in call.args)
    assert ko is not None and en is not None, f"{where}: L() 인자는 문자열이어야 함"
    assert ko.strip() and en.strip(), f"{where}: 빈 메시지"
    assert HANGUL.search(ko), f"{where}: 첫 인자(한국어)에 한글이 없음: {ko!r}"
    assert not HANGUL.search(en), f"{where}: 둘째 인자(영어)에 한글이 섞임: {en!r}"
