# 문제 해결 / Troubleshooting

AI가 보여 준 오류 문장을 아래에서 찾으세요(`Ctrl+F` 로 문장 앞부분 검색). 먼저 `blender-fx-doctor` 를 돌리면 대부분 원인이 한 줄로 나옵니다.
Search this page for the error sentence the AI showed you. Running `blender-fx-doctor` first usually names the cause.

```bash
uvx --from git+https://github.com/choisam4u-creator/blender-fx-mcp blender-fx-doctor
```

여기 없는 문제는 [버그 신고](https://github.com/choisam4u-creator/blender-fx-mcp/issues/new?template=bug_report.yml)에 doctor 출력과 함께 올려 주세요.
If your problem is not here, open a [bug report](https://github.com/choisam4u-creator/blender-fx-mcp/issues/new?template=bug_report.yml) with the doctor output.
`blender-fx-doctor --json` 은 같은 결과를 JSON 으로 냅니다(항목 id: `python`·`blender-fx-mcp`·`mcp`·`uv`·`blender`·`addon`·`connection`·`client`·`output`), `clients` 에는 등록이 보인 MCP 클라이언트가 들어갑니다.
`blender-fx-doctor --json` prints the same result as JSON, with language-independent check ids; `clients` lists the MCP clients where it is registered.

---

## Tools not visible in the client

**클라이언트에 도구가 안 보임**

증상: AI에게 시켜도 `make_demo_building` 같은 도구를 모른다고 하거나, `/` 메뉴에 `first_demo` 가 없습니다. 블렌더 연결 전 단계 문제입니다.
doctor 의 "MCP 클라이언트 등록" 줄이 `-` 이면 아래 1번부터, 클라이언트 이름이 보이면 2번부터 합니다.

1. 등록을 확인합니다. Claude Code 는 `claude mcp list` 에 `blender-fx` 가 있어야 합니다. 없으면
   `claude mcp add -s user blender-fx -- uvx --from git+https://github.com/choisam4u-creator/blender-fx-mcp blender-fx-mcp`
2. 앱을 **완전히** 껐다 켭니다(창 닫기가 아니라 종료: macOS 는 `Cmd+Q`, Windows 는 트레이 아이콘에서 종료). Claude Code 는 새 세션을 엽니다.
3. 설정 파일을 직접 고쳤다면 위치와 JSON 문법을 확인합니다(쉼표 하나로 파일 전체가 무시됩니다).

| 클라이언트 | 설정 파일 |
|---|---|
| Claude Code | `~/.claude.json`(전체) 또는 프로젝트의 `.mcp.json` |
| Claude Desktop | macOS `~/Library/Application Support/Claude/claude_desktop_config.json`, Windows `%APPDATA%\Claude\claude_desktop_config.json` |
| Cursor | `~/.cursor/mcp.json` |
| Codex | `~/.codex/config.toml` |

4. 그래도 안 보이면 `uv` 가 앱의 PATH 에 없을 수 있습니다. 설정의 `uvx` 를 `which uvx`(Windows `where uvx`)가 알려 준 전체 경로로 바꿉니다.

Symptom: the AI does not know tools such as `make_demo_building`, or `first_demo` is missing from the `/` menu. This happens before any Blender connection.
If doctor's "MCP client registration" line shows `-`, start at step 1; if it names your client, start at step 2.
1. Check registration: `claude mcp list` must show `blender-fx` (otherwise run the `claude mcp add` line above).
2. Fully quit and reopen the app (`Cmd+Q` on macOS, quit from the tray on Windows); in Claude Code start a new session.
3. If you edited a config file by hand, check its location (table above) and JSON syntax; one stray comma makes the whole file ignored.
4. If the tools still do not appear, the app may not see `uv` on its PATH: replace `uvx` with the full path printed by `which uvx` (`where uvx` on Windows).

## Connection refused

**연결 거부**

> 블렌더에 연결할 수 없습니다(localhost:9876).
> Cannot connect to Blender (localhost:9876).

원인: 블렌더가 꺼져 있거나, 수신기 애드온(blender-mcp)이 아직 연결을 기다리지 않습니다.
오류 문장 뒤에는 원인을 좁힌 다음 한 단계가 붙습니다: 이 컴퓨터에서 애드온 파일을 못 찾으면 **설치부터**, 찾으면 **Connect**,
`BLENDER_FX_PORT` 를 바꿨으면 **포트 맞추기**(doctor 의 "수신기 애드온 파일" 줄과 같은 폴더를 봅니다).

1. 블렌더를 켭니다.
2. 3D 화면에서 `N` 키 → **BlenderMCP** 탭 → **Connect to MCP server** 를 누릅니다.
3. 탭이 안 보이면 Edit → Preferences → Add-ons 에서 blender-mcp 애드온을 켭니다(doctor 의 "수신기 애드온 파일" 줄 참고).
4. `BLENDER_FX_HOST`·`BLENDER_FX_PORT` 를 바꿨다면 애드온 패널의 포트와 같은지 확인합니다.

Cause: Blender is closed, or the receiver add-on is not listening. The error ends with one narrowed-down next step: install the
add-on if no add-on file is found on this computer, otherwise click Connect, and match the port if you changed `BLENDER_FX_PORT`. Open Blender, press `N` in the 3D view, open the
**BlenderMCP** tab and click **Connect to MCP server**. If the tab is missing, enable the blender-mcp add-on in
Edit → Preferences → Add-ons. If you changed `BLENDER_FX_HOST`/`BLENDER_FX_PORT`, match the port shown in the add-on panel.

## Timeout

**시간 초과**

> 블렌더가 600초 안에 응답하지 않았습니다(시간 초과).
> Blender did not respond within 600 s.

원인: 굽기(물·연기·조각 물리)나 렌더가 기다리는 시간보다 오래 걸렸거나, 블렌더가 멈췄습니다.

- 가볍게: `pieces`(조각 수), `frames`(프레임 수), `resolution`(물·연기 해상도)을 줄여 다시 시킵니다.
- 일부러 무거운 장면이면: MCP 설정의 환경변수 `BLENDER_FX_TIMEOUT`(초)을 크게(예: `3600`) 주고 MCP 서버를 다시 시작합니다.
  굽기·렌더 도구는 최소 1800초(`render_video` 3600초)를 기다리고, 이 값이 더 크면 따라 늘어납니다.
- 블렌더 창이 응답 없음이면 블렌더를 다시 켜고 `restore` 로 직전 스냅샷을 불러옵니다.

Cause: a bake or render took longer than the wait, or Blender froze. Lower `pieces`, `frames` or `resolution`;
for an intentionally heavy scene set `BLENDER_FX_TIMEOUT` (seconds, e.g. `3600`) in your MCP config and restart the server.
Bake and render tools wait at least 1800 s (`render_video` 3600 s) and grow with this value.
If Blender is frozen, restart it and `restore` the last snapshot.

## Empty response, Blender error

**빈 응답·블렌더 오류**

> 블렌더가 빈 응답을 보냈습니다.
> Blender sent an empty response.

수신기가 명령을 받다가 끊겼습니다. 다른 MCP 서버(예: blender-mcp 자체)를 같이 켜 두면 수신기가 하나라 서로 끊길 수 있습니다.
하나만 켜고, 블렌더에서 **Connect to MCP server** 를 다시 누릅니다.
The receiver dropped the request. Another MCP server sharing the same receiver (e.g. blender-mcp itself) can cut it off;
keep only one running and click **Connect to MCP server** again.

> 블렌더 오류: …
> Blender error: …

수신기가 코드를 실행하다 실패했습니다. 뒤에 붙은 메시지가 원인입니다. 레시피 오류(아래)가 아니라 이 문장이 나오면 버그일 가능성이 큽니다. 신고해 주세요.
The receiver failed while running code; the rest of the message is the cause. If you see this instead of a recipe error below, it is likely a bug — please report it.

## Port already in use

**포트 충돌**

증상: 애드온의 **Connect to MCP server** 를 눌러도 연결되지 않고, 블렌더 콘솔에 `Address already in use` 가 보입니다.
다른 프로그램(또는 다른 블렌더 창)이 9876 포트를 쓰고 있습니다.

- 블렌더 창을 하나만 켭니다.
- 그래도 안 되면 애드온 패널의 포트를 다른 값(예: `9877`)으로 바꾸고, MCP 설정에 `BLENDER_FX_PORT=9877` 을 주고 다시 시작합니다.
- 수신기는 인증이 없으므로 `BLENDER_FX_HOST` 는 `localhost` 로 둡니다([SECURITY.md](../SECURITY.md)).

Symptom: **Connect to MCP server** does nothing and the Blender console shows `Address already in use`. Another program
(or another Blender window) holds port 9876. Keep one Blender window open, or change the port in the add-on panel
(e.g. `9877`) and set `BLENDER_FX_PORT=9877` in your MCP config. Keep `BLENDER_FX_HOST` on `localhost`; the receiver has no authentication.

## Fluid bake failed

**물·연기 굽기 실패**

> 물 덩어리(0.10m)가 계산 격자 한 칸(0.25m)보다 작아 물이 생기지 않습니다.
> The water source (0.10m) is smaller than one simulation cell (0.25m), so no liquid forms.

`size` 를 키우거나, 문장에 나온 값 이상으로 `resolution` 을 올립니다.
Increase `size`, or raise `resolution` to at least the value in the message.

> 물 굽기 결과가 비어 있습니다.
> The liquid bake produced nothing.

> 연기 굽기 결과가 비어 있습니다.
> The smoke bake produced nothing.

`resolution` 이나 `frames` 를 줄여 다시 시킵니다. 디스크가 가득 찼으면 `clear_caches` 로 캐시를 비웁니다.
`pip install bpy` 로 만든 파이썬에서는 Mantaflow 유체가 깨져 있어 항상 실패합니다. 블렌더 앱을 쓰세요(`CONTRIBUTING.md` 참고).
Lower `resolution` or `frames` and try again; free disk space with `clear_caches`. Mantaflow fluids are broken in the
`pip install bpy` module, so use the Blender app (see `CONTRIBUTING.md`).

## Black preview, effect not visible

**미리보기가 검거나 효과가 안 보임**

> 빠른 미리보기라 하늘·연기·물은 보이지 않습니다.
> Fast preview: sky, smoke and water are not shown.

기본 미리보기(`quality="preview"`)는 빠른 워크벤치 렌더라 연기·물·하늘 텍스처를 그리지 않습니다.
`render_preview(quality="smoke")` 로 다시 봅니다.
The default preview is a fast Workbench render that skips smoke, water and sky textures. Use `render_preview(quality="smoke")`.

화면이 통째로 검으면:

- `set_look(preset="night")` 뒤라면 정상입니다. `set_look(preset="day")` 로 밝힙니다.
- 카메라가 물체 안에 있을 수 있습니다. `camera(preset="wide")` 로 다시 잡습니다.
- `set_render(exposure=...)` 를 크게 낮췄다면 `0` 으로 되돌립니다.

If the whole frame is black: after `set_look(preset="night")` that is expected (use `"day"`); the camera may be inside an
object (`camera(preset="wide")`); or exposure was lowered too far (`set_render(exposure=0)`).

> 카메라도 오브젝트도 없어 렌더할 수 없습니다.
> There is no camera and no object, so nothing can be rendered.

장면이 비어 있습니다. `make_demo_building` 이나 `import_model` 로 먼저 물체를 만듭니다.
The scene is empty. Create something first with `make_demo_building` or `import_model`.

## Fracture or import failed

**부수기·가져오기 실패**

> 조각을 하나도 만들지 못했습니다.
> No chunks could be created.

`pieces` 를 줄이거나 `repair=True` 로 다시 시킵니다. 먼저 `inspect_mesh` 로 모델이 닫혀 있는지 봅니다.
Lower `pieces` or use `repair=True`. Check the model with `inspect_mesh` first.

> 파일이 없습니다: …
> File not found: …

경로는 블렌더가 돌고 있는 컴퓨터 기준입니다. 절대 경로로 줍니다.
Paths are on the computer running Blender; give an absolute path.

## No video

**영상이 안 나옴**

> 영상 파일이 만들어지지 않았습니다.
> No video file was produced.

이 블렌더 빌드에서 FFmpeg 출력이 안 될 수 있습니다. `render_preview` 로 프레임을 받거나 공식 블렌더 빌드를 씁니다.
FFmpeg output may be missing from this Blender build; use `render_preview` for frames, or the official Blender build.
