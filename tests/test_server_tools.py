# 도구 함수를 끝까지(성공 갈래) 불러 결과 문장(한/영)을 확인한다. 블렌더 없이 돈다.
# run_recipe 를 가짜로 바꿔 레시피마다 미리 정한 결과를 돌려준다.
import re

import pytest

from blender_fx_mcp import server
from blender_fx_mcp.bridge import BlenderError
from mcp.server.mcpserver import Image

HANGUL = re.compile(r"[가-힣]")

RESULTS = {
    "list_objects": {"objects": [{"name": "Building", "size_m": [4, 4, 9]}]},
    "inspect_mesh": {"closed": True, "volume_m3": 144.0, "faces": 1200},
    "demo_scene": {"target": "Building", "size_m": [4.0, 4.0, 9.0], "floors": 3, "style": "windows",
                   "windows": 36, "ground": "asphalt", "volume_m3": 144.0, "closed": True,
                   "overlapping": "Cube", "notes": ["창문을 파냈습니다"]},
    "import_model": {"name": "Tower", "size_m": [2.0, 2.0, 12.0], "vertices": 5000, "faces": 4800, "joined": 7},
    "export_model": {"path": "/out/a.glb", "size_bytes": 2_500_000, "objects": 12, "baked_chunks": 40},
    "destroy": {"target": "Building", "pieces": 120, "pattern": "impact", "focus": 0.5, "material": "concrete",
                "impact": "left", "frames": 72, "total_mass_kg": 33000, "glue": "none", "glue_constraints": 0,
                "dust": "low", "moved_ratio": 0.05, "max_fall_m": 0.2, "volume_kept": 0.998, "open_chunks": 0},
    "explode": {"center": [0, 0, 1], "radius": 2.0, "burst_frame": 12, "power": 1.0, "fire": True,
                "resolution": 48, "chunks": 120, "moved_ratio": 0.8, "smoke_effectors": 30},
    "water": {"liquid": "honey", "mode": "stream", "at": [0, 0, 3], "size": 0.4, "direction_deg": 90.0,
              "pitch_deg": 0.0, "speed": 4.0, "viscosity": 2.0, "gravity_scale": 1.0, "resolution": 64,
              "domain_size_m": 8.0, "effectors": 2, "drift": [3.1, 0.0, -2.0]},
    "emit": {"target": "", "at": [1, 2, 0], "emit_frames": [1, 72], "resolution": 96, "domain_size_m": 6.0},
    "particles": {"kind": "snow", "count": 4000, "frames": [1, 72], "lifetime": 120, "size": 0.02,
                  "gravity": 0.1, "drag": 0.8},
    "wind": {"direction_deg": 45.0, "strength": 3.0, "turbulence": 1.0, "objects": "Wind"},
    "ocean": {"size_m": 60.0, "wave_scale": 1.5, "choppiness": 1.2, "wind_velocity": 25.0},
    "cloth_flag": {"width": 3.0, "height": 2.0, "pole_height": 5.0, "tip_moved_m": 0.7},
    "set_ground": {"material": "grass", "size_m": 40.0, "z": 0.0},
    "camera": {"preset": "low", "location": [5, -8, 0.5], "lens": 24.0},
    "camera_shake": {"frame": 12, "duration": 20, "strength": 0.3},
    "set_look": {"preset": "sunset", "sun_energy": 3.0, "sun_elevation_deg": 8.0, "sky_mode": "procedural"},
    "set_timing": {"frame_range": [1, 288], "fps": 24,
                   "slow_motion": {"frames": [10, 30], "factor": 0.25, "applied_to": "rigidbody"},
                   "global_slow": {"factor": 0.25, "new_frame_end": 288}},
    "set_physics": {"gravity": 1.62, "substeps": 20, "solver_iterations": 30, "speed": 1.0, "fps": 24,
                    "rebaked": True},
    "set_render": {"resolution": [1920, 1080], "fps": 24, "exposure": 0.5, "view_transform": "AgX",
                   "look": "None", "changed": ["samples"]},
    "snapshot": {"size_bytes": 3_400_000, "objects": 9, "snapshots": ["a", "b"]},
    "restore": {"objects": 9, "meshes": 5, "frame_range": [1, 72], "camera": "Camera"},
    "save_blend": {"path": "/out/fx_scene.blend", "size_bytes": 1_200_000, "note": "유체 캐시는 캐시 폴더에"},
    "render_video": {"path": "/out/fx.mp4", "size_bytes": 8_000_000, "size": [1280, 720], "fps": 24,
                     "frames": [1, 72], "engine": "EEVEE"},
    "clear_caches": {"freed_mb": 512, "fluid_domains": 2},
    "reset": {"removed": 130},
}


@pytest.fixture
def fake(monkeypatch, tmp_path):
    """run_recipe 를 가로채 (레시피, 파라미터)를 기록하고 RESULTS 를 돌려준다. render 는 실제 png 하나를 만든다."""
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    seen = []

    def fake_run_recipe(recipe, params, timeout=None):
        seen.append((recipe, params))
        if recipe == "render":
            png = tmp_path / "f1.png"
            png.write_bytes(b"\x89PNG\r\n\x1a\n")
            return {"ok": True, "engine": "WORKBENCH", "size": [640, 360], "frames": [1, 36],
                    "paths": [str(png), str(tmp_path / "없는파일.png")], "missing_in_preview": True}
        return {"ok": True, **RESULTS[recipe]}

    monkeypatch.setattr(server, "run_recipe", fake_run_recipe)
    return seen


CALLS = {
    "list_objects": lambda: server.list_objects(),
    "inspect_mesh": lambda: server.inspect_mesh("Building", decimate_to=500),
    "make_demo_building": lambda: server.make_demo_building(style="windows", ground="asphalt"),
    "import_model": lambda: server.import_model("/m/tower.glb", size=12.0),
    "export_model": lambda: server.export_model("/out/a.glb", bake_physics=True),
    "destroy": lambda: server.destroy("Building"),
    "explode": lambda: server.explode(target="Building"),
    "water": lambda: server.water(mode="stream", liquid="honey", direction_deg=90.0, speed=4.0),
    "splash": lambda: server.splash(target="Building"),
    "fire": lambda: server.fire(at=[1.0, 2.0, 0.0]),
    "smoke": lambda: server.smoke(at=[1.0, 2.0, 0.0]),
    "particles": lambda: server.particles(kind="snow", gravity=0.1),
    "wind": lambda: server.wind(direction_deg=45.0, turbulence=1.0),
    "ocean": lambda: server.ocean(),
    "cloth_flag": lambda: server.cloth_flag(),
    "set_ground": lambda: server.set_ground("grass"),
    "camera": lambda: server.camera("low"),
    "camera_shake": lambda: server.camera_shake(),
    "set_look": lambda: server.set_look("sunset", sky="procedural"),
    "set_timing": lambda: server.set_timing(slow_from=10, slow_to=30, global_slow=0.25),
    "set_physics": lambda: server.set_physics(gravity=1.62),
    "set_render": lambda: server.set_render(samples=64),
    "snapshot": lambda: server.snapshot("before"),
    "restore": lambda: server.restore("before"),
    "save_blend": lambda: server.save_blend(),
    "render_preview": lambda: server.render_preview(frames=[1, 36]),
    "render_video": lambda: server.render_video(),
    "clear_caches": lambda: server.clear_caches(),
    "reset_destroy": lambda: server.reset_destroy(),
}


def _text(out):
    return out[0] if isinstance(out, list) else out


@pytest.mark.parametrize("name", sorted(CALLS))
@pytest.mark.parametrize("lang", ["ko", "en"])
def test_tool_success_message(fake, monkeypatch, name, lang):
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    out = CALLS[name]()
    text = _text(out)
    assert isinstance(text, str) and text
    assert not text.startswith(("실패", "Failed")), text
    if lang == "en":
        # 영어 문장에 한국어가 섞이면 안 된다(레시피가 돌려준 값은 그대로 나올 수 있어 RESULTS 의 한글은 뺐다)
        assert not HANGUL.search(text.replace("창문을 파냈습니다", "")), text
    if isinstance(out, list):
        # 미리보기가 붙는 도구: 있는 파일만 Image 로 붙는다
        assert len(out) == 2 and isinstance(out[1], Image)


def test_every_tool_is_covered():
    import asyncio
    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert names - set(CALLS) <= {"doctor", "ping_blender", "list_snapshots"}


def test_destroy_warns_when_nothing_moved(fake, monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    assert "Almost nothing moved" in _text(server.destroy("Building"))
    monkeypatch.setenv("BLENDER_FX_LANG", "ko")
    assert "impact_power" in _text(server.destroy("Building"))


def test_demo_building_reports_overlap_notes_and_preview(fake, monkeypatch):
    monkeypatch.delenv("BLENDER_FX_LANG", raising=False)
    text = _text(server.make_demo_building())
    assert "Cube" in text and "- 창문을 파냈습니다" in text and "render_preview" in text


def test_export_reports_baked_chunks(fake, monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    assert server.export_model("/out/a.glb") == (
        "Exported: /out/a.glb (2.5MB, 12 objects). Baked physics to keyframes for 40 chunks.")


def test_explode_mentions_chunks_and_smoke_blockers(fake, monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    text = _text(server.explode(target="Building"))
    assert "80% of 120 chunks" in text and "30 chunks block the smoke" in text
    assert [r for r, _ in fake][:2] == ["destroy", "explode"]


def test_fire_names_point_or_target(fake, monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    assert _text(server.fire(at=[1.0, 2.0, 0.0])).startswith("Fire: at [1, 2, 0]")
    RESULTS_TARGET = dict(RESULTS["emit"], target="Building")
    monkeypatch.setitem(RESULTS, "emit", RESULTS_TARGET)
    assert _text(server.smoke(target="Building")).startswith("Smoke: target Building")


def test_set_timing_reports_both_slow_motions(fake, monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    text = server.set_timing(slow_from=10, slow_to=30, global_slow=0.25)
    assert "Range slow motion 10-30 ×0.25" in text and "length now 288 frames" in text


def test_restore_saves_before_restore_first(fake, monkeypatch, tmp_path):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    text = server.restore("../before")
    (r1, p1), (r2, p2) = fake
    assert (r1, r2) == ("snapshot", "restore")
    assert p1["path"].endswith("before_restore.blend") and p2["path"].endswith("before.blend")
    assert text.endswith("The previous state was saved as before_restore.")


def test_splash_maps_to_water_drop(fake):
    server.splash(target="Building", radius=0.5, velocity=2.0)
    recipe, p = fake[0]
    assert recipe == "water" and p["mode"] == "drop" and p["pitch_deg"] == -90.0
    assert p["obstacles"] == ["Building"] and p["size"] == 0.5 and p["speed"] == 2.0


def test_render_failure_after_recipe_success_is_reported(monkeypatch, tmp_path):
    # 효과는 성공했는데 미리보기 렌더가 실패해도 예외가 아니라 실패 문장으로 돌아와야 한다
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", "en")

    def run(recipe, params, timeout=None):
        if recipe == "render":
            raise BlenderError("GPU lost")
        return {"ok": True, **RESULTS[recipe]}

    monkeypatch.setattr(server, "run_recipe", run)
    assert server.ocean() == "Failed: GPU lost"


def test_list_snapshots_lists_files(monkeypatch, tmp_path):
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    (server.snapshot_dir() / "a.blend").write_bytes(b"x" * 2_000_000)
    text = server.list_snapshots()
    assert text.startswith("Snapshots:\n- a (2.0MB, ")


# ---------- 실패 갈래: 블렌더가 꺼져 있거나 레시피가 오류를 내면 예외 대신 실패 문장 ----------

@pytest.mark.parametrize("name", sorted(CALLS))
@pytest.mark.parametrize("lang", ["ko", "en"])
def test_tool_failure_message(monkeypatch, tmp_path, name, lang):
    # 사용자가 가장 자주 보는 경로(블렌더 연결 실패). 어느 도구든 같은 모양으로, 고른 언어로 알려야 한다
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", lang)

    def run(recipe, params, timeout=None):
        raise BlenderError("connection refused")

    monkeypatch.setattr(server, "run_recipe", run)
    text = _text(CALLS[name]())
    assert text == ("실패: connection refused" if lang == "ko" else "Failed: connection refused"), text


@pytest.mark.parametrize("lang,ok,bad", [("ko", "연결됨 (", "실패: "), ("en", "Connected (", "Failed: ")])
def test_ping_blender(monkeypatch, lang, ok, bad):
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    monkeypatch.setenv("BLENDER_FX_PORT", "9999")
    monkeypatch.setattr(server.bridge, "ping", lambda: {"ok": True})
    assert server.ping_blender() == f"{ok}{server.bridge.host()}:9999)"

    def down():
        raise BlenderError("no receiver")

    monkeypatch.setattr(server.bridge, "ping", down)
    assert server.ping_blender() == f"{bad}no receiver"


def test_doctor_tool_returns_report(monkeypatch):
    from blender_fx_mcp import doctor

    monkeypatch.setattr(doctor, "run_checks", lambda: [("python", True, "3.11")])
    monkeypatch.setattr(doctor, "format_report", lambda rows: f"report:{rows[0][0]}")
    assert server.doctor() == "report:python"


def test_preview_note_only_when_something_is_hidden(monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    assert server._preview_note({"missing_in_preview": False}) == ""
    assert "render_preview(quality=\"smoke\")" in server._preview_note({"missing_in_preview": True})


def test_reset_destroy_passes_target(fake):
    server.reset_destroy("Building")
    server.reset_destroy()
    assert [p for r, p in fake if r == "reset"] == [{"target": "Building"}, {"target": None}]
