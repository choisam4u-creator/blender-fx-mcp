# 기여 안내 / Contributing

**English:** Every effect is one recipe file in `src/blender_fx_mcp/recipes/` plus one tool in `server.py`. Recipes run inside Blender with `PARAMS` prepended by the server and must end with `run_guarded(main)`, printing one `FX_RESULT` JSON line. Lint with `uvx ruff check .`. Server-side coverage (recipes excluded, same command as CI): `uv run pytest -q tests --ignore=tests/test_asset_robustness.py --ignore=tests/test_recipes_fx_extra.py --ignore=tests/test_recipes_headless.py --ignore=tests/test_recipes_v05.py --ignore=tests/test_recipes_v06.py --cov --cov-report=term` (99% on 2026-10-08; CI fails below the 95% floor, `--cov-fail-under=95`); only the Blender-only recipe test files are ignored, so new test files join CI automatically. Test headlessly with `uv run pytest -q` (needs Blender on this machine) and, with Blender open, `uv run python scripts/e2e_socket.py`. For a new tool, add a row to both README tool tables: `uv run python scripts/gen_tool_table.py --draft` prints draft rows from the docstrings, and running it without arguments lists rows or `a/b/c` value lists that disagree with the server. Keep error messages human-readable; the AI shows them to a non-technical user. Start with [docs/architecture.md](docs/architecture.md) for the call path and test paths, or pick a small task from [Good first contributions](#good-first-contributions).

## 구조

도구 호출이 지나가는 길과 시험 경로 그림은 [docs/architecture.md](docs/architecture.md).

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
    water.py       물
    render.py      프레임 렌더
    render_video.py mp4 렌더
    save_blend.py  장면 저장
    list_objects.py / reset.py
```

## 새 효과 추가하는 법

1. `recipes/새효과.py` 를 만든다. 맨 위에 `PARAMS` 가 있다고 가정하고, `def main(): ... return dict(...)` 뒤에 `run_guarded(main)` 을 붙인다.
2. 실패는 `raise FxError(L("한국어 문장", "English sentence"))` 로 낸다. `L()` 은 `PARAMS["_lang"]` 을 보고 고른다.
   AI가 그 문장을 그대로 사용자에게 보여주므로, 무엇을 바꾸면 되는지까지 쓴다.
3. `server.py` 에 `@mcp.tool(annotations=...)` 함수를 하나 붙인다(`READ_ONLY`·`SETTING`·`ADDITIVE`·`DESTRUCTIVE` 중 하나). 인자 설명(docstring)이 곧 AI가 보는 설명서다.
   `tests/test_server_tools.py` 의 `RESULTS`·`CALLS` 에 성공 결과와 호출 한 줄을 넣는다(빠지면 시험이 실패한다).
   README 한/영 도구 표에 한 줄씩 넣는다. `uv run python scripts/gen_tool_table.py --draft` 가 도구 설명으로 만든 초안 행을 주고, 인자 없이 돌리면 표와 서버(빠진 도구·`a/b/c` 값 목록)가 어긋난 곳을 알려 준다.
4. `headless.py` 의 `STEPS` 에 단계를 추가하고, `tests/test_recipes_headless.py` 에 테스트를 넣는다. 결과 이미지가 실제로 달라지는지(픽셀) 확인하는 assert 를 포함한다.
5. `uvx ruff check .` 와 `uv run pytest -q` 통과 후 PR.
   - 서버 쪽 커버리지(CI 와 같은 명령): `uv run pytest -q tests --ignore=tests/test_asset_robustness.py --ignore=tests/test_recipes_fx_extra.py --ignore=tests/test_recipes_headless.py --ignore=tests/test_recipes_v05.py --ignore=tests/test_recipes_v06.py --cov --cov-report=term`.
     블렌더가 있어야 하는 레시피 시험 파일만 `--ignore` 로 빼므로 새 시험 파일은 저절로 CI 에 들어간다. 레시피 시험 파일을 새로 만들면 이 목록과 `ci.yml` 에 함께 더한다.
     레시피는 블렌더 안에서 문자열로 실행돼 잴 수 없으므로 뺀다(`[tool.coverage.run] omit`). CI 는 이 표를 작업 요약에 남긴다.
     2026-10-08 기준 **99%**(i18n·bridge 100%, server·doctor·headless 99%. 같은 날 앞 회차에는 95%, 10-07 에는 94%, 10-06 에는 84%, 도구 성공 갈래 시험 전에는 59%). CI 는 **95% 아래면 실패**한다(`--cov-fail-under=95`). 줄면 PR 에 이유를 적는다.
   - 블렌더 앱이 없으면 `pip install bpy` 한 파이썬 3.11 로도 레시피 시험 대부분이 돈다:
     `uv pip install bpy==5.0.1` 뒤 `BLENDER_FX_BLENDER=.venv/bin/python uv run pytest -q`.
     Linux 에서 렌더하려면 `libegl1 libegl-mesa0 libgl1-mesa-dri` 가 있어야 한다.
     Linux 에서는 `scripts/bpy_tests.sh` 한 줄로 같은 일을 한다(따로 만든 `.venv-bpy` 에 bpy 를 깔아 개발용 `.venv` 를 건드리지 않음, libEGL 이 없으면 설치 명령을 알려 줌, 뒤에 붙인 인자는 pytest 로 넘김).
     bpy 모듈은 Mantaflow(연기·불·물)가 깨져 있어 `@pytest.mark.app_only` 시험은 건너뛴다.
     이런 기능을 쓰는 새 시험에는 `@pytest.mark.app_only` 를 붙인다.
     bpy 4.2·4.5 LTS 휠도 같은 결함이 있다(2026-10 확인). 이 시험은 Actions 의 **app-tests** 작업(손으로 실행, 공식 블렌더 Linux 빌드)으로 돌린다.

## 처음 기여하기 좋은 일

블렌더 코드를 몰라도 할 수 있는 작은 일입니다. 이슈에 `good first issue` 라벨이 붙은 것부터 고르면 됩니다.
모두 블렌더 없이 아래 시험 명령으로 확인할 수 있습니다(새 바닥 재질만 블렌더로 한 번 더).

| 할 일 | 고칠 파일 | 확인 명령 |
|---|---|---|
| 오류 문장의 영어·한국어 다듬기 | `src/blender_fx_mcp/recipes/_common.py` 같은 레시피의 `L()`, `src/blender_fx_mcp/server.py`·`src/blender_fx_mcp/bridge.py` 의 `t()`. 같은 문장이 `docs/troubleshooting.md` 에도 있으면 함께 | `uv run pytest -q tests/test_recipe_messages.py tests/test_server_messages.py tests/test_troubleshooting.py` |
| 자연어 명령 예시 추가(한/영 같은 번호로) | `docs/recipes.md` | `uv run pytest -q tests/test_repo_files.py -k recipes` |
| 오류별 해결법 절 추가 | `docs/troubleshooting.md` | `uv run pytest -q tests/test_troubleshooting.py` |
| 새 바닥 재질 값(예: `gravel`) | `src/blender_fx_mcp/recipes/_common.py` 의 `GROUND_MATERIALS`, `src/blender_fx_mcp/server.py` 의 `CHOICES`, `set_ground`·`make_demo_building` 도구 설명 | `uv run pytest -q tests/test_server_choices.py tests/test_server_tools.py` (블렌더가 있으면 `uv run pytest -q tests/test_recipes_v05.py -k ground`) |

라벨 뜻:

- `good first issue` — 위 표 정도 크기의 일. 파일 한두 개, 시험 명령 하나로 끝난다.
- `needs-info` — 재현 정보(doctor 출력·블렌더 판·불린 도구와 인자)를 기다리는 이슈. 30일 동안 답이 없으면 닫을 수 있다([SUPPORT.md](SUPPORT.md)).

PR 전에는 늘 `uvx ruff check .` 와 위 확인 명령을 돌립니다.

### Good first contributions

Small tasks that need no Blender knowledge. Pick an issue labelled `good first issue`. All of them are checked without
Blender by the command in the last column (a new ground material is worth one extra run in Blender).

| Task | Files | Check |
|---|---|---|
| Polish an error message (English or Korean) | `L()` in recipes such as `src/blender_fx_mcp/recipes/_common.py`, `t()` in `src/blender_fx_mcp/server.py` and `src/blender_fx_mcp/bridge.py`; update `docs/troubleshooting.md` if it quotes the sentence | `uv run pytest -q tests/test_recipe_messages.py tests/test_server_messages.py tests/test_troubleshooting.py` |
| Add a natural-language example (same number in both languages) | `docs/recipes.md` | `uv run pytest -q tests/test_repo_files.py -k recipes` |
| Add a troubleshooting section for an error | `docs/troubleshooting.md` | `uv run pytest -q tests/test_troubleshooting.py` |
| Add a ground material value (e.g. `gravel`) | `GROUND_MATERIALS` in `src/blender_fx_mcp/recipes/_common.py`, `CHOICES` in `src/blender_fx_mcp/server.py`, the `set_ground` and `make_demo_building` descriptions | `uv run pytest -q tests/test_server_choices.py tests/test_server_tools.py` (with Blender: `uv run pytest -q tests/test_recipes_v05.py -k ground`) |

Labels:

- `good first issue` — about the size of the rows above: one or two files and one test command.
- `needs-info` — waiting for repro info (doctor output, Blender version, tool and arguments); may be closed after 30 days
  without a reply ([SUPPORT.md](SUPPORT.md)).

Always run `uvx ruff check .` and the check command before opening a PR.

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
