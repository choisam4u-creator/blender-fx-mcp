#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# CI lint 잡(.github/workflows/ci.yml)과 같은 검사를 한 줄로: ruff · actionlint(+ shellcheck) · zizmor.
# 판은 CONTRIBUTING 의 "판을 고정한 도구" 표에서 읽는다(표 한 곳만 고치면 된다). 블렌더 없이 돈다.
#
#   scripts/lint.sh           # 셋을 모두 돌리고, 하나라도 실패하면 종료 코드 1
#   scripts/lint.sh --print   # 돌릴 명령만 보여 줌(tests/test_lint_script.py 가 CI 단계와 같은지 비교)
#
# actionlint 는 PATH 에 shellcheck 가 없으면 run: 스크립트 검사를 조용히 건너뛴다(CI 러너에는 있음).
# 그래서 판을 고정한 shellcheck-py 를 함께 깔아(--with) 로컬에서도 같은 결과가 나오게 한다.
set -euo pipefail

cd "$(dirname "$0")/.."

ver() {
  # CONTRIBUTING 표의 "| 도구 | 판 |" 줄에서 판을 꺼낸다. 없으면 무엇을 고칠지 말하고 멈춘다.
  local v
  v=$(awk -F' *\\| *' -v t="$1" '$2 == t { print $3; exit }' CONTRIBUTING.md)
  if [ -z "$v" ]; then
    echo "CONTRIBUTING.md 의 '판을 고정한 도구' 표에 $1 이 없습니다. 표에 '| $1 | 판 | 쓰는 곳 |' 줄을 더하세요." >&2
    exit 2
  fi
  echo "$v"
}

CMDS=(
  "uvx ruff@$(ver ruff) check ."
  "uvx --with shellcheck-py==$(ver shellcheck-py) --from actionlint-py@$(ver actionlint-py) actionlint"
  "uvx zizmor@$(ver zizmor) --offline .github/workflows"
)

case "${1:-}" in
  --print) printf '%s\n' "${CMDS[@]}"; exit 0 ;;
  "") ;;
  *) echo "쓰는 법: scripts/lint.sh [--print]" >&2; exit 2 ;;
esac

if ! command -v uvx >/dev/null 2>&1; then
  echo "uvx 가 없습니다. uv 를 먼저 설치하세요: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 2
fi

failed=()
for cmd in "${CMDS[@]}"; do
  echo "==> $cmd"
  # shellcheck disable=SC2086  # 명령 문자열을 낱말로 나눠 실행한다(인자에 빈칸 없음)
  if ! $cmd; then
    failed+=("$cmd")
  fi
done

if [ ${#failed[@]} -gt 0 ]; then
  echo
  echo "실패한 검사 ${#failed[@]}개 — 위 출력을 고친 뒤 scripts/lint.sh 를 다시 돌리세요:" >&2
  printf '  %s\n' "${failed[@]}" >&2
  exit 1
fi
echo
echo "lint 모두 통과(CI lint 잡과 같은 검사)."
