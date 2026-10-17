# 기여 안내 / Contributing

**English:** Every effect is one recipe file in `src/blender_fx_mcp/recipes/` plus one tool in `server.py`. Recipes run inside Blender with `PARAMS` prepended by the server and must end with `run_guarded(main)`, printing one `FX_RESULT` JSON line. Lint with `uvx ruff@0.15.20 check .`. Server-side coverage (recipes excluded, same command as CI): `uv run pytest -q tests --ignore=tests/test_asset_robustness.py --ignore=tests/test_recipe_failure_keeps_scene.py --ignore=tests/test_recipes_fx_extra.py --ignore=tests/test_recipes_headless.py --ignore=tests/test_recipes_v05.py --ignore=tests/test_recipes_v06.py --cov --cov-report=term` (100% on 2026-10-11; CI fails below the 99% floor, `--cov-fail-under=99`, so a new error branch needs its own test); only the Blender-only recipe test files are ignored, so new test files join CI automatically. The fake Blender in tests is `fake_blender` from `tests/conftest.py` (a Python body behind a `/bin/sh` or `.cmd` wrapper), so the failure, timeout and trimming branches also run on Windows CI; only 4 `@posix_only` tests (the segfault signal in `tests/test_headless.py` and the three bash `scripts/lint.sh` tests in `tests/test_lint_script.py`) are skipped there. Test headlessly with `uv run pytest -q` (needs Blender on this machine; on Linux without Blender, `scripts/bpy_tests.sh` installs bpy into `.venv-bpy`, and `BPY_WHEEL=path/to/bpy-5.0.1-….whl` reuses a wheel you already downloaded instead of the 356MB download) and, with Blender open, `uv run python scripts/e2e_socket.py`. For a new tool, add a row to both README tool tables: `uv run python scripts/gen_tool_table.py --draft` prints draft rows from the docstrings, and running it without arguments lists rows or `a/b/c` value lists that disagree with the server. After adding a troubleshooting section or changing a recipe error sentence, run `uv run python scripts/gen_help_index.py --write`: it rebuilds `src/blender_fx_mcp/help_index.py`, which the server uses to end recipe errors with a "Help: …#section" link (a test fails while it is stale). Keep error messages human-readable; the AI shows them to a non-technical user (see [Error message rules](#error-message-rules)). Start with [docs/architecture.md](docs/architecture.md) for the call path and test paths, or pick a small task from [Good first contributions](#good-first-contributions).

## 구조

도구 호출이 지나가는 길과 시험 경로 그림은 [docs/architecture.md](docs/architecture.md).

```
src/blender_fx_mcp/
  server.py        MCP 도구. 레시피를 고르고 값을 넘긴 뒤 결과와 이미지를 돌려준다
  bridge.py        블렌더 수신기와 소켓 통신 (명령마다 붙었다 뗀다)
  headless.py      블렌더를 창 없이 띄워 레시피를 돌리는 개발용 CLI
  doctor.py        준비물 점검 CLI
  i18n.py          메시지 언어 (BLENDER_FX_LANG, 없으면 로캘)
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
   README 한/영 도구 표에 한 줄씩 넣는다. `uv run python scripts/gen_tool_table.py --draft` 가 도구 설명으로 만든 초안 행을 주고, 인자 없이 돌리면 표와 서버(빠진 도구·`a/b/c` 값 목록)가 어긋난 곳을 알려 준다. 해결법 문서에 절을 더하거나 레시피 오류 문장을 바꿨으면 `uv run python scripts/gen_help_index.py --write` 로 `src/blender_fx_mcp/help_index.py` 를 새로 쓴다. 서버가 이 표로 레시피 오류 끝에 "해결법: …#절" 을 붙인다(표가 낡으면 시험이 실패).
4. `headless.py` 의 `STEPS` 에 단계를 추가하고, `tests/test_recipes_headless.py` 에 테스트를 넣는다. 결과 이미지가 실제로 달라지는지(픽셀) 확인하는 assert 를 포함한다.
5. `uvx ruff@0.15.20 check .` 와 `uv run pytest -q` 통과 후 PR. 워크플로(`.github/workflows/`)를 고쳤다면 `scripts/lint.sh` 도: CI lint 잡과 같은 세 검사(ruff·actionlint·zizmor)를 아래 표의 판으로 한 번에 돌린다. actionlint 는 PATH 에 `shellcheck` 가 없으면 `run:` 스크립트 검사를 조용히 건너뛰므로, 스크립트와 CI 모두 판을 고정한 `shellcheck-py` 를 함께 깐다(따로 설치할 것 없음).
   - 서버 쪽 커버리지(CI 와 같은 명령): `uv run pytest -q tests --ignore=tests/test_asset_robustness.py --ignore=tests/test_recipe_failure_keeps_scene.py --ignore=tests/test_recipes_fx_extra.py --ignore=tests/test_recipes_headless.py --ignore=tests/test_recipes_v05.py --ignore=tests/test_recipes_v06.py --cov --cov-report=term`.
     블렌더가 있어야 하는 레시피 시험 파일만 `--ignore` 로 빼므로 새 시험 파일은 저절로 CI 에 들어간다. 레시피 시험 파일을 새로 만들면 이 목록과 `ci.yml` 에 함께 더한다.
     레시피는 블렌더 안에서 문자열로 실행돼 잴 수 없으므로 뺀다(`[tool.coverage.run] omit`). CI 는 이 표를 작업 요약에 남긴다.
     2026-10-11 기준 **100%**(모든 파일. 10-08 에는 99%, 그 앞 회차 95%, 10-07 에는 94%, 10-06 에는 84%, 도구 성공 갈래 시험 전에는 59%). CI 는 **99% 아래면 실패**한다(`--cov-fail-under=99`). 새 오류 갈래를 넣으면 그 갈래 시험도 함께 넣는다. 줄면 PR 에 이유를 적는다.
   - 블렌더 앱이 없으면 `pip install bpy` 한 파이썬 3.11 로도 레시피 시험 대부분이 돈다:
     `uv pip install bpy==5.0.1` 뒤 `BLENDER_FX_BLENDER=.venv/bin/python uv run pytest -q`.
     Linux 에서 렌더하려면 `libegl1 libegl-mesa0 libgl1-mesa-dri` 가 있어야 한다.
     Linux 에서는 `scripts/bpy_tests.sh` 한 줄로 같은 일을 한다(따로 만든 `.venv-bpy` 에 bpy 를 깔아 개발용 `.venv` 를 건드리지 않음, libEGL 이 없으면 설치 명령을 알려 줌, 뒤에 붙인 인자는 pytest 로 넘김).
     처음엔 bpy 휠(356MB, 설치 뒤 약 1GB)을 받느라 몇 분~20분 걸린다. 이미 받은 휠이 있으면 `BPY_WHEEL=휠경로 scripts/bpy_tests.sh` 로 내려받기 없이 깐다.
     bpy 모듈은 Mantaflow(연기·불·물)가 깨져 있어 `@pytest.mark.app_only` 시험은 건너뛴다.
     이런 기능을 쓰는 새 시험에는 `@pytest.mark.app_only` 를 붙인다.
     bpy 4.2·4.5 LTS 휠도 같은 결함이 있다(2026-10 확인). 이 시험은 Actions 의 **app-tests** 작업(손으로 실행, 공식 블렌더 Linux 빌드)으로 돌린다.
   - Mac 실측: `uv run python scripts/mac_report.py` 가 `docs/test-reports/CLOUD-NOTES.md` 맨 위 명령을 돌려 `docs/test-reports/latest.md` 를 새로 쓴다(집 폴더는 `~`). 클라우드 회차가 그 결과부터 읽는다.
   - Windows: CI `server-tests-os` 가 Windows 에서도 서버 시험을 돌린다. 가짜 블렌더는 `tests/conftest.py` 의 `fake_blender`(본문은 파이썬,
     POSIX 는 `/bin/sh` 감싸개, Windows 는 `.cmd` 감싸개)라 실행 실패·시간 초과·출력 자르기 갈래도 Windows 에서 돈다.
     건너뛰는 것은 `@posix_only` 4개: 세그폴트 흉내(시그널) 1개(`tests/test_headless.py`)와 bash 스크립트 `scripts/lint.sh` 시험 3개(`tests/test_lint_script.py`)뿐이다.

## 처음 기여하기 좋은 일

블렌더 코드를 몰라도 할 수 있는 작은 일입니다. 이슈에 `good first issue` 라벨이 붙은 것부터 고르면 됩니다.
모두 블렌더 없이 아래 시험 명령으로 확인할 수 있습니다(새 바닥 재질만 블렌더로 한 번 더).

| 할 일 | 고칠 파일 | 확인 명령 |
|---|---|---|
| 오류 문장의 영어·한국어 다듬기 | `src/blender_fx_mcp/recipes/_common.py` 같은 레시피의 `L()`, `src/blender_fx_mcp/server.py`·`src/blender_fx_mcp/bridge.py` 의 `t()`. 같은 문장이 `docs/troubleshooting.md` 에도 있으면 함께 | `uv run pytest -q tests/test_recipe_messages.py tests/test_recipe_next_steps.py tests/test_server_messages.py tests/test_server_next_steps.py tests/test_troubleshooting.py` |
| 자연어 명령 예시 추가(한/영 같은 번호로) | `docs/recipes.md` | `uv run pytest -q tests/test_repo_files.py -k recipes` |
| 오류별 해결법 절 추가 | `docs/troubleshooting.md` | `uv run pytest -q tests/test_troubleshooting.py` |
| 새 바닥 재질 값(예: `gravel`) | `src/blender_fx_mcp/recipes/_common.py` 의 `GROUND_MATERIALS`, `src/blender_fx_mcp/server.py` 의 `CHOICES`, `set_ground`·`make_demo_building` 도구 설명 | `uv run pytest -q tests/test_server_choices.py tests/test_server_tools.py` (블렌더가 있으면 `uv run pytest -q tests/test_recipes_v05.py -k ground`) |

라벨 뜻:

- `good first issue` — 위 표 정도 크기의 일. 파일 한두 개, 시험 명령 하나로 끝난다.
- `needs-info` — 재현 정보(doctor 출력·블렌더 판·불린 도구와 인자)를 기다리는 이슈. 30일 동안 답이 없으면 닫을 수 있다([SUPPORT.md](SUPPORT.md)).

PR 전에는 늘 `uvx ruff@0.15.20 check .` 와 위 확인 명령을 돌립니다.

### Good first contributions

Small tasks that need no Blender knowledge. Pick an issue labelled `good first issue`. All of them are checked without
Blender by the command in the last column (a new ground material is worth one extra run in Blender).

| Task | Files | Check |
|---|---|---|
| Polish an error message (English or Korean) | `L()` in recipes such as `src/blender_fx_mcp/recipes/_common.py`, `t()` in `src/blender_fx_mcp/server.py` and `src/blender_fx_mcp/bridge.py`; update `docs/troubleshooting.md` if it quotes the sentence | `uv run pytest -q tests/test_recipe_messages.py tests/test_recipe_next_steps.py tests/test_server_messages.py tests/test_server_next_steps.py tests/test_troubleshooting.py` |
| Add a natural-language example (same number in both languages) | `docs/recipes.md` | `uv run pytest -q tests/test_repo_files.py -k recipes` |
| Add a troubleshooting section for an error | `docs/troubleshooting.md` | `uv run pytest -q tests/test_troubleshooting.py` |
| Add a ground material value (e.g. `gravel`) | `GROUND_MATERIALS` in `src/blender_fx_mcp/recipes/_common.py`, `CHOICES` in `src/blender_fx_mcp/server.py`, the `set_ground` and `make_demo_building` descriptions | `uv run pytest -q tests/test_server_choices.py tests/test_server_tools.py` (with Blender: `uv run pytest -q tests/test_recipes_v05.py -k ground`) |

Labels:

- `good first issue` — about the size of the rows above: one or two files and one test command.
- `needs-info` — waiting for repro info (doctor output, Blender version, tool and arguments); may be closed after 30 days
  without a reply ([SUPPORT.md](SUPPORT.md)).

Always run `uvx ruff@0.15.20 check .` and the check command before opening a PR; after editing `.github/workflows/`, also `scripts/lint.sh`, which runs the CI lint job's three checks (ruff, actionlint, zizmor) at the versions in the table below. actionlint silently skips `run:` scripts without `shellcheck` on PATH, so both the script and CI install the pinned `shellcheck-py` alongside it (nothing else to install).

## 규칙

- 블렌더 enum 값은 버전마다 바뀐다. 가능하면 `try/except TypeError` 로 감싸거나, 현재 값을 읽어 쓴다.
- `bpy.ops.*` 는 컨텍스트가 필요하다. `bpy.context.temp_override(...)` 로 감싼다.
- 노드는 이름이 아니라 `type` 으로 찾는다 (`n.type == "BSDF_PRINCIPLED"`). 이름은 UI 언어에 따라 바뀐다.
- 사용자 오브젝트를 지우지 않는다. 이 도구가 만든 것만 `fx_role` 태그로 표시하고 정리한다.
- 주석은 한국어, 코드 식별자는 영어. 사용자에게 보이는 문장은 `L()`(레시피) 또는 `t()`(서버, `i18n.py`) 로 한국어·영어 둘 다 쓴다.
- 사용자 오브젝트에 모디파이어를 붙일 때는 이름을 `FX_` 로 시작한다. `cleanup_fx` 가 그 이름만 떼어 낸다.
- 되돌리기 어려운 동작(파일 열기, 물리 굽기 적용)을 넣을 때는 `snapshot` 을 먼저 권하는 문구를 도구 설명에 넣는다.

## 판을 고정한 도구 / Pinned tools

`uvx` 로 부르는 검사 도구는 `uv.lock` 밖이라 dependabot 이 올려 주지 않습니다. 판은 이 표 한 곳에 모으고, 워크플로·문서의 `도구@판` 이 표와 같은지 `tests/test_pinned_tools.py` 가 확인합니다.
Tools run through `uvx` live outside `uv.lock`, so dependabot never bumps them. Their versions live in this one table; `tests/test_pinned_tools.py` checks that every `tool@version` in workflows and docs matches it.

| 도구 / Tool | 판 / Version | 쓰는 곳 / Used in |
|---|---|---|
| ruff | 0.15.20 | CI `lint`, PR 양식 / PR template |
| actionlint-py | 1.7.12.25 | CI `lint` (워크플로 검사 / workflow lint), `scripts/lint.sh` |
| shellcheck-py | 0.11.0.1 | CI `lint` (actionlint 의 `run:` 검사 / shell checks in `run:`), `scripts/lint.sh` |
| zizmor | 1.30.1 | CI `lint` (워크플로 보안 / workflow security) |
| twine | 7.0.0 | CI `build`, `release.yml` |

분기마다(1·4·7·10월 첫 주) 각 도구의 최신 판을 확인해(`uvx pip index versions <도구>` 또는 PyPI) 표와 `.github/workflows/`·문서의 판을 한 번에 올리고, `uv run pytest -q tests/test_pinned_tools.py` 와 CI lint 가 초록인지 봅니다.
Once a quarter (first week of Jan/Apr/Jul/Oct), check each tool's latest release, bump the table, workflows and docs together, and make sure `tests/test_pinned_tools.py` and the CI lint job stay green.

## 오류 문장 규칙

AI 는 오류 문장을 그대로 사용자(대개 개발자가 아님)에게 보여 줍니다. 그래서 오류 하나가 아래 네 가지를 모두 말해야 합니다.

1. **무엇이 틀렸나** — 받은 값을 그대로 넣는다(`fps 값 -24 은(는) 범위 밖입니다`, `파일이 없습니다: tower.glb`).
2. **다음 할 일** — 시키는 말(`…다시 시키세요`, `…확인하세요`) 또는 고를 값 목록(`가능한 값: …`, 권장 값, 비슷한 파일 이름). 고칠 길이 없으면 신고 방법이나 해결법 링크.
3. **실제 이름** — 문장 속 도구·인자 이름은 실제로 있는 것만(`reset_destroy`, `pieces`). AI 가 그 이름 그대로 부른다.
4. **한/영 짝** — 레시피는 `L("한국어", "English")`, 서버는 `t("한국어", "English")`. 두 문장이 같은 다음 할 일을 말한다.

이 규칙은 아래 시험이 지킵니다. 새 오류를 넣고 이 명령이 통과하면 규칙을 지킨 것입니다.
`uv run pytest -q tests/test_recipe_messages.py tests/test_recipe_next_steps.py tests/test_server_next_steps.py tests/test_server_ranges.py tests/test_server_prompts.py tests/test_troubleshooting.py`

| 시험 파일 | 보는 것 |
|---|---|
| `tests/test_recipe_messages.py` | 레시피 `FxError` 가 모두 `L()` 한/영 짝인지 |
| `tests/test_recipe_next_steps.py` | 레시피 오류의 한/영 다음 할 일 표지, 실제 도구·인자 이름 |
| `tests/test_server_next_steps.py` | 서버·연결 오류(`BlenderError`)의 한/영 다음 할 일 표지, 실제 이름, 범위 오류의 권장 값 |
| `tests/test_server_ranges.py` | 숫자 인자 범위를 블렌더에 보내기 전에 막고 권장 값을 말하는지 |
| `tests/test_server_prompts.py` | 프롬프트·문서가 말하는 도구·인자 이름이 실제인지 |
| `tests/test_troubleshooting.py` | 연결 오류 문장이 `docs/troubleshooting.md` 에 있고 링크가 맞는 절을 가리키는지 |

### Error message rules

The AI shows an error message to the user (usually not a developer) as it is, so each error says all four things below.

1. **What was wrong**: include the value received (`fps -24 is out of range`, `File not found: tower.glb`).
2. **What to do next**: an instruction (`...ask again`, `Check ...`) or the values to pick from (`Choose one of: ...`, recommended values, similar file names). If there is no fix, say how to report it or link the troubleshooting section.
3. **Real names**: tool and argument names in the sentence must exist (`reset_destroy`, `pieces`); the AI calls them by that name.
4. **Korean/English pair**: `L("Korean", "English")` in recipes, `t("Korean", "English")` in the server. Both say the same next step.

The tests below enforce these rules. If you add an error and this command passes, the rules are kept:
`uv run pytest -q tests/test_recipe_messages.py tests/test_recipe_next_steps.py tests/test_server_next_steps.py tests/test_server_ranges.py tests/test_server_prompts.py tests/test_troubleshooting.py`

| Test file | Checks |
|---|---|
| `tests/test_recipe_messages.py` | every recipe `FxError` is an `L()` Korean/English pair |
| `tests/test_recipe_next_steps.py` | next-step markers in both languages for recipe errors, real tool and argument names |
| `tests/test_server_next_steps.py` | the same for server and connection errors (`BlenderError`), and recommended values in range errors |
| `tests/test_server_ranges.py` | number arguments are checked before reaching Blender, with recommended values |
| `tests/test_server_prompts.py` | tool and argument names in prompts and docs are real |
| `tests/test_troubleshooting.py` | connection errors are quoted in `docs/troubleshooting.md` and link to the right section |

## 이슈 올리기 전에

```bash
uv run blender-fx-doctor
```

결과와 블렌더 버전, OS, GPU, 재현 명령(또는 AI에게 한 말)을 함께 적어 주세요.
