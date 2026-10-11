# SPDX-License-Identifier: MIT
"""Mac 실측 보고: CLOUD-NOTES 맨 위 "맥에서 돌릴 명령" 을 차례로 돌려 docs/test-reports/latest.md 를 다시 쓴다.

  uv run python scripts/mac_report.py              # 명령을 돌리고 latest.md 를 새로 씀(커밋은 사람이)
  uv run python scripts/mac_report.py --dry-run    # 돌릴 명령만 보여 줌

클라우드 회차는 latest.md 를 읽고 FAIL 부터 고친다. 명령 줄 끝의 `# …` 는 "확인할 것" 칸으로 옮긴다.
출력의 집 폴더는 `~` 로 가린다(저장소에 올라가므로). 명령 하나가 실패해도 나머지를 마저 돌린다.
"""

from __future__ import annotations

import argparse
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTES = ROOT / "docs" / "test-reports" / "CLOUD-NOTES.md"
OUT = ROOT / "docs" / "test-reports" / "latest.md"
sys.path.insert(0, str(ROOT / "src"))

from blender_fx_mcp.doctor import mask_home  # noqa: E402
from blender_fx_mcp.headless import find_blender  # noqa: E402


def mac_commands(notes: str) -> list[tuple[str, str]]:
    """CLOUD-NOTES 의 '## 맥에서 돌릴 명령' 절 첫 코드 블록 → (명령, 확인할 것)."""
    m = re.search(r"^## 맥에서 돌릴 명령[^\n]*\n.*?```\w*\n(.*?)```", notes, re.S | re.M)
    if not m:
        return []
    out = []
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cmd, _, note = line.partition("  #")  # 명령 안의 '#' 은 두 칸 띄운 주석만 주석으로 본다
        out.append((cmd.strip(), note.strip().lstrip("#").strip()))
    return out


def run(cmd: str, timeout: float) -> tuple[bool, float, str]:
    start = time.monotonic()
    try:
        p = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
        ok, output = p.returncode == 0, (p.stdout + p.stderr)
    except subprocess.TimeoutExpired as e:
        ok, output = False, f"시간 초과({timeout:.0f}초) / timed out\n{e.stdout or ''}"
    return ok, time.monotonic() - start, output


def summary_line(output: str) -> str:
    """결과 칸에 넣을 한 줄: pytest 요약이 있으면 그것, 없으면 마지막 줄."""
    lines = [x.strip() for x in output.splitlines() if x.strip()]
    found = [x for x in lines if re.search(r"\d+ (passed|failed)", x)]
    text = (found or lines or [""])[-1]
    return text.replace("|", "/")[:160]


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "?"


def blender_version() -> str:
    exe = find_blender()
    if not exe:
        return "블렌더 없음"
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=60).stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        return "블렌더 실행 실패"
    return out[0].strip() if out else "블렌더 판 모름"


def report(results: list[tuple[str, str, bool, float, str]], when: str, branch: str, commit: str, env: str) -> str:
    failed = [r for r in results if not r[2]]
    verdict = "**PASS**" if not failed else f"**FAIL** — {len(failed)}개 실패"
    rows = "\n".join(
        f"| `{cmd}` | {'PASS' if ok else '**FAIL**'} ({secs:.0f}초) {summary_line(out)} | {note} |"
        for cmd, note, ok, secs, out in results)
    text = f"""# Mac 시험 결과 (최신)

- 날짜: {when}
- 시험한 브랜치: `{branch}` (커밋 {commit})
- 환경: {env}
- 종합: {verdict}
- 만든 방법: `uv run python scripts/mac_report.py` (CLOUD-NOTES 맨 위 명령을 그대로 돌림)

| 명령 | 결과 | 확인할 것 |
|---|---|---|
{rows}
"""
    if failed:
        text += "\n## 실패 핵심\n"
        for cmd, _, _, _, out in failed:
            tail = "\n".join(out.strip().splitlines()[-25:])
            text += f"\n`{cmd}`\n\n```\n{tail}\n```\n"
        text += "\n## 다음 클라우드 회차가 할 일 (이것부터)\n\n- 위 실패를 고친다.\n"
    return mask_home(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mac_report.py", description="CLOUD-NOTES 의 Mac 명령을 돌려 latest.md 를 쓴다")
    parser.add_argument("--dry-run", action="store_true", help="돌릴 명령만 출력")
    parser.add_argument("--notes", type=Path, default=NOTES)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--timeout", type=float, default=1800.0, help="명령 하나의 시간 제한(초)")
    args = parser.parse_args(argv)
    commands = mac_commands(args.notes.read_text(encoding="utf-8"))
    if not commands:
        print(f"{args.notes} 에 '## 맥에서 돌릴 명령' 코드 블록이 없습니다", file=sys.stderr)
        return 2
    if args.dry_run:
        for cmd, note in commands:
            print(f"{cmd}    # {note}" if note else cmd)
        return 0
    results = []
    for i, (cmd, note) in enumerate(commands, 1):
        print(f"[{i}/{len(commands)}] {cmd}", flush=True)
        ok, secs, out = run(cmd, args.timeout)
        print(f"    {'PASS' if ok else 'FAIL'} ({secs:.0f}s) {summary_line(out)}", flush=True)
        results.append((cmd, note, ok, secs, out))
    v = sys.version_info
    env = f"{platform.system()} {platform.machine()} {platform.mac_ver()[0] or platform.release()}, {blender_version()}, " \
          f"Python {v.major}.{v.minor}.{v.micro}"
    text = report(results, time.strftime("%Y-%m-%d"), git("rev-parse", "--abbrev-ref", "HEAD"),
                  git("rev-parse", "--short", "HEAD"), env)
    args.out.write_text(text, encoding="utf-8")
    print(f"썼습니다: {args.out} — 확인 뒤 커밋하세요")
    return 0 if all(r[2] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
