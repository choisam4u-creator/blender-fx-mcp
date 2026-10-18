# SPDX-License-Identifier: MIT
"""이슈 대응 기록: 열린 이슈·PR 마다 첫 답까지 며칠 걸렸는지 보고, SUPPORT.md 목표(보안·버그 7일, 그 밖 14일)를 넘은 것만 표로 낸다.
기본 브랜치와 열린 PR 브랜치의 최신 CI 도 보고, 빨간 워크플로마다 빨간 지 며칠째인지와 실패한 잡 이름을 표로 낸다(3일 넘으면 ⚠).
재실행해서야 초록이 된 실행(흔들리는 시험)은 표 아래 "흔들림" 줄로 남긴다(종료 코드에는 안 셈).

  uv run python scripts/triage_report.py                 # 이 저장소, 목표를 넘은 것만 + 빨간 CI
  uv run python scripts/triage_report.py --all           # 목표 안인 것까지 모두
  uv run python scripts/triage_report.py --no-ci         # CI 칸 없이(이슈·PR 첫 답만)
  uv run python scripts/triage_report.py --repo 주인/이름

GitHub 는 `gh api` 로만 묻는다(토큰은 gh 가 가진 것, 이 스크립트는 저장하지도 출력하지도 않음). gh 가 없거나 로그인 전이면 할 일을 알려 주고 2 로 끝난다.
"첫 답"은 글쓴이가 아닌 사람(봇 제외)의 첫 댓글, PR 이면 첫 리뷰도 친다. 봇이 연 PR(dependabot 등)과 관리자(OWNER·MEMBER·COLLABORATOR)가
연 것(자동 회차 PR 등, 답을 기다리는 사용자가 없음)은 `--include-bots`·`--include-own` 없이는 뺀다.
종료 코드: 0 = 목표를 넘은 것도, 3일 넘게 빨간 CI 도 없음, 1 = 있음(표를 보고 답하기·고치기), 2 = gh 문제·잘못된 인자.
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
# CI 가 이만큼 넘게 빨가면 ⚠(10/15~17 lint 빨강이 3일 동안 아무도 몰랐던 것)
CI_RED_DAYS = 3
CI_LOOKBACK_DAYS = 30
RED = {"failure", "timed_out", "startup_failure"}
# 결과가 건강을 말하지 않는 실행: 새 push 로 취소(concurrency), 조건으로 건너뜀, 포크 PR 승인 대기. 최신·연속을 셀 때 건너뛴다
# (빼지 않으면 빨간 main 위에 취소된 실행 하나가 CI 를 초록으로 보이게 한다)
NO_SIGNAL = {"cancelled", "skipped", "neutral", "action_required", "stale"}

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


def _runs(repo: str, branch: str, api: Api, since: str) -> list[dict]:
    """그 브랜치의 끝난 실행(최근 CI_LOOKBACK_DAYS 일, --paginate 가 끝없이 받지 않게 날짜로 묶음), 새것부터."""
    pages = api(f"repos/{repo}/actions/runs?branch={branch}&status=completed&created=%3E%3D{since}&per_page=100")
    runs = [r for page in pages for r in page.get("workflow_runs", [])]
    return sorted(runs, key=lambda r: r["created_at"], reverse=True)


def _flaky(repo: str, runs: list[dict], api: Api) -> list[dict]:
    """재실행해서 초록이 된 실행(같은 커밋에서 바로 앞 시도가 빨강), 새것부터. 목록 API 는 실행마다 마지막 시도만 주어
    초록이 되면 표에서 사라지므로, run_attempt > 1 인 초록 실행만 앞 시도를 한 번 더 묻는다."""
    out = []
    for run in runs:
        attempt = run.get("run_attempt") or 1
        if run.get("conclusion") != "success" or attempt < 2:
            continue
        before = api(f"repos/{repo}/actions/runs/{run['id']}/attempts/{attempt - 1}")
        if before and before[0].get("conclusion") in RED:
            out.append(run)
    return out


def ci_status(repo: str, api: Api, now: datetime) -> list[dict]:
    """기본 브랜치·열린 PR 브랜치마다 워크플로별 최신 실행이 빨가면 {브랜치, PR, 워크플로, 빨간 지 일수, 실패 잡, 넘음}.
    최근 CI_LOOKBACK_DAYS 일 안에 재실행해서 초록이 된 것은 {…, flaky: 횟수, url: 가장 최근 것} 으로 따로(넘음은 아님)."""
    since = datetime.fromtimestamp(now.timestamp() - CI_LOOKBACK_DAYS * 86400, timezone.utc).date().isoformat()
    default = api(f"repos/{repo}")[0]["default_branch"]
    branches = [(default, None)] + [(p["head"]["ref"], p["number"]) for p in api(f"repos/{repo}/pulls?state=open&per_page=100")]
    rows = []
    for branch, pr in branches:
        by_workflow: dict[str, list[dict]] = {}
        for run in _runs(repo, branch, api, since):
            if run.get("conclusion") in NO_SIGNAL:
                continue
            by_workflow.setdefault(run["name"], []).append(run)
        for name, runs in sorted(by_workflow.items()):
            flaky = _flaky(repo, runs, api)
            if flaky:
                rows.append(dict(branch=branch, pr=pr, workflow=name, flaky=len(flaky), url=flaky[0].get("html_url", ""), late=False))
            if runs[0].get("conclusion") not in RED:
                continue
            first_red = runs[0]
            for run in runs:  # 새것부터 거슬러 올라가 연달아 빨간 첫 실행 = 빨개진 때
                if run.get("conclusion") not in RED:
                    break
                first_red = run
            days = round((now - _when(first_red["created_at"])).total_seconds() / 86400, 1)
            jobs = [j["name"] for page in api(f"repos/{repo}/actions/runs/{runs[0]['id']}/jobs?per_page=100")
                    for j in page.get("jobs", []) if j.get("conclusion") in RED]
            rows.append(dict(branch=branch, pr=pr, workflow=name, red_days=days, jobs=jobs,
                             url=runs[0].get("html_url", ""), late=days > CI_RED_DAYS))
    return rows


def format_flaky(rows: list[dict]) -> list[str]:
    """흔들리는 워크플로 줄(표 아래). 재실행해서 초록이면 표에서 사라져 아무도 고치지 않으니 따로 남긴다."""
    lines = []
    for r in rows:
        where = r["branch"] + (f" (PR #{r['pr']})" if r["pr"] else "")
        lines.append(f"흔들림 / Flaky: {where} · {r['workflow']} — 재실행해서 초록 {r['flaky']}번(최근 {CI_LOOKBACK_DAYS}일), 시험을 고치세요 / "
                     f"green only after a re-run {r['flaky']}x (last {CI_LOOKBACK_DAYS} days), fix the test: {r['url'] or '-'}")
    return lines


def format_ci(rows: list[dict]) -> str:
    flaky = format_flaky([r for r in rows if r.get("flaky")])
    rows = [r for r in rows if not r.get("flaky")]
    if not rows:
        return "\n".join(["CI: 기본 브랜치·열린 PR 의 최신 실행이 모두 초록 / CI: latest runs on the default branch and open PRs are all green",
                          *flaky])
    late = sum(r["late"] for r in rows)
    lines = [f"CI: 빨간 워크플로 {len(rows)}개, {CI_RED_DAYS}일 넘은 것 {late}개 / "
             f"{len(rows)} red workflows, {late} red for more than {CI_RED_DAYS} days", "",
             "| 브랜치 / Branch | 워크플로 / Workflow | 빨간 지 / Red for | 실패 잡 / Failed jobs | 실행 / Run |", "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: -r["red_days"]):
        where = r["branch"] + (f" (PR #{r['pr']})" if r["pr"] else "")
        jobs = ", ".join(r["jobs"]).replace("|", "\\|") or "-"
        lines.append(f"| {where} | {r['workflow']} | {r['red_days']}일 / d{' ⚠' if r['late'] else ''} | {jobs} | {r['url'] or '-'} |")
    return "\n".join(lines + ([""] + flaky if flaky else []))


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
    ap.add_argument("--no-ci", action="store_true", help="CI 칸 없이 / skip the CI section")
    args = ap.parse_args(argv)
    now = now or datetime.now(timezone.utc)
    try:
        rows = triage(args.repo, api, now, args.include_bots, args.include_own)
        ci = [] if args.no_ci else ci_status(args.repo, api, now)
    except GhError as e:
        print(e, file=sys.stderr)
        return 2
    print(format_table(rows, args.all))
    if not args.no_ci:
        print("\n" + format_ci(ci))
    return 1 if any(r["late"] for r in rows + ci) else 0


if __name__ == "__main__":
    sys.exit(main())
