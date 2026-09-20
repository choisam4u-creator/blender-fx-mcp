# 변경 이력

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
