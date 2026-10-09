# SPDX-License-Identifier: MIT
"""자가 진단: 준비물이 갖춰졌는지 한 번에 확인한다. 이슈 올리기 전에 먼저 돌려 본다.

  uv run blender-fx-doctor          # 사람이 읽는 줄
  uv run blender-fx-doctor --json   # 기계가 읽는 JSON(항목 id 는 언어와 상관없이 같다)
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import platform
import shutil
import subprocess
import sys
from importlib import metadata

from . import __version__, bridge
from .headless import find_blender
from .i18n import is_en, t

ADDON_GLOBS = [
    "~/Library/Application Support/Blender/*/scripts/addons/blender_mcp.py",  # macOS
    "~/.config/blender/*/scripts/addons/blender_mcp.py",  # Linux
    "~/AppData/Roaming/Blender Foundation/Blender/*/scripts/addons/blender_mcp.py",  # Windows
    "~/Library/Application Support/Blender/*/extensions/*/*blender_mcp*/__init__.py",
]


def _check(name: str, ok: bool, detail: str, key: str = "") -> dict:
    # key 는 --json 의 id. 화면 이름(name)은 언어에 따라 바뀌어도 id 는 그대로라 신고끼리 비교할 수 있다.
    return {"id": key or name, "name": name, "ok": ok, "detail": detail}


def run_checks() -> list[dict]:
    out: list[dict] = []
    v = sys.version_info
    out.append(_check("python", v >= (3, 10), f"{v.major}.{v.minor}.{v.micro} ({platform.system()} {platform.machine()})",
                      "python"))

    # 이슈에 붙인 결과만 보고 어느 판인지 알 수 있게 맨 위에 둔다
    out.append(_check("blender-fx-mcp", True, __version__, "blender-fx-mcp"))

    name_mcp = t("mcp 라이브러리", "mcp library")
    try:
        out.append(_check(name_mcp, True, metadata.version("mcp"), "mcp"))
    except Exception as e:
        out.append(_check(name_mcp, False, t(f"설치 안 됨: {e}", f"not installed: {e}"), "mcp"))

    uv = shutil.which("uv")
    out.append(_check("uv", uv is not None, uv or t("PATH 에 없음. brew install uv", "not on PATH. brew install uv"), "uv"))

    name_blender = t("블렌더 실행 파일", "Blender executable")
    blender = find_blender()
    if blender:
        try:
            lines = subprocess.run([blender, "--version"], capture_output=True, text=True, timeout=30).stdout.splitlines()
            ver = lines[0] if lines else t("버전 출력 없음", "printed no version")
        except Exception as e:
            ver = t(f"실행 실패: {e}", f"failed to run: {e}")
        out.append(_check(name_blender, True, f"{blender} — {ver}", "blender"))
    else:
        out.append(_check(name_blender, False, t(
            "못 찾음. BLENDER_FX_BLENDER 환경변수로 경로를 알려주세요 (헤드리스 테스트에만 필요)",
            "not found. Set BLENDER_FX_BLENDER to its path (only needed for headless tests)"), "blender"))

    # normpath: Windows 에서 expanduser 가 붙인 `\` 와 패턴의 `/` 가 섞여 보이지 않게
    found = [os.path.normpath(p) for g in ADDON_GLOBS for p in glob.glob(os.path.expanduser(g))]
    out.append(_check(t("수신기 애드온 파일(blender-mcp)", "receiver add-on file (blender-mcp)"), bool(found),
                      found[0] if found else t(
                          "블렌더 애드온 폴더에 blender_mcp.py 가 없음. https://github.com/ahujasid/blender-mcp 의 addon.py 를 설치하세요",
                          "blender_mcp.py is not in the Blender add-ons folder. Install addon.py from https://github.com/ahujasid/blender-mcp"),
                      "addon"))

    name_conn = t("수신기 연결", "receiver connection")
    try:
        bridge.ping()
        out.append(_check(name_conn, True, t(f"{bridge.host()}:{bridge.port()} 응답함", f"{bridge.host()}:{bridge.port()} responded"),
                          "connection"))
    except bridge.BlenderError as e:
        out.append(_check(name_conn, False, str(e), "connection"))

    name_out = t("출력 폴더", "output folder")
    root = os.path.expanduser(os.environ.get("BLENDER_FX_OUT", "~/blender-fx-output"))
    try:
        os.makedirs(root, exist_ok=True)
        test = os.path.join(root, ".write_test")
        with open(test, "w") as f:
            f.write("ok")
        os.remove(test)
        out.append(_check(name_out, True, root, "output"))
    except Exception as e:
        out.append(_check(name_out, False, t(f"{root} 에 쓸 수 없음: {e}", f"cannot write to {root}: {e}"), "output"))
    return out


def format_report(checks: list[dict]) -> str:
    lines = [f"[{'OK' if c['ok'] else 'X '}] {c['name']}: {c['detail']}" for c in checks]
    bad = [c["name"] for c in checks if not c["ok"]]
    lines.append(t("모두 정상입니다.", "Everything looks good.") if not bad
                 else t(f"확인 필요: {', '.join(bad)}. 해결법: {bridge.TROUBLESHOOTING_URL}",
                        f"Needs attention: {', '.join(bad)}. Help: {bridge.TROUBLESHOOTING_URL}"))
    return "\n".join(lines)


def format_json(checks: list[dict]) -> str:
    """버그 신고에 붙여 그대로 비교·재현할 수 있는 JSON. 항목·결과는 format_report 와 같다."""
    bad = [c["id"] for c in checks if not c["ok"]]
    report = {
        "blender_fx_mcp": __version__,
        "lang": "en" if is_en() else "ko",
        "ok": not bad,
        "blender": find_blender(),
        "host": bridge.host(),
        "port": bridge.port(),
        "checks": [{"id": c["id"], "name": c["name"], "ok": c["ok"], "detail": c["detail"]} for c in checks],
        "failed": bad,
        "help": bridge.TROUBLESHOOTING_URL if bad else None,
    }
    return json.dumps(report, ensure_ascii=False, indent=2)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="blender-fx-doctor",
                                     description=t("blender-fx-mcp 준비물 점검", "blender-fx-mcp prerequisite check"))
    parser.add_argument("--json", action="store_true",
                        help=t("결과를 JSON 으로 출력(버그 신고에 붙이기)", "print the result as JSON (for bug reports)"))
    args = parser.parse_args(argv)
    checks = run_checks()
    print(format_json(checks) if args.json else format_report(checks))
    critical = {"python", "mcp"}
    sys.exit(1 if any(not c["ok"] and c["id"] in critical for c in checks) else 0)

if __name__ == "__main__":
    main()
