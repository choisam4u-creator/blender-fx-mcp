# SPDX-License-Identifier: MIT
"""이슈 대응 기록: 열린 이슈·PR 마다 첫 답까지 며칠 걸렸는지 보고, SUPPORT.md 목표(보안·버그 7일, 그 밖 14일)를 넘은 것만 표로 낸다.

  uv run python scripts/triage_report.py                 # 이 저장소, 목표를 넘은 것만
  uv run python scripts/triage_report.py --all           # 목표 안인 것까지 모두
  uv run python scripts/triage_report.py --repo 주인/이름

GitHub 는 `gh api` 로만 묻는다(토큰은 gh 가 가진 것, 이 스크립트는 저장하지도 출력하지도 않음). gh 가 없거나 로그인 전이면 할 일을 알려 주고 2 로 끝난다.
"첫 답"은 글쓴이가 아닌 사람(봇 제외)의 첫 댓글, PR 이면 첫 리뷰도 친다. 봇이 연 PR(dependabot 등)과 관리자(OWNER·MEMBER·COLLABORATOR)가
연 것(자동 회차 PR 등, 답을 기다리는 사용자가 없음)은 `--include-bots`·`--include-own` 없이는 뺀다.
종료 코드: 0 = 목표를 넘은 것 없음, 1 = 있음(표를 보고 답하기), 2 = gh 문제·잘못된 인자.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime, timezone

DEFAULT_REPO = "choisam4u-creator/blender-fx-mcp"
OWN = {"OWNER", "MEMBER", "COLLABORATOR"}
# SUPPORT.md "응답 목표" 표와 같아야 한다(시험이 대조한다)
TARGET_DAYS = {"security": 7, "bug": 7}
OTHER_DAYS = 14

GH_HELP = (
    "gh(GitHub CLI)가 필요합니다. 설치: macOS `brew install gh`, 그 밖은 https://cli.github.com 을 본 뒤 `gh auth login` 으로 로그인하세요.\n"
    "gh (GitHub CLI) is required. Install it (macOS: `brew install gh`, others: https://cli.github.com), then run `gh auth login`."
)

Api = Callable[[str], list]


class GhError(RuntimeError):
    pass


def gh_api(path: str) -> list:
    """`gh api --paginate` 로 목록을 받는다. 쪽마다 따로 온 JSON 배열을 하나로 합친다."""
    if shutil.which("gh") is None:
        raise GhError(GH_HELP)
    proc = subprocess.run(["gh", "api", "--paginate", path], capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-1:] or [""]
        raise GhError(f"gh api {path} 실패 / failed: {tail[0]}\n{GH_HELP}")
    out, dec, text, i = [], json.JSONDecoder(), proc.stdout, 0
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue
        page, i = dec.raw_decode(text, i)
        out.extend(page if isinstance(page, list) else [page])
    return out


def _when(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def _is_bot(user: dict | None) -> bool:
    return not user or user.get("type") == "Bot" or user.get("login", "").endswith("[bot]")


def target_days(labels: list[str]) -> int:
    return min([TARGET_DAYS[name] for name in labels if name in TARGET_DAYS], default=OTHER_DAYS)


def first_reply(item: dict, repo: str, api: Api) -> datetime | None:
    """글쓴이가 아닌 사람의 첫 댓글(PR 이면 첫 리뷰 포함) 시각. 없으면 None."""
    author = (item.get("user") or {}).get("login")
    n = item["number"]
    stamps = [c["created_at"] for c in api(f"repos/{repo}/issues/{n}/comments?per_page=100")
              if not _is_bot(c.get("user")) and c["user"].get("login") != author]
    if "pull_request" in item:
        stamps += [r["submitted_at"] for r in api(f"repos/{repo}/pulls/{n}/reviews?per_page=100")
                   if r.get("submitted_at") and not _is_bot(r.get("user")) and r["user"].get("login") != author]
    return min((_when(s) for s in stamps), default=None)


def triage(repo: str, api: Api, now: datetime, include_bots: bool = False, include_own: bool = False) -> list[dict]:
    """열린 이슈·PR 마다 {번호, 종류, 제목, 목표 일수, 첫 답까지 일수(없으면 None), 지난 일수, 넘음}."""
    rows = []
    for item in api(f"repos/{repo}/issues?state=open&per_page=100"):
        if _is_bot(item.get("user")) and not include_bots:
            continue
        if item.get("author_association") in OWN and not include_own:
            continue
        labels = [lab["name"] for lab in item.get("labels", [])]
        opened = _when(item["created_at"])
        reply = first_reply(item, repo, api)
        days = target_days(labels)
        waited = ((reply or now) - opened).total_seconds() / 86400
        rows.append(dict(number=item["number"], kind="PR" if "pull_request" in item else "issue",
                         title=item["title"], labels=labels, target=days,
                         reply_days=None if reply is None else round(waited, 1),
                         age_days=round((now - opened).total_seconds() / 86400, 1), late=waited > days))
    return rows


def format_table(rows: list[dict], show_all: bool) -> str:
    shown = [r for r in rows if show_all or r["late"]]
    late = sum(r["late"] for r in rows)
    head = (f"열린 이슈·PR {len(rows)}개 중 첫 답 목표(SUPPORT.md)를 넘은 것 {late}개 / "
            f"{late} of {len(rows)} open issues and PRs are past the first-reply target (SUPPORT.md)")
    if not shown:
        return head
    lines = [head, "", "| # | 종류 / Kind | 제목 / Title | 라벨 / Labels | 목표 / Target | 첫 답 / First reply | 연 뒤 / Open for |",
             "|---|---|---|---|---|---|---|"]
    for r in sorted(shown, key=lambda r: (not r["late"], -r["age_days"])):
        reply = "없음 / none" if r["reply_days"] is None else f"{r['reply_days']}일 / d"
        title = r["title"].replace("|", "\\|")
        lines.append(f"| {r['number']} | {r['kind']} | {title} | {', '.join(r['labels']) or '-'} | {r['target']}일 / d "
                     f"| {reply}{' ⚠' if r['late'] else ''} | {r['age_days']}일 / d |")
    return "\n".join(lines)


def main(argv: list[str] | None = None, api: Api = gh_api, now: datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--all", action="store_true", help="목표 안인 것도 표에 / include items within target")
    ap.add_argument("--include-bots", action="store_true", help="봇이 연 PR 도 / include bot-opened PRs")
    ap.add_argument("--include-own", action="store_true", help="관리자가 연 것도 / include items opened by maintainers")
    args = ap.parse_args(argv)
    try:
        rows = triage(args.repo, api, now or datetime.now(timezone.utc), args.include_bots, args.include_own)
    except GhError as e:
        print(e, file=sys.stderr)
        return 2
    print(format_table(rows, args.all))
    return 1 if any(r["late"] for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
