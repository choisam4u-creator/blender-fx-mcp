# v0.6 검증: 보로노이 파괴(부피 보존), 아무 메시나 수리, 물 방향·점성, 설정 개방
import os

import pytest

from blender_fx_mcp.headless import find_blender, run_steps

BLENDER = find_blender()
pytestmark = pytest.mark.skipif(BLENDER is None, reason="블렌더 실행 파일이 없어 건너뜀")

OPEN_SHELL = """
import bpy, bmesh
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=2.0)
bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[bm.faces[0], bm.faces[1]], context="FACES")  # 구멍 뚫린 껍데기
me = bpy.data.meshes.new("Broken")
bm.to_mesh(me); bm.free()
o = bpy.data.objects.new("Broken", me)
bpy.context.scene.collection.objects.link(o)
o.location = (0.0, 0.0, 1.0)
"""


def test_voronoi_conserves_volume(tmp_path):
    """조각 부피의 합이 원본과 같아야 물리적으로 맞게 쪼갠 것이다."""
    results = run_steps([
        ("demo_scene", {"style": "plain"}),
        ("destroy", {"target": "Building", "pieces": 60, "frames": 24, "pattern": "uniform", "dust": "none"}),
        ("demo_scene", {"style": "windows"}),
        ("destroy", {"target": "Building", "pieces": 60, "frames": 24, "pattern": "impact", "focus": 0.7, "dust": "none"}),
    ], blender=BLENDER)
    for r in results:
        assert r["ok"], r
    for d in (results[1], results[3]):
        assert 0.95 <= d["volume_kept"] <= 1.05, d
        assert d["open_chunks"] == 0, d
        assert d["pieces"] >= 55, d


def test_focus_concentrates_chunks(tmp_path):
    """맞은 곳에 조각이 몰리면 그쪽 조각이 더 작아진다."""
    common = dict(target="Building", pieces=80, frames=12, dust="none", seed=5, impact="left")
    results = run_steps([
        ("demo_scene", {"style": "plain"}),
        ("destroy", dict(common, pattern="uniform", focus=0.0)),
        ("demo_scene", {"style": "plain"}),
        ("destroy", dict(common, pattern="impact", focus=0.9)),
    ], blender=BLENDER)
    for r in results:
        assert r["ok"], r
    # 두 경우 모두 부피는 보존되어야 하고, 집중했을 때 조각 크기가 더 고르지 않아야 한다
    assert 0.95 <= results[3]["volume_kept"] <= 1.05, results[3]
    assert results[3]["pattern"] == "impact" and results[3]["focus"] == 0.9


def test_broken_mesh_is_repaired(tmp_path):
    """구멍 뚫린 껍데기 메시도 진단하고 두께를 줘서 부술 수 있어야 한다."""
    results = run_steps([
        ("demo_scene", {"style": "plain"}),
        ("inspect_mesh", {"target": "Building"}),
    ], blender=BLENDER, extra_code=OPEN_SHELL)
    for r in results:
        assert r["ok"], r

    broken = run_steps([
        ("inspect_mesh", {"target": "Broken"}),
        ("destroy", {"target": "Broken", "pieces": 20, "frames": 12, "dust": "none",
                     "repair": True, "shell_thickness": 0.15}),
    ], blender=BLENDER, extra_code=OPEN_SHELL)
    info, dest = broken
    assert info["ok"] and info["closed"] is False and info["open_edges"] > 0, info
    assert any("닫혀" in n or "not closed" in n for n in info["notes"]), info
    assert dest["ok"], dest
    assert dest["pieces"] >= 10, dest
    assert dest["source_volume_m3"] > 0.1, dest  # 두께를 줘서 부피가 생겼다


def test_water_direction_and_viscosity(tmp_path):
    """옆으로 쏜 물은 옆으로 가야 하고, 꿀은 물보다 덜 퍼져야 한다."""
    base = dict(mode="stream", at=[-6.0, 0.0, 5.0], size=0.5, direction_deg=90, pitch_deg=-10,
                speed=9.0, duration=20, frames=32, resolution=48)
    results = run_steps([
        ("demo_scene", {"style": "plain", "width": 3.0, "depth": 3.0, "floors": 2}),
        ("water", dict(base, liquid="water", cache_dir=str(tmp_path / "w"))),
        ("water", dict(base, liquid="honey", cache_dir=str(tmp_path / "h"))),
        ("water", {"mode": "pool", "size": 0.8, "frames": 24, "resolution": 48, "cache_dir": str(tmp_path / "p")}),
    ], blender=BLENDER)
    for r in results:
        assert r["ok"], r
    w, h, pool = results[1], results[2], results[3]
    assert w["drift"][0] > 1.0, w          # +X 방향으로 실제로 날아갔다
    assert abs(w["drift"][1]) < 0.6, w     # 옆으로는 거의 안 샜다
    assert w["viscosity"] == 0.0 and h["viscosity"] > 0.5, (w, h)
    assert h["water_verts"] > 100 and w["water_verts"] > 100
    assert pool["water_verts"] > 100, pool


def test_water_too_small_gives_clear_error(tmp_path):
    results = run_steps([
        ("demo_scene", {}),
        ("water", {"mode": "drop", "at": [0, 0, 20], "size": 0.02, "frames": 12,
                   "resolution": 32, "cache_dir": str(tmp_path / "x")}),
    ], blender=BLENDER)
    assert results[1]["ok"] is False
    assert "resolution" in results[1]["error"], results[1]


def test_physics_and_render_settings(tmp_path):
    """중력을 0으로 하면 조각이 떨어지지 않아야 한다."""
    results = run_steps([
        ("demo_scene", {"style": "plain"}),
        ("set_physics", {"gravity": 0.0, "substeps": 12, "rebake": False}),
        ("destroy", {"target": "Building", "pieces": 30, "frames": 24, "impact": "none", "dust": "none"}),
        ("set_render", {"samples": 24, "motion_blur": True, "width": 320, "height": 180, "exposure": 0.5}),
    ], blender=BLENDER)
    for r in results:
        assert r["ok"], r
    phys, dest, rend = results[1], results[2], results[3]
    assert phys["gravity"][2] == 0.0 and phys["substeps"] == 12, phys
    assert dest["max_fall_m"] < 0.1, dest  # 무중력이라 안 떨어진다
    assert rend["resolution"] == [320, 180] and rend["changed"]["samples"] == 24, rend
    assert rend["changed"]["motion_blur"]["on"] is True, rend


def test_global_slow_motion_changes_length(tmp_path):
    results = run_steps([
        ("demo_scene", {"style": "plain"}),
        ("destroy", {"target": "Building", "pieces": 20, "frames": 24, "dust": "none"}),
        ("set_timing", {"global_slow": 0.5, "rebake": False}),
    ], blender=BLENDER)
    for r in results:
        assert r["ok"], r
    t = results[2]
    assert t["global_slow"]["factor"] == 0.5
    assert t["frame_range"][1] == 48, t  # 24프레임이 48프레임으로 늘어난다
    assert t["frame_map"] == [100, 200], t


def test_alembic_export(tmp_path):
    abc = tmp_path / "scene.abc"
    results = run_steps([
        ("demo_scene", {"style": "plain"}),
        ("destroy", {"target": "Building", "pieces": 20, "frames": 12, "dust": "none"}),
        ("export_model", {"path": str(abc)}),
    ], blender=BLENDER)
    for r in results:
        assert r["ok"], r
    assert os.path.exists(abc) and os.path.getsize(abc) > 5000, results[2]
