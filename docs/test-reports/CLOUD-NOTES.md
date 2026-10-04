# 클라우드 회차 기록

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
