# 클라우드 회차 기록

## 2026-10-06 (2회차)

- 한 일: `latest.md`(10/1) FAIL 2건은 10/2 회차에 이미 고쳐 main 에 병합됨 → 백로그로 진행. 시작 때 main(PR #8 병합분)을 받아 옴(빨리감기). 백로그 4개 완료 → 남은 항목 1개라 새 항목 5개 추가.
  1. **워크플로 최소 권한** — `ci.yml`·`app-tests.yml` 최상위 `permissions: contents: read`. 시험: 모든 워크플로에 있는지, write 없는지.
  2. **MCP 도구 annotations** — 32개 모두(READ_ONLY 5·SETTING 7·ADDITIVE 15·DESTRUCTIVE 5, `openWorldHint=false`). 백로그에 적힌 `reset_scene` 등은 없는 이름이라 `restore`·`clear_caches`·`reset_destroy`·`export_model`·`snapshot` 을 destructive 로. 시험 5종. 이 변경으로 README 도구 표 시험의 정규식이 도구를 못 찾게 돼 함께 고침.
  3. **도구 성공 갈래 시험** `tests/test_server_tools.py` — 가짜 레시피 결과로 도구 29개를 한/영 끝까지 호출. 커버리지 **server 49% → 88%, 전체 59% → 84%**(CONTRIBUTING 갱신, CI 목록에 추가).
  4. **`docs/troubleshooting.md`(한/영)** — 오류 문장 8묶음별 해결법. 연결·시간 초과 오류와 doctor 의 확인 필요 줄에 링크(절 제목 영어 → ASCII 앵커). `tests/test_troubleshooting.py`(문장 25개가 소스·문서 양쪽에 있는지, 링크 절 존재). CI 목록에 추가.
  - CHANGELOG 미출시 절 반영, 시험 수 348개(블렌더 없이 314개).
- 돌린 시험: `uvx ruff@0.15.20 check .` 통과. `uv run pytest -q`(Python 3.13) → **314 통과, 34 건너뜀**(블렌더 없음). CI 서버 시험 목록을 Python 3.10 + `--cov` 로 → 310 통과, 4 건너뜀, 커버리지 84%. `uv lock --check`·`uv build` 통과. 못 돌린 것: 레시피 시험 34개(블렌더 필요 — 이번 회차는 레시피를 건드리지 않아 bpy 로도 안 돌림). 오류 문장 끝 링크는 GitHub 에서 앵커가 실제로 열리는지 브라우저로 확인 못 함(병합 전이라 main 에 문서가 없음).
- Mac에서 확인할 것:
  1. `uv run pytest -q` (블렌더 앱으로 전체 통과)
  2. `BLENDER_FX_PORT=1 uv run blender-fx-doctor | tail -1` (끝에 troubleshooting.md 링크)
  3. 병합 뒤 그 링크에 `#connection-refused` 를 붙여 열었을 때 해당 절로 가는지

## 2026-10-06

- 한 일: `latest.md`(10/1) FAIL 2건은 10/2 회차에 이미 고쳐 main 에 병합됨 → 백로그로 진행. PR #5 가 병합돼 `claude/cloud-work` 를 main(6385bb4)에서 다시 시작. 남은 백로그 4개 완료 → 남은 항목이 0개라 새 항목 5개 추가.
  1. **PR 양식** `.github/pull_request_template.md`(한/영, 확인 칸 8개). 시험: 명령이 CONTRIBUTING 과 같은지, 새 레시피 칸이 빠지지 않았는지.
  2. **`examples/`** — 클로드 데스크톱·커서(`.cursor/mcp.json`)·코덱스(`config.toml`, 굽기용 `tool_timeout_sec = 3600`) 설정과 한/영 안내. README 한/영 설치 절에서 링크. `tests/test_examples.py` 5개(CI 에 추가, tomllib 시험은 3.10 에서 건너뜀).
  3. **README 배지** CI·MIT·Python 3.10–3.13. 시험: 워크플로 파일·라이선스·분류자 양 끝과 일치.
  4. **CI 커버리지 요약** — `pytest-cov>=7`, 레시피 제외(블렌더 안 문자열 실행이라 못 잼). 서버 쪽 **59%**(bridge·i18n 100%, doctor 80%, headless 56%, server 49%) — CONTRIBUTING 에 기록, CI 작업 요약에 표.
  - CHANGELOG 미출시 절에 반영.
- 돌린 시험: `uvx ruff@0.15.20 check .` 통과. `uv run pytest -q`(Python 3.13) → **198 통과, 34 건너뜀**(블렌더 없음). CI 서버 시험 목록을 `--cov` 와 함께 Python 3.10·3.13 으로 → 193+4건너뜀 / 197 통과, 작업 요약 markdown 생성 확인. `uv lock --check` 통과. 못 돌린 것: 레시피 시험 34개(블렌더 필요 — 이번 회차는 레시피를 건드리지 않아 bpy 로도 안 돌림).
- PR: claude/cloud-work → main #8 을 새로 열었음(Mac 총괄이 확인 후 병합).
- Mac에서 확인할 것:
  1. `uv sync --group dev && uv run pytest -q` (pytest-cov 추가 뒤에도 전체 통과)
  2. GitHub PR 화면에서 PR 양식이 뜨는지, Actions → ci → server-tests 요약에 커버리지 표가 있는지
  3. README 첫 화면 배지 3개가 깨지지 않는지

## 2026-10-05 (2회차)

- 한 일: `latest.md`(10/1) FAIL 2건은 10/2 회차에 이미 고쳐 main 에 병합됨 → 백로그로 진행. 시작 때 main(PR #4 병합분)을 받아 옴(빨리감기). 남은 백로그 3개 완료 → 새 항목 5개 추가 → 그중 1개 더 완료(모두 4개).
  1. **CI 파이썬 행렬에 3.13** (3.10·3.12·3.13). 시험: 분류자의 가장 낮은·높은 판이 CI 행렬에 있는지.
  2. **`.github/dependabot.yml`** — uv·GitHub Actions 주 1회. schemastore 의 dependabot-2.0 스키마로 검증 통과. 시험 1개.
  3. **ruff** — `[tool.ruff]`(recipes 의 `F821`, `_common.py` 의 `F401` 만 끔: 서버가 이어 붙이는 구조라서), CI `lint` 작업(`uvx ruff@0.15.20 check .`). 지적 2곳 정리(안 쓰는 변수·import). CONTRIBUTING 에 한 줄.
  4. **시간 초과 오류 안내** — 기다린 초와 `BLENDER_FX_TIMEOUT`(초)로 늘리고 재시작하라는 문장(한/영). 답 안 하는 가짜 수신기로 시험 2개.
  - CHANGELOG 미출시 절에 위 내용 반영.
  - PR #5 Codex 리뷰 지적 1건 고침: 연결 단계(10초 고정)의 시간 초과까지 `BLENDER_FX_TIMEOUT` 안내가 나가던 것 → 연결 실패 안내로. 회귀 시험 1개(블렌더 없이 190 통과).
- 돌린 시험: `uvx ruff check .` 통과. `uv run pytest -q`(Python 3.13) → 189 통과, 34 건너뜀(블렌더 없음). bpy 5.0.1(Python 3.11, 소프트웨어 EGL)로 → **217 통과, 6 건너뜀**(유체 5개는 bpy 모듈의 Mantaflow 결함이라 블렌더 앱 필요, 실제 캐릭터 1개는 파일 없음).
- Mac에서 확인할 것:
  1. `uv run pytest -q` (블렌더 앱에서 전체 통과)
  2. `uvx ruff check .`
  3. GitHub → Settings → Code security 에서 Dependabot version updates 가 켜졌는지(설정 파일만으로 동작)

## 2026-10-05

- 한 일: `latest.md`(10/1) FAIL 2건은 10/2 회차에 이미 고쳐 main 에 병합됨 → 백로그로 진행. main(PR #3 병합분)을 먼저 받아 옴(빨리감기). 백로그 4개 완료, 남은 항목 3개라 새 항목은 안 넣음.
  1. **접착(glue) 세그폴트 원인 찾아 고침.** gdb 로 보니 시뮬레이션이 아니라 첫 `bpy.ops.rigidbody.constraint_add` 에서 Object 가 NULL. 이 연산자는 `temp_override(active_object=…)` 가 아니라 뷰 레이어의 **실제 활성 객체**를 씀 → bpy 에선 활성 객체가 없어 세그폴트, 앱에선 활성 조각에 빈 제약이 하나 더 붙음(bpy 로 재현: 147+1개). 접착 빈 객체를 `view_layer.objects.active` 로 진짜 활성화했다가 되돌림. 접착 시험의 `app_only` 해제 → 이제 bpy CI 에서도 돎.
  2. **README 영어 절** — 준비물·doctor·설치(`-e BLENDER_FX_LANG=en`)·환경변수 표·첫 명령·도구 32개 표·보안/기여/라이선스. 시험: 한/영 도구 표가 `server.py` 도구를 다 담는지, 영어 절에 한글이 없는지.
  3. **서버 메시지 정적 시험** `tests/test_server_messages.py` — server·bridge·doctor 의 `t()` 70곳 한/영 순서, t() 밖 한국어 누출, 도구 설명 첫 줄 영어(이미 모두 영어였음). 서버 안내문(instructions)이 한국어뿐이라 한/영 두 판으로 나눔. CI 에 추가.
  4. **`pyproject.toml` `[project.urls]`·Python 3.10~3.13 분류자** + 시험 2개. `uv build` 로 METADATA 확인.
- 돌린 시험: `uv run pytest -q` → 182 통과, 34 건너뜀(블렌더 없음). bpy 5.0.1(Python 3.11, 소프트웨어 EGL)로 → **210 통과, 6 건너뜀**(유체 5개는 bpy 모듈의 Mantaflow 결함이라 블렌더 앱 필요, 실제 캐릭터 1개는 파일 없음). `uv build` 성공.
- PR: claude/cloud-work → main #4 를 새로 열었음(아래 확인 후 Mac 총괄이 병합). CI 3개 초록. Codex 리뷰 지적 1건(`BLENDER_FX_TIMEOUT` 이 굽기·렌더 도구에 안 먹음) 고침 — 더 큰 값이면 그 도구들도 따라 늘어남, 시험 3개 추가(블렌더 없이 185 통과).
- Mac에서 확인할 것:
  1. `uv run pytest -q tests/test_recipes_v05.py -k glue` (블렌더 앱에서도 접착이 붙고 덜 무너지는지)
  2. `uv run pytest -q` (전체 통과)
  3. `BLENDER_FX_LANG=en uv run python -c "from blender_fx_mcp import server; print(server.INSTRUCTIONS[:40])"` (영어 안내문)

## 2026-10-04 (2회차)

- 한 일: `latest.md`(10/1) FAIL 2건은 10/2 회차에 이미 고쳐 main 에 병합됨 → 백로그로 진행. main(PR #2 병합분)을 먼저 받아 옴. 백로그 4개 완료, 남은 항목이 2개라 새 항목 5개 추가.
  1. **레시피 오류 한/영 쌍 정적 시험** `tests/test_recipe_messages.py` — 모든 `raise FxError` 가 `L(한국어, 영어)` 인지, `L()` 60곳이 (한글, 한글 없는 영어) 순서인지 AST 로 검사. 한국어만 나가던 힘장 오류 2곳(`explode.py`, `_common.py`) 고침.
  2. **이슈 양식** — `feature_request.md`, `config.yml`(보안 비공개 신고·recipes 링크), 버그 양식에 수신기 버전·`BLENDER_FX_LANG` 칸. `blender-fx-doctor` 첫 줄에 blender-fx-mcp 판 번호 표시. `tests/test_repo_files.py`.
  3. **`SECURITY.md`·`CODE_OF_CONDUCT.md`** — 9876 포트 무인증 수신기 위험, `BLENDER_FX_HOST` 를 localhost 로 둘 것, GitHub 비공개 신고 양식. 행동 강령은 Contributor Covenant 2.1 요약+링크. README 에 보안 절.
  4. **bpy 4.5 LTS 로 유체 — 안 됨.** 4.5.14·4.2.23 휠도 `LevelsetGrid.setConst` 없음, 접착 세그폴트도 같음. 대신 공식 블렌더 Linux 빌드를 받아 `app_only` 를 돌리는 **손 실행** 워크플로 `.github/workflows/app-tests.yml`(PR 에서는 안 돎). 클라우드에서는 download.blender.org 가 프록시에 막혀(403) **미검증**. 덤: bpy 4.5.14 로 나머지 레시피 시험 133개 통과.
- 돌린 시험: `uv run pytest -q` → 106 통과, 34 건너뜀(블렌더 없음). bpy 4.5.14 로 → 133 통과, 7 건너뜀(앱 전용 6 + 실제 캐릭터 파일 없음 1). `-m app_only` 를 bpy 4.5·4.2 로 강제 실행 → 유체·접착 실패(위 결함, 블렌더 앱 필요). 워크플로 두 개는 GitHub 워크플로 스키마 검증 통과.
- Mac에서 확인할 것:
  1. `uv run pytest -q && uv run blender-fx-doctor | head -1` (첫 줄 `blender-fx-mcp: 0.6.3`)
  2. GitHub Actions → app-tests → Run workflow (기본값 5.2.0) 가 초록인지
  3. 저장소 Settings → Security 에서 Private vulnerability reporting 켜기(SECURITY.md 링크가 이것을 씀)

## 2026-10-04

- 한 일: `latest.md`(10/1) FAIL 2건은 10/2 회차에 이미 고쳐 main 에 병합됨(PR #1) → 백로그로 진행. 백로그 4개 모두 완료 후 새 항목 6개 추가.
  1. **`pip install bpy` 헤드리스 시험 가능 — 됨.** bpy 5.0.1(Python 3.11) + libEGL(소프트웨어 Mesa)로 레시피 시험 64개 통과. `headless.py` 가 bpy 를 설치한 파이썬도 실행기로 받음. bpy 모듈에서 깨지는 6개(Mantaflow 유체 5개 `LevelsetGrid.setConst` 없음, 리지드바디 접착 1개 세그폴트)는 `@pytest.mark.app_only` 로 표시해 bpy 일 때만 건너뜀. CI 에 `recipe-tests-bpy` 작업 추가. `run_steps` 실패 메시지에 멈춘 단계·종료 이유 표시.
  2. **`server.json.example` 레지스트리 점검.** 2025-12-11 스키마로 검증 — 옛 snake_case 키는 `registryType` 누락으로 거부됨 → camelCase 로, 버전 0.6.0 → 0.6.3, README 에 `mcp-name` 줄. `docs/registry.md`(절차), `tests/test_registry.py` 6개.
  3. **`docs/recipes.md`**: 자연어 명령 5개. 1~3번은 bpy 실측값, 4·5번(유체)은 확인할 칸.
  4. **CHANGELOG 0.7.0(미출시) 절과 출시 순서.** 버전 번호는 출시 때 올림.
  - 덤: bpy 로 돌리다 찾은 버그 수정 — `import_model(size=…)` 의 `volume_m3` 가 크기 바꾸기 전 값(144㎥, 실제 18㎥). 회귀 시험 추가. 저장소의 개인 경로 2곳 제거(실제 캐릭터 시험은 이제 `BLENDER_FX_REAL_CHARACTER` 환경변수 필요).
- 돌린 시험: `uv run pytest -q` → 37 통과, 34 건너뜀(블렌더 없음). bpy 로 `BLENDER_FX_BLENDER=<bpy 파이썬> uv run pytest -q` → **64 통과, 7 건너뜀**(앱 전용 6 + 실제 캐릭터 파일 없음 1). `uv build` 성공. 못 돌린 것: 유체 5개·접착 1개(bpy 모듈 결함, 블렌더 앱 필요), 실제 캐릭터 1개(파일 없음).
- Mac에서 확인할 것:
  1. `BLENDER_FX_REAL_CHARACTER=<캐릭터 glb 경로> uv run pytest -q` (71개 모두 통과하는지)
  2. `uv run pytest -q -m app_only` (앱에서 유체·접착 6개 통과하는지)
  3. GitHub Actions 의 `recipe-tests-bpy` 작업이 초록인지

## 2026-10-03

- 한 일: `latest.md`(10/1)의 FAIL 2건은 지난 회차(6587f84)에서 이미 고쳤고 그 뒤 새 Mac 결과가 없어 백로그로 진행. 백로그 3번 "블렌더 없이 도는 단위 시험 + CI" 완료 — `tests/test_server_params.py` 19개 추가(run_recipe 의 None 제거·언어 주입·오류+traceback 메시지, destroy/explode/set_render/inspect_mesh 의 기본값→파라미터 변환, snapshot 이름 정리, restore 실패 흐름, 가짜 소켓 수신기로 bridge 의 분할 응답·error 상태·빈 응답 처리). CI(`ci.yml`)에 이 파일을 추가.
- 돌린 시험: `uv run pytest -q` → 28 통과, 33 건너뜀(건너뛴 것은 블렌더 실행 파일이 필요한 레시피 시험이라 클라우드에서 못 돌림).
- Mac에서 확인할 것:
  1. `uv run pytest -q` (61개 모두 통과하는지)
  2. `uv run pytest -q tests/test_server_params.py` (블렌더를 켠 상태에서도 9876 포트와 안 부딪히는지)

## 2026-10-02

- 한 일: 10/1 Mac 시험 FAIL 2건 수정(이번 회차는 이것만). ① README 5번째 줄 데모 GIF 이미지를 HTML 주석으로 감쌈(GIF가 생기면 주석 해제). ② 버튼 이름을 "Connect to MCP server"로 통일 — `bridge.py` 연결 실패 안내(한/영)와 `docs/demo-script.md` 수정.
- 돌린 시험: `uv run pytest -q` → 9 통과, 33 건너뜀(건너뛴 것은 블렌더 실행 파일이 필요한 레시피 시험). README 상대 링크 점검(주석 제외) → 깨진 링크 0개.
- Mac에서 확인할 것:
  1. `uv run pytest -q`
  2. README 상대 링크 점검 → 깨짐 0개인지
  3. 블렌더를 끈 채 `uv run blender-fx-doctor` → 안내 문구에 "Connect to MCP server" 가 나오는지

## 2026-09-26

- 한 일: `claude/cloud-work` 브랜치 새로 만듦(main 기준). `docs/test-reports/latest.md` 가 아직 없어 FAIL 확인 불가 → 백로그로 진행. `docs/CLOUD-BACKLOG.md` 생성. README 첫 화면(한 줄 소개·연결 3줄·첫 명령·GIF 자리) 추가, `docs/demo-script.md`(GIF 촬영 대본) 작성.
- 돌린 시험: `uv run pytest -q` → 9 통과, 33 건너뜀. 건너뛴 33개는 블렌더(bpy) 실행 파일이 필요한 레시피 시험이라 클라우드에서 못 돌림.
- Mac에서 확인할 것:
  1. `uv run pytest -q` (블렌더 있는 환경에서 전체 통과 확인, 결과를 `docs/test-reports/latest.md` 에 기록)
  2. `docs/demo-script.md` 대로 촬영 → `docs/media/demo.gif` 추가
  3. README 첫 화면의 연결 명령 3줄이 그대로 동작하는지 확인
