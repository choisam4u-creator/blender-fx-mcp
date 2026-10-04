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
