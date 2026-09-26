# 클라우드 회차 기록

## 2026-09-26

- 한 일: `claude/cloud-work` 브랜치 새로 만듦(main 기준). `docs/test-reports/latest.md` 가 아직 없어 FAIL 확인 불가 → 백로그로 진행. `docs/CLOUD-BACKLOG.md` 생성. README 첫 화면(한 줄 소개·연결 3줄·첫 명령·GIF 자리) 추가, `docs/demo-script.md`(GIF 촬영 대본) 작성.
- 돌린 시험: `uv run pytest -q` → 9 통과, 33 건너뜀. 건너뛴 33개는 블렌더(bpy) 실행 파일이 필요한 레시피 시험이라 클라우드에서 못 돌림.
- Mac에서 확인할 것:
  1. `uv run pytest -q` (블렌더 있는 환경에서 전체 통과 확인, 결과를 `docs/test-reports/latest.md` 에 기록)
  2. `docs/demo-script.md` 대로 촬영 → `docs/media/demo.gif` 추가
  3. README 첫 화면의 연결 명령 3줄이 그대로 동작하는지 확인
