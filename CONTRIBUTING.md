# 기여 안내 / Contributing

**English:** Every effect is one recipe file in `src/blender_fx_mcp/recipes/` plus one tool in `server.py`. Recipes run inside Blender with `PARAMS` prepended by the server and must end with `run_guarded(main)`, printing one `FX_RESULT` JSON line. Lint with `uvx ruff check .`. Server-side coverage (recipes excluded): `uv run pytest -q --cov` on the CI test list (59% on 2026-10-06). Test headlessly with `uv run pytest -q` (needs Blender on this machine) and, with Blender open, `uv run python scripts/e2e_socket.py`. Keep error messages human-readable; the AI shows them to a non-technical user.

## 구조

```
src/blender_fx_mcp/
  server.py        MCP 도구. 레시피를 고르고 값을 넘긴 뒤 결과와 이미지를 돌려준다
  bridge.py        블렌더 수신기와 소켓 통신 (명령마다 붙었다 뗀다)
  headless.py      블렌더를 창 없이 띄워 레시피를 돌리는 개발용 CLI
  doctor.py        준비물 점검 CLI
  i18n.py          메시지 언어 (BLENDER_FX_LANG)
  recipes/
    _common.py     공용 도우미 (재질·힘장·접착·하늘·렌더 품질·언어)
    demo_scene.py  연습용 건물
    destroy.py     파괴
    explode.py     폭발
    splash.py      물
    render.py      프레임 렌더
    render_video.py mp4 렌더
    save_blend.py  장면 저장
    list_objects.py / reset.py
```

## 새 효과 추가하는 법

1. `recipes/새효과.py` 를 만든다. 맨 위에 `PARAMS` 가 있다고 가정하고, `def main(): ... return dict(...)` 뒤에 `run_guarded(main)` 을 붙인다.
2. 실패는 `raise FxError(L("한국어 문장", "English sentence"))` 로 낸다. `L()` 은 `PARAMS["_lang"]` 을 보고 고른다.
   AI가 그 문장을 그대로 사용자에게 보여주므로, 무엇을 바꾸면 되는지까지 쓴다.
3. `server.py` 에 `@mcp.tool()` 함수를 하나 붙인다. 인자 설명(docstring)이 곧 AI가 보는 설명서다.
4. `headless.py` 의 `STEPS` 에 단계를 추가하고, `tests/test_recipes_headless.py` 에 테스트를 넣는다. 결과 이미지가 실제로 달라지는지(픽셀) 확인하는 assert 를 포함한다.
5. `uvx ruff check .` 와 `uv run pytest -q` 통과 후 PR.
   - 서버 쪽 커버리지: `uv run pytest -q --cov --cov-report=term tests/test_server*.py tests/test_registry.py tests/test_recipe_messages.py tests/test_repo_files.py tests/test_examples.py`.
     레시피는 블렌더 안에서 문자열로 실행돼 잴 수 없으므로 뺀다(`[tool.coverage.run] omit`). CI 는 이 표를 작업 요약에 남긴다.
     2026-10-06 기준 **59%**(bridge·i18n 100%, doctor 80%, headless 56%, server 49%). 줄면 PR 에 이유를 적는다.
   - 블렌더 앱이 없으면 `pip install bpy` 한 파이썬 3.11 로도 레시피 시험 대부분이 돈다:
     `uv pip install bpy==5.0.1` 뒤 `BLENDER_FX_BLENDER=.venv/bin/python uv run pytest -q`.
     Linux 에서 렌더하려면 `libegl1 libegl-mesa0 libgl1-mesa-dri` 가 있어야 한다.
     bpy 모듈은 Mantaflow(연기·불·물)가 깨져 있어 `@pytest.mark.app_only` 시험은 건너뛴다.
     이런 기능을 쓰는 새 시험에는 `@pytest.mark.app_only` 를 붙인다.
     bpy 4.2·4.5 LTS 휠도 같은 결함이 있다(2026-10 확인). 이 시험은 Actions 의 **app-tests** 작업(손으로 실행, 공식 블렌더 Linux 빌드)으로 돌린다.

## 규칙

- 블렌더 enum 값은 버전마다 바뀐다. 가능하면 `try/except TypeError` 로 감싸거나, 현재 값을 읽어 쓴다.
- `bpy.ops.*` 는 컨텍스트가 필요하다. `bpy.context.temp_override(...)` 로 감싼다.
- 노드는 이름이 아니라 `type` 으로 찾는다 (`n.type == "BSDF_PRINCIPLED"`). 이름은 UI 언어에 따라 바뀐다.
- 사용자 오브젝트를 지우지 않는다. 이 도구가 만든 것만 `fx_role` 태그로 표시하고 정리한다.
- 주석은 한국어, 코드 식별자는 영어. 사용자에게 보이는 문장은 `L()`(레시피) 또는 `t()`(서버, `i18n.py`) 로 한국어·영어 둘 다 쓴다.
- 사용자 오브젝트에 모디파이어를 붙일 때는 이름을 `FX_` 로 시작한다. `cleanup_fx` 가 그 이름만 떼어 낸다.
- 되돌리기 어려운 동작(파일 열기, 물리 굽기 적용)을 넣을 때는 `snapshot` 을 먼저 권하는 문구를 도구 설명에 넣는다.

## 이슈 올리기 전에

```bash
uv run blender-fx-doctor
```

결과와 블렌더 버전, OS, GPU, 재현 명령(또는 AI에게 한 말)을 함께 적어 주세요.
