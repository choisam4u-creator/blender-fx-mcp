"""블렌더 안 수신기(blender-mcp 애드온)와 소켓으로 대화하는 부분.

수신기는 JSON 한 덩어리 {"type": ..., "params": {...}} 를 받아 블렌더 메인 스레드에서 실행하고
{"status": "success", "result": {...}} 또는 {"status": "error", "message": "..."} 를 돌려준다.
명령마다 새로 연결하고 끊는다. 다른 MCP 서버(blender-mcp 자체 등)와 수신기를 같이 쓸 때
충돌을 줄이기 위해서다.
"""

from __future__ import annotations

import json
import os
import socket

from .i18n import t


class BlenderError(RuntimeError):
    """사용자에게 그대로 보여줄 오류 메시지"""


def host() -> str:
    return os.environ.get("BLENDER_FX_HOST", "localhost")


def port() -> int:
    return int(os.environ.get("BLENDER_FX_PORT", "9876"))


def default_timeout() -> float:
    # 굽기·렌더는 몇 분 걸릴 수 있어 기본 10분
    return float(os.environ.get("BLENDER_FX_TIMEOUT", "600"))


def send_command(cmd_type: str, params: dict | None = None, timeout: float | None = None) -> dict:
    payload = json.dumps({"type": cmd_type, "params": params or {}}).encode("utf-8")
    timeout = timeout or default_timeout()
    buf = b""
    resp: dict | None = None
    try:
        with socket.create_connection((host(), port()), timeout=10.0) as s:
            s.settimeout(timeout)
            s.sendall(payload)
            while True:
                chunk = s.recv(65536)
                if not chunk:
                    break
                buf += chunk
                try:
                    resp = json.loads(buf.decode("utf-8"))
                    break
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # 아직 덜 온 것. 더 받는다
                    continue
    except (ConnectionRefusedError, OSError) as e:
        if isinstance(e, socket.timeout):
            raise BlenderError(t(
                "블렌더가 응답하지 않습니다(시간 초과). 굽기나 렌더가 너무 오래 걸리거나 블렌더가 멈췄을 수 있습니다. "
                "조각 수(pieces)나 프레임 수(frames)를 줄여 보세요.",
                "Blender did not respond in time. A bake or render may be too heavy, or Blender is stuck. "
                "Try lowering pieces or frames.",
            )) from e
        raise BlenderError(t(
            f"블렌더에 연결할 수 없습니다({host()}:{port()}). "
            "블렌더를 켜고, 3D 화면에서 N 키 → BlenderMCP 탭 → 서버 시작(Connect)을 눌렀는지 확인하세요.",
            f"Cannot connect to Blender ({host()}:{port()}). "
            "Open Blender, press N in the 3D view, go to the BlenderMCP tab and start the server.",
        )) from e

    if resp is None:
        raise BlenderError(t("블렌더가 빈 응답을 보냈습니다. 수신기 애드온이 켜져 있는지 확인하세요.",
                             "Blender sent an empty response. Check that the receiver add-on is running."))
    if resp.get("status") != "success":
        raise BlenderError(t(f"블렌더 오류: {resp.get('message', '(메시지 없음)')}",
                             f"Blender error: {resp.get('message', '(no message)')}"))
    return resp.get("result") or {}


def ping() -> bool:
    result = send_command("ping", timeout=10.0)
    return bool(result.get("pong"))


def run_python(code: str, timeout: float | None = None) -> str:
    """파이썬 코드를 블렌더에서 실행하고 표준 출력을 돌려준다."""
    result = send_command("execute_code", {"code": code}, timeout=timeout)
    return str(result.get("result", ""))
