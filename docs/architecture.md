# 구조 / Architecture

코드를 읽기 전에 한 번 훑어보는 지도입니다. English follows the Korean section.

## 한국어

### 한 번의 도구 호출이 지나가는 길

```
[MCP 클라이언트: Claude · Cursor · Codex …]
   │  도구 호출  destroy(target="Building", material="brick", pieces=200)
   ▼
[src/blender_fx_mcp/server.py]  MCP 서버(stdio). 도구 33개
   │  1. check_choices / check_ranges — 오타·범위 밖 값은 여기서 바로 오류 (블렌더로 안 감)
   │  2. build_code — "PARAMS = {...}" 한 줄 + recipes/_common.py + recipes/destroy.py 를 이어 붙임
   ▼
[src/blender_fx_mcp/bridge.py]  localhost:9876 소켓. 명령마다 붙었다 뗀다
   │  {"type": "execute_code", "params": {"code": "..."}}
   ▼
[블렌더 안 수신기 애드온 (blender-mcp 의 addon.py)]  메인 스레드에서 코드 실행
   │
   ▼
[레시피]  main() → run_guarded(main) → 표준 출력에 "FX_RESULT {json}" 한 줄
   │
   ▼
[server.py]  parse_result — 마지막 FX_RESULT 를 읽음. ok=false 면 error 문장을 그대로 사용자에게
   │  render 레시피를 한 번 더 보내 미리보기 프레임(png)을 만듦
   ▼
[MCP 클라이언트]  결과 문장(한/영) + 미리보기 이미지
```

AI 는 블렌더 코드를 짜지 않습니다. 검증된 레시피와 값만 고릅니다.

### 파일별 역할

| 파일 | 하는 일 |
|---|---|
| `src/blender_fx_mcp/server.py` | MCP 도구 정의, 인자 미리 검사(`CHOICES`·`RANGES`), 레시피 조립(`build_code`), 결과 문장, 긴 작업 진행 알림(`FxServer`·`_progress`) |
| `src/blender_fx_mcp/bridge.py` | 수신기와 소켓 통신, 연결 거부·시간 초과 오류 문장 |
| `src/blender_fx_mcp/disk.py` | 출력 폴더 디스크 여유(doctor 선택 항목, 굽기 전 1GB 아래면 멈춤) |
| `src/blender_fx_mcp/i18n.py` | `t(한국어, 영어)` — `BLENDER_FX_LANG`, 없으면 로캘로 언어 고르기 |
| `src/blender_fx_mcp/doctor.py` | `blender-fx-doctor` 준비물 점검 |
| `src/blender_fx_mcp/headless.py` | `blender-fx-headless` — 소켓 없이 블렌더를 백그라운드로 띄워 레시피 실행(개발·시험용) |
| `src/blender_fx_mcp/recipes/_common.py` | 레시피 공용 도우미: `FxError`·`L()`·`run_guarded`·재질·힘장·렌더 품질 |
| `src/blender_fx_mcp/recipes/destroy.py` 등 | 효과 하나당 파일 하나. 블렌더 안에서만 돈다(`bpy`) |
| `scripts/e2e_socket.py` | 실제 MCP 클라이언트 → 서버 → 열린 블렌더까지 끝까지 확인 |
| `tests/` | 아래 "시험 경로" |

### 레시피 규칙

- 맨 위에 `PARAMS`(dict)가 있다고 가정합니다. 서버가 붙입니다. `PARAMS["_lang"]` 은 `ko`/`en`.
- `def main(): ... return dict(...)` 뒤에 `run_guarded(main)`. 성공이면 `FX_RESULT {"ok": true, ...}`.
- 사용자에게 보일 실패는 `raise FxError(L("한국어", "English"))`. 그 밖의 예외는 원인 추적이 함께 갑니다.
- 레시피는 문자열로 블렌더에 보내져 실행되므로 커버리지 측정에서 빠집니다.

### 시험 경로

```
블렌더 없이 (CI server-tests, 3.10·3.11·3.12·3.13·3.14)
  tests/test_server*.py · test_doctor.py · test_headless.py · …
  가짜 소켓·가짜 레시피 결과·가짜 실행 파일로 server/bridge/doctor/headless 를 시험

bpy 모듈로 (CI recipe-tests-bpy)
  tests/test_recipes*.py → headless.run_steps → BLENDER_FX_BLENDER(파이썬+bpy) 로 레시피 실행
  Mantaflow 유체는 bpy 휠에서 깨져 @pytest.mark.app_only 로 건너뜀 (tests/conftest.py)

블렌더 앱으로 (Mac · 손 실행 app-tests 워크플로)
  uv run pytest -q  — app_only 까지 전부
  uv run python scripts/e2e_socket.py  — 블렌더 창 + 수신기를 켠 상태에서 끝까지
```

새 효과를 더하는 순서는 [CONTRIBUTING.md](../CONTRIBUTING.md), 오류 문장별 해결법은 [troubleshooting.md](troubleshooting.md).

## English

### The path of one tool call

```
[MCP client: Claude, Cursor, Codex, ...]
   │  tool call  destroy(target="Building", material="brick", pieces=200)
   ▼
[src/blender_fx_mcp/server.py]  MCP server over stdio, 33 tools
   │  1. check_choices / check_ranges: typos and out-of-range values fail here, before Blender
   │  2. build_code: one "PARAMS = {...}" line + recipes/_common.py + recipes/destroy.py
   ▼
[src/blender_fx_mcp/bridge.py]  socket to localhost:9876, one connection per command
   │  {"type": "execute_code", "params": {"code": "..."}}
   ▼
[receiver add-on inside Blender (addon.py from blender-mcp)]  runs the code on the main thread
   │
   ▼
[recipe]  main() → run_guarded(main) → prints one "FX_RESULT {json}" line
   │
   ▼
[server.py]  parse_result reads the last FX_RESULT; if ok=false the error sentence goes to the user as is
   │  then sends the render recipe to make preview frames (png)
   ▼
[MCP client]  result sentence (Korean or English) + preview images
```

The AI never writes Blender code. It only picks a tested recipe and its values.

### Files

| File | Role |
|---|---|
| `src/blender_fx_mcp/server.py` | MCP tools, argument checks (`CHOICES`, `RANGES`), recipe assembly (`build_code`), result sentences, progress notifications for long work (`FxServer`, `_progress`) |
| `src/blender_fx_mcp/bridge.py` | Socket talk with the receiver; connection-refused and timeout messages |
| `src/blender_fx_mcp/disk.py` | Output folder free space (optional doctor check; bakes stop below 1GB before reaching Blender) |
| `src/blender_fx_mcp/i18n.py` | `t(korean, english)`, picks the language from `BLENDER_FX_LANG`, else the locale |
| `src/blender_fx_mcp/doctor.py` | `blender-fx-doctor` setup check |
| `src/blender_fx_mcp/headless.py` | `blender-fx-headless`: runs recipes in background Blender without the socket (development, tests) |
| `src/blender_fx_mcp/recipes/_common.py` | Shared recipe helpers: `FxError`, `L()`, `run_guarded`, materials, force fields, render quality |
| `src/blender_fx_mcp/recipes/destroy.py` etc. | One file per effect. Runs only inside Blender (`bpy`) |
| `scripts/e2e_socket.py` | End-to-end check: real MCP client → server → open Blender |
| `tests/` | See "Test paths" |

### Recipe rules

- Assume a `PARAMS` dict at the top; the server prepends it. `PARAMS["_lang"]` is `ko` or `en`.
- End with `run_guarded(main)` after `def main(): ... return dict(...)`. Success prints `FX_RESULT {"ok": true, ...}`.
- User-facing failures: `raise FxError(L("Korean", "English"))`. Any other exception is sent with its traceback.
- Recipes are sent to Blender as strings, so coverage does not measure them.

### Test paths

```
Without Blender (CI server-tests, Python 3.10, 3.11, 3.12, 3.13, 3.14)
  tests/test_server*.py, test_doctor.py, test_headless.py, ...
  fake socket, fake recipe results and fake executables test server/bridge/doctor/headless

With the bpy module (CI recipe-tests-bpy)
  tests/test_recipes*.py → headless.run_steps → recipes run by BLENDER_FX_BLENDER (python + bpy)
  Mantaflow fluids are broken in bpy wheels, so @pytest.mark.app_only tests are skipped (tests/conftest.py)

With the Blender app (Mac, manual app-tests workflow)
  uv run pytest -q  — everything, app_only included
  uv run python scripts/e2e_socket.py  — end to end with the Blender window and receiver running
```

How to add an effect: [CONTRIBUTING.md](../CONTRIBUTING.md). Fixes by error message: [troubleshooting.md](troubleshooting.md).
