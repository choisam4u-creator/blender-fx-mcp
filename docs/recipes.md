# 자연어 명령 예시 5개

AI(Claude 등)에게 이렇게 말하면 어떤 도구가 어떤 인자로 불리고, 결과로 무엇이 나오는지 정리했다.
숫자는 **2026-10-04 클라우드에서 `pip install bpy`(Blender 5.0.1 모듈)로 실제로 돌린 값**이다.
유체(4·5번)는 bpy 모듈에서 Mantaflow 가 깨져 있어 클라우드에서 못 돌렸으므로 숫자 대신 확인할 칸을 적었다.
블렌더 앱에서는 물리 결과가 조금 다를 수 있다(시드·버전 차이).

> 시작 전: 블렌더에서 `N` → BlenderMCP → **Connect to MCP server**, AI 에게 "doctor 돌려 줘"로 연결 확인.

---

## 1. "창문 있는 건물 만들고 왼쪽에서 들이받아 무너뜨려"

| 순서 | 도구(인자) |
|---|---|
| 1 | `make_demo_building(style="windows", ground="asphalt")` |
| 2 | `destroy(target="Building", impact="left", pieces=120)` |

결과(실측, `dust="none"` 으로 측정):

- 건물 4×4×9m, 3층, 창문 36개, 닫힌 메시, 부피 138.5㎥(창문을 실제로 파내서 144㎥ 보다 작다)
- 조각 120개, 무게 약 332t, **움직인 조각 100%**, 최대 낙하 **7.62m**, 부피 보존 **1.0**, 열린 조각 0
- 미리보기 5장이 `~/blender-fx-output/<실행 폴더>/` 에 저장되고 대화에 그림으로 붙는다

더 말해 볼 것: "먼지 많이"(`dust="high"`), "벽돌로"(`material="brick"`), "맞은 곳만 잘게"(`pattern="impact", focus=0.9`).

## 2. "유리처럼 가운데부터 산산조각 내고, 깨지는 순간은 슬로모션으로"

| 순서 | 도구(인자) |
|---|---|
| 1 | `destroy(target="Building", material="glass", pattern="radial", impact="front", pieces=150)` |
| 2 | `set_timing(slow_from=12, slow_to=40, slow_factor=0.25)` |

결과(실측, 민무늬 건물 4×4×9m):

- 조각 150개(radial), 재질 glass, 무게 약 360t, 움직인 조각 100%, 최대 낙하 **8.25m**, 부피 보존 **1.0**
- 12~40프레임만 1/4 속도. 리지드바디 물리를 다시 구웠다(`rebaked: true`)
- 파티클까지 한꺼번에 느리게 하려면 "전체를 절반 속도로" → `set_timing(global_slow=0.5)`

## 3. "이 모델 가져와서 상태 보고, 6m 로 맞춰서 부숴 줘"

| 순서 | 도구(인자) |
|---|---|
| 1 | `import_model(path="…/model.glb", size=6.0)` |
| 2 | `inspect_mesh(target="model")` |
| 3 | `destroy(target="model", pieces=80)` |

결과(실측, 창문 건물을 glb 로 내보낸 뒤 다시 가져옴):

- 가져오기: 2.67×2.67×6m, 정점 496·면 988, glTF 가 쪼개 둔 꼭짓점 **672개를 다시 붙여** 닫힌 메시
- 진단: 닫힘, 열린 모서리 0, 볼록한 정도 0.962, 부피 41.0㎥, 수리할 것 없음
- 파괴: 조각 80개, 무게 약 98t, 움직인 조각 100%, 최대 낙하 5.2m, 부피 보존 1.0

닫히지 않은 모델이면 `inspect_mesh` 의 `notes` 가 `shell_thickness` 나 `repair` 를 권한다.
뼈대 있는 캐릭터는 결과의 `parts` 목록을 보고 "몸통만 가져와"(`parts=["Body"]`)처럼 고른다.

## 4. "건물 안에서 크게 터뜨려, 불도 붙여서"

| 순서 | 도구(인자) |
|---|---|
| 1 | `explode(target="Building", power=2.0, fire=True, resolution=48)` |

- 안에서 먼저 조각낸 뒤(`destroy(impact="none", hold_until=11)`) 12프레임에 힘장으로 날리고 연기·불을 만든다
- 확인할 칸: `moved_ratio`(0.5 이상이면 조각이 날아감), `cache_files`(0 이면 연기가 안 구워진 것)
- 미리보기는 연기가 보이도록 EEVEE(`quality="smoke"`)로 렌더한다
- 클라우드 미측정(Mantaflow). Mac 시험 `test_explode_building` 이 같은 흐름을 검증한다

## 5. "옆에서 호스로 꿀을 쏴 줘"

| 순서 | 도구(인자) |
|---|---|
| 1 | `water(mode="stream", at=[-6, 0, 5], direction_deg=90, pitch_deg=-10, speed=9, liquid="honey", duration=22)` |

- `direction_deg=90` 은 +X 쪽, `pitch_deg=-10` 은 살짝 아래로
- 확인할 칸: `drift` — 물이 실제로 간 방향(x,y,z m). 이 예시면 x 가 양수여야 한다
- 물 덩어리가 계산 격자보다 작으면 필요한 `resolution` 숫자를 알려 주는 오류가 난다
- 클라우드 미측정(Mantaflow). Mac 시험 `test_water_direction_and_viscosity` 가 방향·점성을 검증한다

---

## 되돌리기

마음에 안 들면 "아까로 되돌려" → `restore(name)`. 큰 작업 전에 "지금 상태 저장해 둬" → `snapshot(name)`.
`restore` 는 직전 상태를 `before_restore` 로 자동 저장하므로 되돌리기를 다시 되돌릴 수 있다.
