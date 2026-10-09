# 지원 / Support

## 어디로 보내나 / Where to go

| 무엇 / What | 어디로 / Where |
|---|---|
| 오류 문장이 떴다 / An error message | 먼저 [docs/troubleshooting.md](docs/troubleshooting.md) — 오류 문장별 해결법 / fixes per error message |
| 어떻게 시키나 / How do I ask for X | [docs/recipes.md](docs/recipes.md)(자연어 명령 예시와 결과 수치 / example prompts and results), README "도구" 절 / tool table |
| 버그 / Bug | [버그 신고 양식 / Bug report form](https://github.com/choisam4u-creator/blender-fx-mcp/issues/new?template=bug_report.yml) — `blender-fx-doctor` 출력 필수 / doctor output required |
| 새 효과·도구 제안 / Feature idea | [기능 요청 양식 / Feature request](https://github.com/choisam4u-creator/blender-fx-mcp/issues/new?template=feature_request.yml) |
| 질문 / Question | 이슈를 열고 제목 앞에 `[질문]` / `[question]` 을 붙여 주세요 / open an issue with a `[question]` prefix |
| 보안 문제 / Security issue | **공개 이슈 금지.** [SECURITY.md](SECURITY.md) 의 비공개 신고 / never in a public issue; report privately |
| 수신기 애드온 자체의 문제 / Receiver add-on bug | [blender-mcp](https://github.com/ahujasid/blender-mcp) 저장소 / upstream project |

## 응답 목표 / Response targets

1인 관리 프로젝트라 약속이 아니라 목표입니다. / Single-maintainer project: these are goals, not guarantees.

| 종류 / Kind | 첫 답 / First reply |
|---|---|
| 보안 신고 / Security report | 7일 안 / within 7 days |
| 버그 / Bug | 7일 안 / within 7 days |
| 질문·기능 요청 / Question, feature | 14일 안 / within 14 days |

재현 정보(doctor 출력·블렌더 판·불린 도구와 인자)가 없는 버그는 정보를 받을 때까지 `needs-info` 로 둡니다. 30일 동안 답이 없으면 닫을 수 있고, 정보를 주시면 다시 엽니다.
Bugs without repro info (doctor output, Blender version, tool and arguments) wait as `needs-info`; they may be closed after 30 days without a reply and reopened when the info arrives.

## 지원하는 판 / Supported versions

| 대상 / Component | 판 / Version | 상태 / Status |
|---|---|---|
| 블렌더 / Blender | 5.2 LTS | 지원 — 실제 앱으로 전체 시험 / supported, full test suite on the real app |
| 블렌더 / Blender | 5.0 (`bpy` 5.0.1 모듈 / module) | CI 의 레시피 시험용(유체 제외) / CI recipe tests only, fluids excluded |
| 블렌더 / Blender | 4.x 이하 / older | 확인 안 함 / untested |
| 파이썬 / Python | 3.10, 3.11, 3.12, 3.13, 3.14 | 지원 — CI 가 3.10·3.11·3.12·3.13·3.14 를 모두 돌림 / supported, CI runs 3.10, 3.11, 3.12, 3.13, 3.14 |
| 운영체제 / OS | macOS·Linux·Windows | 지원 — CI 가 서버 시험을 macOS, Linux, Windows 에서 돌림(레시피 시험은 Linux bpy·Mac 앱) / supported, CI runs server tests on macOS, Linux, Windows (recipe tests: Linux bpy, Mac app) |
| blender-fx-mcp | 0.6.x (최신 / latest) | 버그·보안 수정 / bug and security fixes |

판 정책은 [SECURITY.md](SECURITY.md) 와 같습니다. 이 표가 `pyproject.toml`·CI·README 와 어긋나면 시험이 실패합니다.
Kept in sync with SECURITY.md; tests fail if this table drifts from `pyproject.toml`, CI or the README.

이슈 분류 순서·판 정리 기준은 [docs/maintenance.md](docs/maintenance.md). / Triage order and version-dropping rules: [docs/maintenance.md](docs/maintenance.md).
