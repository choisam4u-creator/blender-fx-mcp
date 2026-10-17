# 문제 해결 / Troubleshooting

AI가 보여 준 오류 문장을 아래에서 찾으세요(`Ctrl+F` 로 문장 앞부분 검색). 먼저 `blender-fx-doctor` 를 돌리면 대부분 원인이 한 줄로 나옵니다.
Search this page for the error sentence the AI showed you. Running `blender-fx-doctor` first usually names the cause.

```bash
uvx --from blender-fx-mcp blender-fx-doctor
```

여기 없는 문제는 [버그 신고](https://github.com/choisam4u-creator/blender-fx-mcp/issues/new?template=bug_report.yml)에 doctor 출력과 함께 올려 주세요.
If your problem is not here, open a [bug report](https://github.com/choisam4u-creator/blender-fx-mcp/issues/new?template=bug_report.yml) with the doctor output.
이슈에는 `blender-fx-doctor --issue` 를 붙이면 됩니다(판·OS·블렌더·클라이언트·언어 표와 점검 전체, 집 폴더는 `~` 로 가림).
`blender-fx-doctor --json` 은 같은 결과를 JSON 으로 냅니다(항목 id: `python`·`blender-fx-mcp`·`mcp`·`uv`·`blender`·`addon`·`connection`·`client`·`output`·`space`), `clients` 에는 등록이 보인 MCP 클라이언트가, 실패한 항목의 `help` 에는 이 문서에서 볼 절 주소가 들어갑니다(사람이 읽는 출력의 마지막 "해결법:" 줄도 같은 절).
For an issue, paste `blender-fx-doctor --issue` (version, OS, Blender, clients and language table plus all checks, home folder masked as `~`).
`blender-fx-doctor --json` prints the same result as JSON, with language-independent check ids; `clients` lists the MCP clients where it is registered, and each failed check's `help` is the section of this page to read (the last "Help:" line of the plain output links the same sections).

---

## uv not found

**uv 를 찾을 수 없음**

> zsh: command not found: uvx
> 'uvx' is not recognized as an internal or external command

원인: uv(파이썬 실행기)가 없거나, 설치한 뒤 터미널을 새로 열지 않았습니다. doctor 도 uv 로 돌기 때문에 이 단계는 doctor 없이 합니다.

1. 설치합니다. macOS `brew install uv`(Homebrew 가 없으면 아래 Linux 줄), Linux·macOS `curl -LsSf https://astral.sh/uv/install.sh | sh`,
   Windows PowerShell `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`.
2. 터미널을 **새로** 열고 `uv --version` 이 판 번호를 내는지 봅니다. 그다음 `uvx --from blender-fx-mcp blender-fx-doctor`.
3. 터미널에서는 되는데 클로드 데스크톱·커서에서만 도구가 안 보이면 [클라이언트에 도구가 안 보임](#tools-not-visible-in-the-client)의 4번(전체 경로).

Cause: uv (the Python runner) is not installed, or the terminal was opened before installing it. doctor itself runs through uv, so do this step without it.
1. Install: macOS `brew install uv` (without Homebrew, use the Linux line), Linux and macOS `curl -LsSf https://astral.sh/uv/install.sh | sh`,
   Windows PowerShell `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`.
2. Open a **new** terminal and check that `uv --version` prints a version, then run `uvx --from blender-fx-mcp blender-fx-doctor`.
3. If it works in the terminal but the tools do not show up in Claude Desktop or Cursor, see step 4 of [Tools not visible in the client](#tools-not-visible-in-the-client) (full path).

## Tools not visible in the client

**클라이언트에 도구가 안 보임**

증상: AI에게 시켜도 `make_demo_building` 같은 도구를 모른다고 하거나, `/` 메뉴에 `first_demo` 가 없습니다. 블렌더 연결 전 단계 문제입니다.
doctor 의 "MCP 클라이언트 등록" 줄이 `-` 이면 아래 1번부터, 클라이언트 이름이 보이면 2번부터 합니다.

1. 등록을 확인합니다. Claude Code 는 `claude mcp list` 에 `blender-fx` 가 있어야 합니다. 없으면
   `claude mcp add -s user blender-fx -- uvx blender-fx-mcp`
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
- 굽기·렌더 도구는 5초마다 MCP 진행 알림("물 굽는 중 — 45초 지남(블렌더에서 작업 중)")을 보냅니다. 이를 보여 주는 클라이언트라면 숫자가 늘고 있는 동안은 멈춘 것이 아닙니다.

Cause: a bake or render took longer than the wait, or Blender froze. Lower `pieces`, `frames` or `resolution`;
for an intentionally heavy scene set `BLENDER_FX_TIMEOUT` (seconds, e.g. `3600`) in your MCP config and restart the server.
Bake and render tools wait at least 1800 s (`render_video` 3600 s) and grow with this value.
If Blender is frozen, restart it and `restore` the last snapshot. Bake and render tools send an MCP progress notification every 5 s
("Baking the liquid — 45s so far (Blender is working)"); in clients that show it, a growing number means the tool is still working.

## Empty response, Blender error

**빈 응답·블렌더 오류**

> 블렌더가 빈 응답을 보냈습니다.
> Blender sent an empty response.

수신기가 명령을 받다가 끊겼습니다. 다른 MCP 서버(예: blender-mcp 자체)를 같이 켜 두면 수신기가 하나라 서로 끊길 수 있습니다.
하나만 켜고, 블렌더에서 **Connect to MCP server** 를 다시 누릅니다.
The receiver dropped the request. Another MCP server sharing the same receiver (e.g. blender-mcp itself) can cut it off;
keep only one running and click **Connect to MCP server** again.

> 명령 도중 블렌더와의 연결이 끊겼습니다(ConnectionResetError).
> The connection to Blender dropped during the command (ConnectionResetError).

> 블렌더 응답이 중간에 끊겼습니다(1234바이트 받음).
> Blender's response was cut off (1234 bytes received).

연결은 됐는데 블렌더가 명령을 처리하다 멈추거나 꺼진 경우입니다(무거운 굽기 중 메모리 부족이 흔함). 명령이 일부 실행됐을 수 있습니다.
블렌더 창을 확인하고, 꺼졌으면 다시 켜서 **Connect to MCP server** 를 누른 뒤 `restore` 로 직전 스냅샷을 불러옵니다. 같은 명령이면 `resolution`·`pieces` 를 줄여 다시 시킵니다.
Blender froze or quit while handling the command (often out of memory during a heavy bake), and the command may have partly run.
Check the Blender window; if it closed, reopen it, click **Connect to MCP server** and `restore` the last snapshot. Retry with a lower `resolution` or `pieces`.

> 블렌더 수신기가 알 수 없는 응답을 보냈습니다
> The Blender receiver sent an unexpected response

9876 포트에서 다른 프로그램이 답하고 있거나 수신기가 blender-mcp 애드온이 아닙니다. 블렌더 쪽 애드온과 포트를 확인합니다.
Another program answers on the port, or the receiver is not the blender-mcp add-on. Check the add-on and the port.

> 환경변수 BLENDER_FX_TIMEOUT='0' 은(는) 쓸 수 없습니다
> The environment variable BLENDER_FX_TIMEOUT='0' is not valid (a number, at least 1).

`BLENDER_FX_PORT`(1~65535)·`BLENDER_FX_TIMEOUT`(1 이상, 초)은 숫자여야 합니다. MCP 설정에서 고치거나 지우고 클라이언트를 다시 시작합니다.
`BLENDER_FX_PORT` (1-65535) and `BLENDER_FX_TIMEOUT` (1 or more, seconds) must be numbers. Fix or remove them in your MCP config and restart the client.

> 블렌더 오류: …
> Blender error: …

수신기가 코드를 실행하다 실패했습니다. 뒤에 붙은 메시지가 원인입니다. 레시피 오류(아래)가 아니라 이 문장이 나오면 버그일 가능성이 큽니다. 신고해 주세요.
The receiver failed while running code; the rest of the message is the cause. If you see this instead of a recipe error below, it is likely a bug — please report it.

> 블렌더가 결과 줄(FX_RESULT)을 돌려주지 않았습니다.
> Blender returned no FX_RESULT line.

블렌더는 명령을 끝냈는데 결과를 알리는 줄이 없었습니다. 수신기가 출력을 잘랐거나 다른 애드온이 출력을 가로챈 경우입니다. 한 번 더 시켜 보고,
같은 일이 계속되면 `blender-fx-doctor --issue` 결과와 문장 끝의 "출력 끝부분"을 붙여 신고해 주세요.
Blender finished the command but sent no result line (the receiver cut the output, or another add-on captured it). Try once more;
if it keeps happening, report it with `blender-fx-doctor --issue` and the "End of output" part of the message.

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

## Output folder not writable

**출력 폴더에 쓸 수 없음**

> 출력 폴더 … 에 쓸 수 없음
> output folder … cannot write to

렌더·영상·스냅샷·캐시는 모두 출력 폴더(기본 `~/blender-fx-output`, MCP 설정의 `BLENDER_FX_OUT`)에 씁니다. doctor 가 이 줄을 실패로 보이면:

- 폴더가 외장 디스크·네트워크 드라이브에 있으면 연결돼 있는지 봅니다.
- 내 계정이 쓸 수 있는 폴더로 바꿉니다. MCP 설정의 `env` 에 `"BLENDER_FX_OUT": "~/blender-fx-output"` 처럼 집 폴더 아래를 주고 클라이언트 앱을 완전히 껐다 켭니다(폴더는 없으면 만듭니다).
- macOS 에서 `Documents`·`Desktop` 아래를 골랐다면 시스템 설정 → 개인정보 보호 및 보안 → 파일 및 폴더에서 클라이언트 앱에 접근을 허용하거나, 그 밖의 폴더를 씁니다.
- 고친 뒤 `blender-fx-doctor` 를 다시 돌려 출력 폴더 줄이 `[OK]` 인지 확인합니다.

Renders, videos, snapshots and caches all go to the output folder (default `~/blender-fx-output`, or `BLENDER_FX_OUT` in your MCP config).
If doctor shows this line as failed: check that an external or network drive holding the folder is connected; point `BLENDER_FX_OUT`
in the `env` of your MCP config to a folder your account can write, e.g. `"BLENDER_FX_OUT": "~/blender-fx-output"`, and fully restart the
client app (the folder is created if missing); on macOS, for a folder under `Documents` or `Desktop`, allow the client app in System
Settings → Privacy & Security → Files and Folders, or use another folder. Run `blender-fx-doctor` again and check the line is `[OK]`.

## Fluid bake failed

**물·연기 굽기 실패**

> 물 덩어리(0.10m)가 계산 격자 한 칸(0.25m)보다 작아 물이 생기지 않습니다.
> The water source (0.10m) is smaller than one simulation cell (0.25m), so no liquid forms.
> 물 덩어리(0.10m)가 계산 격자 한 칸(0.25m)보다 작아 물이 생기지 않고, resolution 은 320 까지라 올려서는 안 됩니다.
> The water source (0.10m) is smaller than one simulation cell (0.25m), so no liquid forms, … resolution only goes up to 320.

`size` 를 키우거나, 문장에 나온 값 이상으로 `resolution` 을 올립니다. 그 값이 상한 320 을 넘으면 문장이 대신 되는 `size` 를 알려 줍니다
(`mode="object"` 면 더 큰 `source_object` 나 `domain_at`·`domain_size` 로 물 공간 줄이기).
Increase `size`, or raise `resolution` to at least the value in the message. When that would exceed the limit of 320, the message gives a `size` that works instead
(for `mode="object"`, use a larger `source_object` or shrink the space with `domain_at` and `domain_size`).

> 물 굽기 결과가 비어 있습니다.
> The liquid bake produced nothing.

> 연기 굽기 결과가 비어 있습니다.
> The smoke bake produced nothing.

`resolution` 이나 `frames` 를 줄여 다시 시킵니다. 디스크가 가득 찼으면 `clear_caches` 로 캐시를 비웁니다.
`pip install bpy` 로 만든 파이썬에서는 Mantaflow 유체가 깨져 있어 항상 실패합니다. 블렌더 앱을 쓰세요(`CONTRIBUTING.md` 참고).
Lower `resolution` or `frames` and try again; free disk space with `clear_caches`. Mantaflow fluids are broken in the
`pip install bpy` module, so use the Blender app (see `CONTRIBUTING.md`).

> 디스크 여유가 0.4GB 뿐이라 굽기를 시작하지 않았습니다(물·연기 캐시는 수 GB).
> Only 0.4GB of disk space is left, so the bake was not started (water and smoke caches take several GB).

굽기 전에 서버가 멈춘 것이라 장면은 바뀌지 않았습니다. AI 에게 `clear_caches` 를 시켜 구운 캐시를 지우고(오래된 스냅샷은 `clear_snapshots`), 그래도 모자라면 MCP 설정의 `BLENDER_FX_OUT` 을
여유 있는 디스크의 폴더로 바꾼 뒤 다시 시킵니다. `blender-fx-doctor` 의 "출력 폴더 여유 공간" 줄이 남은 공간과 이 폴더가 쓰는 공간을, 5GB 아래면 큰 것(구운 캐시·스냅샷·렌더 결과)과 크기, 그것을 지울 도구를 큰 것부터 보여 줍니다.
The server stopped before baking, so the scene is unchanged. Ask the AI to run `clear_caches` (and `clear_snapshots` for old snapshots); if that is not enough, point `BLENDER_FX_OUT` to a folder on a
disk with more space, then ask again. The "output folder free space" line of `blender-fx-doctor` shows free space and what this folder uses; below 5GB it also lists the largest parts (baked caches, snapshots, render results) with their size and the tool that clears each, largest first.

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

## Argument value rejected

**인자 값이 거부됨**

서버가 블렌더에 보내기 전에 막은 값입니다. 장면은 바뀌지 않았습니다. 문장에 가능한 값·권장 값이 함께 나오니 그 안에서 다시 시킵니다.
The server stopped the value before anything reached Blender, so the scene is unchanged. The message lists the allowed or recommended values; ask again with one of them.

> … 은(는) 범위 밖입니다. 가능한 범위: …
> … is out of range. Allowed: …

숫자가 범위 밖입니다(예: `fps` 1~240, `width`·`height` 16~7680, 프레임 번호 1 이상). 대부분 0 은 "지금 장면 값 그대로" 입니다.
A number is outside its range (for example `fps` 1-240, `width`/`height` 16-7680, frame numbers from 1). For most of them, 0 keeps the scene's current value.

> … 은(는) 쓸 수 없습니다. 가능한 값: …
> … is not allowed. Choose one of: …

정해진 목록 밖의 이름입니다(`material`·`preset`·`liquid` 등). 비슷한 값이 있으면 "혹시 … 인가요?" 로 함께 알려 줍니다.
The name is not in the fixed list (`material`, `preset`, `liquid`, …). A close match is suggested with "Did you mean …?".

> keep=… 은 쓸 수 없습니다. 남길 스냅샷 개수를 0~1000 사이 정수로 다시 시키세요(기본 5).
> keep=… is not allowed. Ask again with the number of snapshots to keep, an integer from 0 to 1000 (default 5).

`clear_snapshots` 의 `keep` 은 0~1000 정수입니다. 0 이면 `before_restore` 만 남기고 모두 지웁니다.
`keep` of `clear_snapshots` is an integer from 0 to 1000. With 0, everything except `before_restore` is deleted.

> … 보다 같거나 커야 합니다. 장면은 바꾸지 않았습니다.
> … must be at least … The scene was not changed.
> … 보다 커야 합니다. 장면은 바꾸지 않았습니다.
> … must be greater than … The scene was not changed.

`frame_start`·`frame_end` 나 `slow_from`·`slow_to` 를 거꾸로 줬습니다. 문장에 적힌 대로 두 값을 바꿔 다시 시킵니다(`slow_to` 는 `slow_from` 보다 커야 합니다).
A pair such as `frame_start`/`frame_end` or `slow_from`/`slow_to` was given in reverse. Swap the two values as the message shows (`slow_to` must be greater than `slow_from`).

> frame_end(…) 가 frame_start(…) 보다 작습니다. 두 값을 바꿔 다시 시키세요.
> frame_end(…) is smaller than frame_start(…). Swap the two values and ask again.
> slow_to(…) 는 slow_from(…) 보다 커야 합니다.
> slow_to(…) must be greater than slow_from(…).

블렌더가 지금 장면 값과 비교해 막은 같은 종류의 오류입니다. 문장대로 두 값을 바꿉니다.
The same kind of error, caught by Blender against the scene's current values. Swap the two values as the message says.

> frame_start(…) 가 장면 끝(frame_end …) 뒤입니다. frame_end 도 함께 주어(…) 다시 시키세요.
> frame_start (…) is after the scene's end (frame_end …). Give frame_end too (…) and ask again.
> frame_end(…) 가 장면 시작(frame_start …) 앞입니다.
> frame_end (…) is before the scene's start (frame_start …).

`render_video` 에 한쪽 끝만 줬는데 장면의 다른 끝을 넘었습니다. 두 값을 함께 줍니다(예: `frame_start=100, frame_end=171`). 장면 길이를 아예 바꾸려면 `set_timing` 을 씁니다.
Only one end was given to `render_video`, and it passes the scene's other end. Give both (for example `frame_start=100, frame_end=171`), or change the scene length with `set_timing`.

> at 은(는) [x, y, z] 숫자 세 개로 주세요(지금 [1, 2]).
> Give at as three numbers [x, y, z] (got [1, 2]).

위치(`at`·`domain_at`)는 미터 단위 숫자 세 개입니다. 높이(z)를 빠뜨린 경우가 많으니 `at=[x, y, 0]` 처럼 셋을 다 적어 다시 시킵니다.
A position (`at`, `domain_at`) is three numbers in metres. The height (z) is the one usually missing; ask again with all three, such as `at=[x, y, 0]`.

> … 에 유한한 숫자를 주세요(지금 nan).
> … must be a finite number (got nan).

`nan`·`inf` 같은 값은 물리·렌더에 쓸 수 없습니다. 보통 AI 가 계산을 잘못 넘긴 것이니 숫자를 직접 적어 다시 시킵니다.
Values like `nan` or `inf` cannot be used for physics or rendering. The AI usually passed a broken calculation; ask again with a plain number.

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

> '…' 에 면이 없어 조각낼 수 없습니다.
> '…' has no faces, so it cannot be fractured.

선이나 점만 있는 오브젝트(커브를 바꾼 것, 빈 메시)입니다. `inspect_mesh` 로 면 수를 보고 면이 있는 오브젝트로 다시 시킵니다.
The object has only edges or points (a converted curve, an empty mesh). Check the face count with `inspect_mesh` and pick an object with faces.

> 가져온 파일에 메시가 없습니다.
> The imported file contains no mesh.

파일에 카메라·조명·뼈대만 있습니다(문장에 들어 있던 종류가 나옵니다). 모양이 든 파일을 고르거나, 원래 프로그램에서 메시로 바꿔 내보냅니다.
The file holds only cameras, lights or armatures (the message lists what it held). Pick a file with a shape, or convert it to a mesh in the original program and export again.

> parts 에 맞는 부품이 없습니다.
> No part matched 'parts'.

`parts` 의 이름이 파일 안 부품 이름과 하나도 맞지 않았습니다. 문장에 나온 부품 이름 중에서 골라 다시 시키거나 `parts` 를 빼고 통째로 가져옵니다.
None of the names in `parts` matched a part in the file. Pick from the part names in the message, or leave `parts` out to import everything.

> 지원하지 않는 형식: …
> Unsupported format: …

가져오기는 glb·gltf·fbx·obj·stl·usd·blend, 내보내기는 glb·gltf·fbx·obj·abc 입니다. 다른 형식은 원래 프로그램에서 glb 로 바꿔 씁니다.
Import takes glb, gltf, fbx, obj, stl, usd and blend; export writes glb, gltf, fbx, obj and abc. Convert other formats to glb in the original program.

## Object or file not found

**오브젝트·파일을 찾을 수 없음**

> '…' 이름의 메시 오브젝트가 없습니다.
> No mesh object named '…'.

이름은 대소문자까지 같아야 합니다. 문장에 지금 있는 메시와 비슷한 이름("혹시 … 인가요?")이 함께 나오니 그 이름으로 다시 시킵니다. 목록은 `list_objects` 로 봅니다.
장면에 메시가 하나도 없으면 `make_demo_building` 이나 `import_model` 로 먼저 만듭니다.
Names are case-sensitive. The message lists the meshes in the scene and a close match ("Did you mean …?"); ask again with that name, or see them all with `list_objects`.
If the scene has no meshes at all, create one first with `make_demo_building` or `import_model`.

> '…' 은(는) 메시가 아니라 … 입니다.
> '…' is a …, not a mesh.

카메라·조명·빈 오브젝트는 부수거나 태울 수 없습니다. 문장에 나온 메시 중 하나로 다시 시킵니다.
Cameras, lights and empties cannot be fractured or burned. Ask again with one of the meshes in the message.

> '…' 은(는) 지난 효과가 만든 보조 오브젝트라 새 효과를 시작할 때 지워집니다.
> '…' is a helper object made by the previous effect, and it is removed when the new one starts.

`list_objects` 에 보이는 `FX_EmitFlow`·`FX_LiquidFlow` 같은 이름은 지난 불·연기·물의 일부라, 새 효과를 만들 때 먼저 지워집니다. 장면은 바꾸지 않았습니다. 문장 끝의 원래 메시 이름(건물·가져온 모델)으로 다시 시킵니다.
Names such as `FX_EmitFlow` or `FX_LiquidFlow` in `list_objects` belong to the previous fire, smoke or water and are removed before the new effect is built. The scene was not changed. Ask again with one of the original meshes listed at the end of the message.

> mode='object' 에는 source_object 이름이 필요합니다.
> mode='object' needs a source_object name.

`water(mode="object")` 는 물로 바꿀 메시 이름이 있어야 합니다. `list_objects` 로 이름을 찾아 `source_object` 로 줍니다.
`water(mode="object")` turns a mesh into liquid, so it needs that mesh's name. Find it with `list_objects` and pass it as `source_object`.

> HDRI 파일이 없습니다: …
> HDRI file not found: …

경로는 블렌더가 돌고 있는 컴퓨터 기준입니다. 문장 끝에 비슷한 파일이나 찾아본 폴더가 나옵니다. `.hdr`·`.exr` 파일의 절대 경로로 줍니다.
The path is on the computer running Blender. The end of the message names similar files or the folders searched; give the absolute path of an `.hdr` or `.exr` file.

> 스냅샷 파일이 없습니다: …
> Snapshot file not found: …
> 스냅샷이 없습니다: …
> Snapshot not found: …
> 블렌더가 있는 컴퓨터에 스냅샷 '…' 이 없습니다(…).
> There is no snapshot '…' on the Blender computer (…).

`restore` 의 이름이 틀렸습니다. 문장에 있는 스냅샷 이름 중 하나로 다시 시키거나 `list_snapshots` 로 전체를 봅니다. 하나도 없으면 되돌리고 싶은 상태에서 `snapshot` 으로 먼저 저장합니다.
The name given to `restore` does not exist. Ask again with one of the snapshot names in the message, or list them with `list_snapshots`. If there are none, save one with `snapshot` first, at the state you want to return to.

## Tool needs another step first

**먼저 다른 단계가 필요함**

> 슬로모션을 걸 시뮬레이션이 없습니다.
> There is no simulation to slow down.

`set_timing` 의 슬로모션(`slow_from`·`slow_to`)은 부수기·폭발·물이 있어야 걸립니다. `destroy`·`explode`·`splash` 를 먼저 시킨 뒤 다시 시킵니다.
Slow motion in `set_timing` (`slow_from`/`slow_to`) needs a destruction, explosion or water simulation. Run `destroy`, `explode` or `splash` first, then ask again.

> 바다가 바닥을 대신하고 있어 바닥 재질을 바꿀 수 없습니다.
> The ocean is acting as the ground, so the ground material cannot be changed.

`ocean` 을 만들면 바닥이 숨습니다. 바닥 재질을 바꾸려면 `reset_destroy` 로 바다를 지운 뒤 `set_ground` 를 다시 시킵니다.
Creating an `ocean` hides the ground. To change the ground material, remove the ocean with `reset_destroy`, then ask `set_ground` again.

## Snapshot or restore refused

**스냅샷·되돌리기 거절**

> 'before_restore' 은 restore 가 직전 상태를 자동으로 저장하는 이름이라 쓸 수 없습니다.
> 'before_restore' is the name restore uses to auto-save the previous state.

`before_restore` 는 `restore` 가 되돌리기 직전 장면을 넣어 두는 자리입니다(`restore("before_restore")` 가 되돌리기를 취소). 다른 이름으로 `snapshot` 을 다시 시킵니다.
`before_restore` is where `restore` keeps the scene from just before it ran (`restore("before_restore")` undoes a restore). Ask `snapshot` again with another name.

> 다른 컴퓨터의 블렌더에서는 before_restore 로 되돌릴 수 없습니다(지금 장면을 저장하면 그 파일을 덮어씀).
> Restoring before_restore is not supported with a remote Blender (saving the current scene would overwrite it).

블렌더가 다른 컴퓨터(`BLENDER_FX_HOST`)에 있으면 지금 장면을 저장할 때 그 파일을 덮어쓰게 됩니다. `snapshot` 으로 지금 장면을 다른 이름으로 저장한 뒤, 블렌더에서 `before_restore.blend` 를 직접 엽니다.
With Blender on another computer (`BLENDER_FX_HOST`), saving the current scene would overwrite that file. Save the current scene with `snapshot` under another name, then open `before_restore.blend` in Blender yourself.

## Export failed

**내보내기 실패**

> 내보낼 오브젝트가 없습니다.
> There is nothing to export.

렌더에서 숨긴 것과 효과 보조 오브젝트(먼지·바람·불 뿜는 곳 등)는 빠집니다. `list_objects` 로 장면을 보고 내보낼 이름을 `names` 로 직접 줍니다.
Objects hidden from render and effect helpers (dust, wind, emitters and so on) are left out. Check the scene with `list_objects` and pass the names to export as `names`.

> 내보낸 파일이 만들어지지 않았습니다: …
> The export file was not created: …

그 폴더에 쓸 수 있는지 확인하고, 안 되면 glb 로 다시 내보냅니다. 블렌더 창 아래 상태 줄이나 Info 창에 내보내기 오류가 나옵니다.
Check that the folder is writable, or export again as glb. Blender's status bar or Info editor shows the exporter's error.

## No video

**영상이 안 나옴**

> 영상 파일이 만들어지지 않았습니다.
> No video file was produced.

이 블렌더 빌드에서 FFmpeg 출력이 안 될 수 있습니다. `render_preview` 로 프레임을 받거나 공식 블렌더 빌드를 씁니다.
FFmpeg output may be missing from this Blender build; use `render_preview` for frames, or the official Blender build.

## Still on the old version

**새 판이 나왔는데 예전 판이 돎**

`uvx blender-fx-mcp` 는 처음 받은 판을 캐시에 두고 계속 씁니다. doctor 는 PyPI 에 새 판이 있으면 "새 판" 줄로 알려 줍니다(2초 안에 답이 없거나 `BLENDER_FX_NO_UPDATE_CHECK=1` 이면 그 줄 없이 건너뜀). doctor 의 `blender-fx-mcp` 줄에 보이는 판이 [PyPI](https://pypi.org/project/blender-fx-mcp/) 의 최신 판보다 낮으면
아래 한 줄로 캐시를 비운 뒤(다음 실행 때 최신 판을 받음) 클라이언트 앱을 완전히 껐다 켭니다. 아직 출시되지 않은 `main` 의 변경을 시험하려면 `uvx --from git+https://github.com/choisam4u-creator/blender-fx-mcp blender-fx-mcp` 로 등록합니다.

`uvx blender-fx-mcp` keeps the version it first downloaded. doctor shows a "newer release" line when PyPI has one (skipped without a line if PyPI does not answer within 2 s or `BLENDER_FX_NO_UPDATE_CHECK=1`). If the version on doctor's `blender-fx-mcp` line is older than the latest on PyPI,
clear the cache with the line below (the next run downloads the latest) and fully restart the client app. To try unreleased changes on `main`, register `uvx --from git+https://github.com/choisam4u-creator/blender-fx-mcp blender-fx-mcp` instead.

```bash
uv cache clean blender-fx-mcp
```
