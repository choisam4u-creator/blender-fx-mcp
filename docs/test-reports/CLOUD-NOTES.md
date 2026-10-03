# 클라우드 회차 기록

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
