# 보안 정책 / Security policy

## 지원하는 판 / Supported versions

| 판 / Version | 보안 수정 / Security fixes |
|---|---|
| 0.6.x (최신 / latest) | 예 / yes |
| 그 이전 / older | 아니오 — 최신 판으로 올려 주세요 / no, please upgrade |

## 구조상 알아 둘 위험 / Risks by design

이 서버는 **파이썬 코드를 블렌더에 보내 실행하는 구조**입니다.

- blender-fx-mcp 는 레시피(파이썬)를 `localhost:9876` 소켓으로 블렌더 안 수신기 애드온([blender-mcp](https://github.com/ahujasid/blender-mcp))에 보내고, 수신기는 그 코드를 **블렌더 권한 그대로**(= 사용자 계정 권한) 실행합니다.
- 수신기에는 인증이 없습니다. 9876 포트에 접속할 수 있는 프로그램은 누구든 블렌더 안에서 임의의 파이썬을 실행할 수 있습니다. 그래서:
  - `BLENDER_FX_HOST` 를 기본값(`localhost`) 그대로 두세요. 다른 컴퓨터의 블렌더에 붙이려면 SSH 터널을 쓰고, 수신기 포트를 공유기·방화벽 밖으로 열지 마세요.
  - 쓰지 않을 때는 블렌더 BlenderMCP 탭에서 수신기를 끄세요.
- AI는 코드를 직접 짜지 않고 도구와 값만 고릅니다. 값은 `PARAMS = {...}` 로 `repr` 되어 레시피 앞에 붙으므로 문자열 값이 코드로 해석되지 않습니다. 이 경계를 깨는 입력을 찾으면 보안 문제로 신고해 주세요.
- `import_model`·`export_model`·`save_blend`·`render_*` 는 AI가 고른 경로의 파일을 읽고 씁니다(내 계정이 접근할 수 있는 곳이면 어디든). 클라이언트에서 도구 실행 승인을 켜 두면 경로를 확인할 수 있습니다.
- 모르는 출처의 `.blend` 파일은 열지 마세요. `.blend` 에는 자동 실행 스크립트가 들어 있을 수 있습니다(블렌더 설정 "Auto Run Python Scripts" 를 끈 채로 두세요).

**English summary.** blender-fx-mcp sends Python recipes to the blender-mcp receiver add-on on `localhost:9876`, which runs them inside Blender with your user's permissions and **without authentication**. Keep `BLENDER_FX_HOST=localhost`, never expose port 9876 beyond your machine (use an SSH tunnel for remote Blender), and turn the receiver off when not in use. Tool arguments are passed as a `repr`'d `PARAMS` dict, never as code; any input that escapes that boundary is a security bug. File tools (`import_model`, `export_model`, `save_blend`, renders) read/write paths chosen by the AI, so keep tool-call approval on in your client if that matters to you.

## 공급망 조치 / Supply-chain measures

저장소와 CI 가 의존성·워크플로를 어떻게 지키는지 한곳에 모았습니다. 표의 시험이 실패하면 CI 가 빨개집니다.
How the repository and CI protect dependencies and workflows. Each row is enforced by the listed test or job.

| 조치 / Measure | 어디 / Where | 확인 / Enforced by |
|---|---|---|
| 외부 액션을 커밋 SHA + 판 주석으로 고정 / Actions pinned to a commit SHA with a version comment | `.github/workflows/*.yml` | `test_workflow_actions_pinned_to_sha` |
| 기본 토큰 읽기 전용, 쓰기 권한은 작업 단위 허용 목록만 / Read-only default token; write scopes only per job, from an allow list | `.github/workflows/*.yml` | `test_workflow_top_level_permissions_read_only` |
| `pull_request_target` 작업은 PR 코드를 체크아웃하지 않음 / `pull_request_target` jobs never check out PR code | `.github/workflows/greet.yml` | `test_greet_workflow_is_safe_and_links_exist` |
| 의존성은 해시가 적힌 잠금 파일로만 설치 / Dependencies installed only from the hash-pinned lock file | `uv.lock`, `uv sync --locked` | `test_ci_installs_from_the_lock_file` |
| 의존성·액션 판을 주 1회 갱신 PR 로 / Weekly update PRs for dependencies and actions | `.github/dependabot.yml` | `test_dependabot_watches_uv_and_actions` |
| 의존성 라이선스가 허용 목록 안 / Dependency licenses within a permissive allow list | `scripts/license_check.py`, `docs/third-party-licenses.md` | CI `lint` 작업 / job |
| OpenSSF Scorecard 점수 공개 / OpenSSF Scorecard results published | `.github/workflows/scorecard.yml` | `test_scorecard_workflow_and_badge` |
| 휠·sdist 메타데이터 점검 / Wheel and sdist metadata checked before release | `scripts/release_check.py --dist`, `twine check` | CI `server-tests` 작업 / job |

## 신고하는 법 / Reporting a vulnerability

**공개 이슈에 쓰지 마세요.** GitHub 의 비공개 신고 양식을 써 주세요:
<https://github.com/choisam4u-creator/blender-fx-mcp/security/advisories/new>

Please do **not** open a public issue. Use GitHub private vulnerability reporting at the link above.

적어 주실 것 / Please include:

- 재현 순서(어떤 도구에 어떤 값을 넘겼나) / steps to reproduce (tool and arguments)
- `blender-fx-doctor` 결과(첫 줄에 판 번호) / `blender-fx-doctor` output (first line shows the version)
- 영향(무엇을 할 수 있게 되나) / impact

1인 관리 프로젝트라 첫 답은 7일 안을 목표로 합니다. 수정이 나오면 CHANGELOG 와 GitHub 보안 권고에 신고자 이름을 (원하시면) 함께 적습니다.
This is a single-maintainer project; we aim to reply within 7 days and credit reporters (if they wish) in the CHANGELOG and the advisory.

수신기 애드온 자체의 문제는 [blender-mcp](https://github.com/ahujasid/blender-mcp) 저장소에도 알려 주세요.
Issues in the receiver add-on itself should also be reported to the blender-mcp project.
