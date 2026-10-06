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

이미 다른 서버가 등록돼 있으면 `mcpServers` 안에 `"blender-fx": {...}` 한 덩어리만 더합니다.
If other servers are already configured, add only the `"blender-fx": {...}` entry inside `mcpServers`.

로컬 폴더에서 개발 중이면 `command` 를 `uv`, `args` 를 `["--directory", "<저장소 절대 경로>", "run", "blender-fx-mcp"]` 로 바꿉니다.
For a local checkout use `uv` with `["--directory", "<absolute path to the repo>", "run", "blender-fx-mcp"]`.
