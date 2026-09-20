"""자가 진단: 준비물이 갖춰졌는지 한 번에 확인한다. 이슈 올리기 전에 먼저 돌려 본다.

  uv run blender-fx-doctor
"""

from __future__ import annotations

import glob
import os
import platform
import shutil
import subprocess
import sys
from importlib import metadata

from . import bridge
from .headless import find_blender
from .i18n import t

ADDON_GLOBS = [
    "~/Library/Application Support/Blender/*/scripts/addons/blender_mcp.py",  # macOS
    "~/.config/blender/*/scripts/addons/blender_mcp.py",  # Linux
    "~/AppData/Roaming/Blender Foundation/Blender/*/scripts/addons/blender_mcp.py",  # Windows
    "~/Library/Application Support/Blender/*/extensions/*/*blender_mcp*/__init__.py",
]


def _check(name: str, ok: bool, detail: str) -> dict:
    return {"name": name, "ok": ok, "detail": detail}


def run_checks() -> list[dict]:
    out: list[dict] = []
    v = sys.version_info
    out.append(_check("python", v >= (3, 10), f"{v.major}.{v.minor}.{v.micro} ({platform.system()} {platform.machine()})"))

    name_mcp = t("mcp 라이브러리", "mcp library")
    try:
        out.append(_check(name_mcp, True, metadata.version("mcp")))
    except Exception as e:  # pragma: no cover
        out.append(_check(name_mcp, False, t(f"설치 안 됨: {e}", f"not installed: {e}")))

    uv = shutil.which("uv")
    out.append(_check("uv", uv is not None, uv or t("PATH 에 없음. brew install uv", "not on PATH. brew install uv")))

    name_blender = t("블렌더 실행 파일", "Blender executable")
    blender = find_blender()
    if blender:
        try:
            ver = subprocess.run([blender, "--version"], capture_output=True, text=True, timeout=30).stdout.splitlines()[0]
        except Exception as e:
            ver = t(f"실행 실패: {e}", f"failed to run: {e}")
        out.append(_check(name_blender, True, f"{blender} — {ver}"))
    else:
        out.append(_check(name_blender, False, t(
            "못 찾음. BLENDER_FX_BLENDER 환경변수로 경로를 알려주세요 (헤드리스 테스트에만 필요)",
            "not found. Set BLENDER_FX_BLENDER to its path (only needed for headless tests)")))

    found = [p for g in ADDON_GLOBS for p in glob.glob(os.path.expanduser(g))]
    out.append(_check(t("수신기 애드온 파일(blender-mcp)", "receiver add-on file (blender-mcp)"), bool(found),
                      found[0] if found else t(
                          "블렌더 애드온 폴더에 blender_mcp.py 가 없음. https://github.com/ahujasid/blender-mcp 의 addon.py 를 설치하세요",
                          "blender_mcp.py is not in the Blender add-ons folder. Install addon.py from https://github.com/ahujasid/blender-mcp")))

    name_conn = t("수신기 연결", "receiver connection")
    try:
        bridge.ping()
        out.append(_check(name_conn, True, t(f"{bridge.host()}:{bridge.port()} 응답함", f"{bridge.host()}:{bridge.port()} responded")))
    except bridge.BlenderError as e:
        out.append(_check(name_conn, False, str(e)))

    name_out = t("출력 폴더", "output folder")
    root = os.path.expanduser(os.environ.get("BLENDER_FX_OUT", "~/blender-fx-output"))
    try:
        os.makedirs(root, exist_ok=True)
        test = os.path.join(root, ".write_test")
        with open(test, "w") as f:
            f.write("ok")
        os.remove(test)
        out.append(_check(name_out, True, root))
    except Exception as e:
        out.append(_check(name_out, False, t(f"{root} 에 쓸 수 없음: {e}", f"cannot write to {root}: {e}")))
    return out


def format_report(checks: list[dict]) -> str:
    lines = [f"[{'OK' if c['ok'] else 'X '}] {c['name']}: {c['detail']}" for c in checks]
    bad = [c["name"] for c in checks if not c["ok"]]
    lines.append(t("모두 정상입니다.", "Everything looks good.") if not bad
                 else t(f"확인 필요: {', '.join(bad)}", f"Needs attention: {', '.join(bad)}"))
    return "\n".join(lines)


def main() -> None:
    checks = run_checks()
    print(format_report(checks))
    critical = {"python", "mcp 라이브러리", "mcp library"}
    sys.exit(1 if any(not c["ok"] and c["name"] in critical for c in checks) else 0)


if __name__ == "__main__":
    main()
