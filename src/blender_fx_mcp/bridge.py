# SPDX-License-Identifier: MIT
"""블렌더 안 수신기(blender-mcp 애드온)와 소켓으로 대화하는 부분.

수신기는 JSON 한 덩어리 {"type": ..., "params": {...}} 를 받아 블렌더 메인 스레드에서 실행하고
{"status": "success", "result": {...}} 또는 {"status": "error", "message": "..."} 를 돌려준다.
명령마다 새로 연결하고 끊는다. 다른 MCP 서버(blender-mcp 자체 등)와 수신기를 같이 쓸 때
충돌을 줄이기 위해서다.
"""

from __future__ import annotations

import glob
import json
import os
import socket

from .i18n import t


# 오류 문장 끝에 붙이는 해결법 문서. 문서의 절 제목이 바뀌면 tests/test_troubleshooting.py 가 알려 준다
TROUBLESHOOTING_URL = "https://github.com/choisam4u-creator/blender-fx-mcp/blob/main/docs/troubleshooting.md"


class BlenderError(RuntimeError):
    """사용자에게 그대로 보여줄 오류 메시지"""


def host() -> str:
    return os.environ.get("BLENDER_FX_HOST", "localhost")


DEFAULT_PORT = 9876  # blender-mcp 수신기 애드온의 기본 포트


def _env_number(name: str, kind: type, default: float, low: float, high: float | None = None):
    """숫자 환경변수. 비었으면 기본값, 숫자가 아니거나 범위 밖이면 고칠 곳을 말하는 BlenderError."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = kind(raw)
    except ValueError:
        value = None
    if value is None or value != value or value < low or (high is not None and value > high):  # value != value: NaN
        span = (t(f"{low:g}~{high:g} 의 숫자", f"a number, {low:g}-{high:g}") if high is not None
                else t(f"{low:g} 이상의 숫자", f"a number, at least {low:g}"))
        raise BlenderError(t(
            f"환경변수 {name}={raw!r} 은(는) 쓸 수 없습니다({span}). MCP 설정에서 고치거나 지운 뒤 클라이언트를 다시 시작하세요.",
            f"The environment variable {name}={raw!r} is not valid ({span}). "
            "Fix or remove it in your MCP config and restart the client."))
    return value


def check_env() -> None:
    """연결에 쓰는 숫자 환경변수를 미리 본다. 잘못됐으면 BlenderError(모든 도구가 같은 문장을 낸다)."""
    _env_number("BLENDER_FX_PORT", int, DEFAULT_PORT, 1, 65535)
    _env_number("BLENDER_FX_TIMEOUT", float, 600.0, 1)


def port() -> int:
    # 화면에 보이는 값. 잘못된 값이면 기본값을 보이고, 실제 연결은 check_env 가 막는다
    try:
        return _env_number("BLENDER_FX_PORT", int, DEFAULT_PORT, 1, 65535)
    except BlenderError:
        return DEFAULT_PORT


# 수신기 애드온(blender-mcp)이 설치되는 곳. doctor 의 "수신기 애드온 파일" 줄과 연결 거부 안내가 같이 쓴다
ADDON_GLOBS = [
    "~/Library/Application Support/Blender/*/scripts/addons/blender_mcp.py",  # macOS
    "~/.config/blender/*/scripts/addons/blender_mcp.py",  # Linux
    "~/AppData/Roaming/Blender Foundation/Blender/*/scripts/addons/blender_mcp.py",  # Windows
    "~/Library/Application Support/Blender/*/extensions/*/*blender_mcp*/__init__.py",
]

ADDON_URL = "https://github.com/ahujasid/blender-mcp"


def addon_files() -> list[str]:
    # normpath: Windows 에서 expanduser 가 붙인 `\` 와 패턴의 `/` 가 섞여 보이지 않게
    return [os.path.normpath(p) for g in ADDON_GLOBS for p in glob.glob(os.path.expanduser(g))]


def is_local() -> bool:
    return host() in ("localhost", "127.0.0.1", "::1")


def connect_steps() -> str:
    """연결이 거부됐을 때 사용자가 할 다음 단계. 원인을 좁혀 하나만 고른다.

    - 이 컴퓨터에 애드온 파일이 없음 → 설치부터(이미 깔았는데 못 찾는 경우를 위해 Connect 도 이어서 말한다)
    - 애드온은 있음 → 블렌더를 켜고 Connect
    - BLENDER_FX_PORT 를 바꿨음 → 애드온 패널의 Port 도 같은 값으로(위 둘에 덧붙인다)
    다른 컴퓨터의 블렌더(BLENDER_FX_HOST)면 이 컴퓨터의 애드온 폴더는 볼 이유가 없어 Connect 만 말한다.
    """
    connect = t("블렌더를 켜고, 3D 화면에서 N 키 → BlenderMCP 탭 → Connect to MCP server 를 누르세요.",
                "Open Blender, press N in the 3D view, go to the BlenderMCP tab and click Connect to MCP server.")
    if is_local() and not addon_files():
        step = t(
            f"수신기 애드온(blender-mcp)을 찾지 못했습니다. 아직 설치하지 않았다면 {ADDON_URL} 에서 addon.py 를 받아 "
            "블렌더 Edit → Preferences → Add-ons → 오른쪽 위 ▾ → Install from Disk 로 설치하고 체크한 뒤, "
            "3D 화면에서 N 키 → BlenderMCP 탭 → Connect to MCP server 를 누르세요.",
            f"The receiver add-on (blender-mcp) was not found. If you have not installed it, download addon.py from {ADDON_URL}, "
            "then in Blender Edit → Preferences → Add-ons → top-right ▾ → Install from Disk, tick it, and "
            "press N in the 3D view → BlenderMCP tab → Connect to MCP server.")
    else:
        step = connect
    if port() != DEFAULT_PORT:
        step += t(f" BLENDER_FX_PORT 가 {port()} 이므로 BlenderMCP 탭의 Port 도 {port()} 인지 확인하세요"
                  f"(애드온 기본값은 {DEFAULT_PORT}).",
                  f" BLENDER_FX_PORT is {port()}, so make sure Port in the BlenderMCP tab is also {port()}"
                  f" (the add-on default is {DEFAULT_PORT}).")
    return step


def default_timeout() -> float:
    # 굽기·렌더는 몇 분 걸릴 수 있어 기본 10분. 0·음수·숫자가 아니면 기본값(연결 전에 check_env 가 알린다)
    try:
        return _env_number("BLENDER_FX_TIMEOUT", float, 600.0, 1)
    except BlenderError:
        return 600.0


def _decode(buf: bytes) -> dict | None:
    """받은 바이트에서 JSON 객체 하나. 아직 덜 왔으면 None. 객체 뒤의 군더더기는 무시한다."""
    try:
        text = buf.decode("utf-8")
    except UnicodeDecodeError:
        return None  # 여러 바이트 글자가 반쯤 온 것
    try:
        obj, _ = json.JSONDecoder().raw_decode(text.lstrip())
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        raise BlenderError(t(f"블렌더 수신기가 알 수 없는 응답을 보냈습니다: {text[:200]!r}. 수신기 애드온(blender-mcp)이 맞는지 확인하세요.",
                             f"The Blender receiver sent an unexpected response: {text[:200]!r}. "
                             "Check that the receiver is the blender-mcp add-on."))
    return obj


def send_command(cmd_type: str, params: dict | None = None, timeout: float | None = None) -> dict:
    check_env()
    payload = json.dumps({"type": cmd_type, "params": params or {}}).encode("utf-8")
    timeout = default_timeout() if timeout is None else timeout
    chunks = bytearray()
    resp: dict | None = None
    connected = False  # 연결 단계(10초 고정)의 시간 초과는 BLENDER_FX_TIMEOUT 과 무관하다
    try:
        with socket.create_connection((host(), port()), timeout=10.0) as s:
            connected = True
            s.settimeout(timeout)
            s.sendall(payload)
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                chunks += chunk
                # 큰 응답을 조각마다 처음부터 다시 풀지 않게, 객체가 끝났을 법할 때(마지막 글자가 }) 만 풀어 본다
                if chunk.rstrip().endswith(b"}"):
                    resp = _decode(bytes(chunks))
                    if resp is not None:
                        break
    except (ConnectionRefusedError, OSError) as e:
        if connected and isinstance(e, socket.timeout):
            raise BlenderError(t(
                f"블렌더가 {timeout:.0f}초 안에 응답하지 않았습니다(시간 초과). 굽기나 렌더가 너무 오래 걸리거나 블렌더가 멈췄을 수 있습니다. "
                "조각 수(pieces)나 프레임 수(frames)를 줄여 보세요. 무거운 장면을 일부러 굽는 중이면 "
                "MCP 설정의 환경변수 BLENDER_FX_TIMEOUT(초)을 더 크게 주고 다시 시작하세요. "
                f"해결법: {TROUBLESHOOTING_URL}#timeout",
                f"Blender did not respond within {timeout:.0f} s. A bake or render may be too heavy, or Blender is stuck. "
                "Try lowering pieces or frames. If the heavy scene is intended, set the environment variable "
                "BLENDER_FX_TIMEOUT (seconds) higher in your MCP config and restart. "
                f"Help: {TROUBLESHOOTING_URL}#timeout",
            )) from e
        if connected:  # 연결은 됐는데 명령 도중 끊김: 설치·Connect 안내는 틀린 말이다
            raise BlenderError(t(
                f"명령 도중 블렌더와의 연결이 끊겼습니다({e.__class__.__name__}). 블렌더가 멈추거나 꺼졌을 수 있고, 명령이 일부 실행됐을 수 있습니다. "
                "블렌더 창을 확인하고, 꺼졌다면 다시 켜서 Connect 한 뒤 restore 로 직전 스냅샷을 불러오세요. "
                f"해결법: {TROUBLESHOOTING_URL}#empty-response-blender-error",
                f"The connection to Blender dropped during the command ({e.__class__.__name__}). Blender may have frozen or quit, "
                "and the command may have partly run. Check the Blender window; if it closed, reopen it, click Connect and "
                f"restore the last snapshot. Help: {TROUBLESHOOTING_URL}#empty-response-blender-error",
            )) from e
        raise BlenderError(t(
            f"블렌더에 연결할 수 없습니다({host()}:{port()}). {connect_steps()} "
            f"해결법: {TROUBLESHOOTING_URL}#connection-refused",
            f"Cannot connect to Blender ({host()}:{port()}). {connect_steps()} "
            f"Help: {TROUBLESHOOTING_URL}#connection-refused",
        )) from e

    if resp is None and chunks:
        resp = _decode(bytes(chunks))  # 끝이 } 가 아니었어도(뒤에 공백·군더더기) 연결이 닫혔으면 한 번 더
    if resp is None and chunks:
        raise BlenderError(t(
            f"블렌더 응답이 중간에 끊겼습니다({len(chunks)}바이트 받음). 블렌더가 응답 도중 멈췄거나 꺼졌을 수 있습니다. 블렌더 창을 확인하세요. "
            f"해결법: {TROUBLESHOOTING_URL}#empty-response-blender-error",
            f"Blender's response was cut off ({len(chunks)} bytes received). Blender may have frozen or quit while answering. "
            f"Check the Blender window. Help: {TROUBLESHOOTING_URL}#empty-response-blender-error"))
    if resp is None:
        raise BlenderError(t("블렌더가 빈 응답을 보냈습니다. 수신기 애드온이 켜져 있는지 확인하세요.",
                             "Blender sent an empty response. Check that the receiver add-on is running."))
    if resp.get("status") != "success":
        # 레시피 오류는 FX_RESULT 로 오므로, 여기까지 왔으면 수신기 쪽 실패 — 버그일 가능성이 커서 신고 방법을 알려 준다
        raise BlenderError(t(f"블렌더 오류: {resp.get('message', '(메시지 없음)')}. 버그일 수 있습니다. "
                             f"uvx --from blender-fx-mcp blender-fx-doctor --issue 결과를 붙여 신고해 주세요. 해결법: {TROUBLESHOOTING_URL}#empty-response-blender-error",
                             f"Blender error: {resp.get('message', '(no message)')}. This may be a bug; please report it with "
                             f"the output of uvx --from blender-fx-mcp blender-fx-doctor --issue. Help: {TROUBLESHOOTING_URL}#empty-response-blender-error"))
    return resp.get("result") or {}


def ping() -> bool:
    result = send_command("ping", timeout=10.0)
    return bool(result.get("pong"))


SUPPORTED_BLENDER = "5.2"  # SUPPORT.md 의 지원 LTS 판. 바꾸면 SUPPORT 표도(tests/test_server.py 가 비교한다)


def blender_version() -> str:
    """수신기에 물어 연결된 블렌더의 판 문자열(예: '5.2.0 LTS'). 못 알아내면 빈 문자열."""
    try:
        lines = run_python("import bpy\nprint(bpy.app.version_string)", timeout=10.0).strip().splitlines()
    except BlenderError:
        return ""
    return lines[-1].strip() if lines else ""


def version_warning(version: str) -> str:
    """지원 판이 아니면 한 줄 경고, 맞거나 모르면 빈 문자열."""
    if not version or version == SUPPORTED_BLENDER or version.startswith(SUPPORTED_BLENDER + "."):
        return ""
    return t(f"블렌더 {version} 은 시험한 판이 아닙니다(지원: {SUPPORTED_BLENDER} LTS). 효과가 실패하면 {SUPPORTED_BLENDER} LTS 로 다시 해 보세요.",
             f"Blender {version} is not a tested version (supported: {SUPPORTED_BLENDER} LTS). "
             f"If an effect fails, try again with {SUPPORTED_BLENDER} LTS.")


def run_python(code: str, timeout: float | None = None) -> str:
    """파이썬 코드를 블렌더에서 실행하고 표준 출력을 돌려준다."""
    result = send_command("execute_code", {"code": code}, timeout=timeout)
    return str(result.get("result", ""))
