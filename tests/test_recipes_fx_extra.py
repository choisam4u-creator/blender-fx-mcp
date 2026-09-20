# FX 보조 기능 검증: 모델 가져오기·내보내기, 카메라, 흔들림, 조명, 타이밍, 불·연기, 파티클, 바람, 바다, 깃발, 캐시 정리
import os

import pytest

from blender_fx_mcp.headless import find_blender, run_steps

BLENDER = find_blender()
pytestmark = pytest.mark.skipif(BLENDER is None, reason="블렌더 실행 파일이 없어 건너뜀")


def _differ(a, b):
    return open(a, "rb").read() != open(b, "rb").read()


def test_scene_tools(tmp_path):
    glb = tmp_path / "model.glb"
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "junk.uni").write_bytes(b"x" * 2048)
    results = run_steps([
        ("demo_scene", {}),
        ("export_model", {"path": str(glb)}),
        ("import_model", {"path": str(glb), "name": "Imported", "size": 6.0}),
        ("camera", {"preset": "low"}),
        ("camera_shake", {"frame": 5, "strength": 0.5, "duration": 6}),
        ("set_look", {"preset": "sunset"}),
        ("render", {"out_dir": str(tmp_path), "frames": [1, 8], "quality": "preview"}),
        ("clear_caches", {"cache_dirs": [str(cache)]}),
        ("list_objects", {}),
    ], blender=BLENDER)
    for r in results:
        assert r["ok"], r
    export, imported, cam, shake, look, render, cleared, listing = results[1:]
    assert os.path.getsize(glb) > 1000 and export["objects"] >= 1
    assert imported["name"] == "Imported" and abs(max(imported["size_m"]) - 6.0) < 0.05, imported
    assert cam["preset"] == "low" and cam["lens"] == 28
    assert shake["duration"] == 6
    assert look["preset"] == "sunset"
    assert _differ(*render["paths"])  # 8프레임은 흔들리는 중이라 1프레임과 달라야 한다
    assert cleared["freed_mb"] >= 0.0 and not os.path.exists(cache / "junk.uni")
    assert any(o["name"] == "Imported" for o in listing["objects"])


def test_fire_wind_timing(tmp_path):
    results = run_steps([
        ("demo_scene", {}),
        ("wind", {"direction_deg": 90, "strength": 4.0, "turbulence": 1.0}),
        ("emit", {"kind": "fire", "target": "Building", "frames": 24, "resolution": 32, "cache_dir": str(tmp_path / "emit")}),
        ("set_timing", {"slow_from": 8, "slow_to": 16, "slow_factor": 0.25, "rebake": True}),
        ("render", {"out_dir": str(tmp_path), "frames": [2, 20], "quality": "smoke"}),
    ], blender=BLENDER)
    for r in results:
        assert r["ok"], r
    wind, fire, timing, render = results[1:]
    assert wind["objects"] == ["FX_Wind", "FX_Turbulence"]
    assert fire["cache_files"] > 0 and fire["target"] == "Building"
    assert timing["slow_motion"]["applied_to"], timing
    assert render["engine"] != "BLENDER_WORKBENCH"
    assert _differ(*render["paths"])


def test_particles_ocean_flag(tmp_path):
    results = run_steps([
        ("ocean", {"size": 30, "frames": 24}),
        ("particles", {"kind": "snow", "frames": 24, "area": 10.0}),
        ("particles", {"kind": "sparks", "at": [0.0, 0.0, 3.0], "start_frame": 3, "frames": 24}),
        ("cloth_flag", {"at": [8.0, 0.0, 0.0], "frames": 24}),
        ("render", {"out_dir": str(tmp_path), "frames": [1, 24], "quality": "preview"}),
    ], blender=BLENDER)
    for r in results:
        assert r["ok"], r
    ocean, snow, sparks, flag, render = results
    assert ocean["frames"] == 24
    assert snow["kind"] == "snow" and snow["count"] > 0
    assert sparks["count"] == 600 and sparks["frames"] == [3, 9]
    assert flag["pinned"] > 0 and flag["tip_moved_m"] > 0.05, flag
    assert _differ(*render["paths"])
