# 클라이언트별 연결 설정 / Client config examples

모두 같은 명령(`uvx --from git+https://github.com/choisam4u-creator/blender-fx-mcp blender-fx-mcp`)을 띄웁니다.
`BLENDER_FX_LANG` 은 `ko`(기본) 또는 `en`. 다른 환경변수는 저장소 README 의 표를 보세요.
등록 뒤 앱을 완전히 껐다 켜야 도구가 보입니다.

All examples launch the same command. Set `BLENDER_FX_LANG` to `en` for English messages. Fully restart the app after editing.

| 클라이언트 / Client | 파일 / File | 붙여 넣을 곳 / Where it goes |
|---|---|---|
| Claude Code | (명령 한 줄 / one command) | `claude mcp add -s user blender-fx -e BLENDER_FX_LANG=en -- uvx --from git+https://github.com/choisam4u-creator/blender-fx-mcp blender-fx-mcp` |
| Claude Desktop | [`claude_desktop_config.json`](claude_desktop_config.json) | macOS `~/Library/Application Support/Claude/claude_desktop_config.json`, Windows `%APPDATA%\Claude\claude_desktop_config.json` |
| Cursor | [`cursor-mcp.json`](cursor-mcp.json) | 프로젝트의 `.cursor/mcp.json` 또는 전역 `~/.cursor/mcp.json` / project `.cursor/mcp.json` or global `~/.cursor/mcp.json` |
| Codex | [`codex-config.toml`](codex-config.toml) | `~/.codex/config.toml` |

Claude Desktop·Cursor 같은 창 앱은 터미널의 PATH 를 물려받지 않아(특히 macOS 의 brew) `uvx` 를 못 찾을 수 있습니다.
도구가 안 보이면 `command` 를 `which uvx`(Windows `where uvx`)가 알려 준 전체 경로로 바꿉니다. `blender-fx-doctor` 의 uv 줄과 등록 안내에도 그 경로가 나옵니다.
Desktop apps such as Claude Desktop and Cursor do not inherit your terminal PATH (notably Homebrew on macOS), so they may not find `uvx`.
If the tools do not appear, set `command` to the full path printed by `which uvx` (`where uvx` on Windows); `blender-fx-doctor` shows it too.

이미 다른 서버가 등록돼 있으면 `mcpServers` 안에 `"blender-fx": {...}` 한 덩어리만 더합니다.
If other servers are already configured, add only the `"blender-fx": {...}` entry inside `mcpServers`.

로컬 폴더에서 개발 중이면 `command` 를 `uv`, `args` 를 `["--directory", "<저장소 절대 경로>", "run", "blender-fx-mcp"]` 로 바꿉니다.
For a local checkout use `uv` with `["--directory", "<absolute path to the repo>", "run", "blender-fx-mcp"]`.

## 직접 짜는 클라이언트 / Writing your own client

[`list_tools.py`](list_tools.py) 는 공식 `mcp` 파이썬 클라이언트로 서버를 stdio 로 띄워 도구 목록을 받고 `ping_blender` 를 부릅니다.
블렌더가 꺼져 있어도 돌며, 그때는 연결 실패 문장이 나옵니다. 자기 클라이언트·자동화 스크립트의 출발점으로 복사해 쓰세요.

[`list_tools.py`](list_tools.py) starts the server over stdio with the official `mcp` Python client, lists the tools and
calls `ping_blender`. It runs without Blender (you then get the connection failure message). Copy it as a starting point.

```sh
uv run python examples/list_tools.py
BLENDER_FX_LANG=en uv run python examples/list_tools.py uvx --from git+https://github.com/choisam4u-creator/blender-fx-mcp blender-fx-mcp
```

## 터미널에서 첫 렌더까지 / First render from the terminal

[`first_render.py`](first_render.py) 는 같은 방식으로 서버를 띄워 `ping_blender` → `make_demo_building` → `destroy` → `render_preview` 를
차례로 부르고 미리보기 PNG 경로를 출력합니다. MCP 클라이언트를 붙이기 전에 블렌더 쪽이 첫 렌더까지 되는지 확인할 때 씁니다.
블렌더를 켜고 BlenderMCP 탭에서 Connect 를 누른 뒤 돌리세요. 연결이 안 되면 원인별 다음 할 일을 출력하고 종료 코드 2,
도구가 실패하면 그 오류 문장을 출력하고 종료 코드 1 입니다. 장면에 `Building` 이 하나 더해지지만,
시작 전에 지금 장면을 스냅샷 `first_render_before` 로 저장하므로 AI 에게 `restore first_render_before`(또는 `/undo_last`)로 돌아갈 수 있습니다.

[`first_render.py`](first_render.py) starts the server the same way, calls `ping_blender` → `make_demo_building` → `destroy` →
`render_preview` and prints the preview PNG paths, so you can check Blender renders before attaching an MCP client.
Open Blender and click Connect first. Without a connection it prints the next step and exits with 2; a failing tool exits with 1.
Your scene is saved first as snapshot `first_render_before`, so `restore first_render_before` (or `/undo_last`) brings it back.

```sh
uv run python examples/first_render.py
```
