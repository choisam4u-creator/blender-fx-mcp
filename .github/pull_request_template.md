<!-- 한국어나 영어 중 편한 쪽으로 쓰면 됩니다. / Write in Korean or English. -->

## 무엇을·왜 / What and why

<!-- 바꾼 것과 이유. 관련 이슈가 있으면 `Fixes #번호`. / What changed and why. Link issues with `Fixes #123`. -->

## 확인 / Checklist

- [ ] `uvx ruff check .` 통과 / passes
- [ ] `uv run pytest -q` 통과 (블렌더 앱이나 `pip install bpy` 파이썬으로) / passes (with Blender, or a `pip install bpy` Python)
- [ ] 사용자에게 보이는 문장은 한/영 둘 다: 레시피는 `L("한국어", "English")`, 서버는 `t(...)` / user-facing messages are bilingual
- [ ] `CHANGELOG.md` 의 미출시 절에 한 줄 / one line under Unreleased in `CHANGELOG.md`

새 효과(레시피)를 넣었다면 / If you added a new effect (recipe):

- [ ] `recipes/*.py` 가 `run_guarded(main)` 으로 끝남 / ends with `run_guarded(main)`
- [ ] `headless.py` 의 `STEPS` 에 단계 + `tests/` 에 픽셀까지 보는 시험 / a `STEPS` entry in `headless.py` and a test that checks the rendered pixels
- [ ] README 의 도구 표 두 곳(`## 도구 목록`, `## English`)에 도구 이름 / tool name in both README tool tables
- [ ] 앱에서만 도는 기능(Mantaflow 등)이면 `@pytest.mark.app_only` / mark Blender-app-only tests with `@pytest.mark.app_only`

## 블렌더에서 확인한 것 / Tested in Blender

<!-- 블렌더 판, OS, 돌린 명령이나 AI에게 한 말, 결과 이미지(있으면). / Blender version, OS, what you ran or said to the AI, result image if any. -->
