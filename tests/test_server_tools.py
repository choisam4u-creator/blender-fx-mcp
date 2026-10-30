# 도구 함수를 끝까지(성공 갈래) 불러 결과 문장(한/영)을 확인한다. 블렌더 없이 돈다.
# run_recipe 를 가짜로 바꿔 레시피마다 미리 정한 결과를 돌려준다.
import os
import re

import pytest

from blender_fx_mcp import server
from blender_fx_mcp.bridge import BlenderError
from mcp.server.mcpserver import Image
from conftest import tool_text

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
                "resolution": 48, "cell_m": 0.5, "chunks": 120, "moved_ratio": 0.8, "smoke_effectors": 30},
    "water": {"liquid": "honey", "mode": "stream", "at": [0, 0, 3], "size": 0.4, "direction_deg": 90.0,
              "pitch_deg": 0.0, "speed": 4.0, "viscosity": 2.0, "gravity_scale": 1.0, "resolution": 64,
              "cell_m": 0.125, "domain_size_m": 8.0, "effectors": 2, "drift": [3.1, 0.0, -2.0]},
    "emit": {"target": "", "at": [1, 2, 0], "emit_frames": [1, 72], "resolution": 96, "cell_m": 0.1,
             "domain_size_m": 6.0},
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


def _snapshots(root, *names):
    (root / "snapshots").mkdir(parents=True, exist_ok=True)
    for n in names:
        (root / "snapshots" / f"{n}.blend").write_bytes(b"x")


@pytest.fixture
def fake(monkeypatch, tmp_path):
    """run_recipe 를 가로채 (레시피, 파라미터)를 기록하고 RESULTS 를 돌려준다. render 는 실제 png 하나를 만든다."""
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    _snapshots(tmp_path, "before", "_before")  # restore 가 되돌릴 스냅샷(없으면 블렌더에 보내기 전에 막는다)
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
    # 이 OS 의 절대 경로(Windows 에서 "/m/..." 는 드라이브가 없어 상대 경로로 풀린다)
    "import_model": lambda: server.import_model(os.path.abspath("/m/tower.glb"), size=12.0),
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


def _without_paths(text, *dirs):
    """문장에서 주어진 폴더 경로(그대로·실제 경로 둘 다)를 지운다."""
    for d in dirs:
        for form in {str(d), str(d.resolve())}:
            text = text.replace(form, "<OUT>")
    return text


def _text(out):
    return tool_text(out)


@pytest.mark.parametrize("name", sorted(CALLS))
@pytest.mark.parametrize("lang", ["ko", "en"])
def test_tool_success_message(fake, monkeypatch, tmp_path, name, lang):
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    out = CALLS[name]()
    text = _text(out)
    assert isinstance(text, str) and text
    assert not text.startswith(("실패", "Failed")), text
    if lang == "en":
        # 영어 문장에 한국어가 섞이면 안 된다(레시피가 돌려준 값은 그대로 나올 수 있어 RESULTS 의 한글은 뺐다)
        # 출력 폴더 경로는 사용자 것이라 한글일 수 있다(예: 한글 홈 폴더). 경로는 빼고 문장만 본다.
        assert not HANGUL.search(_without_paths(text, tmp_path).replace("창문을 파냈습니다", "")), text
    if isinstance(out, list):
        # 미리보기가 붙는 도구: 있는 파일만 Image 로 붙는다
        assert len(out) == 2 and isinstance(out[1], Image)


@pytest.mark.parametrize("name", ["fire", "water", "render_preview"])
def test_english_message_under_hangul_output_dir(fake, monkeypatch, tmp_path, name):
    """회귀(10/10 Mac): 출력 폴더가 한글 경로여도 영어 문장 자체는 영어이고, 경로는 망가지지 않고 그대로 나온다."""
    out_dir = tmp_path / "사용자" / "출력"
    out_dir.mkdir(parents=True)
    monkeypatch.setenv("BLENDER_FX_OUT", str(out_dir))
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    text = _text(CALLS[name]())
    assert not text.startswith("Failed"), text
    if name != "render_preview":  # 미리보기는 가짜 결과의 png 경로(tmp_path)를 쓴다
        assert str(out_dir) in text, text
    assert not HANGUL.search(_without_paths(text, out_dir, tmp_path)), text


def test_every_tool_is_covered():
    import asyncio
    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert names - set(CALLS) <= {"doctor", "ping_blender", "list_snapshots", "clear_snapshots"}


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
    text = tool_text(server.list_snapshots())
    assert text.startswith("Snapshots:\n- a (2.0MB, ")


# ---------- 실패 갈래: 블렌더가 꺼져 있거나 레시피가 오류를 내면 예외 대신 실패 문장 ----------

@pytest.mark.parametrize("name", sorted(CALLS))
@pytest.mark.parametrize("lang", ["ko", "en"])
def test_tool_failure_message(monkeypatch, tmp_path, name, lang):
    # 사용자가 가장 자주 보는 경로(블렌더 연결 실패). 어느 도구든 같은 모양으로, 고른 언어로 알려야 한다
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    _snapshots(tmp_path, "before")

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

    row = dict(id="python", name="python", ok=True, detail="3.11", fix="")
    monkeypatch.setattr(doctor, "run_checks", lambda clients=True: [row])
    # AI 가 부른 도구라 모두 정상일 때 끝줄이 AI 가 할 순서(for_ai)
    monkeypatch.setattr(doctor, "format_report", lambda rows, for_ai=False: f"report:{rows[0]['id']}:{for_ai}")
    assert tool_text(server.doctor()) == "report:python:True"


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_doctor_tool_does_not_suggest_registering(monkeypatch, tmp_path, lang):
    """MCP doctor 도구를 부른 클라이언트는 이미 연결돼 있다. 설정 파일에 등록이 안 보여도 등록 명령을 권하지 않는다."""
    from blender_fx_mcp import doctor

    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path / "out"))
    monkeypatch.setattr(doctor, "client_configs", lambda: [])  # 어느 설정에도 등록이 안 보임
    monkeypatch.setattr(server.bridge, "ping", lambda: None)
    monkeypatch.setattr(server.bridge, "blender_version", lambda: "5.2.0 LTS")
    report = tool_text(server.doctor())
    assert "claude mcp add" not in report
    assert ("MCP 클라이언트 등록" if lang == "ko" else "MCP client registration") not in report
    # 터미널의 blender-fx-doctor 에는 그대로 있다
    assert "client" in [c["id"] for c in doctor.run_checks()]


def test_preview_note_only_when_something_is_hidden(monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    assert server._preview_note({"missing_in_preview": False}) == ""
    assert "render_preview(quality=\"smoke\")" in server._preview_note({"missing_in_preview": True})


def test_reset_destroy_passes_target(fake):
    server.reset_destroy("Building")
    server.reset_destroy()
    assert [p for r, p in fake if r == "reset"] == [{"target": "Building"}, {"target": None}]


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_restore_unknown_name_keeps_before_restore(fake, monkeypatch, tmp_path, lang):
    """이름이 틀리면 블렌더에 아무것도 보내지 않는다: 자동 저장이 지난 before_restore 를 덮어쓰지 않게. 비슷한 이름을 알려 준다."""
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    _snapshots(tmp_path, "before_fire", "before_restore")
    text = server.restore("before_fier")
    assert fake == [], fake
    assert text.startswith("실패: " if lang == "ko" else "Failed: "), text
    assert "before_fire" in text and "list_snapshots" in text, text


def test_restore_without_snapshots_says_save_first(monkeypatch, tmp_path):
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    monkeypatch.setattr(server, "run_recipe", lambda *a, **k: pytest.fail("블렌더로 보내면 안 됨"))
    assert "no snapshots yet" in server.restore("x") and "snapshot first" in server.restore("x")


def test_restore_remote_blender_skips_local_check(fake, monkeypatch, tmp_path):
    """다른 컴퓨터의 블렌더면 스냅샷이 그쪽 디스크에 있으니 이 컴퓨터에서 막지 않고, 블렌더에 있는지 물은 뒤 되돌린다."""
    monkeypatch.setenv("BLENDER_FX_HOST", "studio-mac.local")
    asked = []
    monkeypatch.setattr(server.bridge, "run_python", lambda code, timeout=None: asked.append(code) or "True\n")
    server.restore("only_on_the_other_machine")
    assert [r for r, _ in fake] == ["snapshot", "restore"]
    assert "only_on_the_other_machine.blend" in asked[0] and "os.path.exists" in asked[0]


@pytest.mark.parametrize("answer", ["False\n", ""])
def test_restore_remote_missing_name_keeps_before_restore(fake, monkeypatch, answer):
    """원격 블렌더에도 이름이 틀리면 자동 저장(before_restore 덮어쓰기) 전에 멈춘다."""
    monkeypatch.setenv("BLENDER_FX_HOST", "studio-mac.local")
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    monkeypatch.setattr(server.bridge, "run_python", lambda code, timeout=None: answer)
    text = server.restore("typo_name")
    assert fake == [] and text.startswith("Failed: ") and "no snapshot 'typo_name'" in text and "untouched" in text


def test_restore_remote_query_failure_is_reported(fake, monkeypatch):
    monkeypatch.setenv("BLENDER_FX_HOST", "studio-mac.local")

    def down(code, timeout=None):
        raise BlenderError("down")

    monkeypatch.setattr(server.bridge, "run_python", down)
    assert server.restore("x").endswith("down") and fake == []


def test_restore_before_restore_swaps_instead_of_losing_it(fake, monkeypatch, tmp_path):
    """'되돌리기를 되돌리기': before_restore 로 되돌릴 때 지금 장면 저장이 그 파일을 덮어쓰면 기록을 잃는다.
    원본을 .swap 으로 옮겨 그것을 열고, 지금 장면이 새 before_restore 가 된다(두 번 하면 처음으로 돌아옴)."""
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    snaps = tmp_path / "snapshots"
    (snaps / "before_restore.blend").write_bytes(b"S0")
    text = server.restore("before_restore")
    (r1, p1), (r2, p2) = fake
    assert (r1, r2) == ("snapshot", "restore")
    assert p1["path"] == str(snaps / "before_restore.blend")  # 지금 장면(S1)을 저장
    assert p2["path"] == str(snaps / ".swap" / "before_restore.blend")  # 연 것은 옮겨 둔 원본(S0)
    assert (snaps / ".swap" / "before_restore.blend").read_bytes() == b"S0"
    assert text.endswith("The previous state was saved as before_restore.")


def test_restore_before_restore_refused_for_remote_blender(fake, monkeypatch, tmp_path):
    monkeypatch.setenv("BLENDER_FX_HOST", "studio-mac.local")
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    text = server.restore("before_restore")
    assert fake == [] and text.startswith("Failed: ") and "remote Blender" in text


@pytest.mark.parametrize("name", ["before_restore", "before restore"])
def test_snapshot_reserves_before_restore(fake, monkeypatch, name):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    text = server.snapshot(name)
    assert fake == [] and text.startswith("Failed: ") and "another name" in text


@pytest.mark.parametrize("name, want", [("/tmp/x", "tmp_x"), ("../../escape", "escape"), ("a:b?c", "a_b_c"), ("", None)])
def test_save_blend_and_video_names_stay_in_output_folder(fake, tmp_path, name, want):
    """name 이 파일 이름에 그대로 들어가 `/tmp/x`·`../x` 가 출력 폴더 밖으로 나가거나 Windows 에서 깨지던 문제."""
    from pathlib import Path

    server.save_blend(name)
    server.render_video(name=name)
    blend = Path(next(p for r, p in fake if r == "save_blend")["path"])
    video = Path(next(p for r, p in fake if r == "render_video")["out_path"])
    for path, default in ((blend, "fx_scene.blend"), (video, "fx.mp4")):
        assert path.resolve().is_relative_to(tmp_path.resolve()), path
        assert path.name == (f"{want}{path.suffix}" if want else default)


def test_snapshot_says_when_it_replaces_one(fake, monkeypatch, tmp_path):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    assert "replaced" not in server.snapshot("fresh_name")
    _snapshots(tmp_path, "a_b")
    assert "replaced the earlier snapshot 'a_b'" in server.snapshot("a b")  # 이름 정리 뒤 같아짐


@pytest.mark.parametrize("lang,timing,video", [
    ("en", "Timing: frames 1-288, 288 frames = 12s at 24fps.", "frames 1-72 — 72 frames = 3s at 24fps, EEVEE)"),
    ("ko", "타이밍: 프레임 1~288, 288프레임 = 24fps 로 12초.", "프레임 1~72 — 72프레임 = 24fps 로 3초, EEVEE)"),
])
def test_timing_and_video_say_the_length_in_seconds(fake, monkeypatch, lang, timing, video):
    """프레임 수만으로는 영상이 몇 초인지 모른다. 결과 문장에 초로 적는다."""
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    assert _text(server.set_timing()).startswith(timing)
    assert _text(server.render_video()).split("\n")[0].endswith(video)


@pytest.mark.parametrize("first,last,fps,expect", [
    (1, 72, 24, "72 frames = 3s at 24fps"), (1, 100, 30, "100 frames = 3.3s at 30fps"),
    (10, 10, 60, "1 frame = 0.02s at 60fps"), (1, 12, 24, "12 frames = 0.5s at 24fps"), (1, 240, 24, "240 frames = 10s at 24fps"), (1, 48, 0, "48 frames = ?s at 0fps"),
])
def test_length_rounds_to_a_tenth(monkeypatch, first, last, fps, expect):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    assert server._length(first, last, fps) == expect


@pytest.mark.parametrize("lang,moved,expect", [
    ("en", {"frame_end": [250, 500]}, "Note: Blender also moved frame_end from 250 to 500 to follow frame_start. "
                                      "If that is not the length you want, give frame_start and frame_end together."),
    ("ko", {"frame_start": [10, 5]}, "알림: frame_end 에 맞춰 블렌더가 frame_start 도 10 → 5 로 옮겼습니다. "
                                     "원하는 길이가 아니면 frame_start·frame_end 를 함께 주세요."),
])
def test_timing_says_when_blender_moved_the_other_end(fake, monkeypatch, lang, moved, expect):
    """한쪽만 준 값(frame_start=500)으로 블렌더가 다른 쪽을 조용히 옮기면 길이가 1프레임이 되는 것을 사용자가 모른다."""
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    monkeypatch.setitem(RESULTS, "set_timing", {**RESULTS["set_timing"], "moved": moved})
    assert expect in _text(server.set_timing(frame_start=500))
    monkeypatch.setitem(RESULTS, "set_timing", {k: v for k, v in RESULTS["set_timing"].items() if k != "moved"})
    assert "moved" not in _text(server.set_timing(frame_start=500)) and "옮겼" not in _text(server.set_timing())


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_water_result_tells_cell_size_and_finer_resolution(fake, monkeypatch, lang):
    # 성공한 뒤에도 다음 조정 방법: 격자 한 칸 크기와 resolution 을 두 배로 했을 때의 한 칸
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    text = tool_text(server.water(mode="stream"))
    assert "0.125m" in text and "resolution=128" in text and "0.062m" in text
    assert ("격자 한 칸" in text) == (lang == "ko") and ("Grid cell" in text) == (lang == "en")


@pytest.mark.parametrize("now,finer", [(200, 320), (320, None)])
def test_water_detail_respects_the_resolution_limit(monkeypatch, now, finer):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    text = server._water_detail({"cell_m": 0.05, "resolution": now})
    if finer:
        assert f"resolution={finer}" in text
    else:
        assert "resolution=" not in text and "domain_at and domain_size" in text and "320 limit" in text


@pytest.mark.parametrize("lang", ["ko", "en"])
@pytest.mark.parametrize("tool", ["fire", "smoke"])
def test_emit_result_tells_cell_size_and_finer_resolution(fake, monkeypatch, lang, tool):
    # 불·연기가 뭉개져 보일 때 무엇을 올릴지: 격자 한 칸 크기와 resolution 을 두 배로 했을 때의 한 칸
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    text = tool_text(getattr(server, tool)())
    assert "0.100m" in text and "resolution=192" in text and "0.050m" in text
    assert ("격자 한 칸" in text) == (lang == "ko") and ("Grid cell" in text) == (lang == "en")


@pytest.mark.parametrize("now,finer", [(96, 192), (200, 256), (256, None)])
def test_emit_detail_respects_the_resolution_limit(monkeypatch, now, finer):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    text = server._emit_detail({"cell_m": 0.05, "resolution": now})
    if finer:
        assert f"resolution={finer}" in text
    else:
        assert "resolution=" not in text and "256 limit" in text and "radius or power" in text


def test_emit_detail_is_quiet_without_cell_size():
    assert server._emit_detail({"resolution": 64}) == ""


@pytest.mark.parametrize("lang,auto", [("ko", "(자동)"), ("en", "(auto)")])
def test_emit_calls_resolution_auto_only_when_not_given(fake, monkeypatch, lang, auto):
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    assert auto in tool_text(server.fire())
    assert auto not in tool_text(server.fire(resolution=96))


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_explode_result_tells_cell_size_and_finer_resolution(fake, monkeypatch, lang):
    # 기본 48 이라 연기가 뭉개져 보이기 쉬운 도구: 다음 값과, 상한이면 power 가 아니라 radius·대상으로 공간 줄이기
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    text = tool_text(server.explode())
    assert "0.500m" in text and "resolution=96" in text and "0.250m" in text
    assert ("격자 한 칸" in text) == (lang == "ko") and ("Grid cell" in text) == (lang == "en")
    monkeypatch.setitem(RESULTS, "explode", {**RESULTS["explode"], "resolution": 256})
    text = tool_text(server.explode())
    assert "resolution=" not in text and ("radius 를 줄이거나 더 작은 대상" in text or "lower radius or pick a smaller target" in text)
    assert "power" not in text.split("\n")[-1]
