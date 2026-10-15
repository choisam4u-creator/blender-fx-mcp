# MCP 프롬프트(first_demo·undo_last) 시험. 클라이언트의 `/` 메뉴에 뜨고, 문장이 실제 도구 이름만 쓰는지 본다. 블렌더 없이 돈다.
import asyncio
import re
from pathlib import Path

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
    assert set(ps) == {"first_demo", "my_model", "undo_last"}
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
@pytest.mark.parametrize("name", ["first_demo", "my_model", "undo_last"])
def test_prompt_follows_language_and_names_real_tools(monkeypatch, lang, name):
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    text = _text(name, {"path": "~/Desktop/tower.glb"} if name == "my_model" else None)
    assert bool(re.search(r"[가-힣]", text)) is (lang == "ko"), text
    # 문장 속 snake_case 단어와 단계 머리 단어 중 도구처럼 보이는 것은 모두 실제 도구여야 한다
    words = set(re.findall(r"\b[a-z]+(?:_[a-z]+)+\b", text)) - {"before_demo", "before_restore", "before_my_model"}
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
        assert "/first_demo" in part and "/undo_last" in part and "/my_model" in part


def test_my_model_steps_and_arguments(monkeypatch):
    import inspect

    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    args = {a.name: a for a in _prompts()["my_model"].arguments}
    assert args["path"].required and not args["size"].required and not args["impact"].required
    assert args["impact"].description.split(" / ") == list(server.CHOICES["destroy"]["impact"])
    text = _text("my_model", {"path": "C:\\모델\\tower 1.glb", "size": "12", "impact": "top"})
    order = ["ping_blender", "snapshot", "import_model", "inspect_mesh", "destroy", "render_preview"]
    pos = [text.index(w) for w in order]
    assert pos == sorted(pos)
    # 경로는 repr 로 감싸 공백·역슬래시·한글이 그대로 전달된다
    assert "path='C:\\\\모델\\\\tower 1.glb', size=12" in text and "impact=top" in text
    assert {"path", "size"} <= set(inspect.signature(server.import_model).parameters)
    assert "ask me whether to continue" in text and "restore before_my_model" in text


@pytest.mark.parametrize("lang", ["ko", "en"])
@pytest.mark.parametrize("bad, shown", [({"impact": "lft"}, "'left'"), ({"size": "12m"}, "12m"), ({"size": "-3"}, "-3")])
def test_my_model_wrong_argument(monkeypatch, lang, bad, shown):
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    text = _text("my_model", {"path": "a.glb", **bad})
    assert text.startswith("/my_model") or text.startswith("Wrong /my_model")
    assert shown in text and "import_model" not in text


# 문서가 사용자·AI 에게 부르라고 적은 이름. 도구·인자가 아닌 것(결과 칸·스냅샷 이름·시험 이름·프롬프트)은 이유와 함께 여기에
DOC_NAMES_OK = {
    "before_restore": "restore 가 자동으로 남기는 스냅샷 이름",
    "volume_kept": "destroy 결과 칸", "moved_ratio": "결과 칸", "cache_files": "결과 칸",
    "first_demo": "프롬프트(/ 메뉴)",
    "first_render_before": "examples/first_render.py 가 남기는 스냅샷 이름",
    "test_explode_building": "recipes.md 가 가리키는 bpy 시험", "test_water_direction_and_viscosity": "위와 같음",
}


DOCS_WITH_NAMES = ["README.md", "docs/troubleshooting.md", "docs/recipes.md", "docs/demo-script.md",
                   "examples/README.md", "docs/architecture.md", "CONTRIBUTING.md"]
# 기여자 문서는 내부 함수 이름(run_guarded·cleanup_fx 등)도 적는다. 그 이름은 코드에 실제로 있어야 한다(지우거나 바꾸면 걸림)
DEV_DOCS = {"docs/architecture.md", "CONTRIBUTING.md"}


def _code_names() -> set[str]:
    root = Path(__file__).parent.parent
    files = [*root.glob("src/**/*.py"), *root.glob("tests/*.py"), *root.glob("scripts/*.py"), *root.glob("examples/*.py")]
    files = [f for f in files if f.name != Path(__file__).name]  # 이 파일은 일부러 없는 이름(glue_neighbors)을 적는다
    return {n for f in files for n in re.findall(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b", f.read_text(encoding="utf-8"))}


@pytest.mark.parametrize("doc", DOCS_WITH_NAMES)
def test_docs_name_only_real_tools_and_arguments(doc):
    """문서의 `코드` 안 snake_case 이름과 `이름(…)` 꼴 호출은 실제 도구·인자여야 한다.
    (README 가 destroy 에 없는 인자 glue_neighbors·glue_max 로 줄이라고 하던 것을 이 시험이 찾음)"""
    from test_recipe_next_steps import _tools_and_args
    tools, args = _tools_and_args()
    known = tools | args | set(DOC_NAMES_OK) | (_code_names() if doc in DEV_DOCS else set())
    text = (Path(__file__).parent.parent / doc).read_text(encoding="utf-8")
    bad = []
    for code in re.findall(r"`([^`\n]+)`", text):
        names = re.findall(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\s*\(", code)
        # 도구 호출 안의 인자 이름(`destroy(glue_max=3)` 의 glue_max)도. 환경변수(대문자)·비교(==)는 빼고
        names += [n for call in re.findall(r"\b[a-z][a-z0-9_]*\(([^)]*)\)", code)
                  for n in re.findall(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\s*=(?!=)", call)]
        if re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+", code.strip()):
            names.append(code.strip())
        bad += [n for n in names if n not in known]
    assert not bad, f"{doc} 에 없는 도구·인자 이름: {sorted(set(bad))}"


def test_doc_name_exceptions_are_still_used():
    docs = "".join((Path(__file__).parent.parent / d).read_text(encoding="utf-8") for d in DOCS_WITH_NAMES)
    assert all(f"`{n}`" in docs for n in DOC_NAMES_OK), "이제 문서에 없는 예외는 지운다"


def test_dev_doc_names_catch_a_removed_function():
    """기여자 문서 허용 목록이 아무 이름이나 통과시키지 않는다(코드에 없는 이름은 걸림)."""
    names = _code_names()
    assert {"run_guarded", "cleanup_fx", "fx_role", "build_code", "fake_blender"} <= names
    assert "run_guarded_v2" not in names and "make_fireworks" not in names


def _tool_schemas() -> dict[str, set[str]]:
    import anyio
    from mcp import Client

    async def tools():
        async with Client(server.mcp) as client:
            return (await client.list_tools()).tools

    return {t.name: set(t.input_schema.get("properties", {})) for t in anyio.run(tools)}


EXAMPLE_SCRIPTS = sorted((Path(__file__).parent.parent / "examples").glob("*.py"))


@pytest.mark.parametrize("script", EXAMPLE_SCRIPTS, ids=lambda p: p.name)
def test_example_scripts_name_only_real_tools_and_arguments(script):
    """examples/*.py 의 docstring·print 문장에 나오는 이름과, 실제로 부르는 도구(`call_tool`·STEPS 의 (이름, 인자))가 서버에 있다.
    예제를 그대로 돌리는 사용자가 없는 도구·인자 이름으로 막히지 않게(문서 시험은 .md 만 훑음)."""
    import ast
    schemas = _tool_schemas()
    tools, args = set(schemas), set().union(*schemas.values())
    tree = ast.parse(script.read_text(encoding="utf-8"))
    bad = []
    # 1) 문장 속 snake_case 이름: 도구·인자·문서 예외이거나, 이 파일 안 코드(변수·함수) 이름이어야 한다
    code_names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | \
                 {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))} | \
                 {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    known = tools | args | set(DOC_NAMES_OK) | code_names
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            bad += [n for n in re.findall(r"(?<![\w./-])([a-z][a-z0-9]*(?:_[a-z0-9]+)+)(?![\w./-])", node.value)
                    if n not in known]
    # 2) 실제로 부르는 도구 이름과 인자 키
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "call_tool" and node.args \
                and isinstance(node.args[0], ast.Constant):
            keys = node.args[1].keys if len(node.args) > 1 and isinstance(node.args[1], ast.Dict) else []
            calls.append((node.args[0].value, keys))
        if isinstance(node, ast.Tuple) and len(node.elts) == 2 and isinstance(node.elts[0], ast.Constant) \
                and isinstance(node.elts[0].value, str) and isinstance(node.elts[1], ast.Dict):
            calls.append((node.elts[0].value, node.elts[1].keys))
    for name, keys in calls:
        if name not in schemas:
            bad.append(f"도구 {name}")
            continue
        bad += [f"{name}({k.value}=)" for k in keys if isinstance(k, ast.Constant) and k.value not in schemas[name]]
    assert not bad, f"{script.name} 에 없는 도구·인자 이름: {sorted(set(bad))}"
    if script.name == "first_render.py":
        assert {"ping_blender", "snapshot", "destroy", "render_preview"} <= {c[0] for c in calls} | set(
            re.findall(r'"([a-z_]+)"', script.read_text(encoding="utf-8"))), "STEPS 를 못 읽음(시험이 비어 통과하지 않게)"
