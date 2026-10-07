"""headless.py 의 실패 갈래 시험. 블렌더 대신 가짜 실행 파일(셸 스크립트)을 진짜로 띄운다.

레시피 개발자가 블렌더가 죽거나 결과를 안 줄 때 보는 안내가 깨지지 않게 한다.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from blender_fx_mcp import headless

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="가짜 실행 파일이 /bin/sh 스크립트")


def _fake(tmp_path: Path, body: str, name: str = "blender") -> str:
    """argv 와 받은 스크립트 내용을 tmp_path 에 남기고 body 를 실행하는 가짜 블렌더."""
    exe = tmp_path / name
    exe.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$@" > "{tmp_path}/argv.txt"\n'
        'for a in "$@"; do last="$a"; done\n'
        f'cat "$last" > "{tmp_path}/script.py"\n'
        + body + "\n",
        encoding="utf-8",
    )
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
    return str(exe)


TWO_STEPS = [("demo_scene", {}), ("destroy", {"target": "Building"})]


def test_success_returns_results_in_order(tmp_path):
    exe = _fake(tmp_path, 'echo "아무 로그"\necho \'FX_RESULT {"n": 1}\'\necho \'FX_RESULT {"n": 2}\'')
    assert headless.run_steps(TWO_STEPS, blender=exe) == [{"n": 1}, {"n": 2}]
    argv = (tmp_path / "argv.txt").read_text().split()
    assert argv[:3] == ["--background", "--factory-startup", "--python"]


def test_bpy_python_gets_script_only(tmp_path):
    exe = _fake(tmp_path, "echo 'FX_RESULT {}'", name="python3.11")
    headless.run_steps([("list_objects", {})], blender=exe)
    argv = (tmp_path / "argv.txt").read_text().split()
    assert len(argv) == 1 and argv[0].endswith(".py")


def test_temp_script_is_removed(tmp_path):
    exe = _fake(tmp_path, "echo 'FX_RESULT {}'")
    headless.run_steps([("list_objects", {})], blender=exe)
    script = (tmp_path / "argv.txt").read_text().split()[-1]
    assert not os.path.exists(script)


def test_immediate_exit_shows_code_and_stderr(tmp_path):
    exe = _fake(tmp_path, 'echo "라이브러리 없음" >&2\nexit 3')
    with pytest.raises(RuntimeError) as e:
        headless.run_steps(TWO_STEPS, blender=exe)
    msg = str(e.value)
    assert "결과 0개 (기대 2개, 1번째 단계 'demo_scene' 에서 멈춤)" in msg
    assert "종료 코드 3" in msg and "라이브러리 없음" in msg


def test_segfault_after_first_step_names_second_step(tmp_path):
    exe = _fake(tmp_path, "echo 'FX_RESULT {\"ok\": true}'\nkill -SEGV $$")
    with pytest.raises(RuntimeError) as e:
        headless.run_steps(TWO_STEPS, blender=exe)
    msg = str(e.value)
    assert "2번째 단계 'destroy'" in msg and "세그폴트" in msg and "-11" in msg


def test_no_fx_result_with_exit_zero_shows_stdout_tail(tmp_path):
    exe = _fake(tmp_path, 'echo "Traceback: 레시피 오류"')
    with pytest.raises(RuntimeError) as e:
        headless.run_steps([("list_objects", {})], blender=exe)
    msg = str(e.value)
    assert "종료 코드 0" in msg and "Traceback: 레시피 오류" in msg


def test_long_output_is_trimmed(tmp_path):
    exe = _fake(tmp_path, "i=0; while [ $i -lt 400 ]; do echo \"줄$i 가나다라마바사\"; i=$((i+1)); done")
    with pytest.raises(RuntimeError) as e:
        headless.run_steps([("list_objects", {})], blender=exe)
    msg = str(e.value)
    assert "줄399" in msg and "줄0 " not in msg
    assert len(msg) < 3500


def test_timeout_raises_and_cleans_script(tmp_path):
    exe = _fake(tmp_path, "sleep 5")
    with pytest.raises(subprocess.TimeoutExpired):
        headless.run_steps([("list_objects", {})], blender=exe, timeout=0.5)
    script = (tmp_path / "argv.txt").read_text().split()[-1]
    assert not os.path.exists(script)


def test_clean_scene_and_extra_code_order(tmp_path):
    exe = _fake(tmp_path, "echo 'FX_RESULT {}'")
    headless.run_steps([("list_objects", {})], blender=exe, extra_code="MARK = 1")
    code = (tmp_path / "script.py").read_text(encoding="utf-8")
    assert code.startswith(headless.CLEAN_SCENE)
    assert code.index("MARK = 1") < code.index("FX_RESULT")

    headless.run_steps([("list_objects", {})], blender=exe, clean=False)
    code = (tmp_path / "script.py").read_text(encoding="utf-8")
    assert headless.CLEAN_SCENE not in code


# ---- 블렌더 찾기 ----

def test_find_blender_prefers_env(tmp_path, monkeypatch):
    exe = _fake(tmp_path, "")
    monkeypatch.setenv("BLENDER_FX_BLENDER", exe)
    assert headless.find_blender() == exe


def test_find_blender_missing_env_falls_back(tmp_path, monkeypatch):
    other = _fake(tmp_path, "", name="other-blender")
    monkeypatch.setenv("BLENDER_FX_BLENDER", str(tmp_path / "없음"))
    monkeypatch.setattr(headless, "CANDIDATES", [str(tmp_path / "없음2"), other])
    assert headless.find_blender() == other


def test_no_blender_raises_with_env_hint(tmp_path, monkeypatch):
    monkeypatch.delenv("BLENDER_FX_BLENDER", raising=False)
    monkeypatch.setattr(headless, "CANDIDATES", [str(tmp_path / "없음")])
    assert headless.find_blender() is None
    with pytest.raises(FileNotFoundError, match="BLENDER_FX_BLENDER"):
        headless.run_steps([("list_objects", {})])


# ---- main() ----

def test_main_unknown_step_exits_2(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["blender-fx-headless", "없는단계"])
    with pytest.raises(SystemExit) as e:
        headless.main()
    assert e.value.code == 2
    out = capsys.readouterr().out
    assert "모르는 단계: 없는단계" in out and "destroy" in out


def test_main_fills_output_paths(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    seen = {}

    def fake_run(steps, **_):
        seen["steps"] = steps
        return [{"ok": True, "i": i} for i in range(len(steps))]

    monkeypatch.setattr(headless, "run_steps", fake_run)
    names = ["render", "explode", "splash", "video", "save", "fire", "export", "import", "clear", "snapshot"]
    monkeypatch.setattr(sys, "argv", ["blender-fx-headless", *names])
    headless.main()
    params = {r: p for r, p in seen["steps"]}
    assert params["render"]["out_dir"] == str(tmp_path / "headless")
    assert params["explode"]["cache_dir"] == str(tmp_path / "cache_fluid")
    assert params["water"]["cache_dir"] == str(tmp_path / "cache_liquid")
    assert params["render_video"]["out_path"].endswith("preview.mp4")
    assert params["save_blend"]["path"].endswith("scene.blend")
    assert params["emit"]["cache_dir"] == str(tmp_path / "cache_emit")
    assert params["import_model"]["path"].endswith("model.glb")
    assert len(params["clear_caches"]["cache_dirs"]) == 3
    assert params["snapshot"]["path"].endswith("headless.blend")
    # STEPS 원본은 바뀌지 않는다
    assert "out_dir" not in headless.STEPS["render"][1]
    out = capsys.readouterr().out
    assert json.loads(out.split("\n}\n")[0] + "\n}") == {"ok": True, "i": 0}


def test_main_default_steps(monkeypatch, tmp_path):
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    seen = {}
    monkeypatch.setattr(headless, "run_steps", lambda steps, **_: seen.setdefault("s", steps) and [])
    monkeypatch.setattr(sys, "argv", ["blender-fx-headless"])
    headless.main()
    assert [r for r, _ in seen["s"]] == ["demo_scene", "destroy", "render"]
