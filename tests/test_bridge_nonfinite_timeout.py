"""대기시간의 무한대는 연결 전에 알리고 유한한 설정은 그대로 쓴다."""
import pytest

from blender_fx_mcp import bridge, server
from blender_fx_mcp.bridge import BlenderError


@pytest.mark.parametrize("value", ["inf", "+Infinity", "1e999"])
@pytest.mark.parametrize("lang, prefix", [("ko", "실패: "), ("en", "Failed: ")])
def test_nonfinite_timeout_is_rejected_before_connect(monkeypatch, tmp_path, value, lang, prefix):
    monkeypatch.setenv("BLENDER_FX_TIMEOUT", value)
    monkeypatch.setenv("BLENDER_FX_PORT", "9876")
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setattr(bridge.socket, "create_connection", lambda *a, **k: pytest.fail("연결하면 안 됨"))

    with pytest.raises(BlenderError, match="BLENDER_FX_TIMEOUT") as error:
        bridge.check_env()
    assert repr(value) in str(error.value)
    assert "MCP" in str(error.value)
    assert bridge.default_timeout() == 600.0
    with pytest.raises(BlenderError, match="BLENDER_FX_TIMEOUT"):
        bridge.send_command("ping")
    message = server.list_objects()
    assert message.startswith(prefix) and "BLENDER_FX_TIMEOUT" in message


@pytest.mark.parametrize("value, expected", [
    (None, 600.0), ("", 600.0), ("1", 1.0), ("1.5", 1.5),
    ("600", 600.0), ("7200", 7200.0), ("1e6", 1e6),
])
def test_finite_timeout_and_defaults_are_preserved(monkeypatch, value, expected):
    monkeypatch.setenv("BLENDER_FX_PORT", "9876")
    if value is None:
        monkeypatch.delenv("BLENDER_FX_TIMEOUT", raising=False)
    else:
        monkeypatch.setenv("BLENDER_FX_TIMEOUT", value)
    bridge.check_env()
    assert bridge.default_timeout() == expected


@pytest.mark.parametrize("value", [1, 65535])
def test_port_boundaries_are_preserved(monkeypatch, value):
    monkeypatch.setenv("BLENDER_FX_TIMEOUT", "600")
    monkeypatch.setenv("BLENDER_FX_PORT", str(value))
    bridge.check_env()
    assert bridge.port() == value
