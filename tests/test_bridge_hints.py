# 연결 거부 오류가 원인을 좁혀 다음 한 단계를 말하는지(애드온 없음 / 있음 / 포트 바꿈). 블렌더 없이 돈다.
import pytest

from blender_fx_mcp import bridge
from blender_fx_mcp.bridge import BlenderError

# (언어, 설치 안내 표지, Connect 표지, 포트 표지)
WORDS = {
    "ko": ("Install from Disk", "Connect to MCP server", "BlenderMCP 탭의 Port 도"),
    "en": ("Install from Disk", "Connect to MCP server", "Port in the BlenderMCP tab is also"),
}


@pytest.fixture
def refused(monkeypatch, tmp_path):
    """수신기가 없는 포트로, 애드온 폴더는 빈 집 폴더로 시작한다. addon(True) 로 애드온 파일을 만든다."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(bridge, "ADDON_GLOBS", [str(home / "addons" / "blender_mcp.py")])
    monkeypatch.setattr(bridge, "DEFAULT_PORT", 1)
    monkeypatch.setenv("BLENDER_FX_PORT", "1")
    monkeypatch.delenv("BLENDER_FX_HOST", raising=False)

    def addon(present: bool):
        if present:
            (home / "addons").mkdir(exist_ok=True)
            (home / "addons" / "blender_mcp.py").write_text("# fake\n", encoding="utf-8")

    def message() -> str:
        with pytest.raises(BlenderError) as e:
            bridge.run_python("print(1)", timeout=2)
        return str(e.value)

    return addon, message


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_no_addon_says_install_first(refused, monkeypatch, lang):
    addon, message = refused
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    addon(False)
    msg = message()
    install, connect, port_word = WORDS[lang]
    assert install in msg and bridge.ADDON_URL in msg and connect in msg, msg
    assert msg.index(install) < msg.index(connect), msg  # 설치가 먼저
    assert port_word not in msg, msg
    assert "#connection-refused" in msg


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_addon_present_says_connect(refused, monkeypatch, lang):
    addon, message = refused
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    addon(True)
    msg = message()
    install, connect, port_word = WORDS[lang]
    assert connect in msg and install not in msg and port_word not in msg, msg


@pytest.mark.parametrize("lang", ["ko", "en"])
@pytest.mark.parametrize("present", [True, False])
def test_changed_port_says_match_the_port(refused, monkeypatch, lang, present):
    addon, message = refused
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    monkeypatch.setattr(bridge, "DEFAULT_PORT", 9876)  # BLENDER_FX_PORT=1 은 기본값과 다르다
    addon(present)
    msg = message()
    _, _, port_word = WORDS[lang]
    assert port_word in msg and "9876" in msg and "BLENDER_FX_PORT" in msg, msg


def test_remote_host_does_not_look_at_local_addon_folder(monkeypatch):
    """다른 컴퓨터의 블렌더면 이 컴퓨터에 애드온이 없어도 설치하라고 하지 않는다."""
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    monkeypatch.setenv("BLENDER_FX_HOST", "studio-mac.local")
    monkeypatch.setattr(bridge, "ADDON_GLOBS", [])
    monkeypatch.setattr(bridge, "port", lambda: bridge.DEFAULT_PORT)
    step = bridge.connect_steps()
    assert "Install from Disk" not in step and "Connect to MCP server" in step


def test_doctor_and_bridge_use_the_same_addon_list(monkeypatch, tmp_path):
    """doctor 의 '수신기 애드온 파일' 줄과 연결 거부 안내가 같은 곳을 본다(한쪽만 고쳐 어긋나지 않게)."""
    from blender_fx_mcp import doctor
    f = tmp_path / "blender_mcp.py"
    f.write_text("# fake\n", encoding="utf-8")
    monkeypatch.setattr(bridge, "ADDON_GLOBS", [str(f)])
    monkeypatch.setattr(bridge, "ping", lambda: None)
    monkeypatch.setattr(doctor, "find_blender", lambda: None)
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path / "out"))
    addon = next(c for c in doctor.run_checks() if c["id"] == "addon")
    assert addon["ok"] and addon["detail"] == bridge.addon_files()[0]
    assert not hasattr(doctor, "ADDON_GLOBS")
