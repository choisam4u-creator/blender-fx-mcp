# 상대 경로를 블렌더에 보내기 전에 이 컴퓨터의 절대 경로로 푸는지. 블렌더 없이 돈다.
# 레시피는 경로를 os.path.expanduser 만 하므로, 그대로 보내면 블렌더의 작업 폴더(Finder 로 켠 Mac 앱은 `/`) 기준이 된다.
import pytest

from blender_fx_mcp import bridge, server
from blender_fx_mcp.bridge import BlenderError


@pytest.fixture
def sent(monkeypatch, tmp_path):
    """run_recipe 에 간 (레시피, 파라미터)를 모으고 거기서 멈춘다. 서버 작업 폴더는 tmp_path/work, 출력 폴더는 tmp_path/out."""
    out, work = tmp_path / "out", tmp_path / "work"
    work.mkdir()
    monkeypatch.setenv("BLENDER_FX_OUT", str(out))
    monkeypatch.delenv("BLENDER_FX_HOST", raising=False)
    monkeypatch.chdir(work)
    calls = []

    def fake(recipe, params, timeout=None):
        calls.append((recipe, params))
        raise BlenderError("reached")

    monkeypatch.setattr(server, "run_recipe", fake)
    return calls, work, out


def test_export_relative_path_goes_to_output_folder(sent):
    calls, _, out = sent
    server.export_model("tower.glb")
    server.export_model("exports/tower.abc")
    assert [p["path"] for _, p in calls] == [str(out / "tower.glb"), str(out / "exports" / "tower.abc")]


def test_export_absolute_and_home_paths(sent, tmp_path, monkeypatch):
    calls, _, _ = sent
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    server.export_model(str(tmp_path / "abs.glb"))
    server.export_model("~/models/a.glb")
    assert [p["path"] for _, p in calls] == [str(tmp_path / "abs.glb"), str(tmp_path / "home" / "models" / "a.glb")]


def test_import_relative_path_found_in_working_folder_then_output_folder(sent):
    calls, work, out = sent
    (work / "models").mkdir()
    (work / "models" / "tower.glb").write_bytes(b"x")
    out.mkdir(parents=True, exist_ok=True)
    (out / "rock.fbx").write_bytes(b"x")
    server.import_model("models/tower.glb")
    server.import_model("rock.fbx")
    assert [p["path"] for _, p in calls] == [str(work / "models" / "tower.glb"), str(out / "rock.fbx")]


@pytest.mark.parametrize("lang,start,tail", [
    ("ko", "실패: 파일이 없습니다: tower.glb. 상대 경로라 이 폴더들에서 찾아봤습니다: ", "전체 경로로 다시 시키세요"),
    ("en", "Failed: File not found: tower.glb. It is a relative path, so these folders were searched: ", "Ask again with the full path"),
])
def test_import_missing_relative_path_stops_before_blender(sent, monkeypatch, lang, start, tail):
    calls, work, out = sent
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    text = server.import_model("tower.glb")
    assert not calls, "찾지 못한 파일을 블렌더로 보냄"
    assert text.startswith(start) and str(work) in text and str(out) in text and tail in text, text


def test_set_look_relative_hdri(sent):
    calls, work, _ = sent
    (work / "sky.hdr").write_bytes(b"x")
    server.set_look("day", hdri="sky.hdr")
    server.set_look("day")
    assert calls[0][1]["hdri"] == str(work / "sky.hdr") and calls[1][1]["hdri"] is None


def test_remote_blender_paths_are_left_alone(sent, monkeypatch):
    """블렌더가 다른 컴퓨터면 경로는 그쪽 디스크 기준이라 서버가 풀거나 막지 않는다."""
    calls, _, _ = sent
    monkeypatch.setenv("BLENDER_FX_HOST", "studio-mac.local")
    assert not bridge.is_local()
    server.import_model("tower.glb")
    server.export_model("tower.glb")
    assert [p["path"] for _, p in calls] == ["tower.glb", "tower.glb"]


def test_import_result_shows_full_path(monkeypatch, tmp_path):
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    monkeypatch.setattr(server, "run_recipe", lambda recipe, params, timeout=None: {
        "name": "Tower", "size_m": [2.0, 2.0, 12.0], "vertices": 50, "faces": 48, "joined": 1, "source": params["path"]})
    monkeypatch.setattr(server, "_render", lambda *a, **k: ({"paths": []}, None))
    monkeypatch.setattr(server, "_preview_note", lambda rend: "")
    (tmp_path / "tower.glb").write_bytes(b"x")
    text = server.import_model(str(tmp_path / "tower.glb"))[0]
    assert text.endswith(f"(joined 1 meshes). File: {tmp_path / 'tower.glb'}"), text
