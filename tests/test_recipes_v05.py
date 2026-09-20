# v0.5 기능 검증: 스냅샷/되돌리기, 조각 접착, 창문 건물, 연기 충돌, 하늘, 바닥 재질, 영어 메시지
import os

import pytest

from blender_fx_mcp.headless import find_blender, run_steps

BLENDER = find_blender()
pytestmark = pytest.mark.skipif(BLENDER is None, reason="블렌더 실행 파일이 없어 건너뜀")


def _differ(a, b):
    return open(a, "rb").read() != open(b, "rb").read()


def test_snapshot_and_restore(tmp_path):
    snap = tmp_path / "before.blend"
    results = run_steps([
        ("demo_scene", {}),
        ("snapshot", {"path": str(snap)}),
        ("destroy", {"target": "Building", "pieces": 25, "frames": 24, "dust": "none"}),
        ("list_objects", {}),
        ("restore", {"path": str(snap)}),
        ("list_objects", {}),
    ], blender=BLENDER)
    for r in results:
        assert r["ok"], r
    saved, destroyed, after_destroy, restored, after_restore = results[1:]
    assert os.path.getsize(snap) > 10000 and "before.blend" in saved["snapshots"]
    assert after_destroy["chunk_count"] == 25, after_destroy
    # 되돌린 뒤에는 조각이 사라지고 원본 건물이 보여야 한다
    assert after_restore["chunk_count"] == 0, after_restore
    building = next(o for o in after_restore["objects"] if o["name"] == "Building")
    assert building["hidden"] is False
    assert restored["meshes"] >= 2 and restored["camera"]


def test_glue_holds_the_building(tmp_path):
    """같은 약한 충격에서 접착이 있으면 덜 무너져야 한다."""
    common = dict(target="Building", pieces=60, frames=48, dust="none", impact_power=0.06, seed=3)
    results = run_steps([
        ("demo_scene", {}),
        ("destroy", dict(common, glue="none")),
        ("demo_scene", {}),
        ("destroy", dict(common, glue="strong")),
    ], blender=BLENDER)
    for r in results:
        assert r["ok"], r
    loose, glued = results[1], results[3]
    assert loose["glue_constraints"] == 0
    assert glued["glue_constraints"] > 0, glued
    assert glued["max_fall_m"] < loose["max_fall_m"], (loose["max_fall_m"], glued["max_fall_m"])


def test_windows_building_and_ground(tmp_path):
    plain = run_steps([
        ("demo_scene", {"style": "plain"}),
        ("render", {"out_dir": str(tmp_path / "plain"), "frames": [1], "quality": "smoke"}),
    ], blender=BLENDER)
    fancy = run_steps([
        ("demo_scene", {"style": "windows", "ground": "grass"}),
        ("render", {"out_dir": str(tmp_path / "windows"), "frames": [1], "quality": "smoke"}),
    ], blender=BLENDER)
    for r in plain + fancy:
        assert r["ok"], r
    assert plain[0]["windows"] == 0
    assert fancy[0]["windows"] == 36, fancy[0]  # 3층 × 4면 × 3칸
    assert fancy[0]["faces"] > plain[0]["faces"]
    assert _differ(plain[1]["paths"][0], fancy[1]["paths"][0])


def test_ground_materials_differ(tmp_path):
    results = run_steps([
        ("demo_scene", {}),
        ("set_ground", {"material": "asphalt"}),
        ("render", {"out_dir": str(tmp_path / "a"), "frames": [1], "quality": "smoke"}),
        ("set_ground", {"material": "snow", "size": 30.0}),
        ("render", {"out_dir": str(tmp_path / "b"), "frames": [1], "quality": "smoke"}),
    ], blender=BLENDER)
    for r in results:
        assert r["ok"], r
    assert results[1]["material"] == "asphalt"
    assert results[3]["material"] == "snow" and abs(results[3]["size_m"] - 30.0) < 0.5
    assert _differ(results[2]["paths"][0], results[4]["paths"][0])


def test_sky_procedural_and_hdri_error(tmp_path):
    results = run_steps([
        ("demo_scene", {}),
        ("set_look", {"preset": "day", "sky": "flat"}),
        ("render", {"out_dir": str(tmp_path / "flat"), "frames": [1], "quality": "smoke"}),
        ("set_look", {"preset": "day", "sky": "procedural"}),
        ("render", {"out_dir": str(tmp_path / "proc"), "frames": [1], "quality": "smoke"}),
        ("set_look", {"preset": "day", "hdri": str(tmp_path / "missing.hdr")}),
    ], blender=BLENDER)
    for r in results[:5]:
        assert r["ok"], r
    assert results[1]["sky_mode"] == "flat"
    assert results[3]["sky_mode"] == "procedural", results[3]
    assert _differ(results[2]["paths"][0], results[4]["paths"][0])
    assert results[5]["ok"] is False and "HDRI" in results[5]["error"]


def test_smoke_collides_with_chunks(tmp_path):
    results = run_steps([
        ("demo_scene", {}),
        ("destroy", {"target": "Building", "pieces": 25, "frames": 30, "impact": "none", "hold_until": 8, "dust": "none"}),
        ("explode", {"target": "Building", "frames": 30, "burst_frame": 8, "resolution": 32,
                     "smoke_collision": True, "cache_dir": str(tmp_path / "fluid")}),
    ], blender=BLENDER)
    for r in results:
        assert r["ok"], r
    ex = results[2]
    assert ex["smoke_effectors"] == 25, ex
    assert ex["cache_files"] > 0, ex


def test_recipe_errors_in_english(tmp_path):
    results = run_steps([
        ("demo_scene", {"_lang": "en"}),
        ("destroy", {"target": "Building", "material": "titanium", "_lang": "en"}),
        ("destroy", {"target": "NoSuchThing", "_lang": "en"}),
    ], blender=BLENDER)
    assert results[0]["ok"]
    assert results[1]["ok"] is False and "material must be one of" in results[1]["error"], results[1]
    assert results[2]["ok"] is False and "No mesh object named" in results[2]["error"], results[2]
