"""headless.py 의 실패 갈래 시험. 블렌더 대신 가짜 실행 파일(conftest 의 `fake_blender`, 본문은 파이썬)을 진짜로 띄운다.

레시피 개발자가 블렌더가 죽거나 결과를 안 줄 때 보는 안내가 깨지지 않게 한다. Windows 에서도 돈다(세그폴트 흉내만 POSIX 전용).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from blender_fx_mcp import headless

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="시그널(세그폴트) 흉내는 POSIX 전용")


TWO_STEPS = [("demo_scene", {}), ("destroy", {"target": "Building"})]


def test_success_returns_results_in_order(tmp_path, fake_blender):
    exe = fake_blender('print("아무 로그")\nprint(\'FX_RESULT {"n": 1}\')\nprint(\'FX_RESULT {"n": 2}\')')
    assert headless.run_steps(TWO_STEPS, blender=exe) == [{"n": 1}, {"n": 2}]
    argv = (tmp_path / "argv.txt").read_text(encoding="utf-8").split()
    assert argv[:3] == ["--background", "--factory-startup", "--python"]


def test_bpy_python_gets_script_only(tmp_path, fake_blender):
    exe = fake_blender("print('FX_RESULT {}')", name="python3.11")
    headless.run_steps([("list_objects", {})], blender=exe)
    argv = (tmp_path / "argv.txt").read_text(encoding="utf-8").split()
    assert len(argv) == 1 and argv[0].endswith(".py")


def test_temp_script_is_removed(tmp_path, fake_blender):
    exe = fake_blender("print('FX_RESULT {}')")
    headless.run_steps([("list_objects", {})], blender=exe)
    script = (tmp_path / "argv.txt").read_text(encoding="utf-8").split()[-1]
    assert not os.path.exists(script)


def test_immediate_exit_shows_code_and_stderr(fake_blender):
    exe = fake_blender('print("라이브러리 없음", file=sys.stderr)\nsys.exit(3)')
    with pytest.raises(RuntimeError) as e:
        headless.run_steps(TWO_STEPS, blender=exe)
    msg = str(e.value)
    assert "결과 0개 (기대 2개, 1번째 단계 'demo_scene' 에서 멈춤)" in msg
    assert "종료 코드 3" in msg and "라이브러리 없음" in msg


@posix_only
def test_segfault_after_first_step_names_second_step(fake_blender):
    exe = fake_blender("print('FX_RESULT {\"ok\": true}', flush=True)\nimport os, signal\nos.kill(os.getpid(), signal.SIGSEGV)")
    with pytest.raises(RuntimeError) as e:
        headless.run_steps(TWO_STEPS, blender=exe)
    msg = str(e.value)
    assert "2번째 단계 'destroy'" in msg and "세그폴트" in msg and "-11" in msg


def test_no_fx_result_with_exit_zero_shows_stdout_tail(fake_blender):
    exe = fake_blender('print("Traceback: 레시피 오류")')
    with pytest.raises(RuntimeError) as e:
        headless.run_steps([("list_objects", {})], blender=exe)
    msg = str(e.value)
    assert "종료 코드 0" in msg and "Traceback: 레시피 오류" in msg


def test_long_output_is_trimmed(fake_blender):
    exe = fake_blender('for i in range(400):\n    print(f"줄{i} 가나다라마바사")')
    with pytest.raises(RuntimeError) as e:
        headless.run_steps([("list_objects", {})], blender=exe)
    msg = str(e.value)
    assert "줄399" in msg and "줄0 " not in msg
    assert len(msg) < 3500


def test_timeout_raises_and_cleans_script(tmp_path, fake_blender):
    # Windows 는 .cmd 감싸개만 죽고 손자 파이썬이 파이프를 쥔 채 남아, run() 이 그 끝(4초)까지 기다린다
    exe = fake_blender("import time\ntime.sleep(4)")
    with pytest.raises(subprocess.TimeoutExpired):
        headless.run_steps([("list_objects", {})], blender=exe, timeout=1.5)
    script = (tmp_path / "argv.txt").read_text(encoding="utf-8").split()[-1]
    assert not os.path.exists(script)


def test_clean_scene_and_extra_code_order(tmp_path, fake_blender):
    exe = fake_blender("print('FX_RESULT {}')")
    headless.run_steps([("list_objects", {})], blender=exe, extra_code="MARK = 1")
    code = (tmp_path / "script.py").read_text(encoding="utf-8")
    assert code.startswith(headless.CLEAN_SCENE)
    assert code.index("MARK = 1") < code.index("FX_RESULT")

    headless.run_steps([("list_objects", {})], blender=exe, clean=False)
    code = (tmp_path / "script.py").read_text(encoding="utf-8")
    assert headless.CLEAN_SCENE not in code


# ---- 블렌더 찾기 ----

def test_find_blender_prefers_env(monkeypatch, fake_blender):
    exe = fake_blender("")
    monkeypatch.setenv("BLENDER_FX_BLENDER", exe)
    assert headless.find_blender() == exe


def test_find_blender_missing_env_falls_back(tmp_path, monkeypatch, fake_blender):
    other = fake_blender("", name="other-blender")
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


def test_undecodable_output_does_not_crash(fake_blender):
    """블렌더 로그에 UTF-8 이 아닌 바이트가 섞여도(Windows 콘솔 코드 페이지 등) 결과를 읽는다."""
    exe = fake_blender("sys.stdout.flush()\nsys.stdout.buffer.write(b'\\xff\\xfe log\\n')\nprint('FX_RESULT {\"n\": 1}')")
    assert headless.run_steps([("list_objects", {})], blender=exe) == [{"n": 1}]
