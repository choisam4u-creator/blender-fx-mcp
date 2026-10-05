# 서버 쪽 사용자 메시지·도구 설명 정적 검사. 블렌더 없이 돈다.
# 서버가 만드는 문장은 모두 `t(한국어, 영어)` 쌍이어야 BLENDER_FX_LANG=en 사용자에게 영어가 나간다.
# 해외 클라이언트의 AI는 도구 설명 첫 줄로 도구를 고르므로 첫 줄은 영어여야 한다.
import ast
import re
from pathlib import Path

import pytest

from blender_fx_mcp import server

HANGUL = re.compile(r"[가-힣ㄱ-ㆎ]")
PKG = Path(server.__file__).parent
# 사용자에게 문장을 돌려주는 모듈. headless.py 는 개발용 도구라 뺀다.
FILES = [PKG / "server.py", PKG / "bridge.py", PKG / "doctor.py"]
# 한글 문자열이 t() 밖에 있어도 되는 곳: (파일, 그 줄에 들어 있는 글자)
ALLOWED_LOOSE = {
    ("server.py", "INSTRUCTIONS_KO"),  # t(INSTRUCTIONS_KO, INSTRUCTIONS_EN) 로 고른다
    ("doctor.py", "critical = "),      # 두 언어의 점검 이름을 모두 담은 비교용 집합
}


def _tree(path):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _texts(node):
    """문자열/f-문자열 노드의 고정 부분 목록. `a if c else b` 는 두 갈래 모두, 이름(상수)은 모듈에서 값을 찾는다.
    문자열로 볼 수 없으면 None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.JoinedStr):
        return ["".join(v.value for v in node.values if isinstance(v, ast.Constant))]
    if isinstance(node, ast.IfExp):
        a, b = _texts(node.body), _texts(node.orelse)
        return a + b if a is not None and b is not None else None
    if isinstance(node, ast.Name) and isinstance(getattr(server, node.id, None), str):
        return [getattr(server, node.id)]
    return None


def _t_calls():
    for path in FILES:
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "t":
                yield f"{path.name}:{node.lineno}", node


def _docstring_nodes(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                yield first.value


def _tools():
    for node in _tree(PKG / "server.py").body:
        if isinstance(node, ast.FunctionDef) and any(
            isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "tool" for d in node.decorator_list
        ):
            yield node


def test_t_calls_found():
    assert len(list(_t_calls())) >= 60


@pytest.mark.parametrize("where,call", list(_t_calls()), ids=lambda v: v if isinstance(v, str) else "")
def test_t_pair_is_korean_then_english(where, call):
    assert len(call.args) == 2 and not call.keywords, f"{where}: t() 는 (한국어, 영어) 두 인자"
    kos, ens = (_texts(a) for a in call.args)
    assert kos is not None and ens is not None, f"{where}: t() 인자는 문자열이어야 함"
    for ko in kos:
        assert ko.strip() and HANGUL.search(ko), f"{where}: 첫 인자(한국어)에 한글이 없음: {ko!r}"
    for en in ens:
        assert en.strip() and not HANGUL.search(en), f"{where}: 둘째 인자(영어)가 비었거나 한글이 섞임: {en!r}"


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_no_korean_outside_t(path):
    """t() 첫 인자·독스트링이 아닌 곳의 한글 문자열은 영어 사용자에게 그대로 새어 나간다."""
    tree = _tree(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    ok = {id(n) for n in _docstring_nodes(tree)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "t" and node.args:
            ok.update(id(n) for n in ast.walk(node.args[0]))
    leaks = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and HANGUL.search(node.value) \
                and id(node) not in ok:
            line = lines[node.lineno - 1]
            if not any(path.name == f and mark in line for f, mark in ALLOWED_LOOSE):
                leaks.append(f"{path.name}:{node.lineno} {node.value[:40]!r}")
    assert not leaks, f"t() 밖의 한국어 문장: {leaks}"


def test_every_tool_has_english_first_line():
    tools = list(_tools())
    assert len(tools) >= 30
    bad = []
    for fn in tools:
        doc = ast.get_docstring(fn)
        if not doc:
            bad.append(f"{fn.name}: 설명 없음")
            continue
        first = doc.strip().splitlines()[0]
        if HANGUL.search(first) or len(first) < 10:
            bad.append(f"{fn.name}: {first!r}")
    assert not bad, f"도구 설명 첫 줄이 영어가 아님: {bad}"


def test_instructions_follow_language():
    assert not HANGUL.search(server.INSTRUCTIONS_EN)
    assert HANGUL.search(server.INSTRUCTIONS_KO)
    # 두 판 모두 같은 도구를 안내한다
    names = {n.name for n in _tools()}
    ko = set(re.findall(r"\b([a-z_]+)\b", server.INSTRUCTIONS_KO)) & names
    en = set(re.findall(r"\b([a-z_]+)\b", server.INSTRUCTIONS_EN)) & names
    assert ko == en and len(en) >= 15, (ko ^ en)
