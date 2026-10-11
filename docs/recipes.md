# 자연어 명령 예시 5개

**[English](#english)** — the same five examples in English are at the bottom of this page.

한국어 절 끝의 [나머지 도구 한 줄 예시](#나머지-도구-한-줄-예시)에 33개 도구가 모두 나온다. / [Every other tool in one line](#every-other-tool-in-one-line) covers the rest of the 33 tools.

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

## 나머지 도구 한 줄 예시

위 예시에 안 나온 도구들이다. 왼쪽처럼 말하면 가운데 호출이 된다(인자는 서버 검사를 통과하는 값).

| 이렇게 말하면 | 도구(인자) | 결과 |
|---|---|---|
| "연결이 안 돼, 점검해 줘" | `doctor()` | 파이썬·mcp·uv·블렌더·수신기·연결·출력 폴더를 줄마다 OK/X 로 |
| "블렌더랑 연결됐어?" | `ping_blender()` | `연결됨 (localhost:9876)` 또는 해결법 링크가 붙은 실패 문장 |
| "장면에 뭐가 있어?" | `list_objects()` | 메시 이름과 크기(m). 다른 도구의 `target` 을 고를 때 |
| "무너지는 장면을 다른 프로그램용으로 내보내" | `export_model(path="…/scene.abc")` | `.abc` 는 조각 움직임·물 표면이 프레임마다 구워져 나감. 연기는 못 나감 |
| "건물 위에 물 한 덩어리 떨어뜨려" | `splash(target="Building")` | `water(mode="drop")` 의 간단판 |
| "건물에 불 붙여" | `fire(target="Building", power=1.5)` | 건물 표면에서 계속 타는 불과 연기. `resolution` 은 크기에 맞춰 자동 |
| "꼭대기에서 굴뚝처럼 연기만 피워" | `smoke(at=[0, 0, 9], radius=0.5)` | 불 없이 피어오르는 연기. 인자는 `fire` 와 같음 |
| "눈 내리게 해" | `particles(kind="snow")` | `rain`·`snow`·`sparks`·`ash` 중 하나 |
| "오른쪽으로 강풍" | `wind(direction_deg=90, strength=8)` | +X 쪽 바람. 파티클·천·연기를 민다(1 산들, 3 보통, 8 강풍) |
| "거친 바다 깔아" | `ocean(wave_scale=4)` | 움직이는 바다 표면. 있는 동안 평평한 바닥은 숨김 |
| "옆에 깃발 세워" | `cloth_flag(at=[6, 0, 0])` | 깃대에 걸려 바람에 펄럭이는 깃발. `at` 은 깃대 밑 |
| "바닥을 눈밭으로" | `set_ground(material="snow")` | `asphalt`·`concrete`·`grass`·`sand`·`dirt`·`snow` |
| "낮은 데서 올려다보게" | `camera(preset="low", target="Building")` | 건물에 맞춘 낮은 구도. `wide`·`closeup`·`top` 등 8가지 |
| "부딪히는 순간 화면 흔들어" | `camera_shake(frame=12, strength=0.3)` | 12프레임에 흔들리고 점점 잦아듦(m 단위, 0.8 은 강하게) |
| "노을 지는 하늘로" | `set_look(preset="sunset", sky="procedural")` | 노을 조명과 진짜 하늘 텍스처(EEVEE/Cycles 렌더에서 보임) |
| "달 중력으로" | `set_physics(gravity=1.62)` | 중력 1.62(지구 9.81). 물리를 다시 굽는다 |
| "모션 블러 켜고 깨끗하게" | `set_render(samples=64, motion_blur=True)` | 샘플 64, 빠른 조각이 흐려지는 영화 느낌 |
| "지금 상태 저장해 둬" | `snapshot(name="before_fire")` | 장면을 이름 붙여 저장. 같은 이름이면 덮어씀 |
| "불 붙이기 전으로 되돌려" | `restore(name="before_fire")` | 저장한 상태로 돌아감. 지금 상태는 `before_restore` 로 자동 저장 |
| "저장해 둔 거 뭐 있어?" | `list_snapshots()` | `snapshot` 으로 저장한 이름·크기·저장 시각과 합계 |
| "오래된 스냅샷 정리해" | `clear_snapshots(keep=3)` | 오래된 것부터 지우고 최근 3개를 남김. `before_restore` 는 늘 남김 |
| "블렌더 파일로 저장해" | `save_blend(name="collapse")` | 출력 폴더에 `collapse.blend`. 블렌더에서 직접 열 수 있음 |
| "연기 보이게 다시 렌더" | `render_preview(quality="smoke")` | 미리보기 5장. `preview` 는 빠르지만 하늘·연기·물이 안 보임 |
| "영상으로 뽑아 줘" | `render_video(quality="final")` | 장면 전체를 mp4 로(720p 72프레임에 1~3분) |
| "캐시 비워서 용량 확보" | `clear_caches()` | 구운 캐시를 지움. 다음 도구 호출 때 다시 구움 |
| "다 지우고 원래 건물로" | `reset_destroy()` | 이 도구가 만든 조각·먼지·연기·물·파티클·바다·깃발을 지우고 원본을 되살림 |

---

## English

Five plain-language requests: which tool the AI calls with which arguments, and what comes back.
Numbers were **measured on 2026-10-04 in the cloud with `pip install bpy` (Blender 5.0.1 as a module)**.
Fluids (examples 4 and 5) could not run there because Mantaflow is broken in the bpy module, so those list what to check instead of numbers.
Results in the Blender app can differ slightly (seed and version).

> Before you start: in Blender press `N` → BlenderMCP → **Connect to MCP server**, then ask the AI to "run doctor" to check the connection.
> Set `BLENDER_FX_LANG=en` to get tool messages in English.

### 1. "Build a building with windows and ram it from the left until it collapses"

| Step | Tool (arguments) |
|---|---|
| 1 | `make_demo_building(style="windows", ground="asphalt")` |
| 2 | `destroy(target="Building", impact="left", pieces=120)` |

Result (measured with `dust="none"`):

- Building 4×4×9 m, 3 floors, 36 windows, closed mesh, volume 138.5 m³ (smaller than 144 m³ because the windows are really cut out)
- 120 pieces, about 332 t, **100% of pieces moved**, max drop **7.62 m**, volume preserved **1.0**, 0 open pieces
- 5 preview frames are saved to `~/blender-fx-output/<run folder>/` and attached to the chat as images

Try next: "lots of dust" (`dust="high"`), "make it brick" (`material="brick"`), "smaller pieces only where it was hit" (`pattern="impact", focus=0.9`).

### 2. "Shatter it like glass from the center, and slow-motion the moment it breaks"

| Step | Tool (arguments) |
|---|---|
| 1 | `destroy(target="Building", material="glass", pattern="radial", impact="front", pieces=150)` |
| 2 | `set_timing(slow_from=12, slow_to=40, slow_factor=0.25)` |

Result (measured, plain 4×4×9 m building):

- 150 pieces (radial), glass material, about 360 t, 100% moved, max drop **8.25 m**, volume preserved **1.0**
- Only frames 12–40 play at 1/4 speed. The rigid-body physics is re-baked (`rebaked: true`)
- To slow particles down too, say "everything at half speed" → `set_timing(global_slow=0.5)`

### 3. "Import this model, check it, scale it to 6 m and break it"

| Step | Tool (arguments) |
|---|---|
| 1 | `import_model(path="…/model.glb", size=6.0)` |
| 2 | `inspect_mesh(target="model")` |
| 3 | `destroy(target="model", pieces=80)` |

Result (measured: the window building exported to glb and imported again):

- Import: 2.67×2.67×6 m, 496 vertices, 988 faces; the **672 vertices glTF had split are welded back** into a closed mesh
- Inspection: closed, 0 open edges, convexity 0.962, volume 41.0 m³, nothing to repair
- Destruction: 80 pieces, about 98 t, 100% moved, max drop 5.2 m, volume preserved 1.0

If the model is not closed, the `notes` from `inspect_mesh` suggest `shell_thickness` or `repair`.
For a rigged character, look at the `parts` list in the result and pick one, e.g. "import only the body" (`parts=["Body"]`).

### 4. "Blow up the building from inside, with fire"

| Step | Tool (arguments) |
|---|---|
| 1 | `explode(target="Building", power=2.0, fire=True, resolution=48)` |

- It first fractures the building from inside (`destroy(impact="none", hold_until=11)`), throws the pieces with a force field at frame 12, then adds smoke and fire
- What to check: `moved_ratio` (0.5 or more means the pieces flew), `cache_files` (0 means the smoke was not baked)
- The preview renders with EEVEE (`quality="smoke"`) so the smoke is visible
- Not measured in the cloud (Mantaflow). The Mac test `test_explode_building` checks the same flow

### 5. "Shoot honey from a hose at the side"

| Step | Tool (arguments) |
|---|---|
| 1 | `water(mode="stream", at=[-6, 0, 5], direction_deg=90, pitch_deg=-10, speed=9, liquid="honey", duration=22)` |

- `direction_deg=90` points toward +X, `pitch_deg=-10` aims slightly down
- What to check: `drift`, the direction the liquid actually travelled (x, y, z in m). Here x must be positive
- If the liquid is smaller than the simulation grid, the error tells you the `resolution` you need
- Not measured in the cloud (Mantaflow). The Mac test `test_water_direction_and_viscosity` checks direction and viscosity

### Undo

Not happy? "Go back to before" → `restore(name)`. Before a big change, "save the current state" → `snapshot(name)`.
`restore` automatically saves the state it replaces as `before_restore`, so you can undo the undo.

### Every other tool in one line

Tools not used in the examples above. Say the left column and the AI calls the middle one (the arguments pass the server checks).

| Say | Tool (arguments) | Result |
|---|---|---|
| "It won't connect, check my setup" | `doctor()` | Python, mcp, uv, Blender, receiver, connection and output folder, one OK/X line each |
| "Are you connected to Blender?" | `ping_blender()` | `Connected (localhost:9876)` or a failure message with a link to the fix |
| "What's in the scene?" | `list_objects()` | Mesh names and sizes (m), for picking `target` in other tools |
| "Export the collapse for another program" | `export_model(path="…/scene.abc")` | `.abc` carries piece motion and the water surface per frame; smoke cannot be exported |
| "Drop a blob of water on the building" | `splash(target="Building")` | Shortcut for `water(mode="drop")` |
| "Set the building on fire" | `fire(target="Building", power=1.5)` | Fire and smoke burning on its surface; `resolution` is picked from its size |
| "Just smoke from the top, like a chimney" | `smoke(at=[0, 0, 9], radius=0.5)` | Rising smoke without fire; same arguments as `fire` |
| "Make it snow" | `particles(kind="snow")` | One of `rain`, `snow`, `sparks`, `ash` |
| "Strong wind to the right" | `wind(direction_deg=90, strength=8)` | Wind toward +X that pushes particles, cloth and smoke (1 breeze, 3 normal, 8 gale) |
| "Add a rough sea" | `ocean(wave_scale=4)` | Animated ocean surface; the flat ground is hidden while it exists |
| "Put a flag next to it" | `cloth_flag(at=[6, 0, 0])` | A flag on a pole flapping in the wind; `at` is the foot of the pole |
| "Make the ground snow" | `set_ground(material="snow")` | `asphalt`, `concrete`, `grass`, `sand`, `dirt`, `snow` |
| "Look up at it from low down" | `camera(preset="low", target="Building")` | A low shot framed on the building; 8 presets such as `wide`, `closeup`, `top` |
| "Shake the camera on impact" | `camera_shake(frame=12, strength=0.3)` | Shakes at frame 12 and settles down (in m; 0.8 is strong) |
| "Make it a sunset" | `set_look(preset="sunset", sky="procedural")` | Sunset lighting with a procedural sky (visible in EEVEE/Cycles renders) |
| "Use moon gravity" | `set_physics(gravity=1.62)` | Gravity 1.62 (Earth is 9.81); physics is re-baked |
| "Turn on motion blur and clean it up" | `set_render(samples=64, motion_blur=True)` | 64 samples and motion blur on fast pieces for a film look |
| "Save the current state" | `snapshot(name="before_fire")` | Saves the scene under a name; the same name overwrites |
| "Go back to before the fire" | `restore(name="before_fire")` | Returns to the saved state; the current one is saved as `before_restore` first |
| "What did we save?" | `list_snapshots()` | Names saved with `snapshot`, with size, time saved and the total |
| "Clean up old snapshots" | `clear_snapshots(keep=3)` | Deletes the oldest first and keeps the newest 3; `before_restore` is always kept |
| "Save it as a Blender file" | `save_blend(name="collapse")` | `collapse.blend` in the output folder, to open in Blender yourself |
| "Re-render so the smoke shows" | `render_preview(quality="smoke")` | 5 preview frames; `preview` is faster but hides sky, smoke and water |
| "Render it as a video" | `render_video(quality="final")` | The whole scene as an mp4 (1 to 3 minutes for 72 frames at 720p) |
| "Clear the caches to free space" | `clear_caches()` | Deletes baked caches; they are re-baked on the next tool call |
| "Remove everything and bring the building back" | `reset_destroy()` | Removes the pieces, dust, smoke, water, particles, ocean and flag this toolbox made and restores the originals |
