# blender-fx-mcp

**[English]** An MCP server that lets an AI (Claude, Codex, Cursor, any MCP client) build Blender FX from plain language: building destruction, explosions with smoke and fire, water splashes, fire, particles, wind, ocean and cloth. You direct ("collapse it from the left, slower, more dust"), the AI picks a tool, Blender simulates, and preview frames come back. No Blender knowledge needed. Requires Blender 5.2, the [blender-mcp](https://github.com/ahujasid/blender-mcp) receiver add-on inside Blender, and `uv`. Set `BLENDER_FX_LANG=en` for English messages. See the Korean sections below for install and daily use; the commands are the same.

---

AI에게 말로 시키면 블렌더에서 **아무 3D 모델이나 물리에 맞게 부수고**, **물을 원하는 방향·점성으로 쏘고**,
폭발·불·연기·비·눈·바다·깃발까지 만들어 주는 MCP 서버입니다.
블렌더를 몰라도 됩니다. 사용자는 감독처럼 "왼쪽에서 충격 줘서 무너뜨려, 더 잘게, 느리게"라고 말하고,
AI가 도구를 골라 실행한 뒤 미리보기 프레임을 보여 줍니다.

## 어떻게 돌아가나

```
[클로드 / 코덱스 / 커서 등 MCP 클라이언트]
        │  "Building을 왼쪽에서 부숴"
        ▼
[blender-fx-mcp]  ← 이 프로젝트. 검증된 레시피를 도구로 감쌌다
        │  파이썬 레시피 전송 (localhost:9876)
        ▼
[블렌더 안 수신기 애드온 (blender-mcp)]
        │
        ▼
[리지드바디 · Mantaflow 연기/물 → 굽기 → 렌더] → 프레임 이미지가 AI에게 돌아온다
```

AI는 코드를 짜지 않습니다. 도구와 값만 고릅니다. 그래서 블렌더 버전이 바뀌어도 레시피 한 곳만 고치면 됩니다.

## 준비물 3가지

1. **블렌더 5.2** (5.x LTS 기준으로 만들었습니다)
2. **블렌더 안 수신기 애드온**: [blender-mcp](https://github.com/ahujasid/blender-mcp)의 `addon.py`를 블렌더에 설치하고 켭니다.
   설치 후 3D 화면에서 `N` 키 → **BlenderMCP** 탭 → **Connect to MCP server** 를 누르면 수신기가 켜집니다.
3. **uv** (파이썬 실행기): `brew install uv`

준비물이 갖춰졌는지 한 번에 확인:

```bash
uvx --from git+https://github.com/choisam4u-creator/blender-fx-mcp blender-fx-doctor
```

## 설치 (한 줄)

클로드 코드:

```bash
claude mcp add -s user blender-fx -- uvx --from git+https://github.com/choisam4u-creator/blender-fx-mcp blender-fx-mcp
```

로컬 폴더에서 개발 중이면:

```bash
claude mcp add -s user blender-fx -- uv --directory /절대/경로/blender-fx-mcp run blender-fx-mcp
```

클로드 데스크톱 앱은 `~/Library/Application Support/Claude/claude_desktop_config.json`의 `mcpServers`에,
코덱스는 `~/.codex/config.toml`의 `[mcp_servers.blender_fx]`에 같은 명령을 적습니다.
등록 후 앱을 완전히 껐다 켜야 도구가 보입니다.

## 매일 쓰는 순서

1. 블렌더를 켠다.
2. `N` 키 → BlenderMCP 탭 → 수신기 켜기.
3. AI에게 말한다: **"연습용 건물 하나 만들고, 왼쪽에서 충격 줘서 콘크리트처럼 무너뜨려."**
4. 돌아온 미리보기 프레임을 보고 다시 말한다: "더 잘게", "맞은 데만 부서지게", "유리처럼", "물을 왼쪽에서 옆으로 쏴", "꿀처럼 걸쭉하게", "중력 절반", "슬로모션", "불 붙여", "눈 내리게", "로우앵글로", "노을로".
5. 마음에 들면: "영상으로 뽑아 줘", "장면 저장해 줘", "glb로 내보내 줘."

자기 모델이 있으면: **"~/Desktop/tower.glb 가져와서 12m 크기로 세우고 왼쪽에서 부숴."**

## 도구 목록

| 도구 | 하는 일 |
|---|---|
| `doctor` | 준비물 점검(파이썬·mcp·uv·블렌더·수신기·출력 폴더). 안 될 때 먼저 부른다 |
| `ping_blender` | 수신기와 연결되는지 확인 |
| `list_objects` | 장면의 메시 이름·크기 목록 (부술 대상 고르기) |
| `inspect_mesh` | 부수기 전 모델 진단: 닫혀 있나, 부피, 오목한 정도, 면 수, 수리하면 얼마나 나아지나 |
| `make_demo_building` | 연습용 건물 + 바닥 + 카메라 + 조명 생성. `style`(plain/windows 창문 건물), `ground`(바닥 재질) |
| `destroy` | **아무 메시나** 보로노이(돌 깨지듯 다각형) 조각으로 부수고 물리로 무너뜨림. 메시 자동 수리 포함. 인자: `impact`(left/right/front/back/top/none), `material`(concrete/brick/glass/wood/stone/metal/ice/plaster), `pieces`, `pattern`(impact/uniform/radial/slabs), `focus`, `glue`(none/weak/medium/strong), `collision`(auto/convex/mesh/box/sphere), `interior`(단면 재질), `repair`, `shell_thickness`, `density`/`friction`/`bounce`, `dust`, `impact_power`, `time_scale`, `frames`, `seed` |
| `explode` | 폭발. `target`을 주면 건물을 조각낸 뒤 안에서 터뜨려 연기·불과 함께 날림. 없으면 `at=[x,y,z]` 위치에 연기·불만. 인자: `power`, `fire`, `frames`, `burst_frame`, `resolution`, `smoke_collision`(연기가 조각에 부딪힘) |
| `water` | **방향·모양·점성을 정하는 물**. `mode`(drop 떨어뜨리기 / stream 호스처럼 쏘기 / pool 물 채우기 / object 내 메시가 물이 됨), `direction_deg`, `pitch_deg`, `speed`, `shape`(sphere/box/column), `liquid`(water/oil/honey/lava/mercury/slime), `viscosity`, `surface_tension`, `gravity_scale`, `obstacles`, `spray`, `resolution`, `smoothing` |
| `splash` | `water(mode="drop")` 의 간단 버전 |
| `fire` / `smoke` | 계속 타오르는 불 / 피어오르는 연기. `resolution=0` 이면 대상 크기에 맞춰 자동. `density`, `dissolve`, `vorticity`, `noise`, `smoke_collision` |
| `particles` | 비·눈·불꽃·재. `kind`(rain/snow/sparks/ash), `area`, `count`, `size`, `gravity`, `drag`, `lifetime`, `speed` |
| `wind` | 바람 힘장. 파티클·깃발·연기를 민다. `direction_deg`, `strength`, `turbulence` |
| `ocean` | 바다 표면(파도 움직임). `size`, `wave_scale`, `choppiness`, `wind_velocity` |
| `cloth_flag` | 깃대에 걸린 깃발(천)이 바람에 펄럭임 |
| `import_model` | glb/gltf/fbx/obj/stl/usd/blend 모델을 가져와 하나로 합치고 크기 맞춰 바닥에 세움 |
| `export_model` | glb/gltf/fbx/obj/**abc** 로 내보내기. `.abc`(Alembic)는 물 표면과 조각 움직임을 프레임마다 담아 다른 프로그램에서 그대로 재생됨. `bake_physics=True` 면 조각 물리를 키프레임으로 |
| `camera` | 구도 프리셋 wide/medium/closeup/low/high/top/front/side + `angle_deg`, `height`, `lens` |
| `camera_shake` | 충돌·폭발 순간 카메라 흔들림 (`frame`, `strength`, `duration`) |
| `set_look` | 조명·하늘 분위기 day/sunset/night/overcast/studio. `sky="procedural"` 진짜 하늘 텍스처, `hdri=파일경로` 내 HDRI 사진으로 조명 |
| `set_ground` | 바닥 재질 asphalt/concrete/grass/sand/dirt/snow, `size`(m) |
| `snapshot` / `list_snapshots` / `restore` | 장면을 저장해 두고 언제든 그때로 되돌린다. 위험한 작업 전에 쓴다 |
| `set_timing` | 프레임 범위·fps·슬로모션. 구간(`slow_from`/`slow_to`/`slow_factor`)은 물리·연기·물에만, `global_slow` 는 파티클까지 전부 |
| `set_physics` | 중력 세기·기울기, 계산 하위단계·반복(정확도), 물리 속도, fps |
| `set_render` | 샘플 수, 모션블러, 해상도, 노출, 필름 룩, 배경 빼기 |
| `render_preview` | 현재 장면 다시 렌더. `quality="preview"` 빠름(연기·물 안 보임), `"smoke"` 연기·물 보임, `"final"` 고화질 |
| `render_video` | 장면 전체를 mp4(H.264)로 렌더 |
| `save_blend` | 현재 장면을 .blend 로 저장 (블렌더에서 직접 열어 손볼 수 있음) |
| `clear_caches` | 구운 캐시와 캐시 폴더 비우기 |
| `reset_destroy` | 이 도구가 만든 것(조각·충격체·연기·물·파티클·바다·깃발)을 지우고 원본 되살리기 |

미리보기·영상·.blend 는 `~/blender-fx-output/` 아래 실행별 폴더에 저장됩니다. (`BLENDER_FX_OUT`으로 변경)
연기·물 캐시는 같은 폴더의 `cache_fluid/`, `cache_liquid/`에 쌓입니다. 용량이 커지면 지워도 됩니다.

## 개발·테스트

블렌더를 창 없이 띄워 레시피를 소켓 없이 검증할 수 있습니다.

```bash
uv sync --group dev
uv run pytest -q
```

```bash
uv run blender-fx-headless demo-windows destroy render
uv run blender-fx-headless demo destroy-hold explode smoke
uv run blender-fx-headless demo water-side smoke
uv run blender-fx-headless demo snapshot destroy restore
uv run blender-fx-headless demo destroy video save
```

블렌더가 켜져 있으면 실제 MCP 클라이언트 → 서버 → 소켓 경로 전체를 확인할 수 있습니다:

```bash
uv run python scripts/e2e_socket.py
```

## 지금 한계 (정직하게)

- **조각내기는 보로노이 + 불리언**이라 정확하지만, 조각 수가 많으면 느립니다. 조각 140개에 약 2초, 400개면 훨씬 오래 걸립니다.
- 조각 부피의 합이 원본과 같은지(`volume_kept`) 결과에 나옵니다. 1.0 에서 크게 벗어나면 원본 메시에 문제가 있다는 뜻입니다.
- 남의 모델은 `inspect_mesh` 로 먼저 보세요. 닫히지 않은 껍데기는 `shell_thickness` 로 두께를 줘야 제대로 부서집니다.
- `glue`(조각 접착)는 제약을 수백 개 만들어 굽기가 느려집니다. `glue_neighbors`, `glue_max` 로 줄일 수 있습니다.
- `restore` 는 블렌더가 그 .blend 파일을 엽니다. 직전 상태는 `before_restore` 로 자동 저장되지만, 여러 단계 실행 취소는 아닙니다.
- `sky="procedural"` 과 연기·물은 EEVEE·Cycles 에서만 보입니다. 빠른 미리보기에서는 도구가 그 사실을 알려 줍니다.
- HDRI 는 가지고 있는 파일만 씁니다. 인터넷에서 받아오지 않습니다.
- 물은 **계산 격자보다 작은 물 덩어리는 사라집니다.** 그럴 때 도구가 필요한 `resolution` 숫자를 알려 줍니다.
- 물 해상도 64 에서 표면에 각이 보입니다. 128 이상이 곱지만 굽기가 몇 배 느립니다.
- 구간 슬로모션은 물리·연기·물에만 걸립니다. 파티클까지 느리게 하려면 `set_timing(global_slow=)` 을 쓰세요(전체 길이가 늘어납니다).
- `export_model` 의 `.abc` 는 물 표면과 조각 움직임을 담지만, 연기(볼륨)는 어떤 형식으로도 나가지 않습니다.
- 창문은 벽을 실제로 파낸 것이지만 실내는 없습니다.
- 블렌더 5.2에서만 확인했습니다.
- 메시지는 한국어가 기본입니다. 영어는 `BLENDER_FX_LANG=en`.
- 수신기 애드온은 blender-mcp 것을 빌려 씁니다. 그쪽 포트·명령이 바뀌면 같이 고쳐야 합니다.
- blender-mcp 서버와 이 서버를 같이 켜 두면 수신기가 하나라 끊길 수 있습니다. 문제가 나면 하나만 켜세요.

## 로드맵

- v0.1 파괴 (완료)
- v0.2 폭발: Mantaflow 연기·불 + 힘장 + 파편 (완료)
- v0.3 물: Mantaflow 액체 스플래시, mp4 렌더, .blend 저장, doctor (완료)
- v0.4 FX 작업 도구: 모델 가져오기/내보내기, 카메라·흔들림, 조명 프리셋, 슬로모션, 불·연기, 파티클, 바람, 바다, 깃발, 캐시 정리 (완료)
- v0.5 스냅샷/되돌리기, 조각 접착(구조 붕괴), 창문 건물, 연기·조각 충돌, 하늘 텍스처·HDRI, 바닥 재질, 영어 메시지 (완료)
- v0.6 보로노이 파괴(아무 메시나, 부피 보존), 메시 자동 수리·진단, 물 방향·점성·모드, 전 설정 개방(set_physics/set_render), 전체 슬로모션, Alembic 내보내기 (완료)
- v1.0 프리셋 JSON 분리, 자체 수신기 애드온 동봉, 도로·차량 같은 소품 프리셋, 도구 설명 영어화

## 기여

[CONTRIBUTING.md](CONTRIBUTING.md)를 보세요. 레시피 하나 = 파일 하나라, 새 효과는 `recipes/` 에 파일을 추가하고 `server.py` 에 도구 하나를 붙이면 됩니다.

## 라이선스

MIT (이 저장소). 블렌더 안 수신기 애드온은 blender-mcp 프로젝트 것이며 그쪽 라이선스를 따릅니다.
