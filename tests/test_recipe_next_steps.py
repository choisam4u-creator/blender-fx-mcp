# 레시피 오류가 "다음 할 일"을 말하는지. 블렌더 없이 돈다(레시피 함수만 떼어 bpy 없이 실행).
# 경로 오타는 가장 흔한 실패라, 파일·스냅샷이 없으면 같은 폴더의 고를 만한 이름을 알려 줘야 한다.
import ast
import difflib
import os

import pytest

from blender_fx_mcp import server
from test_recipe_messages import _calls, _text

RECIPES = server.RECIPES

# 다음 할 일 표지: 시키는 말(…세요) 이거나, 고를 수 있는 값을 늘어놓는 문장
MARKERS = ("세요", "중 하나", "지금 있는", "파일 안 부품", "만 됩니다")

# 다음 할 일을 말하지 않아도 되는 곳과 이유. 새 오류가 표지 없이 생기면 여기에 이유와 함께 더하거나 문장을 고친다
EXEMPT = {
    "_common.py:리지드바디(물리)를 붙이지 못했습니다": "블렌더 내부 실패. 원인 예외 문장을 그대로 붙여 신고에 쓰게 한다",
    "_common.py:힘장(": "블렌더 내부 실패(force field 추가 연산자). 사용자가 고칠 입력이 없다",
    "explode.py:힘장(force field)을 만들지 못했습니다": "위와 같음",
}


def _korean(call):
    return _text(call.args[0].args[0])


def _uses_hint(call):
    """`{hint}`(missing_file_hint 가 만든 다음 할 일 문장)을 끼워 넣는 오류인지."""
    node = call.args[0].args[0]
    return any(isinstance(v, ast.FormattedValue) and isinstance(v.value, ast.Name) and v.value.id == "hint"
               for v in getattr(node, "values", []))


def test_hint_variable_comes_from_missing_file_hint():
    for path in RECIPES.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        for line in src.splitlines():
            if line.strip().startswith("hint = "):
                assert "missing_file_hint(" in line, f"{path.name}: {line.strip()}"


def test_every_recipe_error_says_what_to_do_next():
    missing, used = [], set()
    for where, call in _calls("FxError"):
        ko = _korean(call)
        key = next((k for k in EXEMPT if where.split(":")[0] == k.split(":")[0] and ko.startswith(k.split(":", 1)[1])), None)
        if key:
            used.add(key)
            continue
        if not _uses_hint(call) and not any(m in ko for m in MARKERS):
            missing.append(f"{where} {ko[:60]!r}")
    assert not missing, "다음 할 일(…세요 또는 고를 값)이 없는 오류 문장:\n" + "\n".join(missing)
    assert used == set(EXEMPT), f"이제 없는 예외 항목은 지운다: {set(EXEMPT) - used}"


def _load(recipe, *names, **extra):
    """레시피 파일에서 함수·상수만 떼어 bpy 없이 실행할 이름 공간을 만든다."""
    ns = {"os": os, "difflib": difflib, "PARAMS": {}, **extra}
    common = ast.parse((RECIPES / "_common.py").read_text(encoding="utf-8"))
    keep = [n for n in common.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in ("L", "FxError", "missing_file_hint")]
    exec(compile(ast.Module(body=keep, type_ignores=[]), "_common.py", "exec"), ns)
    if recipe:
        tree = ast.parse((RECIPES / recipe).read_text(encoding="utf-8"))
        body = [n for n in tree.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Call))]  # run_guarded(main) 빼고
        exec(compile(ast.Module(body=body, type_ignores=[]), recipe, "exec"), ns)
    return ns


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_missing_model_suggests_similar_file(tmp_path, lang):
    (tmp_path / "Robot_v2.glb").write_bytes(b"x")
    (tmp_path / "tree.fbx").write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("x")
    ns = _load("import_model.py")
    ns["PARAMS"].update(path=str(tmp_path / "robot_v3.glb"), _lang=lang)
    with pytest.raises(ns["FxError"]) as e:
        ns["main"]()
    msg = str(e.value)
    assert ("파일이 없습니다: " if lang == "ko" else "File not found: ") in msg
    assert "Robot_v2.glb" in msg and "notes.txt" not in msg, msg
    assert ("다시 시키세요" if lang == "ko" else "ask again") in msg


def test_missing_model_lists_folder_when_nothing_is_close(tmp_path):
    for n in ("a.obj", "b.stl", "c.png"):
        (tmp_path / n).write_bytes(b"x")
    ns = _load("import_model.py")
    ns["PARAMS"].update(path=str(tmp_path / "completely_different_name.glb"), _lang="en")
    with pytest.raises(ns["FxError"]) as e:
        ns["main"]()
    msg = str(e.value)
    assert "a.obj, b.stl" in msg and "c.png" not in msg, msg


def test_missing_model_folder_or_no_models(tmp_path):
    ns = _load(None)
    ns["PARAMS"]["_lang"] = "en"
    fmt = (".glb", ".fbx")
    assert "The folder does not exist either" in ns["missing_file_hint"](str(tmp_path / "nope" / "a.glb"), fmt)
    assert "has no glb/fbx file" in ns["missing_file_hint"](str(tmp_path / "a.glb"), fmt)
    for i in range(8):
        (tmp_path / f"zz{i}.glb").write_bytes(b"x")
    assert "(+3)" in ns["missing_file_hint"](str(tmp_path / "a.glb"), fmt)  # 다섯 개까지만 보이고 나머지는 개수


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_restore_missing_lists_existing_snapshots(tmp_path, lang):
    for n in ("before_fire", "before_restore", "v1"):
        (tmp_path / f"{n}.blend").write_bytes(b"x")
    ns = _load("restore.py")
    ns["PARAMS"].update(path=str(tmp_path / "before_fir"), _lang=lang)
    with pytest.raises(ns["FxError"]) as e:
        ns["main"]()
    msg = str(e.value)
    assert "before_fire" in msg and "list_snapshots" in msg and ".blend," not in msg, msg


def test_restore_without_any_snapshot_says_save_first(tmp_path):
    ns = _load("restore.py")
    ns["PARAMS"].update(path=str(tmp_path / "x"), _lang="en")
    with pytest.raises(ns["FxError"]) as e:
        ns["main"]()
    assert "no snapshots yet" in str(e.value) and "snapshot first" in str(e.value)


def test_suggested_tool_names_exist():
    """오류 문장이 권하는 도구 이름이 실제 도구여야 AI 가 그대로 부를 수 있다."""
    import asyncio
    tools = {t.name for t in asyncio.run(server.mcp.list_tools())}
    for name in ("list_objects", "list_snapshots", "inspect_mesh", "make_demo_building", "import_model", "render_preview", "snapshot", "restore"):
        assert name in tools, name
        assert any(name in (RECIPES / f).read_text(encoding="utf-8") for f in os.listdir(RECIPES) if f.endswith(".py")), name
