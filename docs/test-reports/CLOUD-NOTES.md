# 클라우드 회차 기록

## 맥에서 돌릴 명령 (블렌더 필요, 최신 회차 기준)

```sh
BLENDER_FX_LANG=en uv run pytest -q                # 실패 0개인지(10/10 실패 10개는 4회차에 고침, 셸 언어·한글 홈 경로와 무관)
BLENDER_FX_PORT=1 uv run blender-fx-doctor         # 연결 줄 X, 끝 "다음 할 일" 번호 줄. 블렌더 창에서 Connect 뒤 BLENDER_FX_PORT 없이 다시 → 연결 줄에 "Blender 5.2.x"
uv run python -c "from blender_fx_mcp import server; print(server.ping_blender()); print(server.restore('없는이름'))"   # 블렌더 판 표시, restore 는 있는 스냅샷 이름 제안
```

## 2026-10-10 (5회차)

- 한 일: 맨 앞 지시(10/10 Mac 실패 10개)는 **4회차(오늘 이른 시각)에 이미 고쳐져 있음**을 확인 — `HOME`·`--basetemp` 를 한글 폴더로, `BLENDER_FX_LANG=en` 으로 전체 시험 661 통과·0 실패.
  `latest.md`(10/1)의 FAIL 2건은 10/2 에 고쳐 main 에 있음. main 은 앞서 있지 않음. 그다음 백로그(사용자 체감 우선):
  1. **연결 거부 오류가 원인을 좁혀 다음 한 단계**(백로그) — 이 컴퓨터에 애드온 파일이 없으면 설치 메뉴 경로부터, 있으면 Connect, 포트를 바꿨으면 Port 맞추기.
     애드온 폴더 목록을 doctor 에서 bridge 로 옮겨 둘이 같은 곳을 봄. 원격 `BLENDER_FX_HOST` 면 설치 안내 안 함.
  2. **파일·스냅샷 경로 오류에 다음 할 일**(백로그) — `import_model`·HDRI 파일이 없으면 같은 폴더의 비슷한 이름, `restore` 는 있는 스냅샷 이름.
     레시피 오류 문장 44개 전부 다음 할 일 표지(…세요·고를 값)가 있는지 정적 시험(블렌더 내부 실패 3곳만 이유와 함께 예외).
  3. **README 첫 화면 = doctor 순서의 4단계**(백로그) — uv → 블렌더+애드온 → Connect → 클로드 등록, 단계마다 확인할 `[OK]` 줄. 순서·이름이 doctor 와 같은지 시험.
  4. **`restore` 이름 오타가 지난 `before_restore` 를 덮어쓰던 문제**(새 항목, 2번 하다 발견) — 블렌더에 보내기 전에 멈추고 이름 제안.
  5. **`ping_blender`·doctor 에 블렌더 판 + 시험한 판이 아니면 경고**(새 항목).
- 돌린 시험: `uv run pytest -q` **709 통과·34 건너뜀**(3.11, Linux). 한글 HOME·basetemp + `en` 으로도 통과. CI 서버 명령 커버리지 99.42%(하한 95%).
  새 시험 파일은 Python 3.10 으로도 통과. `uvx ruff@0.15.20 check .` 통과. **`scripts/bpy_tests.sh`(bpy 5.0.1) 717 통과·6 건너뜀·0 실패**(레시피 문장 수정 뒤).
  건너뛴 34개(서버 시험)·6개(bpy)는 블렌더 앱이 필요해서 — 유체 `app_only` 5개·실제 캐릭터 파일 1개, 나머지는 bpy 가 없는 기본 환경의 레시피 시험.
- 완료 수·추가 수: **완료 5**(백로그 기존 3 + 새 2) / **추가 5**. 남은 `[ ]` 3개(doctor 클라이언트 등록 줄·MCP 프롬프트·examples/first_render.py).
- Mac에서 확인할 것: 맨 위 명령 3줄.

## 2026-10-10 (4회차)

- 한 일: **10/10 Mac 실측 실패 10개 먼저** → 그다음 백로그. main 이 앞서 있어(#10 병합) 병합 확인(내용 변화 없음).
  1. **시험 결함 10개 고침.** 여기서 그대로 재현: `BLENDER_FX_LANG=en` + 한글 `--basetemp` 로 고치기 전 10 실패 → 고친 뒤 0.
     ① 언어: `tests/conftest.py` autouse 픽스처가 매 시험 `BLENDER_FX_LANG` 을 지우고 시작, 한국어 기대 시험 3개는 `ko` 직접 지정.
     ② 한글 경로: 영어 메시지 한글 검사에서 출력 폴더 경로를 빼고 검사. 회귀 시험 3개(출력 폴더가 `사용자/출력` 일 때 영어 문장·경로가 온전한지).
  2. **Windows 에서도 가짜 블렌더 시험**(백로그) — `fake_blender`(파이썬 본문 + `/bin/sh exec`·`.cmd` 감싸개). 건너뜀 18 → 1(세그폴트).
     덤으로 **제품 문제** 고침: headless·doctor 가 블렌더 출력을 OS 기본 인코딩으로 읽어 Windows 에서 `UnicodeDecodeError` 위험 → UTF-8(errors=replace).
  3. **주 1회 취약점 점검**(백로그) `audit.yml`(pip-audit 2.9.0, `uv.lock` 그대로). **처음 돌리자 실제 취약점 2건**: 간접 의존성 `pyjwt 2.14.0` → 2.15.1 로 올려 0건.
  4. **이슈 양식 공통 칸 시험**(백로그) — 클라이언트 선택지·블렌더 판 placeholder·OS 가 examples/SUPPORT 와 같은지. 어긋난 곳은 없었음.
  5. **doctor "다음 할 일"**(새 항목) — 실패 항목마다 다음 한 단계를 설치 순서대로 번호로. uv 설치 명령을 OS 별로(지금까지 Windows·Linux 에도 `brew`),
     애드온 Install from Disk 경로, 포트를 바꿨으면 포트 맞추기. MCP `doctor` 도구도 같은 보고서.
  6. **doctor 블렌더 실행 파일 = 선택 항목**(새 항목) — MCP 사용에 필요 없는데 `[X ]` 로 떠 첫 사용자를 막던 것 → `[- ]`, 확인 필요·JSON `failed` 에서 뺌.
- 돌린 시험: `uv run pytest -q` **661 통과·34 건너뜀**(Python 3.11, Linux). `BLENDER_FX_LANG=en`·`ko`·없음 × 한글 `--basetemp` 로도 모두 통과.
  `uvx ruff@0.15.20 check .` 통과. 서버 쪽 커버리지 99%. `scripts/license_check.py` 40/40.
  건너뛴 34개는 블렌더(앱·bpy)가 없어서 — 레시피 시험(CI `recipe-tests-bpy`·Mac 앱 몫). Windows CI 결과는 PR #13 에서 확인.
- 완료 수·추가 수: **완료 5**(백로그 기존 3 + 새 2) + Mac 실패 수정 / **추가 5**(새 항목 중 하나는 이미 있던 `CITATION.cff` 라 README 단계 정렬로 바꿈). 남은 `[ ]` 3개.
- 하다가 실수: CHANGELOG 영어 요약 6줄 제한을 넘긴 채 한 번 푸시 → 바로 다음 커밋에서 고침.

## 2026-10-09 (3회차)

- 한 일: `latest.md`(10/1) FAIL 2건(GIF 링크·버튼 이름)은 10/2 회차에 고쳐 main 에 있음을 다시 확인 → 백로그로 진행. main 은 앞서 있지 않았음(cloud-work 가 main 을 포함). **백로그 21개 완료**(앞 회차가 남긴 7개 + 이번 회차에 세 번 나눠 추가한 15개 중 14개. 아래 19줄은 관련 항목을 묶어 적음). 남은 `[ ]` 3개.
  1. **라벨 정의** `.github/labels.yml`(8개, 한/영 설명) + dependabot 라벨 고정 + maintenance.md `gh label create` 8줄. 양식·문서·dependabot·stale 이 쓰는 라벨이 모두 정의돼 있는지 시험.
  2. **`examples/list_tools.py`** — 공식 `mcp` 클라이언트로 서버를 stdio 로 띄워 도구 목록·`ping_blender`. 닫힌 포트로 한/영 시험.
  3. **파이썬 3.14** — 3.14.6 에서 서버 시험·커버리지 통과, 분류자·CI·SUPPORT·배지·architecture 갱신.
  4. **`needs-info` 30일 자동 닫기** `stale.yml`(23일 뒤 `stale` 표시, 7일 뒤 닫음, PR 제외, `issues: write` 만).
  5. **OpenSSF Scorecard** 작업·README 배지(병합 뒤 main 에서 처음 돌아야 점수가 뜸).
  6. **recipes.md 한 줄 예시** — 예시 없던 도구 25개(한/영). 32개 도구 모두 예시가 있고 인자가 서버 검사를 통과하는지 시험.
  7. **`blender-fx-doctor --json`** — 언어와 무관한 항목 id, 버그·질문 양식에 안내.
  8. **의존성 라이선스 점검** `scripts/license_check.py` + `docs/third-party-licenses.md`(40개 모두 허용적 라이선스) + CI lint 단계.
  9. **macOS·Windows CI** `server-tests-os`. 첫 실행에서 Windows 13개 실패 → **제품 버그 2개 고침**(doctor 애드온 경로 `/`·`\` 섞임, release_check 가 CRLF 메타데이터에서 README 를 못 찾음) + 시험 쪽 경로·인코딩·실행 권한 처리.
  10. **질문 이슈 양식** `question.yml`(라벨 `question`), SUPPORT 링크.
  11. **README 도구 표 점검** `scripts/gen_tool_table.py` — 통째 생성 대신(손으로 다듬은 설명이 더 자세함) 빠진 도구·`a/b/c` 값 목록이 서버 허용 값과 같은지 + `--draft` 초안 행.
  12. **3.10 지원 종료 예고** — CHANGELOG 0.7.0(한/영)·maintenance.md(0.8.0 에서 뺌). 드라이런으로 고칠 곳 10곳을 시험이 모두 짚는 것 확인.
  13. **`.gitattributes`** — 모든 OS 에서 LF, 바이너리 지정, CRLF 파일이 생기면 시험 실패.
  14. **SPDX 표기** — 패키지·레시피·스크립트·예제 41개 첫 줄 `# SPDX-License-Identifier: MIT`.
  15. **첫 기여자 인사** `greet.yml`(한/영, PR 코드 체크아웃 없음).
  16. **SECURITY.md 공급망 표**(한/영 8줄) — 쓰다가 CI 의 `uv sync` 에 `--locked` 가 없던 것을 발견해 모두 고침.
  17. **Windows 건너뛰는 시험 문서화** — CONTRIBUTING 에 18개(가짜 `/bin/sh` 블렌더)와 이유, 개수 시험.
  18. **배포물 라이선스 파일 점검** — `release_check.py --dist` 가 휠·sdist 의 LICENSE·제3자 라이선스 표를 봄(25개 OK).
  19. **문서 링크 점검** `tests/test_docs_links.py` — .md 19개의 상대 링크·앵커(한글 제목 포함), 지금 깨진 링크 0개.
- 돌린 시험: `uvx ruff@0.15.20 check .` 통과. `uv run pytest -q`(블렌더 없음, 3.11) → **638 통과, 34 건너뜀**. CI 서버 명령 3.10(629 통과, 9 건너뜀 — tomllib)·3.14(638 통과), 커버리지 99.04%(하한 95%). **`scripts/bpy_tests.sh` → 666 통과, 6 건너뜀**(회차 끝 기준)(유체 `app_only` 5개·실제 캐릭터 파일 1개). `uv build` → `release_check.py --dist` 25개 OK, `twine@7.0.0 check` PASSED 2개. `uv lock --check` 통과. `license_check.py` 40/40 OK. PR CI(run 58, Windows 고친 커밋): lint·server-tests 3.10~3.14·macOS·**Windows**·recipe-tests-bpy 모두 초록.
- 막힌 것: 없음. 라벨 만들기·Scorecard 첫 실행·stale 작업은 병합 뒤 GitHub 에서만 확인 가능(클라우드는 라벨·설정을 바꾸지 않음).
- PR: 열려 있는 claude/cloud-work → main #13 에 이번 커밋이 함께 올라감(본문에 이번 회차 목록 추가).
- Mac에서 확인할 것:
  1. 맨 위 명령 3줄
  2. 병합 뒤 `docs/maintenance.md` 의 `gh label create … --force` 8줄을 저장소 폴더에서 돌려 라벨 만들기
  3. 병합 뒤 Actions 에서 scorecard 작업(main 푸시로 자동 실행)이 초록인지·README Scorecard 배지에 점수가 뜨는지, needs-info 작업을 Run workflow 로 한 번 돌려 초록인지

## 2026-10-09 (2회차)

- 한 일: `latest.md`(10/1) FAIL 2건(GIF 링크·버튼 이름)은 10/2 회차에 고쳐 main 에 있음을 다시 확인 → 백로그로 진행. main 은 앞서 있지 않았음. 백로그 4개 완료 → 남은 항목이 2개라 새 항목 5개 추가(파이썬 3.14·needs-info 자동 닫기·Scorecard·도구 예시 빠짐없이·doctor `--json`).
  1. **`scripts/bpy_tests.sh`** — 블렌더 앱 없이 bpy 5.0.1(Python 3.11)로 레시피 시험. 개발용 `.venv` 와 따로 `.venv-bpy`, libEGL 이 없으면 CI 와 같은 apt 명령을 알려 줌. 판·apt 패키지가 ci.yml 과 같은지 시험 2개. **이번 회차부터 클라우드도 레시피 시험을 돌림.**
  2. **Metadata-Version 2.5 확인** — twine 7.0.0(2026-07-27)부터 2.5 업로드 지원, PyPI 도 받음 → hatchling 판은 묶지 않음. `release_check.py --dist` 에 Metadata-Version(2.1~2.5) 칸, CI 에 `uvx twine@7.0.0 check dist/*`, registry.md 순서 갱신. 시험 4개.
  3. **최저·최고 파이썬 판 한 시험** — 분류자 기준으로 requires-python·ruff target-version·uv.lock·CI 행렬·SUPPORT·README 배지·architecture·maintenance 한/영. 어긋난 곳을 모두 한 번에 알려 줌. maintenance.md 에 판 정리 순서.
  4. **기능 요청 YAML 폼** — 필수 칸 3개(원하는 결과·예시 명령·대신 쓰는 방법), `.md` 지움, SUPPORT 링크 고침. 버그·기능 폼을 같은 시험으로.
- 돌린 시험: `uvx ruff@0.15.20 check .` 통과. `uv run pytest -q`(블렌더 없음) → **573 통과, 34 건너뜀**. CI 서버 명령 3.10(568 통과, 5 건너뜀)·3.13(573 통과), 커버리지 99.35%(하한 95%). **`scripts/bpy_tests.sh` → 601 통과, 6 건너뜀**(유체 `app_only` 5개·실제 캐릭터 파일 1개 — 블렌더 앱·개인 파일 필요). `uv build` → `release_check.py --dist` 22개 OK, `twine@7.0.0 check` 휠·sdist PASSED. `uv lock --check` 통과.
- PR: 열려 있는 claude/cloud-work → main #13 에 이번 커밋이 함께 올라감(본문에 이번 회차 목록 추가).
- Mac에서 확인할 것:
  1. `uv run pytest -q` (블렌더 앱으로 전체 통과)
  2. `uv build && uvx twine@7.0.0 check dist/*` (둘 다 PASSED)
  3. 병합 뒤 New issue 화면에 "기능 요청 / Feature request" 폼과 필수 칸(*)이 보이는지

## 2026-10-09

- 한 일: `latest.md`(10/1) FAIL 2건(GIF 링크·버튼 이름)은 10/2 회차에 고쳐 main 에 있음을 다시 확인 → 백로그로 진행. main 은 앞서 있지 않았음. 백로그 4개 완료 → 남은 항목이 1개라 새 항목 5개 추가.
  1. **CI 시험 목록 자동화** — `pytest -q tests --ignore=…`(블렌더 전용 레시피 시험 5개 파일만 뺌). 새 시험 파일이 저절로 CI 에 들어감. CONTRIBUTING 한/영 커버리지 명령도 같은 줄로(전에는 CI 와 달랐음). 시험 2개.
  2. **커버리지 하한 95%** — `--cov-fail-under=95`. CONTRIBUTING 한/영 수치와 일치 시험.
  3. **CI 패키징 점검** — `release_check.py --dist dist`: 휠·sdist 의 판·Project-URL·License-Expression·마크다운 README·`mcp-name`. 판·"미출시" 점검은 빼서 출시 전 PR 에서도 통과. ci.yml 의 `uv build` 다음 줄. 시험 8개.
  4. **`docs/maintenance.md`(한/영)** — 이슈 분류·dependabot 처리(메이저 판은 변경 기록 확인)·판 번호·출시 주기·파이썬 EOL(3.10 은 2026-10)·블렌더 LTS 정리. README·SUPPORT 링크. 시험 4개.
- 돌린 시험: `uvx ruff@0.15.20 check .` 통과. `uv run pytest -q`(Python 3.11) → **564 통과, 34 건너뜀**(블렌더 없음). 새 CI 명령을 3.10(559 통과, 5 건너뜀 — tomllib)·3.13(564 통과) + 하한 → 99.35%. 실제 `uv build` 결과로 `--dist` 20개 OK. `uv lock --check` 통과. 못 돌린 것: 레시피 시험 34개(블렌더 필요 — 레시피 파일은 안 건드림).
- 발견: hatchling 이 **Metadata-Version 2.5** 로 빌드해 `uvx twine@6.2.0 check` 가 거부함(그래서 CI 에 twine 은 넣지 않음). 출시 전에 PyPI·`uv publish` 가 받는지 확인 필요 → 새 백로그 첫 항목.
- PR: 열려 있는 claude/cloud-work → main #13 에 이번 커밋이 함께 올라감(본문에 이번 회차 목록 추가).
- Mac에서 확인할 것:
  1. `uv run pytest -q` (블렌더 앱으로 전체 통과)
  2. `uv build && uv run python scripts/release_check.py --dist dist` (20개 OK)
  3. 병합 뒤 Actions 의 server-tests 에 "Required test coverage of 95% reached" 가 찍히는지

## 2026-10-08 (2회차)

- 한 일: `latest.md`(10/1) FAIL 2건(GIF 링크·버튼 이름)은 10/2 회차에 고쳐 main 에 있음을 다시 확인 → 백로그로 진행. main 은 앞서 있지 않았음. 백로그 4개 완료 → 남은 항목이 1개 이하라 새 항목 5개 추가.
  1. **`CITATION.cff`** — GitHub "Cite this repository". `uvx cffconvert --validate` 통과. 출시 때 올릴 버전이 **네 곳**이 됨(`release_check.py`·CHANGELOG 출시 순서·registry.md 갱신). 시험 2개 + release_check 판 어긋남 칸.
  2. **CHANGELOG 0.7.0 영어 요약** — *Fixes*·*Tests and CI*·*Docs*. 시험: 미출시 절마다 요약이 있고 한글이 없는지, 한국어 상세보다 앞인지.
  3. **server.py 실패 갈래 시험** — bridge 는 이미 100%. 도구 29개 × 한/영 연결 실패 문장, `ping_blender`·`doctor` 도구 등. **server 94% → 99%**, 서버 쪽 전체 99%.
  4. **CONTRIBUTING "처음 기여하기 좋은 일"(한/영)** — 작은 일 4가지·파일·시험 명령 표, `good first issue`·`needs-info` 뜻. 시험 3개(파일·`-k` 시험 존재, 라벨이 SUPPORT 와 같은지).
- 돌린 시험: `uvx ruff@0.15.20 check .` 통과. `uv run pytest -q`(Python 3.11) → **546 통과, 34 건너뜀**(블렌더 없음). CI 서버 시험 목록을 3.10(544 통과, 5 건너뜀 — tomllib)·3.13(549 통과) + `--cov` → 99%. `uv lock --check` 통과. 못 돌린 것: 레시피 시험 34개(블렌더 필요 — 레시피 파일은 안 건드림).
- 참고: dependabot 이 SHA 고정 액션을 SHA·판 주석 함께 올리는 것 확인(checkout v4.4.0 → v7.0.1, setup-uv v5.4.2 → v10.2.0 브랜치). 메이저 판이라 Mac 에서 변경 기록을 보고 병합할 것(새 백로그 `docs/maintenance.md` 항목에 처리 순서를 적을 예정).
- PR: 열려 있는 claude/cloud-work → main #13 에 이번 커밋이 함께 올라감(본문에 이번 회차 목록 추가).
- Mac에서 확인할 것:
  1. `uv run pytest -q` (블렌더 앱으로 전체 통과)
  2. `uv run python scripts/release_check.py` (CITATION.cff 줄 OK, FAIL 은 "판 다름"·"미출시" 2줄이 정상)
  3. 병합 뒤 GitHub 저장소 오른쪽에 "Cite this repository" 가 뜨는지

## 2026-10-08

- 한 일: `latest.md`(10/1) FAIL 2건(GIF 링크·버튼 이름)은 10/2 회차에 고쳐 main 에 있음을 다시 확인 → 백로그로 진행. main 은 앞서 있지 않았음(병합할 것 없음). PR #13 이 아직 열려 있어 이번 커밋도 그 PR 에 쌓임. 남은 백로그 3개 완료 → 0개가 되어 새 항목 5개 추가, 그중 1개까지 모두 4개.
  1. **버그 신고 YAML 폼** `.github/ISSUE_TEMPLATE/bug_report.yml`(한/영) — 필수 칸 6개(doctor 출력·블렌더 판·OS·MCP 클라이언트·재현 명령·결과). `.md` 양식은 지움(둘 다 있으면 두 개 보임), troubleshooting.md 의 `template=bug_report.md` 링크 2곳 고침. 시험 6개(PyYAML 이 없어 정규식으로 읽음, 로컬에서 PyYAML 로 한 번 파싱 확인).
  2. **`SUPPORT.md`(한/영)** — 신고 경로 표, 응답 목표(보안·버그 7일 = SECURITY.md, 질문·기능 14일), 지원 판 표(블렌더 5.2 LTS·bpy 5.0.1 CI 용·4.x 미확인, 파이썬 3.10~3.13, 0.6.x). README 한/영에서 링크. 시험 4개(분류자·CI 행렬·README·app-tests·bpy 판·SECURITY 와 일치).
  3. **`docs/recipes.md` 영어 절** — 같은 5개 예시·수치. README 영어 절 링크를 `#english` 로. 시험 4개: 한/영 도구 호출 일치, 실제 도구·인자, 영어 절 한글 없음, **예시 인자가 서버 목록·범위 검사를 통과하는지**.
  4. **CI 파이썬 행렬에 3.11** — 분류자 모든 판을 돌림. 시험을 "양 끝" → "모든 판"으로. SUPPORT·architecture·CHANGELOG·CONTRIBUTING(커버리지 95%) 갱신.
- 돌린 시험: `uvx ruff@0.15.20 check .` 통과. `uv run pytest -q`(Python 3.11) → **478 통과, 34 건너뜀**(블렌더 없음). CI 서버 시험 목록을 3.10(473 통과, 5 건너뜀 — tomllib)·3.11·3.13(478 통과) + `--cov` → 95~96%. `uv lock --check` 통과. 못 돌린 것: 레시피 시험 34개(블렌더 필요 — 레시피 파일은 안 건드림). YAML 폼이 GitHub 이슈 화면에서 실제로 보이는지는 main 병합 뒤에만 확인 가능.
- PR: 열려 있는 claude/cloud-work → main #13 에 이번 커밋이 함께 올라감(본문에 이번 회차 목록 추가).
- 참고: SUPPORT.md 가 `needs-info` 라벨을 말하므로 저장소에 그 라벨이 없으면 만들어 두면 좋음(클라우드에서는 라벨을 만들지 않았음).
- Mac에서 확인할 것:
  1. `uv run pytest -q` (블렌더 앱으로 전체 통과)
  2. 병합 뒤 GitHub 에서 New issue → "버그 / Bug report" 폼에 필수 칸(*)이 보이는지
  3. 병합 뒤 Actions 의 server-tests 에 3.11 이 생겼고 초록인지

## 2026-10-07 (2회차)

- 한 일: `latest.md`(10/1) FAIL 2건(README GIF 링크·버튼 이름)은 10/2 회차에 이미 고쳐 main 에 있음을 다시 확인 → 백로그로 진행. 시작 때 main(PR #10 병합분)을 받아 옴(빨리감기). 백로그 4개 완료, 남은 항목 3개라 새 항목은 추가하지 않음.
  1. **도구 설명 ↔ `server.CHOICES` 일치** — 고정 목록 인자 23개를 `이름: a / b / c` 줄로 통일(explode 의 material·pattern·dust·glue, destroy 의 dust, render_video 의 quality 등이 설명에 없었음). `make_demo_building` 의 style·ground 도 서버 검사에 넣음. 시험: 설명과 목록 일치, 새 도구 누락 방지.
  2. **숫자 인자 범위 미리 검사** — 레시피는 범위 밖 값을 조용히 잘라 썼음(resolution=2000 → 320). `server.RANGES`(pieces·resolution·frames·focus·samples) + `check_ranges`, 범위·권장 값을 한/영으로. `tests/test_server_ranges.py` 32개(레시피의 max/min 을 ast 로 비교). **동작 변화:** 예전에 조용히 잘리던 값(frames=6 등)이 이제 오류.
  3. **`docs/architecture.md`(한/영)** — 호출 경로·파일 역할·레시피 규칙·시험 경로. README·CONTRIBUTING 에서 링크, CONTRIBUTING 의 없는 파일 `splash.py` → `water.py`. 시험 4개.
  4. **`scripts/release_check.py`** — 버전 세 곳·CHANGELOG 맨 위 절(판·날짜·중복)·mcp-name, `--build` 면 휠 METADATA. 지금은 "판 다름"·"미출시" 2줄만 FAIL(정상). 출시 순서·registry.md 에 단계 추가. 시험 11개.
- 돌린 시험: `uvx ruff@0.15.20 check .` 통과. `uv run pytest -q`(Python 3.13) → **466 통과, 34 건너뜀**(블렌더 없음). CI 서버 시험 목록을 Python 3.10 + `--cov` → 461 통과, 5 건너뜀(tomllib), 커버리지 94%(server 93%). `uv lock --check` 통과, `release_check.py --build` 로 휠 빌드 확인. 못 돌린 것: 레시피 시험 34개(블렌더 필요 — 레시피 파일은 안 건드림, 레시피 시험은 서버를 거치지 않아 새 범위 검사의 영향 없음).
- PR: claude/cloud-work → main #13 을 새로 열었음(Mac 총괄이 확인 후 병합).
- Mac에서 확인할 것:
  1. `uv run pytest -q` (블렌더 앱으로 전체 통과)
  2. `BLENDER_FX_PORT=1 uv run python -c "from blender_fx_mcp import server; print(server.water(resolution=2000))"` (블렌더 없이 범위 오류)
  3. `uv run python scripts/release_check.py --build` (지금은 FAIL 2줄·종료 코드 1이 정상)

## 2026-10-07

- 한 일: `latest.md`(10/1)의 FAIL 2건은 10/2 회차에 이미 고쳐 main에 병합됨 → 백로그로 진행. 시작할 때 main(PR #9 병합분)을 받아 옴(빨리감기). 백로그 4개 완료 → 남은 항목이 2개라 새 항목 5개 추가.
  1. **`headless.py` 실패 갈래 시험** `tests/test_headless.py` 16개(`/bin/sh` 가짜 블렌더). 커버리지 56% → 99%.
  2. **액션 SHA 고정** — checkout v4.4.0(11d5960…), setup-uv v5.4.2(d4b2f3b…). 태그가 가리키는 커밋은 `git ls-remote` 로 확인. 시험 `test_workflow_actions_pinned_to_sha`.
  3. **고정 목록 인자 미리 검사** — `server.CHOICES` + `check_choices`(`run_recipe` 맨 앞). 가능한 값과 가장 가까운 값을 한/영으로 알려 줌. `tests/test_server_choices.py` 33개(레시피 상수와 ast로 비교). 동작 변화: `interior`·`quality` 오타가 이제 오류로 나옴.
  4. **`doctor.py` 실패 갈래 시험** `tests/test_doctor.py` 21개. 80% → 99%. `--version` 출력이 비면 "list index out of range"로 보이던 것을 고침.
  - CI 서버 시험 목록에 새 시험 파일 3개 추가. CHANGELOG·CONTRIBUTING 갱신(서버 쪽 커버리지 84% → **94%**, 시험 421개).
- 돌린 시험: `uvx ruff@0.15.20 check .` 통과. `uv run pytest -q`(Python 3.13) → **387 통과, 34 건너뜀**(블렌더 없음). CI 서버 시험 목록을 Python 3.10 으로 → 383 통과, 4 건너뜀(tomllib). `--cov` 결과 94%(bridge 96%: 58–60줄은 이번 변경 전에도 안 덮였음. 10/6 기록의 "100%"는 잘못 적은 것으로 보임). `uv lock --check`·`uv build` 통과. 못 돌린 것: 레시피 시험 34개(블렌더 필요 — 레시피 파일은 안 건드림). dependabot 이 SHA 고정 액션을 실제로 올리는지는 다음 주 갱신 PR 이 나와야 확인 가능.
- PR: claude/cloud-work → main #10 을 새로 열었음(Mac 총괄이 확인 후 병합). dependabot PR(checkout v7·setup-uv v7)은 이번 SHA 고정과 겹치므로, #10 병합 뒤 dependabot 이 다시 만들게 두는 것이 낫다.
- Mac에서 확인할 것:
  1. `uv run pytest -q` (블렌더 앱으로 전체 통과, 특히 test_headless·test_doctor 가 macOS /bin/sh 에서)
  2. `BLENDER_FX_PORT=1 uv run python -c "from blender_fx_mcp import server; print(server.destroy('B', material='concret'))"` (블렌더 없이 "혹시 'concrete'")
  3. 병합 뒤 GitHub Actions 에서 SHA 고정 액션으로 ci 가 초록인지

## 2026-10-06 (2회차)

- 한 일: `latest.md`(10/1) FAIL 2건은 10/2 회차에 이미 고쳐 main 에 병합됨 → 백로그로 진행. 시작 때 main(PR #8 병합분)을 받아 옴(빨리감기). 백로그 4개 완료 → 남은 항목 1개라 새 항목 5개 추가.
  1. **워크플로 최소 권한** — `ci.yml`·`app-tests.yml` 최상위 `permissions: contents: read`. 시험: 모든 워크플로에 있는지, write 없는지.
  2. **MCP 도구 annotations** — 32개 모두(READ_ONLY 5·SETTING 7·ADDITIVE 15·DESTRUCTIVE 5, `openWorldHint=false`). 백로그에 적힌 `reset_scene` 등은 없는 이름이라 `restore`·`clear_caches`·`reset_destroy`·`export_model`·`snapshot` 을 destructive 로. 시험 5종. 이 변경으로 README 도구 표 시험의 정규식이 도구를 못 찾게 돼 함께 고침.
  3. **도구 성공 갈래 시험** `tests/test_server_tools.py` — 가짜 레시피 결과로 도구 29개를 한/영 끝까지 호출. 커버리지 **server 49% → 88%, 전체 59% → 84%**(CONTRIBUTING 갱신, CI 목록에 추가).
  4. **`docs/troubleshooting.md`(한/영)** — 오류 문장 8묶음별 해결법. 연결·시간 초과 오류와 doctor 의 확인 필요 줄에 링크(절 제목 영어 → ASCII 앵커). `tests/test_troubleshooting.py`(문장 25개가 소스·문서 양쪽에 있는지, 링크 절 존재). CI 목록에 추가.
  - CHANGELOG 미출시 절 반영, 시험 수 348개(블렌더 없이 314개).
- 돌린 시험: `uvx ruff@0.15.20 check .` 통과. `uv run pytest -q`(Python 3.13) → **314 통과, 34 건너뜀**(블렌더 없음). CI 서버 시험 목록을 Python 3.10 + `--cov` 로 → 310 통과, 4 건너뜀, 커버리지 84%. `uv lock --check`·`uv build` 통과. 못 돌린 것: 레시피 시험 34개(블렌더 필요 — 이번 회차는 레시피를 건드리지 않아 bpy 로도 안 돌림). 오류 문장 끝 링크는 GitHub 에서 앵커가 실제로 열리는지 브라우저로 확인 못 함(병합 전이라 main 에 문서가 없음).
- PR: claude/cloud-work → main #9 를 새로 열었음(Mac 총괄이 확인 후 병합).
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
