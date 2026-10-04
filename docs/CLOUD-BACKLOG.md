# 클라우드 수정 백로그

클라우드 회차가 위에서부터 3~4개씩 처리한다. 끝나면 `[x]`.
항목 끝 괄호는 오픈소스 지원 프로그램 심사 기준(유지보수·문서·시험·라이선스·이슈 대응) 중 무엇을 채우는지다.

- [x] README 첫 화면: 무엇을 해 주나 한 줄 / Claude에 연결하는 설정 3줄 / 첫 명령 예시 / 결과 GIF 자리
- [x] docs/demo-script.md: GIF 촬영 대본(도구 호출 순서)
- [x] 블렌더 없이 도는 단위 시험 늘리기(인자 검증, 명령→파라미터 변환, 오류 메시지) + CI 연결
- [x] pip install bpy 헤드리스 통합 시험 가능 여부 확인, 되면 CI에 일부 추가 — 됨(bpy 5.0.1·Py3.11+libEGL). 유체 5개·접착 1개는 `app_only` 표시로 건너뜀
- [x] server.json.example을 공식 MCP 레지스트리 형식에 맞게 점검, 절차는 docs/registry.md — 2025-12-11 스키마·camelCase·0.6.3, tests/test_registry.py
- [x] docs/recipes.md: 자연어 명령 5개와 예상 결과 — 1~3번은 bpy 실측값, 4·5번(유체)은 확인할 칸
- [x] CHANGELOG와 버전 0.7.0 준비 — 미출시 절과 출시 순서 작성, 버전 번호는 출시 때 올림(시험이 세 곳 일치 강제)

### 2026-10-04 추가

- [x] 모든 레시피 오류(`FxError`, recipes 안 45곳)가 `L(한국어, 영어)` 쌍인지 정적으로 검사하는 단위 시험 + 빠진 곳 고치기 (시험·오류 메시지: `BLENDER_FX_LANG=en` 사용자에게 한국어만 나오면 안 됨) — `tests/test_recipe_messages.py`(AST 검사, L() 60곳의 한/영 순서도 확인), 한국어만 있던 힘장 오류 2곳 고침
- [x] `.github/ISSUE_TEMPLATE` 에 기능 요청 양식·`config.yml` 추가, 버그 양식에 `blender-fx-doctor` 출력과 블렌더 버전 칸 (이슈 대응: 재현 정보 없이 들어오는 이슈 줄이기) — 기능 요청 양식·`config.yml`(보안 비공개 신고·recipes 링크), 버그 양식에 수신기 버전·언어 칸, doctor 첫 줄에 blender-fx-mcp 버전, `tests/test_repo_files.py`
- [x] `SECURITY.md`(로컬 9876 포트로 파이썬을 보내는 구조의 위험과 신고 경로)·`CODE_OF_CONDUCT.md` (라이선스·커뮤니티 표준: GitHub 커뮤니티 프로필 항목) — 한/영, 지원 판·9876 무인증 위험·비공개 신고 양식, CoC 는 Contributor Covenant 2.1 요약+링크, README 에 보안 절, 시험 3개
- [x] bpy 4.5 LTS 휠로 Mantaflow 가 도는지 확인, 되면 CI 에 유체 시험 추가 (시험: 지금 bpy 5.0.1 에서는 유체 5개를 못 돌림) — **안 됨.** bpy 4.5.14·4.2.23 LTS 휠도 `LevelsetGrid.setConst` 없음(유체), 접착은 4.5 에서도 세그폴트. 대신 공식 블렌더 Linux 빌드로 `app_only` 를 돌리는 손 실행 작업 `.github/workflows/app-tests.yml` 추가(클라우드에서는 download.blender.org 가 막혀 미검증). 덤: bpy 4.5.14 로 나머지 레시피 시험 133개 모두 통과
- [ ] 접착(glue) 세그폴트를 bpy 로 짧게 재현해 원인 좁히기, 레시피 쪽에서 피할 수 있으면 고치기 (유지보수: 블렌더 앱에서도 같은 위험이 있는지 판단 근거)
- [ ] README 영어 절을 설치·첫 명령·도구 목록까지 늘리기 (문서: 해외 심사자·사용자가 한국어 없이 시작할 수 있게)

### 2026-10-04 (2회차) 추가

- [ ] `server.py` 의 사용자 메시지 `t(한국어, 영어)` 쌍 정적 검사 + 모든 MCP 도구 설명(docstring) 첫 줄이 영어인지 검사, 빠진 곳 고치기 (시험·오류 메시지: 레시피 쪽은 검사했지만 서버가 만드는 문장은 아직 검사 없음. 해외 클라이언트의 AI는 도구 설명 첫 줄로 도구를 고른다)
- [ ] `pyproject.toml` 에 `[project.urls]`(Homepage·Issues·Changelog·Security)와 Python 판 분류자(3.10~3.13) 추가, 시험으로 고정 (문서·라이선스: PyPI·레지스트리 페이지에서 이슈·보안 경로가 바로 보여야 함)
- [ ] CI 파이썬 행렬에 3.13 추가 (시험: Mac 실측 환경이 Python 3.13.12 인데 CI 는 3.10·3.12 만 돈다)
- [ ] `.github/dependabot.yml`(GitHub Actions·uv 주 1회) (유지보수: 의존성 갱신이 자동으로 PR 로 들어와 "활발한 유지보수" 근거가 됨, `mcp>=2.0` 이 빠르게 바뀜)
- [ ] ruff 설정과 CI lint 단계(레시피는 블렌더 안에서 `PARAMS`·공용 함수가 붙으므로 `F821` 은 recipes 에서 끔) (유지보수: 기여자 PR 품질을 자동으로 맞춤)
