# 유지보수 정책 / Maintenance policy

## 한국어

1인 관리 프로젝트의 유지보수 순서입니다. 약속이 아니라 관리자가 따르는 규칙이고, 응답 목표는 [SUPPORT.md](../SUPPORT.md) 와 같습니다.

### 이슈 분류 순서

1. **보안 신고** — 공개 이슈로 오면 내용을 지우고 [SECURITY.md](../SECURITY.md) 의 비공개 경로로 옮긴다. 첫 답 7일 안.
2. **재현 정보가 있는 버그** — `blender-fx-doctor` 출력·블렌더 판·도구와 인자가 있으면 바로 재현해 본다. 첫 답 7일 안.
3. **재현 정보가 없는 버그** — `needs-info` 라벨을 붙이고 필요한 정보를 묻는다. 30일 동안 답이 없으면 닫고, 정보가 오면 다시 연다.
   마감은 [`.github/workflows/stale.yml`](../.github/workflows/stale.yml) 이 매일 지킨다: 23일 조용하면 `stale` 라벨과 안내, 7일 더 조용하면 닫음. 누가 글을 쓰면 날짜가 다시 센다.
4. **질문·기능 요청** — 첫 답 14일 안. 작고 범위가 분명한 일은 `good first issue` 를 붙인다([CONTRIBUTING.md](../CONTRIBUTING.md) 의 "처음 기여하기 좋은 일").
5. 오류 문장 때문에 온 이슈는 해결법을 [docs/troubleshooting.md](troubleshooting.md) 에도 적는다.
6. **목표를 지켰는지 보기** — 주에 한 번 `uv run python scripts/triage_report.py` 를 돌린다. 열린 이슈·PR 중 첫 답이 위 목표(7·14일)를 넘은 것만 표로 나온다(종료 코드 1). `--all` 은 전부, 봇·관리자가 연 PR 은 기본으로 뺀다. `gh` 로만 묻고 토큰을 저장하지 않는다.

### 라벨

라벨은 [`.github/labels.yml`](../.github/labels.yml) 에 정의한다. 이슈 양식·이 문서·CONTRIBUTING·SUPPORT·dependabot 이 쓰는 라벨이 모두 거기 있어야 한다(시험이 확인). 저장소에 라벨을 만들거나 고칠 때는 저장소 폴더에서 아래를 돌린다(`--force` 는 이미 있으면 색·설명만 고친다).

```sh
gh label create "bug" --color d73a4a --description "동작이 문서와 다름 / Something does not work as documented" --force
gh label create "enhancement" --color a2eeef --description "새 기능·개선 요청 / New feature or improvement" --force
gh label create "needs-info" --color fbca04 --description "재현 정보를 기다림, 30일 뒤 닫힐 수 있음 / Waiting for repro info, may close after 30 days" --force
gh label create "good first issue" --color 7057ff --description "처음 기여하기 좋은 작은 일 / Small task for first-time contributors" --force
gh label create "question" --color d876e3 --description "사용법 질문 / Usage question" --force
gh label create "security" --color b60205 --description "보안 관련, 자세한 내용은 비공개로 / Security related, details go private" --force
gh label create "dependencies" --color 0366d6 --description "의존성·액션 판 갱신 / Dependency or action version update" --force
gh label create "stale" --color ededed --description "needs-info 마감 7일 전 자동 표시 / Marked 7 days before the needs-info deadline" --force
```

### 의존성 갱신 PR(dependabot) 처리 순서

`.github/dependabot.yml` 이 매주 두 종류의 PR 을 연다. 둘 다 `dependencies` 라벨이 붙는다.

1. **`deps`(uv)** — `uv.lock` 갱신. CI(server-tests·recipe-tests-bpy)가 초록이면 병합한다. `mcp` 의 메이저 판이 바뀌면 변경 기록을 먼저 읽는다.
   새 패키지가 들어오면 CI lint 의 라이선스 점검이 실패한다. 라이선스를 확인해 [docs/third-party-licenses.md](third-party-licenses.md) 표에 한 줄 더한다(허용 목록 밖이면 병합하지 않는다).
2. **`ci`(github-actions)** — 액션은 커밋 SHA + `# vX.Y.Z` 주석으로 고정돼 있고 dependabot 은 둘을 함께 올린다.
   - 패치·마이너 판: CI 가 초록이면 병합.
   - **메이저 판**(예: `actions/checkout` v4 → v7, `astral-sh/setup-uv` v5 → v10): 액션의 변경 기록에서 깨지는 변화(입력 이름·기본값·러너 요구)를 확인한 뒤 병합한다.
   - SHA 와 주석이 함께 바뀌었는지 본다. 주석만 바뀌거나 SHA 만 바뀐 PR 은 병합하지 않는다.
3. 같은 액션의 PR 이 여러 개면 가장 새 판 하나만 남기고 나머지는 닫는다.

검토 기록(2026-10-14): checkout v4.4.0 → v7.0.1(#12), setup-uv v5.4.2 → v10.3.0(#17, #11 을 대신함), stale v10.4.0 → v11.0.0(#14).
SHA 가 각 태그 커밋과 같음(`git ls-remote`), 셋 다 `node24`(GitHub 호스트 러너는 됨), 우리가 쓰는 입력(`persist-credentials`, stale 의 `only-labels` 등 7개)이 모두 남아 있음.
setup-uv 는 입력을 주지 않으며, v10 의 캐시 기본값 `auto` 는 태그 push 에서 꺼져 release.yml 이 캐시를 쓰지 않는다. 클라우드 정비 브랜치에 옮겨 CI 로 확인.

### 판 번호와 출시

- 판 번호는 `메이저.마이너.패치` 이다. 1.0 전에는 **마이너** 가 새 도구·인자·동작 변화(예: 범위 밖 값을 오류로 바꾼 것), **패치** 가 고침만이다.
- 동작이 바뀌면 [CHANGELOG.md](../CHANGELOG.md) 에 "동작 변화" 로 적는다.
- 출시 주기 목표: 고침이 쌓이면 패치, 새 도구가 모이면 마이너. 고칠 것이 있는데 3개월 넘게 출시가 없게 두지 않는다.
- 출시 전에 `uv run python scripts/release_check.py --build` 가 모두 OK 여야 하고, 태그를 밀기 전에 `--tag v0.7.0` 으로 태그와 판이 맞는지 본다(release.yml 과 같은 규칙). 태그·PyPI·레지스트리 순서는 [docs/registry.md](registry.md).

### 출시 절차

한 번의 출시를 사람의 기억이 아니라 이 순서로 재현한다. 0.7.0 은 2026-10-11 태그 push 로 release.yml 첫 실행(성공, 44초)이 PyPI 에 올렸다.

1. **판 올리기** — 버전 네 곳과 `uv.lock` 루트 판, CHANGELOG 맨 위 절 제목을 `## [X.Y.Z] - YYYY-MM-DD` 로, SECURITY·SUPPORT 의 지원 판 표에서 지난 판 줄을 지워 X.Y.x 하나로(출시 전에는 PyPI 최신 판도 지원으로 적어 둠, `release_check.py` 가 확인)(PR 로 main 에 병합).
2. **점검** — main 에서 `uv run python scripts/release_check.py --build --tag vX.Y.Z` 가 모두 OK.
3. **태그** — `git tag vX.Y.Z && git push origin vX.Y.Z`. 태그 push 만이 [`.github/workflows/release.yml`](../.github/workflows/release.yml) 을 띄운다.
4. **빌드** — `build` 잡(읽기 권한)이 같은 `release_check.py --tag`, `uv build`, `--dist dist`, twine 점검 뒤 artifact `dist` 를 올린다.
5. **승인** — `publish` 잡은 환경 `pypi` 를 쓴다. 저장소 Settings → Environments → `pypi` 에 필수 검토자(관리자)를 두면 여기서 멈추고, Actions 화면에서 빌드 기록을 본 뒤 **Approve** 한다(두지 않으면 바로 게시된다).
6. **PyPI 확인** — `https://pypi.org/project/blender-fx-mcp/X.Y.Z/` 가 열리고 `uvx --refresh --from blender-fx-mcp==X.Y.Z blender-fx-doctor` 가 돈다.
7. **레지스트리** — [docs/registry.md](registry.md) 의 등록 순서 3~7(`mcp-publisher publish`).
8. **릴리스 노트** — 게시가 끝나면 `release-draft` 잡이 GitHub 릴리스 **초안**(본문 = `scripts/release_notes.py vX.Y.Z` 출력: CHANGELOG 의 그 절, 영어 요약 먼저, 관리자 메모 빼고, 끝에 PyPI 주소. 휠·sdist 첨부)을 만든다.
   Releases 화면에서 초안을 읽고 **Publish release** 를 누른다(공개는 사람). 잡이 실패했으면 Mac 에서 `uv run python scripts/release_notes.py vX.Y.Z > notes.md` 뒤 `gh release create vX.Y.Z --notes-file notes.md`.
   출시 전에 문장을 미리 보려면 `--draft vX.Y.Z`(미출시 절도 초안 표시를 달아 출력).

태그를 잘못 밀었으면(빌드 잡이 빨감) `git push --delete origin vX.Y.Z` 로 지우고 고친 커밋에 다시 단다. PyPI 에 올라간 판은 지울 수 없으니 판을 올린다.

### 지원 판 정리 기준

- **파이썬**: 공식 지원이 끝난 판(EOL)은 그 뒤 첫 마이너 출시에서 뺀다. `pyproject.toml` 의 분류자·`requires-python`, ruff `target-version`, CI 행렬, SUPPORT.md 표, README 배지, architecture.md, 이 문서, `uv lock` 을 함께 고친다. 분류자만 바꾸고 `uv run pytest -q tests/test_repo_files.py -k python_version_range` 를 돌리면 어긋난 곳을 모두 알려 준다.
  지금 가장 낮은 3.11 은 2027-10 에 EOL 이다. 3.10 은 2026-10 EOL 에 맞춰 약속대로 **0.8.0 에서 뺐다**(0.7.0 이 3.10 을 지원한 마지막 판).
  3.11 도 같은 순서로: EOL 1년 전쯤 CHANGELOG 에 예고하고(`tests/test_repo_files.py` 의 `eol_soon` 에 더함), 분류자를 빼면 위 시험이 고칠 곳을 모두 짚는다.
- **블렌더**: 지원 중인 LTS 판을 실제 앱으로 전부 시험한다. 새 LTS 가 나오면 그 판으로 시험을 돌려 SUPPORT.md 표에 올리고, 지원이 끝난 LTS 는 "확인 안 함" 으로 내린다.
- **blender-fx-mcp**: 최신 마이너 판에만 버그·보안 수정을 낸다.

## English

How this single-maintainer project is maintained. These are the rules the maintainer follows, not guarantees; reply targets are the same as in [SUPPORT.md](../SUPPORT.md).

### Issue triage order

1. **Security reports**: if one arrives as a public issue, remove the details and move it to the private channel in [SECURITY.md](../SECURITY.md). First reply within 7 days.
2. **Bugs with repro info**: with `blender-fx-doctor` output, the Blender version and the tool and arguments, reproduce right away. First reply within 7 days.
3. **Bugs without repro info**: label `needs-info` and ask for what is missing. Close after 30 days without a reply; reopen when the info arrives.
   [`.github/workflows/stale.yml`](../.github/workflows/stale.yml) enforces the deadline daily: after 23 quiet days it adds the `stale` label and a notice, and closes the issue after 7 more. Any new comment restarts the count.
4. **Questions and feature requests**: first reply within 14 days. Label small, well-scoped tasks `good first issue` (see "Good first contributions" in [CONTRIBUTING.md](../CONTRIBUTING.md)).
5. When an issue was caused by an error message, add the fix to [docs/troubleshooting.md](troubleshooting.md) as well.
6. **Checking the targets**: once a week, run `uv run python scripts/triage_report.py`. It lists only the open issues and PRs whose first reply is past the targets above (7 or 14 days), exiting with 1 when there are any. `--all` lists everything; PRs opened by bots or maintainers are left out by default. It asks GitHub only through `gh` and stores no token.

### Labels

Labels are defined in [`.github/labels.yml`](../.github/labels.yml). Every label used by the issue forms, this page, CONTRIBUTING, SUPPORT and Dependabot must be listed there (a test checks this). To create or update them in the repository, run the `gh label create` block in the Korean section above from the repository folder; the descriptions are bilingual, and `--force` only updates the color and description of a label that already exists.

### Dependency update PRs (Dependabot)

`.github/dependabot.yml` opens two kinds of PRs every week, both labelled `dependencies`.

1. **`deps` (uv)**: `uv.lock` updates. Merge when CI (server-tests, recipe-tests-bpy) is green. Read the changelog first when `mcp` changes major version.
   A new package makes the CI lint license check fail. Check its license and add a row to [docs/third-party-licenses.md](third-party-licenses.md) (do not merge if it is outside the allowed list).
2. **`ci` (github-actions)**: actions are pinned to a commit SHA plus a `# vX.Y.Z` comment, and Dependabot updates both together.
   - Patch and minor versions: merge when CI is green.
   - **Major versions** (e.g. `actions/checkout` v4 to v7, `astral-sh/setup-uv` v5 to v10): check the action's changelog for breaking changes (input names, defaults, runner requirements) before merging.
   - Check that the SHA and the comment changed together. Do not merge a PR that changes only one of them.
3. If several PRs update the same action, keep the newest one and close the rest.

Review log (2026-10-14): checkout v4.4.0 → v7.0.1 (#12), setup-uv v5.4.2 → v10.3.0 (#17, supersedes #11), stale v10.4.0 → v11.0.0 (#14).
Each SHA matches its tag commit (`git ls-remote`); all three run on `node24` (fine on GitHub-hosted runners); every input we pass (`persist-credentials`, the seven stale inputs) still exists.
We pass no inputs to setup-uv, and its v10 cache default `auto` is off for tag pushes, so release.yml stays cache-free. Ported to the cloud maintenance branch and checked by CI.

### Versions and releases

- Versions are `major.minor.patch`. Before 1.0, a **minor** release adds tools or arguments or changes behavior (e.g. turning out-of-range values into errors); a **patch** release only fixes bugs.
- Behavior changes are listed as such in [CHANGELOG.md](../CHANGELOG.md).
- Release cadence goal: a patch when fixes pile up, a minor when new tools are ready. Fixes should not wait more than 3 months for a release.
- Before a release, `uv run python scripts/release_check.py --build` must be all OK, and before pushing a tag run it with `--tag v0.7.0` to check the tag matches the version (same rule as release.yml). Tag, PyPI and registry steps are in [docs/registry.md](registry.md).

### Release procedure

Every release follows these steps, so it does not depend on one person's memory. 0.7.0 was published to PyPI by the first release.yml run (2026-10-11, success, 44 s) after its tag push.

1. **Bump**: the four version fields, the root package in `uv.lock`, the top CHANGELOG heading as `## [X.Y.Z] - YYYY-MM-DD`, and the supported-version tables in SECURITY and SUPPORT trimmed to X.Y.x (before a release they also list the latest PyPI series; `release_check.py` checks this) (merged to main through a PR).
2. **Check**: on main, `uv run python scripts/release_check.py --build --tag vX.Y.Z` is all OK.
3. **Tag**: `git tag vX.Y.Z && git push origin vX.Y.Z`. Only a tag push starts [`.github/workflows/release.yml`](../.github/workflows/release.yml).
4. **Build**: the `build` job (read-only) runs the same `release_check.py --tag`, `uv build`, `--dist dist` and twine checks, then uploads the `dist` artifact.
5. **Approve**: the `publish` job uses the `pypi` environment. With a required reviewer (the maintainer) set in Settings → Environments → `pypi`, it waits here: review the build in the Actions page and **Approve** it (without one it publishes right away).
6. **Check PyPI**: `https://pypi.org/project/blender-fx-mcp/X.Y.Z/` opens and `uvx --refresh --from blender-fx-mcp==X.Y.Z blender-fx-doctor` runs.
7. **Registry**: steps 3 to 7 of the registration order in [docs/registry.md](registry.md) (`mcp-publisher publish`).
8. **Release notes**: after publishing, the `release-draft` job opens a **draft** GitHub release whose body is the output of `scripts/release_notes.py vX.Y.Z`
   (that CHANGELOG section, English summary first, maintainer notes dropped, PyPI link at the end), with the wheel and sdist attached. Read it under Releases and click
   **Publish release** (a person makes it public). If the job failed, run `uv run python scripts/release_notes.py vX.Y.Z > notes.md` and `gh release create vX.Y.Z --notes-file notes.md` on the Mac.
   To read the notes before the release, use `--draft vX.Y.Z` (prints the unreleased section with a draft marker).

If a wrong tag was pushed (the build job is red), delete it with `git push --delete origin vX.Y.Z` and tag the fixed commit. A version already on PyPI cannot be replaced, so bump the version instead.

### Dropping old versions

- **Python**: a version that reached its end of life is dropped in the next minor release. Update the classifiers and `requires-python` in `pyproject.toml`, ruff `target-version`, the CI matrix, the SUPPORT.md table, the README badge, architecture.md, this page and `uv lock` together. Change the classifiers first and run `uv run pytest -q tests/test_repo_files.py -k python_version_range`: it lists every place that still disagrees.
  The lowest version today, 3.11, reaches end of life in 2027-10. 3.10 (end of life 2026-10) was **dropped in 0.8.0** as announced (0.7.0 was the last release to support it).
  3.11 follows the same steps: announce it in the CHANGELOG about a year before end of life (add it to `eol_soon` in `tests/test_repo_files.py`), then remove the classifier and the test above lists every place to change.
- **Blender**: the supported LTS release gets the full test suite on the real app. When a new LTS ships, run the tests on it and add it to the SUPPORT.md table; an LTS that is out of support moves to "untested".
- **blender-fx-mcp**: bug and security fixes go to the latest minor release only.
