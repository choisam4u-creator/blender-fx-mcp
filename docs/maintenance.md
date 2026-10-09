# 유지보수 정책 / Maintenance policy

## 한국어

1인 관리 프로젝트의 유지보수 순서입니다. 약속이 아니라 관리자가 따르는 규칙이고, 응답 목표는 [SUPPORT.md](../SUPPORT.md) 와 같습니다.

### 이슈 분류 순서

1. **보안 신고** — 공개 이슈로 오면 내용을 지우고 [SECURITY.md](../SECURITY.md) 의 비공개 경로로 옮긴다. 첫 답 7일 안.
2. **재현 정보가 있는 버그** — `blender-fx-doctor` 출력·블렌더 판·도구와 인자가 있으면 바로 재현해 본다. 첫 답 7일 안.
3. **재현 정보가 없는 버그** — `needs-info` 라벨을 붙이고 필요한 정보를 묻는다. 30일 동안 답이 없으면 닫고, 정보가 오면 다시 연다.
4. **질문·기능 요청** — 첫 답 14일 안. 작고 범위가 분명한 일은 `good first issue` 를 붙인다([CONTRIBUTING.md](../CONTRIBUTING.md) 의 "처음 기여하기 좋은 일").
5. 오류 문장 때문에 온 이슈는 해결법을 [docs/troubleshooting.md](troubleshooting.md) 에도 적는다.

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
```

### 의존성 갱신 PR(dependabot) 처리 순서

`.github/dependabot.yml` 이 매주 두 종류의 PR 을 연다. 둘 다 `dependencies` 라벨이 붙는다.

1. **`deps`(uv)** — `uv.lock` 갱신. CI(server-tests·recipe-tests-bpy)가 초록이면 병합한다. `mcp` 의 메이저 판이 바뀌면 변경 기록을 먼저 읽는다.
2. **`ci`(github-actions)** — 액션은 커밋 SHA + `# vX.Y.Z` 주석으로 고정돼 있고 dependabot 은 둘을 함께 올린다.
   - 패치·마이너 판: CI 가 초록이면 병합.
   - **메이저 판**(예: `actions/checkout` v4 → v7, `astral-sh/setup-uv` v5 → v10): 액션의 변경 기록에서 깨지는 변화(입력 이름·기본값·러너 요구)를 확인한 뒤 병합한다.
   - SHA 와 주석이 함께 바뀌었는지 본다. 주석만 바뀌거나 SHA 만 바뀐 PR 은 병합하지 않는다.
3. 같은 액션의 PR 이 여러 개면 가장 새 판 하나만 남기고 나머지는 닫는다.

### 판 번호와 출시

- 판 번호는 `메이저.마이너.패치` 이다. 1.0 전에는 **마이너** 가 새 도구·인자·동작 변화(예: 범위 밖 값을 오류로 바꾼 것), **패치** 가 고침만이다.
- 동작이 바뀌면 [CHANGELOG.md](../CHANGELOG.md) 에 "동작 변화" 로 적는다.
- 출시 주기 목표: 고침이 쌓이면 패치, 새 도구가 모이면 마이너. 고칠 것이 있는데 3개월 넘게 출시가 없게 두지 않는다.
- 출시 전에 `uv run python scripts/release_check.py --build` 가 모두 OK 여야 한다. 태그·PyPI·레지스트리 순서는 [docs/registry.md](registry.md).

### 지원 판 정리 기준

- **파이썬**: 공식 지원이 끝난 판(EOL)은 그 뒤 첫 마이너 출시에서 뺀다. `pyproject.toml` 의 분류자·`requires-python`, ruff `target-version`, CI 행렬, SUPPORT.md 표, README 배지, architecture.md, 이 문서, `uv lock` 을 함께 고친다. 분류자만 바꾸고 `uv run pytest -q tests/test_repo_files.py -k python_version_range` 를 돌리면 어긋난 곳을 모두 알려 준다.
  지금 가장 낮은 3.10 은 2026-10 에 EOL 이므로 다음 마이너 판 뒤에 빼는 것을 검토한다.
- **블렌더**: 지원 중인 LTS 판을 실제 앱으로 전부 시험한다. 새 LTS 가 나오면 그 판으로 시험을 돌려 SUPPORT.md 표에 올리고, 지원이 끝난 LTS 는 "확인 안 함" 으로 내린다.
- **blender-fx-mcp**: 최신 마이너 판에만 버그·보안 수정을 낸다.

## English

How this single-maintainer project is maintained. These are the rules the maintainer follows, not guarantees; reply targets are the same as in [SUPPORT.md](../SUPPORT.md).

### Issue triage order

1. **Security reports**: if one arrives as a public issue, remove the details and move it to the private channel in [SECURITY.md](../SECURITY.md). First reply within 7 days.
2. **Bugs with repro info**: with `blender-fx-doctor` output, the Blender version and the tool and arguments, reproduce right away. First reply within 7 days.
3. **Bugs without repro info**: label `needs-info` and ask for what is missing. Close after 30 days without a reply; reopen when the info arrives.
4. **Questions and feature requests**: first reply within 14 days. Label small, well-scoped tasks `good first issue` (see "Good first contributions" in [CONTRIBUTING.md](../CONTRIBUTING.md)).
5. When an issue was caused by an error message, add the fix to [docs/troubleshooting.md](troubleshooting.md) as well.

### Labels

Labels are defined in [`.github/labels.yml`](../.github/labels.yml). Every label used by the issue forms, this page, CONTRIBUTING, SUPPORT and Dependabot must be listed there (a test checks this). To create or update them in the repository, run the `gh label create` block in the Korean section above from the repository folder; the descriptions are bilingual, and `--force` only updates the color and description of a label that already exists.

### Dependency update PRs (Dependabot)

`.github/dependabot.yml` opens two kinds of PRs every week, both labelled `dependencies`.

1. **`deps` (uv)**: `uv.lock` updates. Merge when CI (server-tests, recipe-tests-bpy) is green. Read the changelog first when `mcp` changes major version.
2. **`ci` (github-actions)**: actions are pinned to a commit SHA plus a `# vX.Y.Z` comment, and Dependabot updates both together.
   - Patch and minor versions: merge when CI is green.
   - **Major versions** (e.g. `actions/checkout` v4 to v7, `astral-sh/setup-uv` v5 to v10): check the action's changelog for breaking changes (input names, defaults, runner requirements) before merging.
   - Check that the SHA and the comment changed together. Do not merge a PR that changes only one of them.
3. If several PRs update the same action, keep the newest one and close the rest.

### Versions and releases

- Versions are `major.minor.patch`. Before 1.0, a **minor** release adds tools or arguments or changes behavior (e.g. turning out-of-range values into errors); a **patch** release only fixes bugs.
- Behavior changes are listed as such in [CHANGELOG.md](../CHANGELOG.md).
- Release cadence goal: a patch when fixes pile up, a minor when new tools are ready. Fixes should not wait more than 3 months for a release.
- Before a release, `uv run python scripts/release_check.py --build` must be all OK. Tag, PyPI and registry steps are in [docs/registry.md](registry.md).

### Dropping old versions

- **Python**: a version that reached its end of life is dropped in the next minor release. Update the classifiers and `requires-python` in `pyproject.toml`, ruff `target-version`, the CI matrix, the SUPPORT.md table, the README badge, architecture.md, this page and `uv lock` together. Change the classifiers first and run `uv run pytest -q tests/test_repo_files.py -k python_version_range`: it lists every place that still disagrees.
  The lowest version today, 3.10, reaches end of life in 2026-10, so dropping it after the next minor release is under review.
- **Blender**: the supported LTS release gets the full test suite on the real app. When a new LTS ships, run the tests on it and add it to the SUPPORT.md table; an LTS that is out of support moves to "untested".
- **blender-fx-mcp**: bug and security fixes go to the latest minor release only.
