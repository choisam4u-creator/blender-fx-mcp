# 목록형 도구(list_objects·inspect_mesh·list_snapshots)와 doctor 가 문장과 함께 구조화 값(structuredContent)을 주는지,
# 공식 클라이언트(메모리 연결)로 확인한다. 블렌더 없이 돈다.
import json

import anyio
import pytest
from mcp import Client

from blender_fx_mcp import bridge, server

SCENE = dict(objects=[dict(name="Building", size_m=[4.0, 4.0, 9.0], location=[0.0, 0.0, 0.0], fx_role=None, hidden=False)],
             chunk_count=0, camera="Camera", frame_range=[1, 72], blender="5.0.1")
MESH = dict(target="Building", closed=True, volume_m3=144.0, faces=12)


async def _call(name, args=None):
    async with Client(server.mcp) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        return await client.call_tool(name, args or {}), tools[name]


def _receiver(res):
    return lambda code, timeout=None: "FX_RESULT " + json.dumps(dict(ok=True, **res))


@pytest.mark.parametrize(("name", "args", "res"), [
    ("list_objects", {}, SCENE),
    ("inspect_mesh", {"target": "Building"}, MESH),
])
def test_scene_tools_return_structured_content(monkeypatch, tmp_path, name, args, res):
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setattr(bridge, "run_python", _receiver(res))
    result, tool = anyio.run(_call, name, args)
    assert not result.is_error, result
    data = result.structured_content
    assert {k: data[k] for k in res} == res, data  # AI 가 문장을 다시 파싱하지 않고 이름·크기를 집는다
    assert json.loads(result.content[0].text) == data  # 구조화 값을 못 읽는 클라이언트도 같은 내용을 본다
    assert tool.output_schema is None  # 결과 모양은 레시피가 정한다. {"result": 문자열} 같은 껍데기 스키마를 내걸지 않는다


def test_list_snapshots_structured(monkeypatch, tmp_path):
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    for n in ("a", "b"):
        (server.snapshot_dir() / f"{n}.blend").write_bytes(b"x" * 1_000_000)
    result, _ = anyio.run(_call, "list_snapshots")
    data = result.structured_content
    assert [s["name"] for s in data["snapshots"]] == ["a", "b"], data
    assert data["snapshots"][0]["size_mb"] == 1.0 and data["total_mb"] == 2.0, data
    assert data["summary"] == result.content[0].text and data["summary"].startswith("Snapshots:\n- a (1.0MB, ")


def test_failure_stays_plain_text(monkeypatch, tmp_path):
    """블렌더가 꺼져 있으면 다른 도구처럼 실패 문장만(구조화 값 없음) 돌려준다."""
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", "en")

    def down(code, timeout=None):
        raise bridge.BlenderError("Blender is not running")

    monkeypatch.setattr(bridge, "run_python", down)
    result, _ = anyio.run(_call, "list_objects")
    assert result.content[0].text == "Failed: Blender is not running"
    assert result.structured_content is None


def test_empty_snapshot_list_is_structured_too(monkeypatch, tmp_path):
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    result, _ = anyio.run(_call, "list_snapshots")
    assert result.content[0].text.startswith("No snapshots yet")
    assert result.structured_content["snapshots"] == [] and result.structured_content["total_mb"] == 0.0


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_doctor_structured_names_failed_checks_and_fixes(monkeypatch, tmp_path, lang):
    """블렌더 수신기가 꺼져 있으면 구조화 값의 failed 에 connection 이, 그 항목의 fix 에 다음 할 일이 있다."""
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    monkeypatch.setenv("BLENDER_FX_NO_UPDATE_CHECK", "1")

    def down():
        raise bridge.BlenderError("refused")

    monkeypatch.setattr(bridge, "ping", down)
    result, tool = anyio.run(_call, "doctor")
    data = result.structured_content
    assert data["summary"] == result.content[0].text
    assert data["ok"] is False and "connection" in data["failed"], data
    rows = {c["id"]: c for c in data["checks"]}
    assert "client" not in rows  # 부른 클라이언트는 이미 연결돼 있다
    conn = rows["connection"]
    assert conn["ok"] is False and conn["fix"] and conn["fix"] in data["summary"]
    assert all(c["fix"] == "" for c in data["checks"] if c["ok"])  # 정상 항목엔 할 일이 없다
    assert data["help"].startswith("https://")
    assert set(data["failed"]) == {c["id"] for c in data["checks"] if not c["ok"] and not c["optional"]}
    assert tool.output_schema is None
    assert data["last_error"] is None  # 이 시험 전에는 실패한 도구가 없음


def test_doctor_structured_carries_last_error(monkeypatch, tmp_path):
    """도구가 실패한 뒤 doctor 를 부르면 구조화 값 last_error 에 그 도구·첫 줄이 있어 AI 가 신고 초안에 바로 쓴다."""
    from blender_fx_mcp import server
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_NO_UPDATE_CHECK", "1")
    monkeypatch.setattr(bridge, "ping", lambda: None)
    server.restore("nope")
    result, _tool = anyio.run(_call, "doctor")
    err = result.structured_content["last_error"]
    assert err["tool"] == "restore" and "nope" in err["message"] and err["time"]
