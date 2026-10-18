# SPDX-License-Identifier: MIT
"""자가 진단: 준비물이 갖춰졌는지 한 번에 확인한다. 이슈 올리기 전에 먼저 돌려 본다.

  uv run blender-fx-doctor          # 사람이 읽는 줄
  uv run blender-fx-doctor --json   # 기계가 읽는 JSON(항목 id 는 언어와 상관없이 같다)
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import urllib.request
from importlib import metadata

from . import __version__, bridge, disk
from .headless import find_blender
from .i18n import is_en, lang_source, t

SERVER_CMD = "uvx blender-fx-mcp"


# 등록했는데도 클라이언트에 도구가 안 보일 때 볼 절. 절 제목이 바뀌면 tests/test_troubleshooting.py 가 알려 준다
CLIENT_HELP = f"{bridge.TROUBLESHOOTING_URL}#tools-not-visible-in-the-client"

# 실패한 항목마다 볼 해결법 절(docs/troubleshooting.md 의 제목 앵커). 없는 항목은 문서 첫머리.
# 절 제목이 바뀌면 tests/test_doctor.py 가 알려 준다
HELP_ANCHORS = {
    "mcp": "uv-not-found",  # uvx 로 돌리면 함께 깔린다. uv 부터
    "uv": "uv-not-found",
    "addon": "connection-refused",
    "connection": "connection-refused",
    "client": "tools-not-visible-in-the-client",
    "output": "output-folder-not-writable",
    "update": "still-on-the-old-version",
    "space": "fluid-bake-failed",
}


def help_url(check_id: str) -> str:
    """그 항목이 실패했을 때 볼 해결법 주소."""
    anchor = HELP_ANCHORS.get(check_id)
    return f"{bridge.TROUBLESHOOTING_URL}#{anchor}" if anchor else bridge.TROUBLESHOOTING_URL


def help_urls(checks: list[dict]) -> list[str]:
    """실패한 항목들의 해결법 주소(설치 순서, 겹치는 것은 한 번). 첫 주소가 먼저 고칠 항목의 절이다."""
    return list(dict.fromkeys(help_url(c.get("id", "")) for c in failed(checks)))


def _check(name: str, ok: bool, detail: str, key: str = "", fix: str = "", optional: bool = False) -> dict:
    # key 는 --json 의 id. 화면 이름(name)은 언어에 따라 바뀌어도 id 는 그대로라 신고끼리 비교할 수 있다.
    # fix 는 실패했을 때 사용자가 할 다음 한 단계. optional 이면 실패해도 MCP 사용에는 지장이 없다(`[- ]`).
    return {"id": key or name, "name": name, "ok": ok, "detail": detail, "fix": "" if ok else fix,
            "optional": optional}


def _uv_install() -> str:
    """이 OS 에서 uv 를 까는 한 줄(https://docs.astral.sh/uv/getting-started/installation/)."""
    if sys.platform == "darwin":
        return "brew install uv"
    if sys.platform == "win32":
        return 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"'
    return "curl -LsSf https://astral.sh/uv/install.sh | sh"


def _connect_fix() -> str:
    step = t("블렌더를 켜고 3D 화면에서 N 키 → BlenderMCP 탭 → Connect to MCP server",
             "Open Blender, press N in the 3D view → BlenderMCP tab → Connect to MCP server")
    if bridge.port() != bridge.DEFAULT_PORT:
        step += t(f" (BlenderMCP 탭의 Port 를 BLENDER_FX_PORT 와 같은 {bridge.port()} 로)",
                  f" (set Port in the BlenderMCP tab to {bridge.port()}, the same as BLENDER_FX_PORT)")
    return step


def client_configs() -> list[tuple[str, str]]:
    """(클라이언트 이름, 설정 파일) 목록. examples/README.md 의 표와 같은 곳을 본다."""
    home = os.path.expanduser("~")
    desktop = {"darwin": os.path.join(home, "Library", "Application Support", "Claude"),
               "win32": os.path.join(os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming")), "Claude")}
    return [
        ("Claude Code", os.path.join(home, ".claude.json")),
        ("Claude Code", os.path.join(os.getcwd(), ".mcp.json")),  # 프로젝트 범위(-s project)
        ("Claude Desktop", os.path.join(desktop.get(sys.platform, os.path.join(home, ".config", "Claude")),
                                        "claude_desktop_config.json")),
        ("Cursor", os.path.join(home, ".cursor", "mcp.json")),
        ("Codex", os.path.join(home, ".codex", "config.toml")),
    ]


def _is_ours(name: str, entry) -> bool:
    return name.replace("_", "-") == "blender-fx" or "blender-fx-mcp" in json.dumps(entry, ensure_ascii=False)


def _has_server(data) -> bool:
    """JSON 어디든 mcpServers 안에 이 서버가 있는지. Claude Code 는 projects.<폴더>.mcpServers 에도 둔다."""
    if isinstance(data, dict):
        servers = data.get("mcpServers")
        if isinstance(servers, dict) and any(_is_ours(k, v) for k, v in servers.items()):
            return True
        return any(_has_server(v) for v in data.values())
    return isinstance(data, list) and any(_has_server(v) for v in data)


# 클라이언트별 예제 설정 파일(examples/). Claude Code 는 명령 한 줄로 등록한다
CLIENT_EXAMPLES = {"Claude Desktop": "examples/claude_desktop_config.json", "Cursor": "examples/cursor-mcp.json",
                   "Codex": "examples/codex-config.toml"}
# 셸 PATH 를 물려받지 않는 창 앱. macOS 에서는 brew 의 uvx 를 못 찾아 "spawn uvx ENOENT" 로 끝난다
GUI_CLIENTS = ("Claude Desktop", "Cursor")


def installed_clients() -> list[str]:
    """이 컴퓨터에 깔린 것으로 보이는 클라이언트(설정 폴더가 있거나 명령이 PATH 에 있음). 등록 여부와는 별개."""
    found: list[str] = []
    for client, path in client_configs():
        if client == "Claude Code":
            hit = shutil.which("claude") is not None or (os.path.isfile(path) and path.endswith(".claude.json"))
        else:
            hit = os.path.isdir(os.path.dirname(path)) or (client == "Codex" and shutil.which("codex") is not None)
        if hit and client not in found:
            found.append(client)
    return found


def _client_fix(uvx: str | None) -> str:
    """등록을 못 찾았을 때의 다음 할 일. Claude Code 가 있거나 아무것도 못 찾으면 등록 명령 한 줄,
    다른 클라이언트만 있으면 그 설정 파일과 붙여 넣을 예제(창 앱이면 command 를 uvx 전체 경로로)."""
    installed = installed_clients()
    if "Claude Code" in installed or not installed:
        return t(f"클로드에 등록: claude mcp add -s user blender-fx -- {SERVER_CMD} "
                 "(다른 클라이언트는 examples/README.md, 등록 뒤 앱을 껐다 켜기). "
                 f"그래도 도구가 안 보이면: {CLIENT_HELP}",
                 f"Register with Claude: claude mcp add -s user blender-fx -e BLENDER_FX_LANG=en -- {SERVER_CMD} "
                 "(other clients: examples/README.md; restart the app afterwards). "
                 f"If the tools still do not show up: {CLIENT_HELP}")
    client = installed[0]
    path = dict((c, p) for c, p in reversed(client_configs()))[client]
    step = t(f"{client} 에 등록: {path} 에 {CLIENT_EXAMPLES[client]} 의 blender-fx 항목을 더하고 앱을 완전히 껐다 켜기",
             f"Register with {client}: add the blender-fx entry from {CLIENT_EXAMPLES[client]} to {path}, "
             "then fully restart the app")
    if client in GUI_CLIENTS and uvx:
        step += t(f" (창 앱은 셸 PATH 를 못 보니 command 를 \"{uvx}\" 로)",
                  f" (desktop apps do not see your shell PATH, so set command to \"{uvx}\")")
    return step + t(f". 그래도 도구가 안 보이면: {CLIENT_HELP}", f". If the tools still do not show up: {CLIENT_HELP}")


def registered_clients() -> list[str]:
    """blender-fx 가 등록된 MCP 클라이언트 이름들(중복 없이, 찾은 순서)."""
    found: list[str] = []
    for client, path in client_configs():
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        if path.endswith(".toml"):
            # 설정 파일 문법이 깨져 있어도 찾도록 tomllib 로 읽지 않고 표 이름·명령만 본다
            hit = "[mcp_servers.blender_fx]" in text or "[mcp_servers.blender-fx]" in text or "blender-fx-mcp" in text
        else:
            try:
                hit = _has_server(json.loads(text))
            except ValueError:
                hit = False
        if hit and client not in found:
            found.append(client)
    return found


PYPI_JSON = "https://pypi.org/pypi/blender-fx-mcp/json"


def latest_version(timeout: float = 2.0) -> str | None:
    """PyPI 의 최신 판. 끔(BLENDER_FX_NO_UPDATE_CHECK=1)·네트워크 없음·느림·이상한 응답이면 None."""
    if os.environ.get("BLENDER_FX_NO_UPDATE_CHECK", "").strip() not in ("", "0"):
        return None
    try:
        with urllib.request.urlopen(PYPI_JSON, timeout=timeout) as resp:
            version = json.loads(resp.read().decode("utf-8"))["info"]["version"]
    except Exception:
        return None
    return version if isinstance(version, str) and re.fullmatch(r"\d+(\.\d+)*", version) else None


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", version.split("+")[0])[:3])


def _update_check() -> dict | None:
    """새 판 알림(선택 항목). uvx 는 처음 받은 판을 계속 써서, 고친 판이 나와도 사용자가 모른다."""
    latest = latest_version()
    if latest is None:
        return None
    name = t("새 판", "newer release")
    if _version_key(latest) <= _version_key(__version__):
        return _check(name, True, t(f"최신(PyPI {latest})", f"up to date (PyPI {latest})"), "update", optional=True)
    return _check(name, False, t(f"PyPI 에 {latest} 이 있음(지금 {__version__})", f"{latest} is on PyPI (you run {__version__})"),
                  "update",
                  t(f"새 판 받기: uv cache clean blender-fx-mcp 뒤 MCP 클라이언트 앱을 껐다 켜기(uvx 가 {latest} 을 받음). "
                    "pip 로 깔았으면 pip install -U blender-fx-mcp. 이 확인을 끄려면 BLENDER_FX_NO_UPDATE_CHECK=1",
                    f"Get it: uv cache clean blender-fx-mcp, then fully restart your MCP client (uvx fetches {latest}). "
                    "If you installed with pip: pip install -U blender-fx-mcp. To skip this check: BLENDER_FX_NO_UPDATE_CHECK=1"),
                  optional=True)


def run_checks(clients: bool = True, updates: bool | None = None) -> list[dict]:
    """준비물 항목들. clients=False 면 MCP 클라이언트 등록 항목을 뺀다(MCP doctor 도구에서).
    updates(기본은 clients 와 같음)면 PyPI 에 새 판이 있는지도 묻는다(2초 제한, 실패하면 줄 없이 건너뜀)."""
    out: list[dict] = []
    v = sys.version_info
    out.append(_check("python", v >= (3, 11), f"{v.major}.{v.minor}.{v.micro} ({platform.system()} {platform.machine()})",
                      "python", t("Python 3.11 이상으로 실행: uvx 가 알아서 고른다(uv python install 3.13)",
                                  "Run with Python 3.11+: uvx picks one for you (uv python install 3.13)")))

    # 이슈에 붙인 결과만 보고 어느 판인지 알 수 있게 맨 위에 둔다
    out.append(_check("blender-fx-mcp", True, __version__, "blender-fx-mcp"))
    if clients if updates is None else updates:
        update = _update_check()
        if update:
            out.append(update)

    name_mcp = t("mcp 라이브러리", "mcp library")
    try:
        out.append(_check(name_mcp, True, metadata.version("mcp"), "mcp"))
    except Exception as e:
        out.append(_check(name_mcp, False, t(f"설치 안 됨: {e}", f"not installed: {e}"), "mcp",
                          t("README 의 uvx 명령으로 실행하면 함께 설치된다(직접 설치: pip install blender-fx-mcp[cli])",
                            "Run it with the uvx command from the README, which installs it "
                            "(manual install: pip install blender-fx-mcp[cli])")))

    uv = shutil.which("uv")
    uvx = shutil.which("uvx")
    # 창 앱(Claude Desktop·Cursor) 설정의 command 에 넣을 전체 경로. uv 와 다른 곳이면 함께 보인다
    uv_detail = uv and (uv if not uvx or os.path.dirname(uvx) == os.path.dirname(uv) else f"{uv} (uvx: {uvx})")
    out.append(_check("uv", uv is not None, uv_detail or t(f"PATH 에 없음. {_uv_install()}", f"not on PATH. {_uv_install()}"),
                      "uv", t(f"uv 설치: {_uv_install()} (새 터미널에서 다시 실행)",
                              f"Install uv: {_uv_install()} (then rerun in a new terminal)")))

    name_blender = t("블렌더 실행 파일", "Blender executable")
    blender = find_blender()
    if blender:
        try:
            lines = subprocess.run([blender, "--version"], capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", timeout=30).stdout.splitlines()
            ver = lines[0] if lines else t("버전 출력 없음", "printed no version")
        except Exception as e:
            ver = t(f"실행 실패: {e}", f"failed to run: {e}")
        out.append(_check(name_blender, True, f"{blender} — {ver}", "blender"))
    else:
        # MCP 로 쓰는 데는 필요 없다(블렌더 창 안의 수신기와 소켓으로 말한다). 헤드리스 시험에만 쓴다
        out.append(_check(name_blender, False, t(
            "못 찾음 — MCP 사용에는 필요 없음. 헤드리스 시험을 돌릴 때만 BLENDER_FX_BLENDER 환경변수로 경로를 알려주세요",
            "not found — not needed to use the MCP server. Only for headless tests: set BLENDER_FX_BLENDER to its path"),
            "blender", optional=True))

    found = bridge.addon_files()
    out.append(_check(t("수신기 애드온 파일(blender-mcp)", "receiver add-on file (blender-mcp)"), bool(found),
                      found[0] if found else t(
                          "블렌더 애드온 폴더에 blender_mcp.py 가 없음. https://github.com/ahujasid/blender-mcp 의 addon.py 를 설치하세요",
                          "blender_mcp.py is not in the Blender add-ons folder. Install addon.py from https://github.com/ahujasid/blender-mcp"),
                      "addon", t(
                          "https://github.com/ahujasid/blender-mcp 에서 addon.py 를 받아 블렌더 Edit → Preferences → Add-ons → "
                          "오른쪽 위 ▾ → Install from Disk 로 설치하고 체크",
                          "Download addon.py from https://github.com/ahujasid/blender-mcp, then in Blender Edit → Preferences → "
                          "Add-ons → top-right ▾ → Install from Disk, and tick it")))

    name_conn = t("수신기 연결", "receiver connection")
    try:
        bridge.ping()
        version = bridge.blender_version()
        detail = t(f"{bridge.host()}:{bridge.port()} 응답함", f"{bridge.host()}:{bridge.port()} responded")
        if version:
            detail += f" — Blender {version}"
        if bridge.version_warning(version):
            detail += f". {bridge.version_warning(version)}"
        out.append(_check(name_conn, True, detail, "connection"))
    except bridge.BlenderError as e:
        out.append(_check(name_conn, False, str(e), "connection", _connect_fix()))

    # 다른 클라이언트(VS Code 등)에만 등록했을 수도 있어 선택 항목이다. 못 찾으면 README 4단계 명령을 다음 할 일로
    if clients:
        regs = registered_clients()
        out.append(_check(t("MCP 클라이언트 등록", "MCP client registration"), bool(regs),
                          ", ".join(regs) if regs else t(
                              "Claude Code·Claude Desktop·Cursor·Codex 설정에서 blender-fx 를 못 찾음(다른 클라이언트에 등록했다면 무시)",
                              "blender-fx not found in Claude Code, Claude Desktop, Cursor or Codex settings "
                              "(ignore if you registered it in another client)"),
                          "client", _client_fix(uvx),
                          optional=True))

    name_out = t("출력 폴더", "output folder")
    root = out_dir()
    try:
        os.makedirs(root, exist_ok=True)
        test = os.path.join(root, ".write_test")
        with open(test, "w") as f:
            f.write("ok")
        os.remove(test)
        out.append(_check(name_out, True, root, "output"))
        out.append(_space_check(root))
    except Exception as e:
        out.append(_check(name_out, False, t(f"{root} 에 쓸 수 없음: {e}", f"cannot write to {root}: {e}"), "output",
                          t("MCP 설정의 BLENDER_FX_OUT 을 쓸 수 있는 폴더로 지정", "Point BLENDER_FX_OUT in your MCP config to a writable folder")))
    return out


def mark(c: dict) -> str:
    """줄 머리 표시: OK / X(고쳐야 함) / -(없어도 되는 선택 항목)."""
    return "OK" if c["ok"] else ("- " if c.get("optional") else "X ")


def failed(checks: list[dict]) -> list[dict]:
    """고쳐야 하는 항목(선택 항목 제외). 순서는 설치 순서(파이썬 → uv → 애드온 → 연결 → 출력 폴더)."""
    return [c for c in checks if not c["ok"] and not c.get("optional")]


def _space_check(root: str) -> dict:
    """출력 폴더 디스크 여유(선택 항목). 물·연기 캐시가 수 GB 라 부족하면 굽다가 실패한다."""
    name = t("출력 폴더 여유 공간", "output folder free space")
    free = disk.free_bytes(root)
    if free is None:
        return _check(name, True, t("알 수 없음", "unknown"), "space", optional=True)
    used = disk.folder_bytes(root)
    detail = t(f"남은 {disk.gb(free)}, 이 폴더가 쓰는 {disk.gb(used)}", f"{disk.gb(free)} free, this folder uses {disk.gb(used)}")
    ok = free >= disk.DOCTOR_WARN_BYTES
    if ok:
        return _check(name, ok, detail, "space", optional=True)
    detail += t(f" — 물·연기 굽기에는 {disk.gb(disk.DOCTOR_WARN_BYTES)} 이상 권장",
                f" — {disk.gb(disk.DOCTOR_WARN_BYTES)} or more recommended for water and smoke bakes")
    groups = [g for g in disk.usage_groups(root) if g[1] >= GROUP_MIN_BYTES]
    if groups:
        detail += t(". 큰 것: ", ". Largest: ") + ", ".join(f"{_GROUP_LABEL[k]()} {disk.gb(b)}" for k, b, _ in groups)
        # 큰 묶음부터 지울 방법을 짝지어 말한다(무엇을 지워야 할지 바로 보이게)
        steps = [_GROUP_FIX[k](c) for k, _, c in groups]
    else:
        steps = [t("출력 폴더는 작아서 지워도 소용없음: 디스크의 다른 큰 파일을 정리",
                   "The output folder is small, so clearing it will not help: free space elsewhere on the disk")]
    steps.append(t("또는 BLENDER_FX_OUT 을 여유 있는 디스크의 폴더로 지정", "or point BLENDER_FX_OUT to a folder on a disk with more space"))
    return _check(name, ok, detail, "space", " / ".join(steps), optional=True)


GROUP_MIN_BYTES = 100 * 1024**2  # 이보다 작은 묶음은 지워도 체감이 없어 안내하지 않는다
_GROUP_LABEL = {
    "caches": lambda: t("구운 캐시(cache_*)", "baked caches (cache_*)"),
    "snapshots": lambda: t("스냅샷(snapshots)", "snapshots"),
    "runs": lambda: t("렌더·미리보기 결과", "render and preview results"),
    "files": lambda: t("폴더 바로 아래 파일(내보낸 모델 등)", "loose files (exported models, ...)"),
}
_GROUP_FIX = {
    "caches": lambda c: t("AI 에게 clear_caches 를 시켜 구운 캐시를 지움", "Ask the AI to run clear_caches (deletes baked caches)"),
    "snapshots": lambda c: t(f"AI 에게 clear_snapshots 를 시켜 오래된 스냅샷 {c}개를 지움(최근 {disk.SNAPSHOT_KEEP}개·before_restore 는 남김)",
                             f"Ask the AI to run clear_snapshots to delete {c} old snapshots "
                             f"(keeps the newest {disk.SNAPSHOT_KEEP} and before_restore)"),
    "runs": lambda c: t(f"출력 폴더의 날짜 이름 폴더({c}개) 중 필요 없는 렌더 결과를 직접 지움",
                        f"Delete render results you no longer need from the date-named folders ({c}) by hand"),
    "files": lambda c: t(f"출력 폴더 바로 아래 파일 {c}개(내보낸 모델 등)를 다른 곳으로 옮기거나 지움",
                         f"Move or delete the {c} files directly in the output folder (exported models, ...)"),
}


def first_step(for_ai: bool = False) -> str:
    """모두 정상일 때 마지막 줄. README 로 돌아가지 않고 바로 첫 렌더로(AI 가 부른 doctor 도구면 AI 가 할 순서)."""
    if for_ai:
        return t("다음 할 일: make_demo_building → snapshot → destroy → render_preview 로 첫 렌더(또는 /first_demo).",
                 "Next: make_demo_building → snapshot → destroy → render_preview for a first render (or /first_demo).")
    return t(f"다음 할 일: AI 에게 \"연습용 건물을 만들고 부숴서 미리보기 보여 줘\"(또는 /first_demo) — AI 없이 블렌더 쪽만: {FIRST_RENDER_CMD}",
             f"Next: ask the AI \"make a demo building, destroy it and show a preview\" (or /first_demo) — Blender side only, no AI: {FIRST_RENDER_CMD}")


FIRST_RENDER_CMD = "uvx --from blender-fx-mcp blender-fx-first-render"  # 저장소 없이(PyPI 설치) 도는 진입점


def format_report(checks: list[dict], for_ai: bool = False) -> str:
    lines = [f"[{mark(c)}] {c['name']}: {c['detail']}" for c in checks]
    bad = failed(checks)
    # 선택 항목 중 할 일이 있는 것(클라이언트 등록)은 필수 항목 뒤에 "(선택)" 을 붙여 이어서 번호를 매긴다
    extra = [c for c in checks if not c["ok"] and c.get("optional") and c.get("fix")]
    steps = [c.get("fix") or c["detail"] for c in bad] + [t("(선택) ", "(optional) ") + c["fix"] for c in extra]
    if not bad:
        lines.append(t("모두 정상입니다.", "Everything looks good."))
        if extra:
            lines.append(t("더 할 수 있는 일:", "You may also:"))
            lines += [f"  {i}. {s}" for i, s in enumerate(steps, 1)]
        lines.append(first_step(for_ai))
        return "\n".join(lines)
    lines.append(t(f"확인 필요: {', '.join(c['name'] for c in bad)}. 다음 할 일:",
                   f"Needs attention: {', '.join(c['name'] for c in bad)}. Next steps:"))
    lines += [f"  {i}. {s}" for i, s in enumerate(steps, 1)]
    urls = " · ".join(help_urls(checks))  # 실패 항목의 절로 바로(문서 첫머리에서 찾지 않게)
    lines.append(t(f"해결법: {urls}", f"Help: {urls}"))
    return "\n".join(lines)


def check_rows(checks: list[dict]) -> list[dict]:
    """점검 항목을 바깥에 보이는 모양으로(--json·MCP doctor 도구의 구조화 출력이 같은 모양을 쓴다)."""
    return [{"id": c["id"], "name": c["name"], "ok": c["ok"], "optional": c.get("optional", False),
             "detail": c["detail"], "fix": c.get("fix", ""), "help": "" if c["ok"] else help_url(c["id"])}
            for c in checks]


def format_json(checks: list[dict]) -> str:
    """버그 신고에 붙여 그대로 비교·재현할 수 있는 JSON. 항목·결과는 format_report 와 같다."""
    bad = [c["id"] for c in failed(checks)]
    report = {
        "blender_fx_mcp": __version__,
        "lang": "en" if is_en() else "ko",
        "lang_source": lang_source(),
        "ok": not bad,
        "blender": find_blender(),
        "host": bridge.host(),
        "port": bridge.port(),
        # 등록이 보인 클라이언트(버그 양식의 클라이언트 선택지와 같은 이름). 신고마다 "어떤 클라이언트?"를 되묻지 않게
        "clients": registered_clients(),
        "checks": check_rows(checks),
        "failed": bad,
        "help": help_urls(checks)[0] if bad else None,
        "last_error": last_error(),  # 마지막 도구 실패(없으면 null). --issue 표의 "최근 실패한 도구" 와 같은 값
    }
    return mask_home(json.dumps(report, ensure_ascii=False, indent=2))  # 버그 신고용이라 집 폴더(사용자 이름)를 가린다


def mask_home(text: str) -> str:
    """집 폴더 경로(사용자 이름이 들어 있음)를 `~` 로 가린다. 역슬래시·슬래시 두 표기 모두."""
    home = os.path.expanduser("~").rstrip("/\\")
    if len(home) <= 1:
        return text
    # JSON 안에서는 역슬래시가 두 번(\\) 쓰여 그 표기도 가린다
    forms = {home, home.replace("\\", "/"), home.replace("/", "\\"), home.replace("\\", "\\\\")}
    for form in sorted(forms, key=len, reverse=True):
        # 경로 경계에서만(/home/sam 이 /home/samuel 의 앞부분을 먹지 않게)
        # 뒤가 이름 글자(문자·숫자·_·-)가 아니면 경계: /home/sam: /home/sam, /home/sam. 도 가린다
        text = re.sub(re.escape(form) + r"(?![\w-])", "~", text)
    return text


def out_dir() -> str:
    """서버와 같은 출력 폴더(BLENDER_FX_OUT, 기본 ~/blender-fx-output). 만들지는 않는다."""
    return os.path.expanduser(os.environ.get("BLENDER_FX_OUT", "~/blender-fx-output"))


def last_error() -> dict | None:
    """서버가 출력 폴더 last_error.txt 에 남긴 마지막 도구 실패 {time, tool, message}(집 폴더는 ~). 없거나 못 읽으면 None.
    --json·MCP doctor 도구·--issue 가 같은 값을 써, AI 가 신고 초안을 만들 때도 오류 문장을 다시 묻지 않는다."""
    try:
        with open(os.path.join(out_dir(), "last_error.txt"), encoding="utf-8") as f:
            when, tool, line = f.readline().rstrip("\n").split("\t", 2)
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    return {"time": when, "tool": tool, "message": mask_home(line)}


def last_failure() -> str | None:
    """last_error() 를 "도구: 문장 (시각)" 한 줄로(마크다운 표 칸이라 | 는 \\|). 없으면 None."""
    err = last_error()
    if err is None:
        return None
    line = err["message"].replace("|", "\\|")
    return f"`{err['tool']}`: {line} ({err['time']})"


def format_issue(checks: list[dict]) -> str:
    """이슈에 그대로 붙일 마크다운. 집 폴더는 ~ 로 가린다. 항목·결과는 format_report 와 같다."""
    clients = ", ".join(registered_clients()) or "-"
    v = sys.version_info
    rows = [
        ("blender-fx-mcp", __version__),
        ("OS", f"{platform.system()} {platform.release()} ({platform.machine()})"),
        ("Python", f"{v.major}.{v.minor}.{v.micro}"),
        (t("블렌더 실행 파일", "Blender executable"), find_blender() or "-"),
        (t("MCP 클라이언트", "MCP clients"), clients),
        (t("언어", "Language"), f"{'en' if is_en() else 'ko'} ({lang_source()})"),
        (t("수신기", "Receiver"), f"{bridge.host()}:{bridge.port()}"),
        # 서버가 남긴 마지막 도구 실패. 신고할 때 오류 문장을 따로 복사해 붙이지 않아도 되게
        (t("최근 실패한 도구", "Last failed tool"), last_failure() or "-"),
    ]
    table = "\n".join(f"| {k} | {val} |" for k, val in rows)
    head = t("blender-fx-doctor 결과", "blender-fx-doctor result")
    block = (f"### {head}\n\n| | |\n|---|---|\n{table}\n\n"
             f"<details><summary>{t('점검 전체', 'All checks')}</summary>\n\n```text\n{format_report(checks)}\n```\n\n</details>\n")
    return mask_home(block)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="blender-fx-doctor",
                                     description=t("blender-fx-mcp 준비물 점검", "blender-fx-mcp prerequisite check"))
    parser.add_argument("--json", action="store_true",
                        help=t("결과를 JSON 으로 출력(버그 신고에 붙이기)", "print the result as JSON (for bug reports)"))
    parser.add_argument("--issue", action="store_true",
                        help=t("이슈에 붙일 마크다운(집 폴더는 ~ 로 가림)", "print Markdown to paste into an issue (home folder masked as ~)"))
    args = parser.parse_args(argv)
    if args.json and args.issue:
        parser.error(t("--json 과 --issue 는 함께 쓸 수 없습니다", "--json and --issue cannot be used together"))
    checks = run_checks()
    print(format_json(checks) if args.json else format_issue(checks) if args.issue else format_report(checks))
    critical = {"python", "mcp"}
    sys.exit(1 if any(not c["ok"] and c["id"] in critical for c in checks) else 0)

if __name__ == "__main__":
    main()
