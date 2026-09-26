# 데모 GIF 촬영 대본

README 맨 위 `docs/media/demo.gif` 를 만들기 위한 순서. 길이 목표 10~15초, 가로 1280 이하, 5MB 이하.

## 준비

1. 블렌더 5.2 새 장면(기본 큐브 삭제), `N` → BlenderMCP → Connect.
2. Claude 에 blender-fx 가 연결돼 있는지 `doctor` 로 확인.
3. `reset_destroy` 로 이전 결과를 비운다.

## 도구 호출 순서

| # | AI에게 하는 말 | 호출되는 도구(인자) | 화면에 보일 것 |
|---|---|---|---|
| 1 | "창문 있는 연습용 건물 만들어, 바닥은 아스팔트" | `make_demo_building(style="windows", ground="asphalt")` | 3층 건물 + 바닥 |
| 2 | "노을 분위기, 로우앵글로" | `set_look(preset="sunset")` → `camera(preset="low")` | 붉은 조명, 올려다보는 구도 |
| 3 | "왼쪽에서 충격 줘서 콘크리트처럼 무너뜨려, 먼지 많이" | `destroy(target="Building", impact="left", material="concrete", pieces=120, dust="high")` | 미리보기 5장 |
| 4 | "무너지는 순간 카메라 흔들어" | `camera_shake(frame=12, strength=0.3)` | — |
| 5 | "후반은 슬로모션" | `set_timing(slow_from=10, slow_to=40, slow_factor=0.4)` | — |
| 6 | "영상으로 뽑아 줘" | `render_video(quality="smoke", width=1280, height=720)` | `~/blender-fx-output/<실행 폴더>/fx.mp4` |

## GIF 변환 (Mac)

```bash
ffmpeg -i fx.mp4 -vf "fps=15,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse" -loop 0 docs/media/demo.gif
```

화면 녹화용으로 쓰려면 1~6 동안 Claude 창과 블렌더 뷰포트를 나란히 두고 QuickTime 으로 녹화한 뒤 같은 명령으로 줄인다.

## 확인

- GIF 크기 5MB 이하 (`ls -lh docs/media/demo.gif`)
- README 첫 화면에서 이미지가 깨지지 않는지 GitHub 에서 확인
