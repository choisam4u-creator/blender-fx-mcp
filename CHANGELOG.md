# 변경 이력

## 0.7.0 — 미출시 (준비 중)

출시 전까지 `pyproject.toml`·`src/blender_fx_mcp/__init__.py`·`server.json.example` 의 버전은 0.6.3 으로 둔다.
아래 "출시 순서"에서 한꺼번에 올린다(`tests/test_registry.py` 가 셋이 어긋나면 실패한다).

**고침**
- `import_model` 에 `size` 를 주면 결과의 `volume_m3` 가 크기를 바꾸기 **전** 부피로 나오던 문제.
  4.5m 로 줄인 건물이 144㎥(실제 18㎥)로 보고됐다
- 힘장을 못 만들었을 때의 오류 2곳이 `BLENDER_FX_LANG=en` 에서도 한국어로만 나오던 문제
- 조각 접착(`glue`)이 활성 객체를 잘못 다루던 문제. `constraint_add` 는 임시 문맥이 아니라 뷰 레이어의 **실제 활성 객체**에
  제약을 붙여서, 활성 객체가 없으면 bpy 모듈에서 세그폴트, 있으면 그 객체(조각 하나)에 빈 제약이 하나 더 붙었다.
  접착용 빈 객체를 진짜로 활성화했다가 원래대로 되돌린다
- MCP 서버 안내문(instructions)이 한국어뿐이던 문제. `BLENDER_FX_LANG=en` 이면 영어 안내문을 보낸다
- `BLENDER_FX_TIMEOUT` 이 굽기·렌더 도구(1800초 고정, `render_video` 3600초)에는 먹지 않던 문제. 이제 더 큰 값을 주면 그 도구들도 따라 늘어난다
- 시간 초과 오류가 몇 초 기다렸는지와 `BLENDER_FX_TIMEOUT` 으로 늘리는 방법을 알려 준다
- `blender-fx-doctor` 첫 줄에 blender-fx-mcp 판 번호를 표시(이슈 재현용)
- 32개 도구 모두에 MCP annotations(`readOnlyHint`·`destructiveHint`·`idempotentHint`·`openWorldHint=false`).
  `restore`·`clear_caches`·`reset_destroy`·`export_model`·`snapshot`(같은 이름 덮어쓰기)은 destructive 로 표시해
  클라이언트가 실행 전에 확인을 띄울 수 있다
- 고정 목록 인자(`impact`·`material`·`pattern`·`glue`·`dust`·`collision`·`interior`·`mode`·`shape`·`liquid`·`kind`·`preset`·`sky`·`quality`)를
  블렌더로 보내기 **전에** 검사한다. 틀리면 가능한 값과 가장 가까운 값을 알려 준다(예: `concret` → "혹시 'concrete' 인가요?").
  지금까지는 블렌더가 꺼져 있으면 오타도 "연결할 수 없습니다"로만 보였고, `interior`·`quality` 오타는 조용히 다른 값으로 돌았다
- 숫자 인자 범위(`pieces` 2~1500, `resolution` 16~320/256, `frames` 12 이상, `focus` 0~1, `samples` 1 이상)를 블렌더로 보내기 **전에**
  검사하고 권장 값을 알려 준다. 지금까지 레시피는 범위 밖 값을 조용히 잘라 써서, `resolution=2000` 을 줘도 320 으로 돌고
  사용자는 왜 결과가 다른지 몰랐다
- `make_demo_building` 의 `style`·`ground` 도 블렌더로 보내기 전에 검사한다
- 도구 설명(docstring)의 값 목록을 실제 허용 값과 맞췄다. `explode` 의 `material`·`pattern`·`dust`·`glue`,
  `destroy` 의 `dust`, `render_video` 의 `quality` 는 설명에 값이 없었고, `interior` 는 "다른 material 이름"으로만 적혀 있었다.
  이제 모든 고정 목록 인자를 `이름: a / b / c` 한 줄로 적고, 시험이 서버 목록과 같은지 확인한다
- `blender-fx-doctor` 가 `--version` 에 아무것도 출력하지 않는 블렌더를 "실행 실패: list index out of range" 대신 "버전 출력 없음"으로 보여 준다

**문서**
- `docs/architecture.md`(한/영): 도구 호출 한 번이 서버 → 소켓 → 수신기 → 레시피 → `FX_RESULT` 로 지나가는 길, 파일별 역할, 시험 경로.
  README·CONTRIBUTING 에서 링크. CONTRIBUTING 구조 그림의 없는 파일(`splash.py`)을 `water.py` 로 고침

**시험·CI**
- 블렌더 없이 도는 서버 단위 시험 추가(파라미터 변환·오류 메시지·가짜 소켓 수신기·레지스트리 형식). 9 → 37개
- `pip install bpy`(5.0.1, Python 3.11)로 **레시피 시험 대부분을 블렌더 앱 없이** 돌린다.
  `BLENDER_FX_BLENDER` 에 bpy 를 설치한 파이썬 경로를 주면 된다. CI 에 이 작업을 추가(Linux, 소프트웨어 EGL 렌더)
- bpy 모듈에서 깨지는 기능(Mantaflow 유체)을 쓰는 시험은 `@pytest.mark.app_only` 로 표시해
  bpy 로 돌릴 때만 건너뛴다. 블렌더 앱에서는 전부 돈다
- `run_steps` 실패 메시지에 **몇 번째 단계에서 멈췄는지**와 종료 이유(세그폴트·중단 등)를 넣었다
- 레시피 오류 메시지가 모두 `L(한국어, 영어)` 쌍인지 정적으로 검사하는 시험
- 서버·연결·점검 메시지가 모두 `t(한국어, 영어)` 쌍인지, 도구 설명 첫 줄이 영어인지 정적으로 검사하는 시험
- 공식 블렌더 Linux 빌드로 `app_only` 시험을 돌리는 손 실행 작업 `app-tests`(bpy 4.2·4.5·5.0 휠은 모두 유체가 깨져 있음)
- CI 파이썬 행렬에 3.13 추가(3.10·3.12·3.13). 분류자의 양 끝 판이 행렬에 빠지면 시험이 실패한다
- ruff lint 작업(판 고정 0.15.20, 설정은 `pyproject.toml`)
- dependabot: uv 의존성·GitHub Actions 판을 주 1회 갱신 PR 로
- CI 서버 시험이 커버리지(레시피 제외)를 작업 요약에 남긴다. 59% → 84%
- 도구 29개를 가짜 레시피 결과로 끝까지 불러 한/영 결과 문장·미리보기 이미지를 확인하는 시험(`tests/test_server_tools.py`). server.py 커버리지 49% → 88%
- 워크플로 기본 토큰을 읽기 전용(`permissions: contents: read`)으로. 빠지면 시험이 실패한다
- `headless.py`·`doctor.py` 실패 갈래 시험(가짜 실행 파일로 즉시 종료·세그폴트·시간 초과·애드온 없음·출력 폴더 쓰기 실패·종료 코드). 서버 쪽 커버리지 84% → 94%
- 워크플로의 외부 액션을 커밋 SHA + 판 주석으로 고정(OpenSSF Scorecard Pinned-Dependencies). 태그로 되돌아가면 시험이 실패한다
- 시험 42 → 421개(블렌더 없이 387개)

**문서**
- PyPI 페이지용 `[project.urls]`(이슈·변경 기록·보안 정책)와 Python 3.10~3.13 분류자
- README 첫 화면: 한 줄 소개, Claude 연결 3줄, 첫 명령 예시, 데모 GIF 자리
- `docs/recipes.md`: 자연어 명령 5개와 실제 결과 수치
- README 에 영어 절(설치·환경변수·첫 명령·도구 전체 표). 한/영 도구 표가 실제 도구와 어긋나면 시험이 실패한다
- `docs/demo-script.md`: 데모 GIF 촬영 대본
- `docs/registry.md`: 공식 MCP 레지스트리 등록 절차
- 버튼 이름을 "Connect to MCP server" 로 통일
- `SECURITY.md`(9876 포트 무인증 수신기 위험·비공개 신고)·`CODE_OF_CONDUCT.md`·기능 요청 이슈 양식
- `examples/`: 클로드 데스크톱·커서·코덱스 연결 설정(코덱스는 굽기용 `tool_timeout_sec`)
- README 맨 위 배지(CI·라이선스·Python 판). 실제 파일과 어긋나면 시험이 실패한다
- PR 양식(한/영): ruff·pytest·한/영 문장·새 레시피 확인 칸
- `docs/troubleshooting.md`(한/영): 연결 거부·시간 초과·빈 응답·포트 충돌·유체 굽기 실패·검은 미리보기·부수기/가져오기·영상 실패의
  오류 문장별 해결법. 연결·시간 초과 오류와 doctor 의 "확인 필요" 줄 끝에 이 문서 링크를 붙였다.
  문서의 오류 문장이 소스와 어긋나거나 링크한 절이 없으면 시험이 실패한다

**배포 준비**
- `server.json.example` 을 MCP 레지스트리 2025-12-11 스키마(camelCase 키)에 맞춤
- README 에 PyPI 소유 확인용 `mcp-name` 줄 추가

**출시 순서 (샘님 Mac)**
1. Mac 에서 `uv run pytest -q` 전부 통과(블렌더 앱으로 71개)
2. 데모 GIF 를 찍어 `docs/media/demo.gif` 로 넣고 README 주석을 푼다(선택)
3. 버전 세 곳을 0.7.0 으로, 이 절의 제목을 날짜로 바꾼다
4. 태그·PyPI·레지스트리 등록은 `docs/registry.md` 순서대로

## 0.6.3 — 2026-09-21

**진짜 파일로 끝까지 확인**
- 충격체가 **바운딩 박스가 아니라 실제 표면**을 조준한다(`surface_aim`). 팔을 벌린 T 포즈처럼
  가로로 넓고 얄팍한 모델에서 허공을 치는 바람에 조각이 **하나도 움직이지 않았다**
  (움직인 비율 0.0 → **1.0**, 최대 낙하 0.0m → **1.39m**). 데모 건물도 0.09m → 0.29m 로 개선
- `.blend` 가져오기에서 **면이 없는 부품을 자동으로 뺀다**. 리깅 조작용 위젯(`WGT-…`)이
  한 파일에 132개 들어 있어 그대로 합쳐지고 있었다
- 부품 이름 목록이 길면 8개까지만 보여 준다(133개를 다 찍던 문제)
- `import_model` 결과에 `empty_parts` 추가
- 결함 회귀 테스트 6종 추가: 겹친 면, n각형, 거울상(음수 크기), 납작(비균등 크기),
  가로로 넓고 얄팍한 모양의 충격 판정, 실제 `.blend` 캐릭터. 테스트 37 → 42개
- **실제 소켓 경로(블렌더 앱 ↔ MCP)를 v0.5 이후 처음으로 다시 확인**. 12단계 전부 성공
- 배포 파일을 0.6.2 로 새로 만듦

## 0.6.2 — 2026-09-20

**실제 게임 에셋(뼈대 있는 캐릭터) 대응**
- 파일 안 **부품 목록**을 결과에 싣고, `parts` 로 원하는 부품만 골라 가져올 수 있게 함.
  보이지 않는 충돌용 껍데기(면 80개짜리 구)가 섞여 있으면 **경고**한다.
  이 구를 그냥 합치면 캐릭터가 통째로 구가 되어 버렸다(부피 0.14㎥ → 3.66㎥)
- 스킨된 메시는 모디파이어를 **먼저 구운 뒤** 부모를 뗀다. 부모를 떼고 위치를 되돌리는
  순서도 교정. 예전 순서로는 부품이 제자리를 벗어나고 크기가 100배 어긋났다
- 수리 단계 보강: 찌그러진 면 정리, **겹친 면 걷어내기**, **비다양체 모서리의 여분 면 걷어내기**,
  구멍 메우기 2차 시도. 캐릭터가 비다양체 10개·구멍 256개에서 **완전히 닫힘**으로 바뀜
- 정리(`resolve_solid`)가 결과를 더 망가뜨리면 **버리고 원본을 쓴다**(캐릭터에서 비다양체가
  10개 → 8,390개로 늘어난 적이 있다). 대신 조각 불리언에서 자기교차 처리를 켠다.
  이 경로로 캐릭터 보존율 **0.405 → 1.00**
- 완전히 닫히진 않아도 구멍이 면 수의 1% 이하이면 씨앗 안쪽 판정을 쓴다.
  요청 60조각에 50개만 나오던 것이 60개로 회복
- `inspect_mesh` 의 볼록한 정도를 **수리된 닫힌 메시에서만** 계산. 팔다리가 벌어진 캐릭터가
  1.0(완전한 볼록 덩어리)으로 나오던 오류 수정(이제 **0.307**)
- 속이 빈 껍데기 모델은 무게를 통짜로 계산한다는 점과 낮출 `density` 값을 알려 준다
- 부피 비교에서 반올림 제거. 5cm 물건이 보존율 1.25 로 뜨던 문제 수정
- 실제 CC0 게임 캐릭터 회귀 테스트 추가(파일이 없으면 건너뜀). 테스트 36 → 37개

## 0.6.1 — 2026-09-20

**내려받은 무료 에셋도 제대로 부서지게**
- 가져오기(glb/gltf 등)에서 **쪼개진 꼭짓점을 다시 붙인다**. glTF 는 저장할 때 꼭짓점을 쪼개므로
  그대로 두면 모든 면이 따로 놀아 닫히지 않은 메시가 되고 조각내기가 망가졌다(실측 `volume_kept` 15.24)
- 수리를 먼저 하고 면 줄이기를 나중에 하도록 순서 교정. 반대로 하면 결과가 깨졌다
- 보로노이 셀을 **볼록 껍질로 다시 만들어** 항상 닫히게 함. 자르는 도중 생긴 틈 때문에 불리언이 실패하던 문제 해결
- **겹치거나 맞닿은 덩어리를 먼저 하나의 solid 로 정리**(`resolve_solid`). 바퀴가 몸통에 박힌 모델,
  내용물이 바닥에 붙은 모델에서 조각이 통째로 사라지던 문제 해결(실측 0.69·0.93 → 1.00)
- `source_volume_m3` 를 불리언 솔버 기준으로 측정. 겹친 덩어리를 두 번 세어 부풀던 값 교정
- 씨앗 안쪽 판정이 좌표를 두 번 변환하던 버그 수정. 물체가 원점에서 떨어져 있으면
  씨앗이 거의 놓이지 않아 요청한 40개 중 3~4개만 나왔다
- 씨앗을 표면에서 살짝 띄우고 씨앗끼리 최소 간격을 두어 종잇장 같은 조각이 버려지지 않게 함
- 셀 자르기 횟수 상한 제거. 조각이 많을 때 셀이 덜 잘려 겹치고 부피가 부풀었다(실측 1.172 → 1.00)
- `destroy` 결과에 `cells_built`, `empty_cells`, `solid_resolved` 추가
- `destroy` 의 `neighbors` 인자 삭제(정확한 조기 종료가 대신하므로 아무 일도 하지 않았다)
- 결함 있는 에셋(겹침·맞닿음·분리)과 조각 200개 회귀 테스트 추가. 테스트 32 → 35개

## 0.6.0 — 2026-09-20

**아무 메시나 물리에 맞게 부수기**
- 조각내기를 무작위 평면에서 **보로노이 셀 + 정확 불리언**으로 교체. 조각 부피의 합이 원본과 일치(`volume_kept` 1.00)
- 메시 자동 진단·수리: 겹친 점 합치기, 법선 정리, 구멍 메우기, `shell_thickness` 로 껍데기에 두께 주기
- `inspect_mesh` 도구: 닫혔는지, 부피, 오목한 정도, 면 수, 수리 예상 결과와 주의사항
- 조각 분포 `pattern`(impact/uniform/radial/slabs)과 `focus`, 충돌 모양 `collision`, 단면 재질 `interior`
- 재질 8종(콘크리트·벽돌·유리·나무·돌·금속·얼음·석고)과 `density`/`friction`/`bounce` 덮어쓰기
- 면이 많은 모델은 `decimate_to` 로 자동 축소 후 조각내기

**물을 마음대로**
- `water` 도구: `mode`(drop/stream/pool/object), `direction_deg`·`pitch_deg`·`speed` 로 방향과 세기,
  `shape`(sphere/box/column), `liquid` 6종(water/oil/honey/lava/mercury/slime), `viscosity`·`surface_tension`·`gravity_scale`
- 물이 날아갈 거리까지 계산해 도메인을 잡고, 바닥판은 크기 계산에서 제외
- 물 덩어리가 계산 격자보다 작으면 필요한 `resolution` 숫자를 알려 주는 오류
- `splash` 는 `water(mode="drop")` 의 간단 버전으로 유지

**설정 개방**
- `set_physics`: 중력 세기·기울기, 하위단계, 해석 반복, 물리 속도, fps
- `set_render`: 샘플, 모션블러, 해상도, 노출, 필름 룩, 배경 빼기
- `fire`/`smoke` 에 density·dissolve·vorticity·noise, `particles` 에 size·gravity·drag·lifetime·speed

**약점 해결**
- 창문을 벽에 실제로 파냄(하나의 닫힌 껍데기 유지)
- `set_timing(global_slow=)` 로 파티클까지 포함한 전체 슬로모션
- `.abc`(Alembic) 내보내기로 물 표면·조각 움직임을 다른 프로그램으로
- `restore` 가 직전 상태를 `before_restore` 로 자동 저장
- 불 해상도 자동 결정, 빠른 미리보기에서 안 보이는 것 안내, 도구 설명 영어 한 줄 추가
- 충격체가 대상 안까지 파고들어 폭발하던 문제 수정(표면에서 멈추고 물리로 전환)
- 낙하 높이를 마지막 프레임에서 재도록 수정

테스트 32개 (헤드리스 23개).

## 0.5.0 — 2026-09-20

- 스냅샷: `snapshot` / `list_snapshots` / `restore` — 저장해 두고 언제든 그때로 되돌린다
- 조각 접착: `destroy(glue=...)` 로 리지드바디 제약을 만들어 맞은 곳만 무너지는 구조 붕괴
- 창문 건물: `make_demo_building(style="windows")` — 층마다 창문 판(3층 기준 36개)
- 연기·조각 충돌: `explode(smoke_collision=True)`, `fire/smoke(smoke_collision=True)`
- 하늘: `set_look(sky="procedural")` 하늘 텍스처, `hdri=경로` 로 내 HDRI 사진 사용. 하늘 조명이 켜지면 태양을 45%로 낮춤
- 바닥 재질: `set_ground` (asphalt/concrete/grass/sand/dirt/snow), `make_demo_building(ground=...)`
- 영어 메시지: `BLENDER_FX_LANG=en`. 서버·브리지·doctor·레시피 오류 전부
- 수정: 낙하 높이를 마지막 프레임에서 재도록(프레임을 되돌린 뒤 재서 항상 0이었음)
- 테스트 24개 (헤드리스 15개). 실제 블렌더 창 소켓 경로로 스냅샷·되돌리기 확인

## 0.4.0 — 2026-09-19

- FX 작업 도구 13개 추가: `import_model`, `export_model`, `camera`, `camera_shake`, `set_look`, `set_timing`, `clear_caches`, `fire`, `smoke`, `particles`, `wind`, `ocean`, `cloth_flag`
- 공용 도우미 정리: 재질(물·연기·단색), 힘장 만들기, 효과 전체 상자(`fx_bbox`), 프레임 길이 규칙(`set_frame_end`)
- 바다가 있으면 바닥 평면을 숨김. 파티클이 있으면 워크벤치 외곽선을 끔(눈이 검은 점으로 찍히던 문제)
- 불: 대상 복사본을 장애물로 두고 표면 바깥 띠에서만 타게 해 벽을 타고 오르도록 수정
- 테스트 14개 (헤드리스 8개)

## 0.3.0 — 2026-09-19

- 물: `splash` 도구 (Mantaflow 액체, 대상은 장애물)
- 영상: `render_video` (mp4, 블렌더 5.x media_type 대응)
- 저장: `save_blend`
- 점검: `doctor` 도구와 `blender-fx-doctor` CLI
- 렌더 품질 설정을 공용 도우미로 통합 (`apply_render_quality`)

## 0.2.0 — 2026-09-19

- 폭발: `explode` 도구 (Mantaflow 연기·불 + 힘장 + 조각 날리기)
- 파괴에 `impact="none"`, `hold_until` 추가 (폭발과 연결)
- 렌더에 `quality="smoke"` (EEVEE 저샘플) 추가

## 0.1.0 — 2026-09-19

- 파괴: `destroy` (랜덤 평면 조각내기, 리지드바디, 충격체, 먼지 파티클)
- `make_demo_building`, `list_objects`, `render_preview`, `reset_destroy`, `ping_blender`
- 헤드리스 테스트 CLI, 소켓 E2E 스크립트
