# Mac 시험 결과 (최신)

- 날짜: 2026-09-28
- 시험한 브랜치: `claude/cloud-work` (커밋 04b6452)
- 환경: macOS arm64, Blender 5.2.0 LTS (백그라운드 모드), Python 3.13.12
- 종합: **FAIL** — main에 병합하지 않음

| 명령 | 결과 |
|---|---|
| `uv run pytest -q` | PASS (42 통과, 0 건너뜀, 2분 17초) |
| `uv run blender-fx-doctor` | PASS (수신기 연결만 X — 블렌더 창을 켜지 않는 시험이라 정상) |
| README 상대 링크 점검 | **FAIL** — 링크 1개 깨짐 |
| README 연결 명령 3줄 | PASS (진입점 `blender-fx-mcp`, `blender-fx-doctor` 모두 pyproject에 있음) |
| `docs/demo-script.md` 대로 GIF 촬영 | 미실행 — 블렌더 창이 필요해 자동 회차에서 못 함 |

## 실패 핵심

```
깨짐 README.md: docs/media/demo.gif
```

README 첫 화면 이미지가 가리키는 `docs/media/demo.gif` 파일이 없다. 공개 저장소 첫 화면에 깨진 이미지가 뜬다.

## 다음 클라우드 회차가 할 일

- GIF가 생길 때까지 README의 `![...](docs/media/demo.gif)` 줄을 HTML 주석으로 감싸거나 지운다(GIF 촬영은 샘님 Mac 몫으로 남긴다).
- 참고: README는 "Connect to MCP server", doctor 안내는 "서버 시작(Connect)"이라고 버튼 이름이 다르다. 한쪽으로 맞춘다.
