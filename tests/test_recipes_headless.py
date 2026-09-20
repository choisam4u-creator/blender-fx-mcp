# 레시피 실제 검증. 블렌더를 백그라운드로 띄워 건물 생성 → 파괴 → 렌더까지 돌린다.
import os

import pytest

from blender_fx_mcp.headless import find_blender, run_steps

BLENDER = find_blender()
pytestmark = pytest.mark.skipif(BLENDER is None, reason="블렌더 실행 파일이 없어 건너뜀")


def test_demo_destroy_render(tmp_path):
    results = run_steps([
        ("demo_scene", {"floors": 3}),
        ("destroy", {"target": "Building", "pieces": 60, "frames": 48, "impact": "left"}),
        ("render", {"out_dir": str(tmp_path), "frame_count": 3}),
        ("list_objects", {}),
    ], blender=BLENDER)
    demo, destroy, render, listing = results
    for r in results:
        assert r["ok"], r

    assert demo["target"] == "Building"
    assert destroy["pieces"] >= 50, destroy
    # 물리가 실제로 돌았는지: 조각의 일부가 움직여야 한다
    assert destroy["moved_ratio"] > 0.2, destroy
    assert destroy["dust_particles"] > 0, destroy
    assert len(render["paths"]) == 3
    for p in render["paths"]:
        assert os.path.exists(p) and os.path.getsize(p) > 1000, p
    assert listing["chunk_count"] == destroy["pieces"]


def test_explode_building(tmp_path):
    cache = tmp_path / "cache_fluid"
    results = run_steps([
        ("demo_scene", {}),
        ("destroy", {"target": "Building", "pieces": 30, "frames": 36, "impact": "none", "hold_until": 9, "dust": "none"}),
        ("explode", {"target": "Building", "frames": 36, "burst_frame": 10, "resolution": 32, "cache_dir": str(cache)}),
        ("render", {"out_dir": str(tmp_path), "frames": [2, 18, 36], "quality": "smoke"}),
    ], blender=BLENDER)
    for r in results:
        assert r["ok"], r
    explode = results[2]
    assert explode["chunks"] == 30
    assert explode["cache_files"] > 0, explode
    assert explode["moved_ratio"] > 0.5, explode  # 힘장이 조각을 날려야 한다
    render = results[3]
    assert render["engine"] != "BLENDER_WORKBENCH", render  # 연기는 워크벤치로 못 본다
    paths = render["paths"]
    assert len(paths) == 3 and all(os.path.getsize(p) > 1000 for p in paths)
    # 터지기 전(2프레임)과 터진 뒤(18프레임) 그림이 달라야 한다
    assert open(paths[0], "rb").read() != open(paths[1], "rb").read()


def test_water_drop_on_building(tmp_path):
    cache = tmp_path / "cache_liquid"
    results = run_steps([
        ("demo_scene", {"width": 3.0, "depth": 3.0, "floors": 2}),
        ("water", {"mode": "drop", "frames": 24, "resolution": 48, "cache_dir": str(cache)}),
        ("render", {"out_dir": str(tmp_path), "frames": [2, 14, 24], "quality": "smoke"}),
    ], blender=BLENDER)
    for r in results:
        assert r["ok"], r
    w = results[1]
    assert w["effectors"] >= 1, w
    assert w["cache_files"] > 0 and w["water_verts"] > 100, w
    assert w["drift"][2] < 0, w  # 떨어졌으니 z 가 내려가야 한다
    paths = results[2]["paths"]
    assert len(paths) == 3 and all(os.path.getsize(p) > 1000 for p in paths)
    assert open(paths[0], "rb").read() != open(paths[1], "rb").read()


def test_video_and_save(tmp_path):
    results = run_steps([
        ("demo_scene", {}),
        ("destroy", {"target": "Building", "pieces": 20, "frames": 12, "dust": "none"}),
        ("render_video", {"out_path": str(tmp_path / "clip.mp4"), "quality": "preview", "width": 320, "height": 180}),
        ("save_blend", {"path": str(tmp_path / "scene.blend")}),
    ], blender=BLENDER)
    for r in results:
        assert r["ok"], r
    video = results[2]
    assert video["path"].endswith(".mp4") and os.path.getsize(video["path"]) > 1000, video
    with open(video["path"], "rb") as f:
        head = f.read(12)
    assert head[4:8] == b"ftyp", head  # 진짜 mp4 인지 헤더로 확인
    assert video["frames"] == [1, 12]
    blend = results[3]
    assert os.path.exists(blend["path"]) and blend["size_bytes"] > 10000


def test_reset_restores_original(tmp_path):
    results = run_steps([
        ("demo_scene", {}),
        ("destroy", {"target": "Building", "pieces": 20, "frames": 24, "dust": "none"}),
        ("reset", {"target": "Building"}),
        ("list_objects", {}),
    ], blender=BLENDER)
    for r in results:
        assert r["ok"], r
    assert results[2]["removed"] == 21  # 조각 20 + 충격체 1
    listing = results[3]
    assert listing["chunk_count"] == 0
    building = next(o for o in listing["objects"] if o["name"] == "Building")
    assert building["hidden"] is False
