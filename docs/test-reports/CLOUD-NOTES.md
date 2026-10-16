# 클라우드 회차 기록

## 맥에서 돌릴 명령 (블렌더 필요, 최신 회차 기준)

한 번에 돌려 `latest.md` 를 새로 쓰려면 `uv run python scripts/mac_report.py`(결과 확인 뒤 커밋). 클라우드 회차는 그 FAIL 부터 고친다.

```sh
uv sync && uv run pytest -q                        # 블렌더 앱으로 전체 통과(새: 레시피 읽기 순서 ast·판 고정 도구 표·troubleshooting 인용 문장 시험)
uv run python -c "from blender_fx_mcp import server; print(server.water(resolution=32))"   # Connect 뒤: 결과 끝에 '격자 한 칸 …m. … resolution=64(한 칸 …m…)'
uv run python -c "from blender_fx_mcp import server; print(server.water(resolution=320))"  # 같은 줄이 'resolution 이 상한 320 이라 … domain_at·domain_size' 로
```

## 2026-10-16 (22회차)

- 시작 확인: 저장된 지시의 최우선 F1·F3(0.7.0 판·release.yml)는 9회차(10/11)에 끝나 PR #13 으로 병합됐고 태그 `v0.7.0` 도 있음. 다시 할 것 없음 → 일반 규칙.
  `latest.md`(10/1)의 FAIL 2건은 main 에 고쳐져 있음(재확인). main 은 앞서 있지 않음.
  열린 `claude/cloud-work-*` PR 중 가장 위(#21, `bb13086`)에서 이어 감. 이 세션은 `claude/cloud-work-helzxf` 에 푸시 → PR 은 #21 위에 쌓음.
- 한 일(백로그 위에서부터, 굽기 시간 어림은 Mac 실측 필요라 건너뜀):
  1. **레시피 읽기 순서 ast 시험** (`421375e`): `main()` 안에서 `get_target`·`fx_bbox`·`point` 가 `cleanup_*`·`set_frame_end`·`remove_object` 보다 앞인지 레시피 27개를 블렌더 없이 훑음.
     지금 결함 없음. 예외는 wind 의 `fx_bbox(None)` 하나(실패하지 않고, 지운 바람은 메시가 아님)이고 근거를 적음. 필요 없어진 예외도 잡음. 변이 확인.
  2. **판 고정 도구 표** (`e106d6f`): CONTRIBUTING 에 ruff·actionlint-py·zizmor·twine 판 표와 분기마다 올리는 절차(한/영). `tests/test_pinned_tools.py` 는 워크플로·문서의 `도구@판` 이 표와 같은지, 판 없는 `uvx 도구` 호출이 없는지 봄.
     시험이 판 없는 곳 4곳을 찾아 고침(CONTRIBUTING 한/영, PR 양식, greet 안내). maintenance 출시 절차의 빠진 쉼표도.
  3. **bpy_tests.sh 휠 재사용·안내** (`543480a`): `BPY_WHEEL=휠경로` 로 내려받기 없이 깔고, 처음 받을 때 크기와 시간을 알림.
     이 컨테이너 실측: 받기 158초, 깔기 12초, `.venv-bpy` 958MB. 없는 파일이나 다른 판 휠이면 가상환경을 만들기 전에 다음 할 일과 함께 멈춤. 시험 3개.
  4. **troubleshooting 인용 문장 시험** (`c904f87`): `> …` 인용 46개의 문구가 실제 소스 문자열에 있는지 봄. 숫자·괄호·[…]·'…' 는 자리표시로 보고, 영문 이름은 f-string 자리와 맞춤.
     예외는 셸 문장 2개와 t() 로 끼워 만드는 문장 2개(REJECTIONS 가 실제 문장으로 확인). 문서만 고친 문장을 잡는 변이 확인.
  5. **water 결과에 격자 크기** (`a14b0b3`): "격자 한 칸 0.125m. 더 작은 물방울이 필요하면 resolution=128(한 칸 0.062m, 굽기가 몇 배 느려짐)"(한/영). 상한 320 이면 domain_at·domain_size 로 공간을 줄이라고 알림. CHANGELOG 한 줄.
  - 남은 `[ ]` 가 1개(Mac 실측)라 새 항목 5개를 추가함(`6a7e2f7`): emit 격자 안내, ast 시험이 도우미 함수 따라가기, 문서에 없는 FxError 목록, CI bpy 휠 캐시, 이슈 대응 기록 스크립트.
- 돌린 시험:
  - `uv run pytest -q`(3.11) **1344 통과·49 건너뜀**(블렌더 필요). CI 서버 명령 `--cov --cov-fail-under=99` → **100%**. `uvx ruff@0.15.20 check .`·actionlint·zizmor 통과("No findings").
  - **`scripts/bpy_tests.sh`(bpy 5.0.1, BPY_WHEEL 로 설치) → 1387 통과·6 건너뜀(2분 52초)**. 건너뛴 것은 유체 `app_only` 5개와 실제 캐릭터 파일 1개(블렌더 앱·개인 파일 필요).
  - 못 돌린 것: water 성공 문장의 실제 굽기(bpy 에서는 mantaflow 가 깨져 `app_only`). 그래서 Mac 명령 2·3줄로 확인함.
- 막힌 것: 없음.
- 완료 수·추가 수: **완료 5** / **추가 5** (완료 ≥ 추가). 남은 `[ ]` 6개(그중 1개는 Mac 실측).
- Mac에서 확인할 것: 맨 위 명령 3줄(또는 `uv run python scripts/mac_report.py` 한 번).

## 2026-10-15 (21회차)

- 시작 확인: 저장된 지시의 최우선 F1·F3(0.7.0 판·release.yml)는 9회차(10/11)에 끝나 PR #13 으로 병합됐고 태그 `v0.7.0` 도 있음. 다시 할 것 없음 → 일반 규칙.
  `latest.md`(10/1)의 FAIL 2건은 main 에 고쳐져 있음(재확인). main 은 앞서 있지 않음.
  열린 `claude/cloud-work-*` PR 중 가장 위(#20, `9044ba9`)에서 이어 감. 이 세션은 `claude/cloud-work-8fnkl3` 에 푸시 → **PR #21**(#20 위에 쌓음).
- 한 일(백로그 위에서부터, 굽기 시간 어림은 Mac 실측 필요라 건너뜀):
  1. **particles 없는 target** (`f872074`): `fx_bbox(target)` 을 정리·장면 길이 바꾸기 앞으로 옮김. BAD_CALLS 에 한 줄 추가. 고침을 되돌리면 실패하는 것을 확인함.
  2. **water 격자 안내 상한** (`b6a7669`, `c02ccad`): 권할 resolution 이 320 을 넘으면 되는 size 를 대신 권함. 지금 resolution 의 값과 320 일 때 값을 함께 주고, object 모드면 더 큰 물체나 domain 을 권함.
     도메인 계산을 `domain_box(size)` 로 묶었음. bpy 시험은 권한 size 로 다시 부르면 격자 검사를 지나는지 봄. 굽기는 bpy 에서 mantaflow 가 죽어서, 캐시 폴더를 일부러 막아 굽기 전에 멈추게 함.
  3. **zizmor** (`3c3dd7e`): CI lint 에 `uvx zizmor@1.30.1 --offline .github/workflows` 를 넣음. checkout 6곳에 `persist-credentials: false`. greet `pull_request_target` 은 근거 주석과 함께 그 줄에서만 끔. 지금 0건.
  4. **examples/README 명령 시험** (`1f9daed`): 스크립트 파일이 있는지, `uv run python` 으로 부르는지, uvx·uv run 이 띄우는 이름이 진입점인지 봄.
  5. **actionlint-py 공급망** (`2821f9a`): sdist 를 열어 확인함. 공식 릴리스 바이너리를 받아 SHA-256 이 맞을 때만 씀(공식 checksums.txt 와 같음). 바꿀 것은 없어 SECURITY 표에 두 줄로 적음.
  - 남은 `[ ]` 가 1개(Mac 실측)라 새 항목 5개를 추가함(`7edc39b`): 정리 전 읽기 ast 시험, uvx 판 고정 도구 표, bpy_tests 설치 안내, 해결법 인용 문장 시험, water 결과에 격자 크기.
- 돌린 시험:
  - `uv run pytest -q`(3.11) **1252 통과·49 건너뜀**(블렌더 필요). `uvx ruff@0.15.20 check .`·actionlint·zizmor 통과.
  - **`scripts/bpy_tests.sh`(bpy 5.0.1) → 1295 통과·6 건너뜀(3분 7초)**. 건너뛴 것은 유체 `app_only` 5개와 실제 캐릭터 파일 1개(블렌더 앱·개인 파일 필요).
  - 환경 메모: libEGL 설치와 bpy 휠 받기에 약 35분이 걸림(새 백로그 항목의 근거).
- 막힌 것: 없음.
- 완료 수·추가 수: **완료 5** / **추가 5** (완료 ≥ 추가). 남은 `[ ]` 6개(그중 1개는 Mac 실측).
- Mac에서 확인할 것: 맨 위 명령 3줄(또는 `uv run python scripts/mac_report.py` 한 번).

## 2026-10-15 (20회차)

- 시작 확인: 저장된 지시의 최우선 F1·F3(0.7.0 판·release.yml)는 9회차(10/11)에 끝나 PR #13 으로 병합, 태그 `v0.7.0` 도 있음. 다시 할 것 없음 → 일반 규칙.
  `latest.md`(10/1)의 FAIL 2건은 main 에 고쳐져 있음(재확인). main 은 앞서 있지 않음.
  19회차 메모대로 열린 `claude/cloud-work-*` PR 중 가장 위(#19, `97216be`)에서 이어 갔다. 이 세션은 `claude/cloud-work-gbvlwr` 에 푸시 → PR 은 #19 위에 쌓음.
- 한 일(백로그 위에서부터, 굽기 시간 어림은 Mac 실측 필요라 건너뜀):
  1. **at·domain_at 을 `point()` 로** (`7e44ac7`) — emit·explode·water(at·domain_at)·particles. 시험으로 먼저 재현: IndexError 5개 + emit·particles 는 지난 효과를 지운 뒤 실패(장면 반쯤 바뀜, particles 는 프레임 범위도). 고친 뒤 통과.
  2. **바다 밑 set_ground 안내가 진짜 되는지** (`a663488`) — 바다 → set_ground 실패(reset_destroy 안내) → reset_destroy → set_ground 성공, 바다 없음·바닥 보임·재질 grass. 안내는 그대로 맞았음.
  3. **doctor 출력 폴더 해결법** (`516c9b1`) — troubleshooting 새 절 "Output folder not writable"(한/영) + `HELP_ANCHORS["output"]`, 앵커·id 시험은 기존 것이 지킴.
  4. **CI 워크플로 검사** (`bfe1394`) — lint 잡에 `uvx --from actionlint-py@1.7.12.25 actionlint`(9/22 판, 지금 경고 0) + 판 고정 시험, CONTRIBUTING 한/영.
  5. **예제 스크립트 이름 시험** (`9ab86ff`) — `examples/*.py` 의 문장 속 이름과 `call_tool`·STEPS 의 도구·인자 키가 서버 스키마에 있는지. 변이(없는 이름 2개)를 잡음.
  - 남은 `[ ]` 1개(Mac 실측)라 새 항목 5개 추가(`89cd60c`: particles target 순서, water resolution 상한 넘는 안내, zizmor 7건, actionlint-py 내려받기 검증, examples/README 명령).
- 돌린 시험: `uv run pytest -q`(3.11) **1248 통과·48 건너뜀**(블렌더 필요), CI 서버 명령 `--cov --cov-fail-under=99` **100%**,
  **`scripts/bpy_tests.sh`(bpy 5.0.1) → 1290 통과·6 건너뜀(2분 2초)**(유체 `app_only` 5개·실제 캐릭터 파일 1개 — 블렌더 앱·개인 파일 필요), `uvx ruff@0.15.20 check .` 통과, actionlint 통과.
  환경 메모: 이 컨테이너엔 libEGL 이 없어 `apt-get install`(bpy_tests.sh 가 알려 주는 줄)부터 했다.
- 막힌 것: 없음. zizmor 는 high 1·medium 6 이 나와 이번엔 CI 에 넣지 않고 백로그로.
- 완료 수·추가 수: **완료 5** / **추가 5** (완료 ≥ 추가). 남은 `[ ]` 6개(그중 1개 Mac 실측).
- Mac에서 확인할 것: 맨 위 명령 3줄(또는 `uv run python scripts/mac_report.py` 한 번).

## 2026-10-14 (19회차)

- 시작 확인: 저장된 지시의 최우선 F1·F3(0.7.0 판·release.yml)는 9회차(10/11)에 끝나 PR #13 으로 병합, 태그 `v0.7.0` 도 있음. 다시 할 것 없음 → 일반 규칙.
  `latest.md`(10/1)의 FAIL 2건은 main 에 고쳐져 있음(재확인). main 은 앞서 있지 않음.
  ⚠️ 처음에 `claude/cloud-work`(16회차 끝)에서 시작해 백로그 5개를 했는데, 17·18회차가 PR #16·#18 로 같은 5개를 이미 해 둔 것을 늦게 봄 →
  그 커밋은 푸시하지 않고 버림. 이 세션은 `claude/cloud-work-knktdu` 에만 푸시할 수 있어 18회차 끝 `ab0ad68`(#18) 위에서 다시 작업했다.
  다음 회차는 시작할 때 열린 `claude/cloud-work-*` PR 중 가장 위 것부터 이어 가야 함.
- 한 일(백로그 위에서부터, 굽기 시간 어림은 Mac 실측 필요라 건너뜀):
  1. **render_video 한쪽 프레임** (`690f4e1`) — 확인해 보니 조용히 옮기지 않고 "두 값을 바꿔" 오류를 냈음(한쪽은 장면 값이라 틀린 안내). 한쪽만 주면 "함께 주어(예: …) 다시 시키세요".
  2. **캐시 폴더 안 남김** (`21b8e9b`) — 물·연기·폭발이 `cache_*` 폴더를 검사 통과 뒤에 만듦. bpy 시험(실패 6개 호출이 폴더를 하나도 안 남김).
  3. **지원 판 표** (`065dc92`) — SECURITY·SUPPORT 에 "0.7.x (PyPI 최신) — 0.8.0 이 나올 때까지". `release_check.py` 가 출시(날짜) 뒤 표를 새 판 하나로 정리하라고 알림. 출시 절차 1단계 한/영.
  4. **릴리스 초안 잡** (`0752ea9`) — release.yml 에 `release-draft`(needs publish, `contents: write` 하나만, build 가 만든 노트·파일 artifact 만 받아 `gh release create --draft`, 저장소 코드 실행 없음).
     노트는 dist 와 다른 artifact(dist/ 전부가 PyPI 로 가므로). 허용목록에 `contents: write` 추가, 기존 거절 시험 그대로 + 잡 단위 시험. 실제 동작은 다음 태그 때.
  5. **실패 = 장면 그대로 확대** (`0557f05`) — 바다·바람·깃발이 있는 장면에서 시험. 찾아 고친 4곳: ocean 이 인자를 다 읽기 전에 옛 바다를 지우고 장면 길이 변경,
     wind·cloth_flag 가 `at=[1, 2]` 에서 옛 효과를 지운 뒤 IndexError, set_ground 가 바다 밑 숨은 바닥을 다시 보이게 함. 서버 `check_points`(at·domain_at 숫자 셋) + 해결법 문장.
  - 남은 `[ ]` 1개(Mac 실측)라 새 항목 5개 추가(`aa2d2a1`).
- 돌린 시험: `uv run pytest -q`(3.11) **1244 통과·47 건너뜀**(블렌더 필요), CI 서버 명령 `--cov --cov-fail-under=99` **100%**,
  **`scripts/bpy_tests.sh`(bpy 5.0.1) → 1285 통과·6 건너뜀(2분 34초)**(유체 `app_only` 5개·실제 캐릭터 파일 1개 — 블렌더 앱·개인 파일 필요), `uvx ruff@0.15.20 check .` 통과.
  변이 확인: 항목 1·2·5 의 레시피 고침을 되돌리면 새 시험이 실패(항목 5 는 7줄).
- 막힌 것: 없음(버린 중복 작업은 위 ⚠️).
- 완료 수·추가 수: **완료 5** / **추가 5** (완료 ≥ 추가). 남은 `[ ]` 6개(그중 1개 Mac 실측).
- Mac에서 확인할 것: 맨 위 명령 3줄(또는 `uv run python scripts/mac_report.py` 한 번).

## 2026-10-14 (18회차)

- 시작 확인: 저장된 지시의 최우선 F1·F3(0.7.0 판·release.yml)는 9회차(10/11)에 끝나 PR #13 으로 병합(`ff7555e`·`4eb778f`), 태그 `v0.7.0` 도 있음. 다시 할 것 없음 → 일반 규칙.
  main 은 `claude/cloud-work` 보다 앞서 있지 않음. `latest.md`(10/1)의 FAIL 2건은 main 에 고쳐져 있음(재확인).
  이 세션은 `claude/cloud-work-9gw4mg` 에만 푸시할 수 있어 17회차(PR #16, `claude/cloud-work-n6i9g1`) 끝 `89fb921` 에서 이어 작업했다.
- 한 일(백로그 위에서부터, 굽기 시간 어림은 Mac 실측 필요라 건너뜀):
  1. **set_timing 옮김 알림** (`5b8668d`) — 한쪽만 준 프레임으로 블렌더가 다른 쪽을 옮기면 결과에 옛 값→새 값과 "함께 주세요".
  2. **실패 = 장면 그대로** (`c94c8ef`) — 새 bpy 시험 `tests/test_recipe_failure_keeps_scene.py`(레시피 11종·잘못된 호출 17개 앞뒤 장면 비교).
     찾아 고친 6곳: `explode`·`emit` 이름 틀리면 지난 효과 삭제, `water` 검사 전 지난 물 삭제·프레임 범위 변경, `destroy` 면 없는 메시에서 다른 효과 삭제,
     `export_model` 형식 검사 전에 물리를 키프레임으로 굽기, `import_model` parts 불일치 때 부품이 남음.
  3. **해결법 '인자 값이 거부됨'** (`6e90759`) — 범위·선택지·순서·유한한 숫자 문장. 시험이 빠져 있던 `check_finite` 를 찾음.
  4. **0.8.0 출시 준비 점검** (`c0cab3b`) — `release_check.py` 는 날짜 줄만 실패. 영어 요약 Fixes 29줄 한 덩어리를 주제별 6개로 + 항목 6줄 상한 시험(미출시 절만).
  5. **dependabot 3개 옮김** (`fd8696f`) — checkout v7.0.1·setup-uv v10.3.0·stale v11.0.0. SHA=태그 커밋, node24, 쓰는 입력 그대로, setup-uv 캐시는 태그 push 에서 꺼짐.
  - 새 백로그 5개 + CHANGELOG 한국어 고침 줄 (`0ac1810`).
- 돌린 시험: `uv run pytest -q`(3.11) **1231 통과·44 건너뜀**(블렌더 필요), CI 서버 명령 `--cov --cov-fail-under=99` **100%**,
  **`scripts/bpy_tests.sh`(bpy 5.0.1) → 1269 통과·6 건너뜀(2분 5초)**(유체 `app_only` 5개·실제 캐릭터 파일 1개 — 블렌더 앱·개인 파일 필요), `uvx ruff@0.15.20 check .` 통과, 도구 표 일치.
  변이 확인: 항목 2 의 고침을 되돌리면 새 시험이 6곳 모두 잡음. 항목 4 의 상한 시험은 옛 CHANGELOG 에서 실패.
- 막힌 것: 없음. (`claude/cloud-work` 에 직접 못 미는 것은 17회차와 같음 → PR 을 `claude/cloud-work` 로 엶, #16 뒤에 병합)
- 완료 수·추가 수: **완료 5** / **추가 5** (완료 ≥ 추가). 남은 `[ ]` 6개(그중 1개 Mac 실측).
- Mac에서 확인할 것: 맨 위 명령 3줄(또는 `uv run python scripts/mac_report.py` 한 번).

## 2026-10-13 (17회차)

- 시작 확인: 저장된 지시의 최우선 F1·F3(0.7.0 판·release.yml)는 9회차(10/11)에 끝나 PR #13 으로 병합, 태그 `v0.7.0` 도 있음. 다시 할 것 없음 → 일반 규칙.
  main 은 `claude/cloud-work` 보다 앞서 있지 않음. `latest.md`(10/1)의 FAIL 2건은 고쳐져 있음(재확인).
  이 세션의 푸시 브랜치는 `claude/cloud-work-n6i9g1`(`claude/cloud-work` 끝 9603f30 에서 이어 감, 앞으로 감기 가능).
- 한 일(백로그 위에서부터, 굽기 시간 어림은 Mac 실측 필요·dependabot 3개는 CI 판단이 필요해 건너뜀):
  1. **set_timing 순서 검사** (`1983ced`) — 거꾸로 준 쌍(`frame_end<frame_start`, `slow_to≤slow_from`, `render_video` 도)을 서버가 보내기 전에 바꿔 줄 값과 함께 막음, 레시피도 바꾸기 전에 검사.
     **하다가 찾은 결함**: `set_timing(fps=…)` 가 결과 키 `fps` 가 겹쳐 늘 TypeError(장면은 이미 바뀐 뒤) → 고침.
  2. **doctor 항목별 해결법 링크** (`24db12a`) — "해결법:" 줄이 실패 항목의 절로, `--json`·`doctor` 도구는 항목마다 `help`. 앵커가 실제 절인지 시험.
  3. **문서 이름 시험 확대** (`8e17ec6`) — 7개 문서 + 호출 안 인자 이름. recipes.md 의 `hold_until` 을 "서버 안쪽 값"으로.
  4. **결과에 길이(초)** (`09f2c3c`) — "288프레임 = 24fps 로 12초" / "72 frames = 3s at 24fps".
  5. (새 항목 첫째) **global_slow 두 번** (`48cfbc8`) — 두 번 시키면 길이만 48→96→192 로 늘고 배율은 2배 그대로이던 결함. 원래 속도 기준·1 이면 되돌림.
  - 남은 `[ ]` 2개라 새 항목 5개 추가(`436d6b2`: global_slow 두 번, 한쪽만 준 프레임 알림, 레시피 실패 = 장면 그대로 점검, 서버 오류 문장 해결법 검색, 0.8.0 출시 준비 점검).
- 돌린 시험: `uv run pytest -q`(3.11) **1221 통과·41 건너뜀**(블렌더 필요), CI 서버 명령 `--cov --cov-fail-under=99` **100%**,
  **`scripts/bpy_tests.sh`(bpy 5.0.1) → 1256 통과·6 건너뜀(2분 4초)**(유체 `app_only` 5개·실제 캐릭터 파일 1개 — 블렌더 앱·개인 파일 필요), `uvx ruff@0.15.20 check .` 통과, `gen_tool_table.py` 일치.
  확인: 고치기 전 레시피로 bpy 재현(fps → TypeError, global_slow 두 번 → 192), 문서에 없는 이름을 넣으면 시험 실패.
- 막힌 것: 없음.
- 완료 수·추가 수: **완료 5** / **추가 5** (완료 ≥ 추가). 남은 `[ ]` 6개(그중 1개 Mac 실측).
- Mac에서 확인할 것: 맨 위 명령 3줄(또는 `uv run python scripts/mac_report.py` 한 번).

## 2026-10-13 (16회차)

- 시작 확인: 저장된 지시의 최우선 F1·F3(0.7.0 판·release.yml)는 9회차(10/11)에 끝나 PR #13 으로 병합(`ff7555e`·`4eb778f`), 태그 `v0.7.0` 도 있음. 다시 할 것 없음 → 일반 규칙.
  main 은 `claude/cloud-work` 보다 앞서 있지 않음. `latest.md`(10/1)의 FAIL 2건은 main 에 고쳐져 있음(재확인). 열린 PR #15 를 갱신.
- 한 일(백로그 위에서부터, 굽기 시간 어림은 Mac 실측 필요라 건너뜀):
  1. **fps·프레임 범위 검사** (`8d50d5b`) — fps 1~240(`set_render`·`render_video`·`set_timing`·`set_physics`), 프레임 번호 1 이상(`frame_start`·`frame_end`·`slow_from`·`slow_to`)을 블렌더에 보내기 전에. 권장 24·30·60, 0 의 뜻을 한/영으로.
  2. **서버 쪽 오류의 다음 할 일** (`bb37b09`) — `tests/test_server_next_steps.py` 가 `BlenderError(t(...))` 18곳+`_missing_snapshot` 을 훑음. 찾아 고친 4곳: 수신기 실패·결과 줄 없음 → 버그일 수 있음 + `doctor --issue` 신고 안내, `samples` 권장 값, `/my_model size` 한국어에 시키는 말.
  3. **문서의 도구·인자 이름** (`3156f92`) — 프롬프트는 이미 시험 중(재확인). README·troubleshooting·recipes·demo-script 시험 추가 → README 한계 절이 `destroy` 에 없는 인자 `glue_neighbors`·`glue_max` 로 줄이라던 것을 `pieces`·`glue="none"` 으로.
  4. **CONTRIBUTING 오류 문장 규칙** (`324cb71`) — 한/영 절(규칙 4가지·지키는 시험 6개·한 줄 확인 명령) + 절이 실제 시험을 가리키는지 시험.
  5. **빠른 시작 단계 수** (`90aaea4`) — 첫 렌더까지 5단계(준비 4 + 첫 명령) 상한 시험, 단계마다 해결법 링크. 하다가 찾음: uv 단계가 "Windows·Linux 명령은 doctor 가 알려 줌" 이었는데 doctor 도 uvx 로 돌아 uv 없이는 못 봄 → OS 별 명령을 직접 + 새 절 `uv not found`.
  - 덧: CHANGELOG 0.8.0 Docs 요약이 7줄이 돼 6줄로 합침, 범위 안내 없는 이름 시험으로 서버 커버리지 100% 유지 (`8f36187`).
  - 남은 `[ ]` 1개(Mac 실측)라 새 항목 5개 추가(`da6becf`: set_timing 순서 검사, doctor 항목별 해결법 링크, 문서 이름 시험 확대, dependabot 3개 재검토, 결과에 길이(초)).
- 돌린 시험: `uv run pytest -q`(3.11) **1191 통과·39 건너뜀**(블렌더 필요), CI 서버 명령 `--cov --cov-fail-under=99` **100%**, **`scripts/bpy_tests.sh`(bpy 5.0.1) → 1224 통과·6 건너뜀(2분 11초)**(유체 `app_only` 5개·실제 캐릭터 파일 1개 — 블렌더 앱·개인 파일 필요), `uvx ruff@0.15.20 check .` 통과, `gen_tool_table.py` 일치.
  변이 확인: 항목 1·2·3·5 의 고침을 되돌리면 새 시험이 각각 13·9·1·4개 실패.
- 막힌 것: 없음.
- 완료 수·추가 수: **완료 5** / **추가 5** (완료 ≥ 추가). 남은 `[ ]` 6개(그중 1개 Mac 실측).
- Mac에서 확인할 것: 맨 위 명령 3줄(또는 `uv run python scripts/mac_report.py` 한 번).

## 2026-10-12 (15회차)

- 시작 확인: 저장된 지시의 최우선 F1·F3(0.7.0 판·release.yml)는 9회차(10/11)에 끝나 PR #13 으로 병합(`ff7555e`·`4eb778f`), 태그 `v0.7.0` 도 있음. 다시 할 것 없음 → 일반 규칙.
  main 은 `claude/cloud-work` 보다 앞서 있지 않음. `latest.md`(10/1)의 FAIL 2건은 main 에 고쳐져 있음(재확인).
- 한 일(백로그 위에서부터, 굽기 시간 어림은 Mac 실측 필요라 건너뜀):
  1. **렌더 크기 범위 검사** (`187c372`) — `render_preview`·`render_video`·`set_render` 의 width/height 16~7680 을 블렌더에 보내기 전에, 권장 크기(가로 1280×720·1920×1080, 세로 1080×1920)와 0 의 뜻을 한/영으로. 레시피가 자르지 않는 값이라 `SERVER_ONLY_RANGES` 로 구분.
  2. **doctor 도구 구조화 출력** (`5b5bbf9`) — 문장 + `ok`·`failed`(id)·`checks`(항목마다 ok·fix)·`help`. 항목 모양은 `--json` 과 같은 `doctor.check_rows`.
  3. **instructions 예산** (`52e665a`) — 도구 설명과 겹치는 괄호 풀이를 빼 한 656→515·영 994→819자. 공식 클라이언트가 받는 값을 한/영 900자 상한·도구 목록과 합산 시험.
  4. **오류 문장 다음 할 일(영어)·실제 도구 이름** (`7a9c0f1`) — 영어 표지 시험 추가(모두 통과). 이름 시험이 `set_ground` 의 없는 도구 `reset` 을 찾아 `reset_destroy` 로 고침.
  - 남은 `[ ]` 1개라 새 항목 5개 추가(`0262e43`: fps·프레임 범위, 서버 쪽 오류 문장 표지, 프롬프트·문서의 도구 이름, CONTRIBUTING 오류 문장 규칙, README 첫 렌더 단계 수).
- 돌린 시험: `uv run pytest -q`(3.11) **1081 통과·39 건너뜀**(블렌더 필요), CI 서버 명령 `--cov --cov-fail-under=99` **100%**, **`scripts/bpy_tests.sh`(bpy 5.0.1) → 1114 통과·6 건너뜀(2분 38초)**(유체 `app_only` 5개·실제 캐릭터 파일 1개 — 블렌더 앱·개인 파일 필요), `uvx ruff@0.15.20 check .` 통과.
  변이 확인: instructions 에 괄호 풀이를 되살리면, set_ground 를 옛 문장으로 되돌리면 각각 새 시험이 실패.
- 막힌 것: 없음.
- 완료 수·추가 수: **완료 4** / **추가 5**. ⚠️ 이번 회차는 추가가 완료보다 1 많음 — 남은 `[ ]` 가 1개(Mac 실측)뿐이라 규칙 3(3개 미만이면 5개 추가)을 따름. 다음 회차는 추가 없이 완료만.
- Mac에서 확인할 것: 맨 위 명령 3줄(또는 `uv run python scripts/mac_report.py` 한 번).

## 2026-10-12 (14회차)

- 시작 확인: 저장된 회차 지시의 최우선 F1·F3(0.7.0 판 맞추기·release.yml)는 9회차(10/11)에 끝나 PR #13 으로 병합, 태그 `v0.7.0`·PyPI 게시까지 됨(지금 main 은 0.8.0 준비 중). 다시 할 것 없음 → 일반 규칙으로.
  main 은 앞서 있지 않음. `latest.md`(10/1)의 FAIL 2건은 main 에 고쳐져 있음(재확인).
- 한 일(백로그 위에서부터, 굽기 시간 어림은 Mac 실측이 필요해 건너뜀):
  1. **CI 커버리지 하한 95% → 99%** — ci.yml·CONTRIBUTING 한/영, 시험이 99 미만 하한을 거절.
  2. **`render_preview` 가 `set_render` 크기를 따름** — 안 주면 정한 비율을 긴 변 640 으로(1080×1920 → 360×640, 작으면 그대로, 정한 적 없으면 640×360), 하나만 주면 비율로. 크기 계산 시험 9개 + bpy 시험(실제 PNG 크기).
  3. **목록형 도구 구조화 출력** — `list_objects`·`inspect_mesh`·`list_snapshots` 가 문장과 함께 `structuredContent`. mcp 2.2 는 `-> str` 도구에 `{"result": 문자열}` 껍데기만 주던 것을 확인.
  4. **도구 목록 토큰 예산** — 실제로 나가는 목록을 재니 33,015자 중 인자 `title`·문장 도구 출력 스키마·독스트링 들여쓰기가 군더더기 → 25,093자(−24%). `FxServer` 의 공개 메서드(`add_tool`·`list_tools`)만 재정의, 설명 문구는 그대로. 상한 시험.
  5. **macOS bpy CI** — bpy 5.0.1 macOS arm64 휠 확인, `recipe-tests-bpy-macos` 추가. 러너 VM 의 Metal 렌더를 몰라 확인될 때까지 `continue-on-error`. 첫 결과는 PR #15 CI 에서.
  - 남은 `[ ]` 가 2개라 새 항목 5개 추가(렌더 크기 범위 검사, macOS 작업 결과 반영, doctor 구조화 출력, instructions 예산, 레시피 오류 문장의 다음 할 일).
- 돌린 시험: `uv run pytest -q`(3.11) **1066 통과·39 건너뜀**(블렌더 필요), 서버 쪽 `--cov --cov-fail-under=99` **100%**(3.11·3.14), **`scripts/bpy_tests.sh` → 1099 통과·6 건너뜀(1분 56초)**(유체 `app_only` 5개·실제 캐릭터 파일 1개 — 블렌더 앱·개인 파일 필요), `uvx ruff@0.15.20 check .` 통과, `gen_tool_table.py` 일치.
- 막힌 것: 없음. macOS 러너에서 bpy 렌더가 되는지는 이 컨테이너(Linux)에서 못 봄 → PR CI 결과로.
  6. (CI 결과를 보고 이어서) **macOS bpy 작업을 막는 작업으로** — PR #15 CI 첫 실행 1098 통과·7 건너뜀(1분 50초)이라 러너 VM 에서도 Metal 렌더가 됨 → `continue-on-error` 뺌. 새로 넣은 항목 중 하나를 바로 끝냄.
- 완료 수·추가 수: **완료 6** / **추가 5**. 남은 `[ ]` 5개(그중 1개 Mac 실측).
- Mac에서 확인할 것: 맨 위 명령 3줄(또는 `uv run python scripts/mac_report.py` 한 번).

## 2026-10-11 (13회차)

- 한 일: 사용자 요청 "남은 백로그 5개 이어서". main 은 앞서 있지 않음, `latest.md`(10/1)의 FAIL 2건은 main 에 고쳐져 있음(재확인). 같은 브랜치에서 다른 세션이 reset 세그폴트 고침(`7006897`)을 먼저 올려 그 위에서 작업.
  1. **원격 블렌더 `restore` 오타** — 블렌더에 스냅샷이 있는지 먼저 물어, 없으면 before_restore 를 덮어쓰기 전에 멈춤.
  2. **미리보기가 워크벤치 셰이딩을 바꾼 채 남김** — 점검해 보니 EEVEE 볼륨 값은 이미 되돌렸고 셰이딩(그림자·캐비티·외곽선·조명)이 남았음 → 되돌림(옛 코드로 실패하는 bpy 시험 확인).
  3. **bpy 시험 시간 4분 17초 → 2분 23초** — `--durations` 로 재 보니 12회차에 내가 넣은 시험이 120초(샘플 200 final 영상) → 샘플 2, 이미지 비교 렌더는 320×180.
  4. **서버 쪽 커버리지 98% → 100%** — 남은 21줄이 모두 오류 갈래(디스크 권한·스냅샷 삭제 실패·반쯤 온 UTF-8·진행 알림 실패·환경변수·표준 입력 없음).
  5. **`scripts/mac_report.py`** — 이 파일 맨 위 Mac 명령을 돌려 `latest.md` 를 새로 씀(PASS/FAIL·시간·실패 끝 25줄, 집 폴더 `~`).
  - 남은 `[ ]` 1개라 다음 후보 5개(커버리지 하한 99%, 도구 설명 토큰 예산, render_preview 크기, macOS bpy CI, 구조화 출력) 추가.
- 돌린 시험: `uv run pytest -q`(3.11) **1046 통과·38 건너뜀**(블렌더 필요), 서버 쪽 `--cov` **100%**(1043 통과), **`scripts/bpy_tests.sh` → 1059 통과·6 건너뜀(2분 23초)**, `uvx ruff@0.15.20 check .` 통과.
- 막힌 것: 없음. 굽기 시간 어림 1개는 Mac 실측 필요(이제 `mac_report.py` 로 결과가 latest.md 에 들어오면 다음 회차가 씀).
- 완료 수·추가 수: **완료 5** / **추가 5**. 남은 `[ ]` 6개(그중 1개 Mac 실측).
- Mac에서 확인할 것: 맨 위 명령 3줄(또는 `uv run python scripts/mac_report.py` 한 번).

## 2026-10-11 (12회차)

- 한 일: 사용자 요청 "남은 백로그 5개 + 필요한 작업 바로바로, 퀄리티 개선 리스트업". main 은 앞서 있지 않음, `latest.md`(10/1)의 FAIL 2건은 main 에 고쳐져 있음(재확인).
  1. 백로그 5개: dependabot PR 3개 검토(세 PR 모두 고칠 것 없음, 아래 표), `release_notes.py --draft`, 진행 알림 사람 말(레시피 27개 한/영), README "도움 받기" 3줄, 진행 알림 stdio 끝까지 시험(`BLENDER_FX_PROGRESS_EVERY`).
  2. **품질 감사**(하위 에이전트가 코드를 읽고 재현한 11건 → 하나씩 확인해 모두 고침, 백로그 "12회차 품질 감사" 절):
     - 높음: `restore("before_restore")` 가 되돌아갈 상태를 덮어씀 → 맞바꾸기. `before_restore` 는 예약 이름.
     - 중간: `destroy`/`reset_destroy(target=X)` 가 바다·물·연기 등 다른 효과까지 지움(옛 코드로 실패하는 bpy 시험 확인), `explode` 가 조각낸 뒤에야 인자 검사, `set_render` 샘플·크기를 렌더가 무시, 명령 도중 끊김을 "애드온 설치"로 안내·`BLENDER_FX_TIMEOUT=0` 이 모든 도구를 깸, 미리보기 실패 시 설정이 바뀐 채 남음.
     - 낮음: 응답 틀(잘림·군더더기·객체 아님·큰 응답 느림), `nan`·`inf`, `render_video` fps 보고, `save_blend`/`render_video` 이름이 출력 폴더 밖으로, 집 폴더 가리기(문장부호·`--json`).
  3. 덧붙임: `snapshot` 덮어쓰기 알림, ruff 에 `B`·`SIM115`·`RUF059` 추가(9곳 정리).
  4. 다음 품질 개선 후보 5개를 근거와 함께 백로그에.
- dependabot PR 검토 표(병합은 사람 몫):

  | PR | 바뀐 것 | 이 저장소에 필요한 일 |
  |---|---|---|
  | #12 checkout v4→v7 | node24, 입력 같음, v6 자격 증명 별도 파일, v7 포크 PR `pull_request_target` 체크아웃 차단 | 없음(greet.yml 은 체크아웃 안 함, 나머지는 `persist-credentials: false`) |
  | #11 setup-uv v5→v10 | node24, 입력 `pyproject-file`·`uv-file` 빠짐, 캐시 기본 glob·`prune-cache` 바뀜, 태그 push 에선 캐시 끔 | 없음(입력을 안 줌, release.yml 은 오히려 안전) |
  | #14 stale v10→v11 | `action.yml` 입력 같음, v11 변경 기록 없음 | 없음. 병합 뒤 needs-info 작업 Run workflow 로 한 번 확인 |
- 돌린 시험: `uv run pytest -q`(3.11) **1023 통과·37 건너뜀**(블렌더 필요). **`scripts/bpy_tests.sh` → 1052 통과, 6 건너뜀**(유체 `app_only` 5개·실제 캐릭터 파일 1개). `uvx ruff@0.15.20 check .`(새 규칙 포함) 통과.
- 막힌 것: GitHub API 가 이 세션에 막혀 dependabot 변경 기록은 raw 파일로 확인. 굽기 시간 어림 1개는 Mac 실측 필요.
- 완료 수·추가 수: **완료 18**(백로그 5 + 감사 11 + 덧붙임 2) / **추가 18**(감사 목록 11 + 덧붙임 2 + 다음 후보 5). 남은 `[ ]` 6개(그중 1개 Mac 실측).
- Mac에서 확인할 것: 맨 위 명령 3줄.

## 2026-10-11 (11회차)

- 한 일: 사용자 요청 "남은 백로그 5개 이어서". 시작 때 PR #13 은 병합됐고(0.7.0 PyPI 게시) 열린 PR 은 #15. main 은 앞서 있지 않음, `latest.md`(10/1)의 FAIL 2건은 main 에 고쳐져 있음(재확인).
  남은 `[ ]` 6개 중 10회차가 넣은 5개를 처리(굽기 시간 어림 1개는 Mac 실측이 필요해 남김):
  1. **CHANGELOG `[0.7.0]` 날짜 2026-10-13 → 2026-10-11**(태그 `v0.7.0` 커밋 날짜·PyPI 게시일) + 출시 절 날짜 = 태그 날짜 시험(태그 없는 얕은 클론은 건너뜀).
  2. **doctor "새 판" 선택 줄** — PyPI JSON 2초 제한, 새 판이면 `uv cache clean blender-fx-mcp` 안내. 오프라인·`BLENDER_FX_NO_UPDATE_CHECK=1`·이상한 응답이면 줄 없음, MCP 도구는 안 물음. 이 컨테이너에서 실제 조회 "최신(PyPI 0.7.0)".
  3. **`scripts/release_notes.py vX.Y.Z`** — CHANGELOG 절을 릴리스 본문으로(영어 요약 먼저, 관리자 메모 빼고, PyPI 주소). 출시 절차 8단계가 이 명령을 씀.
  4. **README PyPI 판 배지** — 파이썬 배지는 PyPI 분류자로 바꾸지 않음(3.10 을 뺀 main 과 출시된 0.7.0 이 출시 전까지 어긋나므로, 지금처럼 pyproject 기준 + 판 범위 시험).
  5. **0.8.0 준비: Python 3.10 지원 종료** — 분류자를 빼자 시험이 짚은 10곳을 한 커밋에, doctor 파이썬 점검 3.11, `uv.lock`(3.10 전용 `exceptiongroup` 빠짐 → 라이선스 점검이 잡아 표 39개), `importorskip("tomllib")` 3곳 제거, 버전 네 곳·uv.lock 0.8.0, SUPPORT·SECURITY 0.8.x. CHANGELOG 0.8.0 에 *Breaking*/동작 변화.
     `test_current_repo_state` 에 "판은 올렸고 날짜만 기다림" 상태 추가(이제 `release_check.py` 는 '미출시' 한 줄만 실패가 정상).
  - 남은 `[ ]` 가 1개라 규칙대로 다음 회차용 5개 추가(dependabot PR 3개 검토, release_notes `--draft`, 진행 알림 문장, README "Getting help", 진행 알림 stdio 시험).
  - 같은 브랜치에 다른 세션이 동시에 시험 고침 1개(`208933d`)를 푸시해 한 번 거절됨 → 받아서 내 커밋을 그 위로 올려 푸시(겹친 파일 없음).
- 돌린 시험: `uv run pytest -q`(3.11) **942 통과·35 건너뜀**(블렌더 필요한 레시피 시험). CI 서버 명령 **3.11·3.14** + `--cov` → 942 통과·**건너뜀 0**(tomllib 건너뜀이 없어짐), 커버리지 98.33%(하한 95%). 3.10 은 `uv sync` 가 거부.
  **`scripts/bpy_tests.sh` → 971 통과, 6 건너뜀**. `uv build` → `release_check.py --dist` 25개 OK, 휠 분류자 3.11~. `license_check.py` 39/39 OK. `uvx ruff@0.15.20 check .` 통과.
- 막힌 것: 없음. 참고 — 0.8.0 버전을 올렸으므로 출시 전까지 PyPI(0.7.0)보다 main 판이 높다. 태그·PyPI 는 사람 몫.
- 완료 수·추가 수: **완료 5** / **추가 5**. 남은 `[ ]` 6개(그중 1개는 Mac 실측 필요).
- Mac에서 확인할 것: 맨 위 명령 3줄.

## 2026-10-11 (10회차)

- 한 일: 맨 앞 지시(F1·F3)는 9회차에 끝나 PR #13 으로 main 에 병합됐고, 사람이 태그 `v0.7.0` 을 밀어 release.yml 첫 실행(10:51 UTC, 성공, 44초)이
  PyPI 에 0.7.0(휠·sdist)을 올린 것을 확인 → 이번 회차는 바로 백로그. `latest.md`(10/1)의 FAIL 2건은 main 에 이미 고쳐져 있음(재확인).
  0.7.0 이 나가 CHANGELOG 맨 위에 `## 0.8.0 — 미출시 (준비 중)` 절을 열고 이번 변경을 모음(버전 네 곳은 0.7.0 그대로 → `release_check.py` 는 "판 다름·미출시" 2줄만 FAIL 이 정상).
  1. **`release_check.py --tag vX.Y.Z`** (`64515f9`): `v` 빠짐·판 다름이면 고칠 곳과 `git push --delete` 안내. release.yml build 잡의 셸 비교를 이 명령 하나로 합쳐 규칙이 한 곳.
  2. **설치 명령을 PyPI 로** (`803802c`): `uvx blender-fx-mcp`, 점검 `uvx --from blender-fx-mcp blender-fx-doctor`. README·examples 7개·doctor·연결 거부 오류·버그 양식.
     이 컨테이너에서 `uvx --from blender-fx-mcp==0.7.0 blender-fx-doctor --json` 실제로 돎. troubleshooting 에 "새 판이 나왔는데 예전 판이 돎" 절.
  3. **doctor 디스크 부족 안내** (`7d85f80`): 5GB 아래면 큰 묶음(구운 캐시·스냅샷·렌더 결과)과 크기, 지울 방법을 큰 것부터. 다 작으면 "지워도 소용없음".
  4. **first_render.py 끝까지 시험** (`c4ce5f3`): 진짜 서버 + 가짜 블렌더 수신기(소켓, 애드온 규약, render 는 진짜 PNG). 한/영 성공·레시피 실패.
  5. **출시 절차 문서** (`f5991ab`): maintenance.md 한/영 8단계 + release.yml 과 이름이 맞는지 시험.
  - 새 백로그 5개 (`6d8f8d6`): CHANGELOG 0.7.0 날짜(제목 10-13, 실제 10-11), doctor 새 판 알림, release_notes.py, PyPI 배지, 0.8.0 에서 3.10 빼기.
- 돌린 시험: `uv run pytest -q`(3.11) **917 통과·35 건너뜀**. CI 서버 명령 3.10 + `--cov` → 908 통과·9 건너뜀, 커버리지 **98.28%**(하한 95%).
  **`scripts/bpy_tests.sh`(bpy) → 946 통과, 6 건너뜀**(유체 `app_only` 5개·실제 캐릭터 파일 1개 — 블렌더 앱·파일 필요). `uvx ruff@0.15.20 check .` 통과.
  변이 확인: README 에 git+ 설치 명령을 되돌리면 새 시험이 실패.
- 막힌 것: 없음. 참고 — release.yml 실행이 44초라 환경 `pypi` 에 필수 검토자가 없었던 것 같음(승인 없이 게시). 의도가 아니면 Settings → Environments → `pypi` 에 검토자 추가.
  CHANGELOG `[0.7.0]` 제목 날짜(2026-10-13)가 실제 게시일(10-11)과 다름 → 백로그 첫 항목으로 남김(사람이 정한 날짜라 이번엔 안 바꿈).
- 완료 수·추가 수: **완료 5** / **추가 5**. 남은 `[ ]` 6개(그중 굽기 시간 어림 1개는 Mac 실측 필요).
- Mac에서 확인할 것: 맨 위 명령 3줄.

## 2026-10-11 (9회차)

- 한 일: 맨 앞 지시(10/11 감사, 0.7.0 출시 준비 F1·F3)부터. main 은 앞서 있지 않음, `latest.md`(10/1)의 FAIL 2건은 main 에 고쳐져 있음(재확인).
  - **F1 버전 0.7.0** (`ff7555e`): pyproject·`__init__`·server.json.example 2곳·CITATION.cff·uv.lock 루트 패키지 판(의존성 그대로, `uv lock --check` 통과).
    SUPPORT·SECURITY 지원 계열 0.7.x. CHANGELOG 머리 `## [0.7.0] - 2026-10-13`, 버전 유예 문장 → "올렸음, 태그·PyPI 는 사람 승인 뒤 Mac".
    `release_check.py` 와 CHANGELOG 절 시험의 제목 정규식이 `## [X.Y.Z] - 날짜`(Keep a Changelog)도 읽게. `release_check.py` → 점검 8개 모두 OK.
  - **F3 `.github/workflows/release.yml`** (`4eb778f`): tag push `v*` 만. 최상위·build `contents: read`. build: checkout(`persist-credentials: false`)
    → 태그·pyproject 판 일치(표현식 대신 `GITHUB_REF_NAME` 환경 변수) → release_check → uv build → `--dist` → twine 7.0.0 check → artifact 업로드.
    publish: `needs: build`, `environment: pypi`, 권한 `id-token: write` 하나, artifact 만 받아 `pypa/gh-action-pypi-publish` (run·checkout 없음).
    액션 SHA 는 `git ls-remote` 로 확인(upload-artifact v7.0.2·download-artifact v8.0.2·pypi-publish v1.14.2 는 주석 태그라 `^{}` 커밋). actionlint 통과.
    시험: `JOB_WRITE_PERMISSIONS` 에 release.yml `id-token: write` 만, 잡이 여럿이어도 잡 단위 블록에서 찾도록. 새 시험 `test_release_workflow_publish_only_uploads_artifact`.
    변이 확인: build 에 id-token 을 넣으면 기존 권한 시험과 새 시험이, `workflow_dispatch` 를 더하면 새 시험이 실패. SECURITY 공급망 표·registry.md 게시 단계 갱신.
  그다음 백로그(사용자 체감 우선) 4개:
  1. **`clear_caches` 지운 양·남은 여유** — 지운 MB(없으면 그렇다고) + 출력 폴더 디스크 여유, 1GB 아래면 다음 할 일. 원격 블렌더면 여유 줄 없음.
  2. **`clear_snapshots(keep=5)`** 새 도구(도구 33개) — 오래된 것부터, `before_restore` 는 늘 남김, `.blend1` 도. `list_snapshots` 에 개수·합계·정리 안내.
  3. **버그 양식 doctor 칸** — `render` 없이 `--issue` 마크다운(표·접기가 보임), `--json` 은 `render: json` 선택 칸. 질문 양식도.
  4. **상대 경로** — 확인해 보니 레시피는 `expanduser` 만 해서 블렌더 작업 폴더(Finder 로 켠 앱은 `/`) 기준이었음. 내보내기 → 출력 폴더,
     가져오기·HDRI → 서버 작업 폴더 → 출력 폴더, 둘 다 없으면 블렌더에 보내기 전에 찾아본 폴더와 "전체 경로로 다시". ⚠️ 동작 변화.
  - 남은 `[ ]` 1개(굽기 시간 어림 — Mac 실측 필요)라 새 항목 5개 추가(`--tag` 점검, PyPI 게시 뒤 설치 명령 단축, doctor 큰 폴더 안내, first_render 가짜 수신기 시험, 출시 절차 문서).
- 돌린 시험: `uv run pytest -q`(3.11) **891 통과·35 건너뜀**. CI 서버 명령 3.10 + `--cov` → 882 통과·9 건너뜀, 커버리지 **98.44%**(하한 95%).
  **`scripts/bpy_tests.sh`(bpy 5.0.1) → 920 통과, 6 건너뜀**(유체 `app_only` 5개·실제 캐릭터 파일 1개 — 블렌더 앱·파일 필요). `uvx ruff@0.15.20 check .` 통과.
  release.yml build 단계를 로컬에서 그대로(태그 v0.7.0 일치·v0.6.9 불일치 검출, release_check 8개, `uv build`, `--dist` 25개, twine PASSED). actionlint 통과.
  못 돌린 것: release.yml 실제 실행(태그를 밀어야 돎 — 사람 몫), PyPI 신뢰 게시자·환경 `pypi` 설정(저장소·PyPI 설정 화면).
- 막힌 것: 없음. 상대 경로 변경이 Windows CI 에서 시험 4개를 깨뜨림(`"/m/tower.glb"` 는 Windows 에서 드라이브가 없어 상대 경로) → 다른 세션이 `d6199cf` 로 시험을 이 OS 의 절대 경로로 고침(제품 동작은 그대로).
- 완료 수·추가 수: **완료 6**(F1·F3 + 백로그 4) / **추가 5**. 남은 `[ ]` 6개.
- 출시 전 사람이 할 것: PyPI 프로젝트 설정 → Publishing 에 저장소·`release.yml`·환경 `pypi` 신뢰 게시자 등록, GitHub Settings → Environments 에 `pypi`(필수 검토자) 생성 → 그다음 태그.
- Mac에서 확인할 것: 맨 위 명령 3줄.

## 2026-10-10 (8회차)

- 한 일: 사용자 요청 "새 항목 5개 추가하고 이어서 처리". main 은 앞서 있지 않음, `latest.md`(10/1)의 FAIL 2건은 main 에 고쳐져 있음(재확인).
  백로그에 사용자 체감 우선 5개를 추가하고 **5개 모두 완료**:
  1. **언어 자동 선택** — `BLENDER_FX_LANG` 이 없으면 로캘(`LC_ALL`→`LC_MESSAGES`→`LANG`): 한국어면 ko, 다른 언어면 en, 없거나 `C`/`POSIX` 면 ko(지금과 같음). doctor `--json` 에 `lang_source`. ⚠️ 동작 변화(영어 로캘 터미널).
  2. **대상 이름 오타 제안** — `destroy(target="building")` → "Did you mean 'Building'? Names are case-sensitive." 메시가 아닌 오브젝트는 종류를, 빈 장면이면 만드는 도구를. bpy 시험.
  3. **디스크 여유** — doctor "출력 폴더 여유 공간" 선택 줄(5GB 아래 `[- ]`), 물·연기·폭발 굽기는 1GB 아래면 블렌더에 보내기 전에 멈춤(폭발은 조각내기 전에). 해결법 문서 문장.
  4. **긴 도구 진행 알림** — 굽기·렌더·저장 중 5초마다 MCP `report_progress`("블렌더에서 작업 중 — 45초"). 클라이언트가 progressToken 을 줄 때만. 도구 서명은 그대로(`FxServer` + contextvar).
  5. **`blender-fx-doctor --issue`** — 이슈용 마크다운(판·OS·파이썬·블렌더·클라이언트·언어 표 + 점검 전체), 집 폴더는 `~` 로 가림. 버그·질문 양식이 권함.
  - 남은 `[ ]` 0개가 되어 원래 규칙(3개 미만이면 5개 추가)대로 다음 회차용 5개를 근거와 함께 추가(clear_caches 확보 용량·스냅샷 정리·굽기 시간 어림·상대 경로·`--issue` 붙일 양식 칸).
- 돌린 시험: `uv run pytest -q` **855 통과·35 건너뜀**(3.11). CI 서버 명령 3.10(846 통과, 9 건너뜀)·3.14(855 통과), 커버리지 98.4~98.7%(하한 95%). **`scripts/bpy_tests.sh` → 884 통과, 6 건너뜀**(유체 `app_only` 5개·실제 캐릭터 파일 1개). `uvx ruff@0.15.20 check .` 통과.
  하다가 시험이 잡은 것 2개: CHANGELOG 영어 요약 6줄 한도(언어 줄에 합침), "오류마다 다음 할 일" 시험(메시가 아닌 대상 문장에 다시 시킬 말 추가).
- 막힌 것: 없음. 진행 알림이 실제 클라이언트(Claude Code·Desktop) 화면에 보이는지는 Mac 몫.
- 완료 수·추가 수: **완료 5** / **추가 10**(요청 5 + 규칙 5). 남은 `[ ]` 5개.
- Mac에서 확인할 것: 맨 위 명령 3줄.

## 2026-10-10 (7회차)

- 한 일: 맨 앞 지시(10/10 Mac 실패 10개)는 **4회차에 이미 고쳐 PR #13 에 있음**(커밋 125b479)을 다시 확인 —
  `BLENDER_FX_LANG=en` + `HOME`·`TMPDIR` 한글 폴더, `ko` 두 갈래로 전체 시험 777 통과·0 실패. `latest.md`(10/1)의 FAIL 2건은 main 에 고쳐져 있음. main 은 앞서 있지 않음.
  그다음 백로그(사용자 체감 우선):
  1. **해결법 문서 "Tools not visible in the client" 절**(백로그) — 등록 확인 → 앱 완전 재시작 → 설정 파일 위치·문법 → `uvx` 전체 경로, 한/영. doctor 등록 할 일 끝에 그 링크.
  2. **doctor `--json` 의 `clients`**(백로그) — 버그 양식 클라이언트 칸에 "doctor `--json` 의 `clients` 를 고르세요". 양식 선택지 = doctor 가 아는 클라이언트 시험.
  3. **서버 명령을 터미널에서 직접 치면 stderr 안내**(새 항목) — "멈춘 것이 아닙니다" + 등록·점검·Ctrl+C. 클라이언트가 띄우면(파이프) 조용.
  4. **doctor 등록 안내를 깔린 클라이언트에 맞게**(새 항목) — Claude Code 없이 Cursor·Claude Desktop·Codex 만 있으면 그 설정 파일 + `examples/` 예제.
  5. **창 앱에는 `uvx` 전체 경로**(새 항목) — Claude Desktop·Cursor 는 셸 PATH 를 못 봄(`spawn uvx ENOENT`). uv 줄·등록 안내·examples/README 한/영.
  6. **`first_render.py` 진행 줄 `[i/5] … (기다리는 중)` + 걸린 초**(새 항목).
  7. **README 한/영 설치 절에 `first_render.py`**(새 항목) — 영어 절에 한글 앵커를 넣었다가 기존 "영어 절에 한글 없음" 시험이 잡아 파일 링크로 고침.
  - CHANGELOG 0.7.0(미출시) 한/영 갱신.
  - 브랜치: 이 세션의 지정 브랜치 `claude/cloud-work-lxraz2` 에서 작업해 푸시하고, PR #13 의 머리 `claude/cloud-work` 에도 같은 커밋을 앞으로 감기(fast-forward)로 푸시.
- 돌린 시험: `uv run pytest -q` **800 통과·34 건너뜀**(3.11, Linux, 23개 추가). 바뀐 시험 파일 5개는 **Python 3.10·3.14** 로도 통과. `uvx ruff@0.15.20 check .` 통과.
  건너뛴 34개는 블렌더(앱·bpy)가 없어서 — 레시피 시험(CI `recipe-tests-bpy`·Mac 앱 몫). 레시피를 안 바꿔 `bpy_tests.sh` 는 안 돌림.
  창 앱이 정말 `uvx` 를 못 찾는지, 진행 줄이 실제 굽기 동안 보이는지는 Mac 의 Claude Desktop·블렌더 앱이 필요해 Mac 몫.
- 완료 수·추가 수: **완료 7**(백로그 기존 2 + 새 5) / **추가 5**. 남은 `[ ]` 0개 — '완료 ≥ 추가'를 지키려 이번 회차엔 더 추가하지 않음. 다음 회차가 맨 먼저 5개 추가.
- Mac에서 확인할 것: 맨 위 명령 3줄.

## 2026-10-10 (6회차)

- 한 일: 맨 앞 지시(10/10 Mac 실패 10개)는 **4회차에 이미 고쳐 main 대상 PR #13 에 있음**을 다시 확인 —
  `HOME`·`--basetemp` 를 한글 폴더로 + `BLENDER_FX_LANG=en` 으로 전체 시험 709 통과·0 실패(고치기 전 재현은 4회차 기록).
  `latest.md`(10/1)의 FAIL 2건은 10/2 에 고쳐 main 에 있음. main 은 앞서 있지 않음. 그다음 백로그(사용자 체감 우선):
  1. **doctor "MCP 클라이언트 등록" 선택 항목**(백로그) — Claude Code(`~/.claude.json` 사용자·폴더 범위, `.mcp.json`)·Claude Desktop·Cursor·Codex 설정에서 찾고,
     없으면 README 4단계 등록 명령을 "(선택)" 할 일로. README 4단계에 `→ [OK] MCP 클라이언트 등록`. 이제 첫 화면 4단계가 모두 doctor 로 확인된다.
  2. **MCP 프롬프트 `/first_demo`·`/undo_last`**(백로그) — 클라이언트 `/` 메뉴에서 첫 데모(연결 → 건물 → 스냅샷 → 붕괴 → 미리보기)와 되돌리기(확인 후 restore).
  3. **`examples/first_render.py`**(백로그) — 터미널에서 첫 렌더 PNG 경로까지. 연결 안 되면 다음 할 일 + 종료 코드 2.
     시험을 짜다 **예제 결함** 발견: `result.isError` 는 지금 SDK 에 없는 이름(`is_error`) → 성공 갈래에서 바로 죽었을 것. 고침.
  4. **MCP `doctor` 도구에서는 클라이언트 등록 항목 뺌**(새 항목, 1번이 만든 문제) — 이미 연결된 AI 에게 등록 명령을 권하지 않게.
  5. **`first_render.py` 가 시작 전에 `first_render_before` 스냅샷**(새 항목) — 사용자 장면에 Building 을 더해 부숴도 돌아갈 수 있게, 끝에 되돌리는 방법.
  6. **MCP 프롬프트 `/my_model`**(새 항목) — 내 모델 가져오기 → `inspect_mesh` 점검(문제면 확인) → 붕괴 → 미리보기.
  - 같은 브랜치에서 다른 세션이 1번 시험의 Python 3.14 CI 실패(`sys.platform` 을 바꾸면 `shutil.which` 가 `_winapi` 로 감)를 먼저 고쳐 푸시해 있어, 그 위에 이어 올림.
- 돌린 시험: `uv run pytest -q` **777 통과·34 건너뜀**(3.11, Linux). 한글 HOME·basetemp + `en` 으로도 통과.
  새·바뀐 시험 파일(doctor·프롬프트·예제·메시지)은 **Python 3.10·3.14** 로도 통과. `uvx ruff@0.15.20 check .` 통과.
  건너뛴 34개는 블렌더(앱·bpy)가 없어서 — 레시피 시험(CI `recipe-tests-bpy`·Mac 앱 몫). 이번 회차는 레시피를 안 바꿔 `bpy_tests.sh` 는 안 돌림.
  `first_render.py` 가 **실제 블렌더로** PNG 를 내는지, 프롬프트가 Claude Code `/` 메뉴에 뜨는지는 블렌더 앱·클라이언트가 필요해 Mac 몫(맨 위 3번째 줄).
- 완료 수·추가 수: **완료 6**(백로그 기존 3 + 새 3) / **추가 5**. 남은 `[ ]` 2개(troubleshooting "도구가 안 보임" 절·doctor `--json` 의 clients).
- Mac에서 확인할 것: 맨 위 명령 3줄.

## 2026-10-10 (5회차)

- 한 일: 맨 앞 지시(10/10 Mac 실패 10개)는 **4회차(오늘 이른 시각)에 이미 고쳐져 있음**을 확인 — `HOME`·`--basetemp` 를 한글 폴더로, `BLENDER_FX_LANG=en` 으로 전체 시험 661 통과·0 실패.
  `latest.md`(10/1)의 FAIL 2건은 10/2 에 고쳐 main 에 있음. main 은 앞서 있지 않음. 그다음 백로그(사용자 체감 우선):
  1. **연결 거부 오류가 원인을 좁혀 다음 한 단계**(백로그) — 이 컴퓨터에 애드온 파일이 없으면 설치 메뉴 경로부터, 있으면 Connect, 포트를 바꿨으면 Port 맞추기.
     애드온 폴더 목록을 doctor 에서 bridge 로 옮겨 둘이 같은 곳을 봄. 원격 `BLENDER_FX_HOST` 면 설치 안내 안 함.
  2. **파일·스냅샷 경로 오류에 다음 할 일**(백로그) — `import_model`·HDRI 파일이 없으면 같은 폴더의 비슷한 이름, `restore` 는 있는 스냅샷 이름.
     레시피 오류 문장 44개 전부 다음 할 일 표지(…세요·고를 값)가 있는지 정적 시험(블렌더 내부 실패 3곳만 이유와 함께 예외).
  3. **README 첫 화면 = doctor 순서의 4단계**(백로그) — uv → 블렌더+애드온 → Connect → 클로드 등록, 단계마다 확인할 `[OK]` 줄. 순서·이름이 doctor 와 같은지 시험.
  4. **`restore` 이름 오타가 지난 `before_restore` 를 덮어쓰던 문제**(새 항목, 2번 하다 발견) — 블렌더에 보내기 전에 멈추고 이름 제안.
  5. **`ping_blender`·doctor 에 블렌더 판 + 시험한 판이 아니면 경고**(새 항목).
- 돌린 시험: `uv run pytest -q` **709 통과·34 건너뜀**(3.11, Linux). 한글 HOME·basetemp + `en` 으로도 통과. CI 서버 명령 커버리지 99.42%(하한 95%).
  새 시험 파일은 Python 3.10 으로도 통과. `uvx ruff@0.15.20 check .` 통과. **`scripts/bpy_tests.sh`(bpy 5.0.1) 717 통과·6 건너뜀·0 실패**(레시피 문장 수정 뒤).
  건너뛴 34개(서버 시험)·6개(bpy)는 블렌더 앱이 필요해서 — 유체 `app_only` 5개·실제 캐릭터 파일 1개, 나머지는 bpy 가 없는 기본 환경의 레시피 시험.
- 완료 수·추가 수: **완료 5**(백로그 기존 3 + 새 2) / **추가 5**. 남은 `[ ]` 3개(doctor 클라이언트 등록 줄·MCP 프롬프트·examples/first_render.py).
- Mac에서 확인할 것: 맨 위 명령 3줄.

## 2026-10-10 (4회차)

- 한 일: **10/10 Mac 실측 실패 10개 먼저** → 그다음 백로그. main 이 앞서 있어(#10 병합) 병합 확인(내용 변화 없음).
  1. **시험 결함 10개 고침.** 여기서 그대로 재현: `BLENDER_FX_LANG=en` + 한글 `--basetemp` 로 고치기 전 10 실패 → 고친 뒤 0.
     ① 언어: `tests/conftest.py` autouse 픽스처가 매 시험 `BLENDER_FX_LANG` 을 지우고 시작, 한국어 기대 시험 3개는 `ko` 직접 지정.
     ② 한글 경로: 영어 메시지 한글 검사에서 출력 폴더 경로를 빼고 검사. 회귀 시험 3개(출력 폴더가 `사용자/출력` 일 때 영어 문장·경로가 온전한지).
  2. **Windows 에서도 가짜 블렌더 시험**(백로그) — `fake_blender`(파이썬 본문 + `/bin/sh exec`·`.cmd` 감싸개). 건너뜀 18 → 1(세그폴트).
     덤으로 **제품 문제** 고침: headless·doctor 가 블렌더 출력을 OS 기본 인코딩으로 읽어 Windows 에서 `UnicodeDecodeError` 위험 → UTF-8(errors=replace).
  3. **주 1회 취약점 점검**(백로그) `audit.yml`(pip-audit 2.9.0, `uv.lock` 그대로). **처음 돌리자 실제 취약점 2건**: 간접 의존성 `pyjwt 2.14.0` → 2.15.1 로 올려 0건.
  4. **이슈 양식 공통 칸 시험**(백로그) — 클라이언트 선택지·블렌더 판 placeholder·OS 가 examples/SUPPORT 와 같은지. 어긋난 곳은 없었음.
  5. **doctor "다음 할 일"**(새 항목) — 실패 항목마다 다음 한 단계를 설치 순서대로 번호로. uv 설치 명령을 OS 별로(지금까지 Windows·Linux 에도 `brew`),
     애드온 Install from Disk 경로, 포트를 바꿨으면 포트 맞추기. MCP `doctor` 도구도 같은 보고서.
  6. **doctor 블렌더 실행 파일 = 선택 항목**(새 항목) — MCP 사용에 필요 없는데 `[X ]` 로 떠 첫 사용자를 막던 것 → `[- ]`, 확인 필요·JSON `failed` 에서 뺌.
- 돌린 시험: `uv run pytest -q` **661 통과·34 건너뜀**(Python 3.11, Linux). `BLENDER_FX_LANG=en`·`ko`·없음 × 한글 `--basetemp` 로도 모두 통과.
  `uvx ruff@0.15.20 check .` 통과. 서버 쪽 커버리지 99%. `scripts/license_check.py` 40/40.
  건너뛴 34개는 블렌더(앱·bpy)가 없어서 — 레시피 시험(CI `recipe-tests-bpy`·Mac 앱 몫). Windows CI 결과는 PR #13 에서 확인.
- 완료 수·추가 수: **완료 5**(백로그 기존 3 + 새 2) + Mac 실패 수정 / **추가 5**(새 항목 중 하나는 이미 있던 `CITATION.cff` 라 README 단계 정렬로 바꿈). 남은 `[ ]` 3개.
- 하다가 실수: CHANGELOG 영어 요약 6줄 제한을 넘긴 채 한 번 푸시 → 바로 다음 커밋에서 고침.

## 2026-10-09 (3회차)

- 한 일: `latest.md`(10/1) FAIL 2건(GIF 링크·버튼 이름)은 10/2 회차에 고쳐 main 에 있음을 다시 확인 → 백로그로 진행. main 은 앞서 있지 않았음(cloud-work 가 main 을 포함). **백로그 21개 완료**(앞 회차가 남긴 7개 + 이번 회차에 세 번 나눠 추가한 15개 중 14개. 아래 19줄은 관련 항목을 묶어 적음). 남은 `[ ]` 3개.
  1. **라벨 정의** `.github/labels.yml`(8개, 한/영 설명) + dependabot 라벨 고정 + maintenance.md `gh label create` 8줄. 양식·문서·dependabot·stale 이 쓰는 라벨이 모두 정의돼 있는지 시험.
  2. **`examples/list_tools.py`** — 공식 `mcp` 클라이언트로 서버를 stdio 로 띄워 도구 목록·`ping_blender`. 닫힌 포트로 한/영 시험.
  3. **파이썬 3.14** — 3.14.6 에서 서버 시험·커버리지 통과, 분류자·CI·SUPPORT·배지·architecture 갱신.
  4. **`needs-info` 30일 자동 닫기** `stale.yml`(23일 뒤 `stale` 표시, 7일 뒤 닫음, PR 제외, `issues: write` 만).
  5. **OpenSSF Scorecard** 작업·README 배지(병합 뒤 main 에서 처음 돌아야 점수가 뜸).
  6. **recipes.md 한 줄 예시** — 예시 없던 도구 25개(한/영). 32개 도구 모두 예시가 있고 인자가 서버 검사를 통과하는지 시험.
  7. **`blender-fx-doctor --json`** — 언어와 무관한 항목 id, 버그·질문 양식에 안내.
  8. **의존성 라이선스 점검** `scripts/license_check.py` + `docs/third-party-licenses.md`(40개 모두 허용적 라이선스) + CI lint 단계.
  9. **macOS·Windows CI** `server-tests-os`. 첫 실행에서 Windows 13개 실패 → **제품 버그 2개 고침**(doctor 애드온 경로 `/`·`\` 섞임, release_check 가 CRLF 메타데이터에서 README 를 못 찾음) + 시험 쪽 경로·인코딩·실행 권한 처리.
  10. **질문 이슈 양식** `question.yml`(라벨 `question`), SUPPORT 링크.
  11. **README 도구 표 점검** `scripts/gen_tool_table.py` — 통째 생성 대신(손으로 다듬은 설명이 더 자세함) 빠진 도구·`a/b/c` 값 목록이 서버 허용 값과 같은지 + `--draft` 초안 행.
  12. **3.10 지원 종료 예고** — CHANGELOG 0.7.0(한/영)·maintenance.md(0.8.0 에서 뺌). 드라이런으로 고칠 곳 10곳을 시험이 모두 짚는 것 확인.
  13. **`.gitattributes`** — 모든 OS 에서 LF, 바이너리 지정, CRLF 파일이 생기면 시험 실패.
  14. **SPDX 표기** — 패키지·레시피·스크립트·예제 41개 첫 줄 `# SPDX-License-Identifier: MIT`.
  15. **첫 기여자 인사** `greet.yml`(한/영, PR 코드 체크아웃 없음).
  16. **SECURITY.md 공급망 표**(한/영 8줄) — 쓰다가 CI 의 `uv sync` 에 `--locked` 가 없던 것을 발견해 모두 고침.
  17. **Windows 건너뛰는 시험 문서화** — CONTRIBUTING 에 18개(가짜 `/bin/sh` 블렌더)와 이유, 개수 시험.
  18. **배포물 라이선스 파일 점검** — `release_check.py --dist` 가 휠·sdist 의 LICENSE·제3자 라이선스 표를 봄(25개 OK).
  19. **문서 링크 점검** `tests/test_docs_links.py` — .md 19개의 상대 링크·앵커(한글 제목 포함), 지금 깨진 링크 0개.
- 돌린 시험: `uvx ruff@0.15.20 check .` 통과. `uv run pytest -q`(블렌더 없음, 3.11) → **638 통과, 34 건너뜀**. CI 서버 명령 3.10(629 통과, 9 건너뜀 — tomllib)·3.14(638 통과), 커버리지 99.04%(하한 95%). **`scripts/bpy_tests.sh` → 666 통과, 6 건너뜀**(회차 끝 기준)(유체 `app_only` 5개·실제 캐릭터 파일 1개). `uv build` → `release_check.py --dist` 25개 OK, `twine@7.0.0 check` PASSED 2개. `uv lock --check` 통과. `license_check.py` 40/40 OK. PR CI(run 58, Windows 고친 커밋): lint·server-tests 3.10~3.14·macOS·**Windows**·recipe-tests-bpy 모두 초록.
- 막힌 것: 없음. 라벨 만들기·Scorecard 첫 실행·stale 작업은 병합 뒤 GitHub 에서만 확인 가능(클라우드는 라벨·설정을 바꾸지 않음).
- PR: 열려 있는 claude/cloud-work → main #13 에 이번 커밋이 함께 올라감(본문에 이번 회차 목록 추가).
- Mac에서 확인할 것:
  1. 맨 위 명령 3줄
  2. 병합 뒤 `docs/maintenance.md` 의 `gh label create … --force` 8줄을 저장소 폴더에서 돌려 라벨 만들기
  3. 병합 뒤 Actions 에서 scorecard 작업(main 푸시로 자동 실행)이 초록인지·README Scorecard 배지에 점수가 뜨는지, needs-info 작업을 Run workflow 로 한 번 돌려 초록인지

## 2026-10-09 (2회차)

- 한 일: `latest.md`(10/1) FAIL 2건(GIF 링크·버튼 이름)은 10/2 회차에 고쳐 main 에 있음을 다시 확인 → 백로그로 진행. main 은 앞서 있지 않았음. 백로그 4개 완료 → 남은 항목이 2개라 새 항목 5개 추가(파이썬 3.14·needs-info 자동 닫기·Scorecard·도구 예시 빠짐없이·doctor `--json`).
  1. **`scripts/bpy_tests.sh`** — 블렌더 앱 없이 bpy 5.0.1(Python 3.11)로 레시피 시험. 개발용 `.venv` 와 따로 `.venv-bpy`, libEGL 이 없으면 CI 와 같은 apt 명령을 알려 줌. 판·apt 패키지가 ci.yml 과 같은지 시험 2개. **이번 회차부터 클라우드도 레시피 시험을 돌림.**
  2. **Metadata-Version 2.5 확인** — twine 7.0.0(2026-07-27)부터 2.5 업로드 지원, PyPI 도 받음 → hatchling 판은 묶지 않음. `release_check.py --dist` 에 Metadata-Version(2.1~2.5) 칸, CI 에 `uvx twine@7.0.0 check dist/*`, registry.md 순서 갱신. 시험 4개.
  3. **최저·최고 파이썬 판 한 시험** — 분류자 기준으로 requires-python·ruff target-version·uv.lock·CI 행렬·SUPPORT·README 배지·architecture·maintenance 한/영. 어긋난 곳을 모두 한 번에 알려 줌. maintenance.md 에 판 정리 순서.
  4. **기능 요청 YAML 폼** — 필수 칸 3개(원하는 결과·예시 명령·대신 쓰는 방법), `.md` 지움, SUPPORT 링크 고침. 버그·기능 폼을 같은 시험으로.
- 돌린 시험: `uvx ruff@0.15.20 check .` 통과. `uv run pytest -q`(블렌더 없음) → **573 통과, 34 건너뜀**. CI 서버 명령 3.10(568 통과, 5 건너뜀)·3.13(573 통과), 커버리지 99.35%(하한 95%). **`scripts/bpy_tests.sh` → 601 통과, 6 건너뜀**(유체 `app_only` 5개·실제 캐릭터 파일 1개 — 블렌더 앱·개인 파일 필요). `uv build` → `release_check.py --dist` 22개 OK, `twine@7.0.0 check` 휠·sdist PASSED. `uv lock --check` 통과.
- PR: 열려 있는 claude/cloud-work → main #13 에 이번 커밋이 함께 올라감(본문에 이번 회차 목록 추가).
- Mac에서 확인할 것:
  1. `uv run pytest -q` (블렌더 앱으로 전체 통과)
  2. `uv build && uvx twine@7.0.0 check dist/*` (둘 다 PASSED)
  3. 병합 뒤 New issue 화면에 "기능 요청 / Feature request" 폼과 필수 칸(*)이 보이는지

## 2026-10-09

- 한 일: `latest.md`(10/1) FAIL 2건(GIF 링크·버튼 이름)은 10/2 회차에 고쳐 main 에 있음을 다시 확인 → 백로그로 진행. main 은 앞서 있지 않았음. 백로그 4개 완료 → 남은 항목이 1개라 새 항목 5개 추가.
  1. **CI 시험 목록 자동화** — `pytest -q tests --ignore=…`(블렌더 전용 레시피 시험 5개 파일만 뺌). 새 시험 파일이 저절로 CI 에 들어감. CONTRIBUTING 한/영 커버리지 명령도 같은 줄로(전에는 CI 와 달랐음). 시험 2개.
  2. **커버리지 하한 95%** — `--cov-fail-under=95`. CONTRIBUTING 한/영 수치와 일치 시험.
  3. **CI 패키징 점검** — `release_check.py --dist dist`: 휠·sdist 의 판·Project-URL·License-Expression·마크다운 README·`mcp-name`. 판·"미출시" 점검은 빼서 출시 전 PR 에서도 통과. ci.yml 의 `uv build` 다음 줄. 시험 8개.
  4. **`docs/maintenance.md`(한/영)** — 이슈 분류·dependabot 처리(메이저 판은 변경 기록 확인)·판 번호·출시 주기·파이썬 EOL(3.10 은 2026-10)·블렌더 LTS 정리. README·SUPPORT 링크. 시험 4개.
- 돌린 시험: `uvx ruff@0.15.20 check .` 통과. `uv run pytest -q`(Python 3.11) → **564 통과, 34 건너뜀**(블렌더 없음). 새 CI 명령을 3.10(559 통과, 5 건너뜀 — tomllib)·3.13(564 통과) + 하한 → 99.35%. 실제 `uv build` 결과로 `--dist` 20개 OK. `uv lock --check` 통과. 못 돌린 것: 레시피 시험 34개(블렌더 필요 — 레시피 파일은 안 건드림).
- 발견: hatchling 이 **Metadata-Version 2.5** 로 빌드해 `uvx twine@6.2.0 check` 가 거부함(그래서 CI 에 twine 은 넣지 않음). 출시 전에 PyPI·`uv publish` 가 받는지 확인 필요 → 새 백로그 첫 항목.
- PR: 열려 있는 claude/cloud-work → main #13 에 이번 커밋이 함께 올라감(본문에 이번 회차 목록 추가).
- Mac에서 확인할 것:
  1. `uv run pytest -q` (블렌더 앱으로 전체 통과)
  2. `uv build && uv run python scripts/release_check.py --dist dist` (20개 OK)
  3. 병합 뒤 Actions 의 server-tests 에 "Required test coverage of 95% reached" 가 찍히는지

## 2026-10-08 (2회차)

- 한 일: `latest.md`(10/1) FAIL 2건(GIF 링크·버튼 이름)은 10/2 회차에 고쳐 main 에 있음을 다시 확인 → 백로그로 진행. main 은 앞서 있지 않았음. 백로그 4개 완료 → 남은 항목이 1개 이하라 새 항목 5개 추가.
  1. **`CITATION.cff`** — GitHub "Cite this repository". `uvx cffconvert --validate` 통과. 출시 때 올릴 버전이 **네 곳**이 됨(`release_check.py`·CHANGELOG 출시 순서·registry.md 갱신). 시험 2개 + release_check 판 어긋남 칸.
  2. **CHANGELOG 0.7.0 영어 요약** — *Fixes*·*Tests and CI*·*Docs*. 시험: 미출시 절마다 요약이 있고 한글이 없는지, 한국어 상세보다 앞인지.
  3. **server.py 실패 갈래 시험** — bridge 는 이미 100%. 도구 29개 × 한/영 연결 실패 문장, `ping_blender`·`doctor` 도구 등. **server 94% → 99%**, 서버 쪽 전체 99%.
  4. **CONTRIBUTING "처음 기여하기 좋은 일"(한/영)** — 작은 일 4가지·파일·시험 명령 표, `good first issue`·`needs-info` 뜻. 시험 3개(파일·`-k` 시험 존재, 라벨이 SUPPORT 와 같은지).
- 돌린 시험: `uvx ruff@0.15.20 check .` 통과. `uv run pytest -q`(Python 3.11) → **546 통과, 34 건너뜀**(블렌더 없음). CI 서버 시험 목록을 3.10(544 통과, 5 건너뜀 — tomllib)·3.13(549 통과) + `--cov` → 99%. `uv lock --check` 통과. 못 돌린 것: 레시피 시험 34개(블렌더 필요 — 레시피 파일은 안 건드림).
- 참고: dependabot 이 SHA 고정 액션을 SHA·판 주석 함께 올리는 것 확인(checkout v4.4.0 → v7.0.1, setup-uv v5.4.2 → v10.2.0 브랜치). 메이저 판이라 Mac 에서 변경 기록을 보고 병합할 것(새 백로그 `docs/maintenance.md` 항목에 처리 순서를 적을 예정).
- PR: 열려 있는 claude/cloud-work → main #13 에 이번 커밋이 함께 올라감(본문에 이번 회차 목록 추가).
- Mac에서 확인할 것:
  1. `uv run pytest -q` (블렌더 앱으로 전체 통과)
  2. `uv run python scripts/release_check.py` (CITATION.cff 줄 OK, FAIL 은 "판 다름"·"미출시" 2줄이 정상)
  3. 병합 뒤 GitHub 저장소 오른쪽에 "Cite this repository" 가 뜨는지

## 2026-10-08

- 한 일: `latest.md`(10/1) FAIL 2건(GIF 링크·버튼 이름)은 10/2 회차에 고쳐 main 에 있음을 다시 확인 → 백로그로 진행. main 은 앞서 있지 않았음(병합할 것 없음). PR #13 이 아직 열려 있어 이번 커밋도 그 PR 에 쌓임. 남은 백로그 3개 완료 → 0개가 되어 새 항목 5개 추가, 그중 1개까지 모두 4개.
  1. **버그 신고 YAML 폼** `.github/ISSUE_TEMPLATE/bug_report.yml`(한/영) — 필수 칸 6개(doctor 출력·블렌더 판·OS·MCP 클라이언트·재현 명령·결과). `.md` 양식은 지움(둘 다 있으면 두 개 보임), troubleshooting.md 의 `template=bug_report.md` 링크 2곳 고침. 시험 6개(PyYAML 이 없어 정규식으로 읽음, 로컬에서 PyYAML 로 한 번 파싱 확인).
  2. **`SUPPORT.md`(한/영)** — 신고 경로 표, 응답 목표(보안·버그 7일 = SECURITY.md, 질문·기능 14일), 지원 판 표(블렌더 5.2 LTS·bpy 5.0.1 CI 용·4.x 미확인, 파이썬 3.10~3.13, 0.6.x). README 한/영에서 링크. 시험 4개(분류자·CI 행렬·README·app-tests·bpy 판·SECURITY 와 일치).
  3. **`docs/recipes.md` 영어 절** — 같은 5개 예시·수치. README 영어 절 링크를 `#english` 로. 시험 4개: 한/영 도구 호출 일치, 실제 도구·인자, 영어 절 한글 없음, **예시 인자가 서버 목록·범위 검사를 통과하는지**.
  4. **CI 파이썬 행렬에 3.11** — 분류자 모든 판을 돌림. 시험을 "양 끝" → "모든 판"으로. SUPPORT·architecture·CHANGELOG·CONTRIBUTING(커버리지 95%) 갱신.
- 돌린 시험: `uvx ruff@0.15.20 check .` 통과. `uv run pytest -q`(Python 3.11) → **478 통과, 34 건너뜀**(블렌더 없음). CI 서버 시험 목록을 3.10(473 통과, 5 건너뜀 — tomllib)·3.11·3.13(478 통과) + `--cov` → 95~96%. `uv lock --check` 통과. 못 돌린 것: 레시피 시험 34개(블렌더 필요 — 레시피 파일은 안 건드림). YAML 폼이 GitHub 이슈 화면에서 실제로 보이는지는 main 병합 뒤에만 확인 가능.
- PR: 열려 있는 claude/cloud-work → main #13 에 이번 커밋이 함께 올라감(본문에 이번 회차 목록 추가).
- 참고: SUPPORT.md 가 `needs-info` 라벨을 말하므로 저장소에 그 라벨이 없으면 만들어 두면 좋음(클라우드에서는 라벨을 만들지 않았음).
- Mac에서 확인할 것:
  1. `uv run pytest -q` (블렌더 앱으로 전체 통과)
  2. 병합 뒤 GitHub 에서 New issue → "버그 / Bug report" 폼에 필수 칸(*)이 보이는지
  3. 병합 뒤 Actions 의 server-tests 에 3.11 이 생겼고 초록인지

## 2026-10-07 (2회차)

- 한 일: `latest.md`(10/1) FAIL 2건(README GIF 링크·버튼 이름)은 10/2 회차에 이미 고쳐 main 에 있음을 다시 확인 → 백로그로 진행. 시작 때 main(PR #10 병합분)을 받아 옴(빨리감기). 백로그 4개 완료, 남은 항목 3개라 새 항목은 추가하지 않음.
  1. **도구 설명 ↔ `server.CHOICES` 일치** — 고정 목록 인자 23개를 `이름: a / b / c` 줄로 통일(explode 의 material·pattern·dust·glue, destroy 의 dust, render_video 의 quality 등이 설명에 없었음). `make_demo_building` 의 style·ground 도 서버 검사에 넣음. 시험: 설명과 목록 일치, 새 도구 누락 방지.
  2. **숫자 인자 범위 미리 검사** — 레시피는 범위 밖 값을 조용히 잘라 썼음(resolution=2000 → 320). `server.RANGES`(pieces·resolution·frames·focus·samples) + `check_ranges`, 범위·권장 값을 한/영으로. `tests/test_server_ranges.py` 32개(레시피의 max/min 을 ast 로 비교). **동작 변화:** 예전에 조용히 잘리던 값(frames=6 등)이 이제 오류.
  3. **`docs/architecture.md`(한/영)** — 호출 경로·파일 역할·레시피 규칙·시험 경로. README·CONTRIBUTING 에서 링크, CONTRIBUTING 의 없는 파일 `splash.py` → `water.py`. 시험 4개.
  4. **`scripts/release_check.py`** — 버전 세 곳·CHANGELOG 맨 위 절(판·날짜·중복)·mcp-name, `--build` 면 휠 METADATA. 지금은 "판 다름"·"미출시" 2줄만 FAIL(정상). 출시 순서·registry.md 에 단계 추가. 시험 11개.
- 돌린 시험: `uvx ruff@0.15.20 check .` 통과. `uv run pytest -q`(Python 3.13) → **466 통과, 34 건너뜀**(블렌더 없음). CI 서버 시험 목록을 Python 3.10 + `--cov` → 461 통과, 5 건너뜀(tomllib), 커버리지 94%(server 93%). `uv lock --check` 통과, `release_check.py --build` 로 휠 빌드 확인. 못 돌린 것: 레시피 시험 34개(블렌더 필요 — 레시피 파일은 안 건드림, 레시피 시험은 서버를 거치지 않아 새 범위 검사의 영향 없음).
- PR: claude/cloud-work → main #13 을 새로 열었음(Mac 총괄이 확인 후 병합).
- Mac에서 확인할 것:
  1. `uv run pytest -q` (블렌더 앱으로 전체 통과)
  2. `BLENDER_FX_PORT=1 uv run python -c "from blender_fx_mcp import server; print(server.water(resolution=2000))"` (블렌더 없이 범위 오류)
  3. `uv run python scripts/release_check.py --build` (지금은 FAIL 2줄·종료 코드 1이 정상)

## 2026-10-07

- 한 일: `latest.md`(10/1)의 FAIL 2건은 10/2 회차에 이미 고쳐 main에 병합됨 → 백로그로 진행. 시작할 때 main(PR #9 병합분)을 받아 옴(빨리감기). 백로그 4개 완료 → 남은 항목이 2개라 새 항목 5개 추가.
  1. **`headless.py` 실패 갈래 시험** `tests/test_headless.py` 16개(`/bin/sh` 가짜 블렌더). 커버리지 56% → 99%.
  2. **액션 SHA 고정** — checkout v4.4.0(11d5960…), setup-uv v5.4.2(d4b2f3b…). 태그가 가리키는 커밋은 `git ls-remote` 로 확인. 시험 `test_workflow_actions_pinned_to_sha`.
  3. **고정 목록 인자 미리 검사** — `server.CHOICES` + `check_choices`(`run_recipe` 맨 앞). 가능한 값과 가장 가까운 값을 한/영으로 알려 줌. `tests/test_server_choices.py` 33개(레시피 상수와 ast로 비교). 동작 변화: `interior`·`quality` 오타가 이제 오류로 나옴.
  4. **`doctor.py` 실패 갈래 시험** `tests/test_doctor.py` 21개. 80% → 99%. `--version` 출력이 비면 "list index out of range"로 보이던 것을 고침.
  - CI 서버 시험 목록에 새 시험 파일 3개 추가. CHANGELOG·CONTRIBUTING 갱신(서버 쪽 커버리지 84% → **94%**, 시험 421개).
- 돌린 시험: `uvx ruff@0.15.20 check .` 통과. `uv run pytest -q`(Python 3.13) → **387 통과, 34 건너뜀**(블렌더 없음). CI 서버 시험 목록을 Python 3.10 으로 → 383 통과, 4 건너뜀(tomllib). `--cov` 결과 94%(bridge 96%: 58–60줄은 이번 변경 전에도 안 덮였음. 10/6 기록의 "100%"는 잘못 적은 것으로 보임). `uv lock --check`·`uv build` 통과. 못 돌린 것: 레시피 시험 34개(블렌더 필요 — 레시피 파일은 안 건드림). dependabot 이 SHA 고정 액션을 실제로 올리는지는 다음 주 갱신 PR 이 나와야 확인 가능.
- PR: claude/cloud-work → main #10 을 새로 열었음(Mac 총괄이 확인 후 병합). dependabot PR(checkout v7·setup-uv v7)은 이번 SHA 고정과 겹치므로, #10 병합 뒤 dependabot 이 다시 만들게 두는 것이 낫다.
- Mac에서 확인할 것:
  1. `uv run pytest -q` (블렌더 앱으로 전체 통과, 특히 test_headless·test_doctor 가 macOS /bin/sh 에서)
  2. `BLENDER_FX_PORT=1 uv run python -c "from blender_fx_mcp import server; print(server.destroy('B', material='concret'))"` (블렌더 없이 "혹시 'concrete'")
  3. 병합 뒤 GitHub Actions 에서 SHA 고정 액션으로 ci 가 초록인지

## 2026-10-06 (2회차)

- 한 일: `latest.md`(10/1) FAIL 2건은 10/2 회차에 이미 고쳐 main 에 병합됨 → 백로그로 진행. 시작 때 main(PR #8 병합분)을 받아 옴(빨리감기). 백로그 4개 완료 → 남은 항목 1개라 새 항목 5개 추가.
  1. **워크플로 최소 권한** — `ci.yml`·`app-tests.yml` 최상위 `permissions: contents: read`. 시험: 모든 워크플로에 있는지, write 없는지.
  2. **MCP 도구 annotations** — 32개 모두(READ_ONLY 5·SETTING 7·ADDITIVE 15·DESTRUCTIVE 5, `openWorldHint=false`). 백로그에 적힌 `reset_scene` 등은 없는 이름이라 `restore`·`clear_caches`·`reset_destroy`·`export_model`·`snapshot` 을 destructive 로. 시험 5종. 이 변경으로 README 도구 표 시험의 정규식이 도구를 못 찾게 돼 함께 고침.
  3. **도구 성공 갈래 시험** `tests/test_server_tools.py` — 가짜 레시피 결과로 도구 29개를 한/영 끝까지 호출. 커버리지 **server 49% → 88%, 전체 59% → 84%**(CONTRIBUTING 갱신, CI 목록에 추가).
  4. **`docs/troubleshooting.md`(한/영)** — 오류 문장 8묶음별 해결법. 연결·시간 초과 오류와 doctor 의 확인 필요 줄에 링크(절 제목 영어 → ASCII 앵커). `tests/test_troubleshooting.py`(문장 25개가 소스·문서 양쪽에 있는지, 링크 절 존재). CI 목록에 추가.
  - CHANGELOG 미출시 절 반영, 시험 수 348개(블렌더 없이 314개).
- 돌린 시험: `uvx ruff@0.15.20 check .` 통과. `uv run pytest -q`(Python 3.13) → **314 통과, 34 건너뜀**(블렌더 없음). CI 서버 시험 목록을 Python 3.10 + `--cov` 로 → 310 통과, 4 건너뜀, 커버리지 84%. `uv lock --check`·`uv build` 통과. 못 돌린 것: 레시피 시험 34개(블렌더 필요 — 이번 회차는 레시피를 건드리지 않아 bpy 로도 안 돌림). 오류 문장 끝 링크는 GitHub 에서 앵커가 실제로 열리는지 브라우저로 확인 못 함(병합 전이라 main 에 문서가 없음).
- PR: claude/cloud-work → main #9 를 새로 열었음(Mac 총괄이 확인 후 병합).
- Mac에서 확인할 것:
  1. `uv run pytest -q` (블렌더 앱으로 전체 통과)
  2. `BLENDER_FX_PORT=1 uv run blender-fx-doctor | tail -1` (끝에 troubleshooting.md 링크)
  3. 병합 뒤 그 링크에 `#connection-refused` 를 붙여 열었을 때 해당 절로 가는지

## 2026-10-06

- 한 일: `latest.md`(10/1) FAIL 2건은 10/2 회차에 이미 고쳐 main 에 병합됨 → 백로그로 진행. PR #5 가 병합돼 `claude/cloud-work` 를 main(6385bb4)에서 다시 시작. 남은 백로그 4개 완료 → 남은 항목이 0개라 새 항목 5개 추가.
  1. **PR 양식** `.github/pull_request_template.md`(한/영, 확인 칸 8개). 시험: 명령이 CONTRIBUTING 과 같은지, 새 레시피 칸이 빠지지 않았는지.
  2. **`examples/`** — 클로드 데스크톱·커서(`.cursor/mcp.json`)·코덱스(`config.toml`, 굽기용 `tool_timeout_sec = 3600`) 설정과 한/영 안내. README 한/영 설치 절에서 링크. `tests/test_examples.py` 5개(CI 에 추가, tomllib 시험은 3.10 에서 건너뜀).
  3. **README 배지** CI·MIT·Python 3.10–3.13. 시험: 워크플로 파일·라이선스·분류자 양 끝과 일치.
  4. **CI 커버리지 요약** — `pytest-cov>=7`, 레시피 제외(블렌더 안 문자열 실행이라 못 잼). 서버 쪽 **59%**(bridge·i18n 100%, doctor 80%, headless 56%, server 49%) — CONTRIBUTING 에 기록, CI 작업 요약에 표.
  - CHANGELOG 미출시 절에 반영.
- 돌린 시험: `uvx ruff@0.15.20 check .` 통과. `uv run pytest -q`(Python 3.13) → **198 통과, 34 건너뜀**(블렌더 없음). CI 서버 시험 목록을 `--cov` 와 함께 Python 3.10·3.13 으로 → 193+4건너뜀 / 197 통과, 작업 요약 markdown 생성 확인. `uv lock --check` 통과. 못 돌린 것: 레시피 시험 34개(블렌더 필요 — 이번 회차는 레시피를 건드리지 않아 bpy 로도 안 돌림).
- PR: claude/cloud-work → main #8 을 새로 열었음(Mac 총괄이 확인 후 병합).
- Mac에서 확인할 것:
  1. `uv sync --group dev && uv run pytest -q` (pytest-cov 추가 뒤에도 전체 통과)
  2. GitHub PR 화면에서 PR 양식이 뜨는지, Actions → ci → server-tests 요약에 커버리지 표가 있는지
  3. README 첫 화면 배지 3개가 깨지지 않는지

## 2026-10-05 (2회차)

- 한 일: `latest.md`(10/1) FAIL 2건은 10/2 회차에 이미 고쳐 main 에 병합됨 → 백로그로 진행. 시작 때 main(PR #4 병합분)을 받아 옴(빨리감기). 남은 백로그 3개 완료 → 새 항목 5개 추가 → 그중 1개 더 완료(모두 4개).
  1. **CI 파이썬 행렬에 3.13** (3.10·3.12·3.13). 시험: 분류자의 가장 낮은·높은 판이 CI 행렬에 있는지.
  2. **`.github/dependabot.yml`** — uv·GitHub Actions 주 1회. schemastore 의 dependabot-2.0 스키마로 검증 통과. 시험 1개.
  3. **ruff** — `[tool.ruff]`(recipes 의 `F821`, `_common.py` 의 `F401` 만 끔: 서버가 이어 붙이는 구조라서), CI `lint` 작업(`uvx ruff@0.15.20 check .`). 지적 2곳 정리(안 쓰는 변수·import). CONTRIBUTING 에 한 줄.
  4. **시간 초과 오류 안내** — 기다린 초와 `BLENDER_FX_TIMEOUT`(초)로 늘리고 재시작하라는 문장(한/영). 답 안 하는 가짜 수신기로 시험 2개.
  - CHANGELOG 미출시 절에 위 내용 반영.
  - PR #5 Codex 리뷰 지적 1건 고침: 연결 단계(10초 고정)의 시간 초과까지 `BLENDER_FX_TIMEOUT` 안내가 나가던 것 → 연결 실패 안내로. 회귀 시험 1개(블렌더 없이 190 통과).
- 돌린 시험: `uvx ruff check .` 통과. `uv run pytest -q`(Python 3.13) → 189 통과, 34 건너뜀(블렌더 없음). bpy 5.0.1(Python 3.11, 소프트웨어 EGL)로 → **217 통과, 6 건너뜀**(유체 5개는 bpy 모듈의 Mantaflow 결함이라 블렌더 앱 필요, 실제 캐릭터 1개는 파일 없음).
- Mac에서 확인할 것:
  1. `uv run pytest -q` (블렌더 앱에서 전체 통과)
  2. `uvx ruff check .`
  3. GitHub → Settings → Code security 에서 Dependabot version updates 가 켜졌는지(설정 파일만으로 동작)

## 2026-10-05

- 한 일: `latest.md`(10/1) FAIL 2건은 10/2 회차에 이미 고쳐 main 에 병합됨 → 백로그로 진행. main(PR #3 병합분)을 먼저 받아 옴(빨리감기). 백로그 4개 완료, 남은 항목 3개라 새 항목은 안 넣음.
  1. **접착(glue) 세그폴트 원인 찾아 고침.** gdb 로 보니 시뮬레이션이 아니라 첫 `bpy.ops.rigidbody.constraint_add` 에서 Object 가 NULL. 이 연산자는 `temp_override(active_object=…)` 가 아니라 뷰 레이어의 **실제 활성 객체**를 씀 → bpy 에선 활성 객체가 없어 세그폴트, 앱에선 활성 조각에 빈 제약이 하나 더 붙음(bpy 로 재현: 147+1개). 접착 빈 객체를 `view_layer.objects.active` 로 진짜 활성화했다가 되돌림. 접착 시험의 `app_only` 해제 → 이제 bpy CI 에서도 돎.
  2. **README 영어 절** — 준비물·doctor·설치(`-e BLENDER_FX_LANG=en`)·환경변수 표·첫 명령·도구 32개 표·보안/기여/라이선스. 시험: 한/영 도구 표가 `server.py` 도구를 다 담는지, 영어 절에 한글이 없는지.
  3. **서버 메시지 정적 시험** `tests/test_server_messages.py` — server·bridge·doctor 의 `t()` 70곳 한/영 순서, t() 밖 한국어 누출, 도구 설명 첫 줄 영어(이미 모두 영어였음). 서버 안내문(instructions)이 한국어뿐이라 한/영 두 판으로 나눔. CI 에 추가.
  4. **`pyproject.toml` `[project.urls]`·Python 3.10~3.13 분류자** + 시험 2개. `uv build` 로 METADATA 확인.
- 돌린 시험: `uv run pytest -q` → 182 통과, 34 건너뜀(블렌더 없음). bpy 5.0.1(Python 3.11, 소프트웨어 EGL)로 → **210 통과, 6 건너뜀**(유체 5개는 bpy 모듈의 Mantaflow 결함이라 블렌더 앱 필요, 실제 캐릭터 1개는 파일 없음). `uv build` 성공.
- PR: claude/cloud-work → main #4 를 새로 열었음(아래 확인 후 Mac 총괄이 병합). CI 3개 초록. Codex 리뷰 지적 1건(`BLENDER_FX_TIMEOUT` 이 굽기·렌더 도구에 안 먹음) 고침 — 더 큰 값이면 그 도구들도 따라 늘어남, 시험 3개 추가(블렌더 없이 185 통과).
- Mac에서 확인할 것:
  1. `uv run pytest -q tests/test_recipes_v05.py -k glue` (블렌더 앱에서도 접착이 붙고 덜 무너지는지)
  2. `uv run pytest -q` (전체 통과)
  3. `BLENDER_FX_LANG=en uv run python -c "from blender_fx_mcp import server; print(server.INSTRUCTIONS[:40])"` (영어 안내문)

## 2026-10-04 (2회차)

- 한 일: `latest.md`(10/1) FAIL 2건은 10/2 회차에 이미 고쳐 main 에 병합됨 → 백로그로 진행. main(PR #2 병합분)을 먼저 받아 옴. 백로그 4개 완료, 남은 항목이 2개라 새 항목 5개 추가.
  1. **레시피 오류 한/영 쌍 정적 시험** `tests/test_recipe_messages.py` — 모든 `raise FxError` 가 `L(한국어, 영어)` 인지, `L()` 60곳이 (한글, 한글 없는 영어) 순서인지 AST 로 검사. 한국어만 나가던 힘장 오류 2곳(`explode.py`, `_common.py`) 고침.
  2. **이슈 양식** — `feature_request.md`, `config.yml`(보안 비공개 신고·recipes 링크), 버그 양식에 수신기 버전·`BLENDER_FX_LANG` 칸. `blender-fx-doctor` 첫 줄에 blender-fx-mcp 판 번호 표시. `tests/test_repo_files.py`.
  3. **`SECURITY.md`·`CODE_OF_CONDUCT.md`** — 9876 포트 무인증 수신기 위험, `BLENDER_FX_HOST` 를 localhost 로 둘 것, GitHub 비공개 신고 양식. 행동 강령은 Contributor Covenant 2.1 요약+링크. README 에 보안 절.
  4. **bpy 4.5 LTS 로 유체 — 안 됨.** 4.5.14·4.2.23 휠도 `LevelsetGrid.setConst` 없음, 접착 세그폴트도 같음. 대신 공식 블렌더 Linux 빌드를 받아 `app_only` 를 돌리는 **손 실행** 워크플로 `.github/workflows/app-tests.yml`(PR 에서는 안 돎). 클라우드에서는 download.blender.org 가 프록시에 막혀(403) **미검증**. 덤: bpy 4.5.14 로 나머지 레시피 시험 133개 통과.
- 돌린 시험: `uv run pytest -q` → 106 통과, 34 건너뜀(블렌더 없음). bpy 4.5.14 로 → 133 통과, 7 건너뜀(앱 전용 6 + 실제 캐릭터 파일 없음 1). `-m app_only` 를 bpy 4.5·4.2 로 강제 실행 → 유체·접착 실패(위 결함, 블렌더 앱 필요). 워크플로 두 개는 GitHub 워크플로 스키마 검증 통과.
- Mac에서 확인할 것:
  1. `uv run pytest -q && uv run blender-fx-doctor | head -1` (첫 줄 `blender-fx-mcp: 0.6.3`)
  2. GitHub Actions → app-tests → Run workflow (기본값 5.2.0) 가 초록인지
  3. 저장소 Settings → Security 에서 Private vulnerability reporting 켜기(SECURITY.md 링크가 이것을 씀)

## 2026-10-04

- 한 일: `latest.md`(10/1) FAIL 2건은 10/2 회차에 이미 고쳐 main 에 병합됨(PR #1) → 백로그로 진행. 백로그 4개 모두 완료 후 새 항목 6개 추가.
  1. **`pip install bpy` 헤드리스 시험 가능 — 됨.** bpy 5.0.1(Python 3.11) + libEGL(소프트웨어 Mesa)로 레시피 시험 64개 통과. `headless.py` 가 bpy 를 설치한 파이썬도 실행기로 받음. bpy 모듈에서 깨지는 6개(Mantaflow 유체 5개 `LevelsetGrid.setConst` 없음, 리지드바디 접착 1개 세그폴트)는 `@pytest.mark.app_only` 로 표시해 bpy 일 때만 건너뜀. CI 에 `recipe-tests-bpy` 작업 추가. `run_steps` 실패 메시지에 멈춘 단계·종료 이유 표시.
  2. **`server.json.example` 레지스트리 점검.** 2025-12-11 스키마로 검증 — 옛 snake_case 키는 `registryType` 누락으로 거부됨 → camelCase 로, 버전 0.6.0 → 0.6.3, README 에 `mcp-name` 줄. `docs/registry.md`(절차), `tests/test_registry.py` 6개.
  3. **`docs/recipes.md`**: 자연어 명령 5개. 1~3번은 bpy 실측값, 4·5번(유체)은 확인할 칸.
  4. **CHANGELOG 0.7.0(미출시) 절과 출시 순서.** 버전 번호는 출시 때 올림.
  - 덤: bpy 로 돌리다 찾은 버그 수정 — `import_model(size=…)` 의 `volume_m3` 가 크기 바꾸기 전 값(144㎥, 실제 18㎥). 회귀 시험 추가. 저장소의 개인 경로 2곳 제거(실제 캐릭터 시험은 이제 `BLENDER_FX_REAL_CHARACTER` 환경변수 필요).
- 돌린 시험: `uv run pytest -q` → 37 통과, 34 건너뜀(블렌더 없음). bpy 로 `BLENDER_FX_BLENDER=<bpy 파이썬> uv run pytest -q` → **64 통과, 7 건너뜀**(앱 전용 6 + 실제 캐릭터 파일 없음 1). `uv build` 성공. 못 돌린 것: 유체 5개·접착 1개(bpy 모듈 결함, 블렌더 앱 필요), 실제 캐릭터 1개(파일 없음).
- Mac에서 확인할 것:
  1. `BLENDER_FX_REAL_CHARACTER=<캐릭터 glb 경로> uv run pytest -q` (71개 모두 통과하는지)
  2. `uv run pytest -q -m app_only` (앱에서 유체·접착 6개 통과하는지)
  3. GitHub Actions 의 `recipe-tests-bpy` 작업이 초록인지

## 2026-10-03

- 한 일: `latest.md`(10/1)의 FAIL 2건은 지난 회차(6587f84)에서 이미 고쳤고 그 뒤 새 Mac 결과가 없어 백로그로 진행. 백로그 3번 "블렌더 없이 도는 단위 시험 + CI" 완료 — `tests/test_server_params.py` 19개 추가(run_recipe 의 None 제거·언어 주입·오류+traceback 메시지, destroy/explode/set_render/inspect_mesh 의 기본값→파라미터 변환, snapshot 이름 정리, restore 실패 흐름, 가짜 소켓 수신기로 bridge 의 분할 응답·error 상태·빈 응답 처리). CI(`ci.yml`)에 이 파일을 추가.
- 돌린 시험: `uv run pytest -q` → 28 통과, 33 건너뜀(건너뛴 것은 블렌더 실행 파일이 필요한 레시피 시험이라 클라우드에서 못 돌림).
- Mac에서 확인할 것:
  1. `uv run pytest -q` (61개 모두 통과하는지)
  2. `uv run pytest -q tests/test_server_params.py` (블렌더를 켠 상태에서도 9876 포트와 안 부딪히는지)

## 2026-10-02

- 한 일: 10/1 Mac 시험 FAIL 2건 수정(이번 회차는 이것만). ① README 5번째 줄 데모 GIF 이미지를 HTML 주석으로 감쌈(GIF가 생기면 주석 해제). ② 버튼 이름을 "Connect to MCP server"로 통일 — `bridge.py` 연결 실패 안내(한/영)와 `docs/demo-script.md` 수정.
- 돌린 시험: `uv run pytest -q` → 9 통과, 33 건너뜀(건너뛴 것은 블렌더 실행 파일이 필요한 레시피 시험). README 상대 링크 점검(주석 제외) → 깨진 링크 0개.
- Mac에서 확인할 것:
  1. `uv run pytest -q`
  2. README 상대 링크 점검 → 깨짐 0개인지
  3. 블렌더를 끈 채 `uv run blender-fx-doctor` → 안내 문구에 "Connect to MCP server" 가 나오는지

## 2026-09-26

- 한 일: `claude/cloud-work` 브랜치 새로 만듦(main 기준). `docs/test-reports/latest.md` 가 아직 없어 FAIL 확인 불가 → 백로그로 진행. `docs/CLOUD-BACKLOG.md` 생성. README 첫 화면(한 줄 소개·연결 3줄·첫 명령·GIF 자리) 추가, `docs/demo-script.md`(GIF 촬영 대본) 작성.
- 돌린 시험: `uv run pytest -q` → 9 통과, 33 건너뜀. 건너뛴 33개는 블렌더(bpy) 실행 파일이 필요한 레시피 시험이라 클라우드에서 못 돌림.
- Mac에서 확인할 것:
  1. `uv run pytest -q` (블렌더 있는 환경에서 전체 통과 확인, 결과를 `docs/test-reports/latest.md` 에 기록)
  2. `docs/demo-script.md` 대로 촬영 → `docs/media/demo.gif` 추가
  3. README 첫 화면의 연결 명령 3줄이 그대로 동작하는지 확인
