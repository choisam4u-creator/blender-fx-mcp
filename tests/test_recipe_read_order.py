# 레시피 정적 점검: main() 안에서 "읽기"(대상 찾기·상자·좌표 검사)가 "지우기"(정리·프레임 바꾸기·오브젝트 지우기)보다 앞에 오는지 ast 로 훑는다.
# explode·set_timing·particles(target) 에서 "정리 뒤에 읽어 실패하면 장면이 반쯤 바뀐 채 남는" 결함이 세 번 나왔다.
# bpy 시험(test_recipe_failure_keeps_scene.py 의 BAD_CALLS)은 한 줄씩 넣어야만 잡으므로, 블렌더 없이 모든 레시피를 한 번에 본다.
import ast
from pathlib import Path

import pytest

RECIPES = Path(__file__).resolve().parents[1] / "src" / "blender_fx_mcp" / "recipes"

# 실패할 수 있는 읽기: 없는 이름·잘못된 좌표면 오류를 낸다
READS = {"get_target", "fx_bbox", "point"}
# 장면을 바꾸는 호출: 이 뒤에 실패하면 장면이 반쯤 바뀐 채 남는다
CHANGES = {"set_frame_end", "remove_object"}

# (레시피, 줄의 호출 이름): 지우기 뒤에 읽어도 되는 곳과 그 근거
ALLOWED_LATE = {
    # fx_bbox(None) 은 실패하지 않고(메시가 없으면 기본 상자), 앞에서 지운 바람·난류는 메시가 아닌 빈 객체라 상자에 들지 않는다
    ("wind", "fx_bbox"),
}


def call_name(node):
    fn = node.func
    if isinstance(fn, ast.Name):
        return fn.id
    if isinstance(fn, ast.Attribute):
        return fn.attr
    return None


def is_change(name):
    return name.startswith("cleanup_") or name in CHANGES


def late_reads(source):
    """main() 의 첫 장면 바꾸기 뒤에 오는 읽기 [(줄, 이름)]. main 이 없거나 바꾸기가 없으면 []."""
    tree = ast.parse(source)
    main = next((f for f in tree.body if isinstance(f, ast.FunctionDef) and f.name == "main"), None)
    if main is None:
        return []
    calls = sorted((n.lineno, call_name(n)) for n in ast.walk(main) if isinstance(n, ast.Call) and call_name(n))
    changes = [line for line, name in calls if is_change(name)]
    if not changes:
        return []
    return [(line, name) for line, name in calls if name in READS and line > min(changes)]


def recipe_files():
    return sorted(p for p in RECIPES.glob("*.py") if not p.name.startswith("_"))


@pytest.mark.parametrize("path", recipe_files(), ids=lambda p: p.stem)
def test_recipe_reads_before_it_changes_the_scene(path):
    late = [(line, name) for line, name in late_reads(path.read_text(encoding="utf-8")) if (path.stem, name) not in ALLOWED_LATE]
    assert not late, (
        f"{path.name}: 장면을 바꾼 뒤에 읽음 {late} — 대상·좌표를 먼저 읽고 검사한 뒤 정리하세요"
        "(실패하면 장면이 반쯤 바뀐 채 남음). 정말 괜찮으면 ALLOWED_LATE 에 근거와 함께 추가."
    )


def test_allowed_late_entries_are_still_needed():
    # 고쳐서 필요 없어진 예외는 지운다(예외 목록이 실제 결함을 덮지 않게)
    for stem, name in ALLOWED_LATE:
        source = (RECIPES / f"{stem}.py").read_text(encoding="utf-8")
        assert any(n == name for _, n in late_reads(source)), f"ALLOWED_LATE 의 ({stem}, {name}) 는 이제 필요 없음 — 지우세요"


def test_checker_catches_a_read_after_cleanup():
    # 변이: particles(target) 결함 모양(정리 뒤 대상 찾기)을 잡는지, 고친 모양은 통과하는지
    bad = "def main():\n    cleanup_kind('snow')\n    set_frame_end(10)\n    lo, hi = fx_bbox(PARAMS.get('target'))\n"
    good = "def main():\n    lo, hi = fx_bbox(PARAMS.get('target'))\n    cleanup_kind('snow')\n    set_frame_end(10)\n"
    assert late_reads(bad) == [(4, "fx_bbox")]
    assert late_reads(good) == []
    assert late_reads("def main():\n    o = get_target('a')\n    remove_object(o)\n    point([1, 2], 'at')\n") == [(4, "point")]


def test_checker_sees_the_recipes_that_matter():
    # 훑기가 헛돌지 않게: 지우기와 읽기를 함께 하는 레시피가 실제로 있어야 한다
    both = []
    for path in recipe_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {call_name(n) for n in ast.walk(tree) if isinstance(n, ast.Call)} - {None}
        if names & READS and any(is_change(n) for n in names):
            both.append(path.stem)
    assert {"destroy", "explode", "emit", "particles", "water"} <= set(both)
