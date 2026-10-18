# 렌더 결과를 여는 OS별 명령 줄. 블렌더 없이 돈다.
import shlex

import pytest

from blender_fx_mcp import server
from blender_fx_mcp.opener import open_command, open_line


@pytest.mark.parametrize("platform, expect", [
    ("darwin", "open '/Users/x/출력 폴더/a.png'"),
    ("linux", "xdg-open '/Users/x/출력 폴더/a.png'"),
    ("win32", 'start "" "/Users/x/출력 폴더/a.png"'),
])
def test_open_command_quotes_path_per_os(platform, expect):
    assert open_command("/Users/x/출력 폴더/a.png", platform) == expect


def test_open_command_posix_quote_survives_shell_specials():
    """따옴표·$ 가 든 경로도 셸이 한 인자로 읽는다."""
    path = "/tmp/it's $HOME/v.mp4"
    assert shlex.split(open_command(path, "darwin")) == ["open", path]


def test_open_line_is_bilingual(monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "ko")
    assert open_line("/o/a.mp4", "darwin") == "\n결과 보기: open /o/a.mp4"
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    assert open_line("/o/a.mp4", "linux") == "\nOpen it: xdg-open /o/a.mp4"


@pytest.fixture
def fake(monkeypatch, tmp_path):
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    results = {
        "render": dict(engine="BLENDER_EEVEE", size=[640, 360], frames=[1], paths=[]),
        "render_video": dict(path=str(tmp_path / "v" / "fx.mp4"), size_bytes=2_000_000, size=[1280, 720],
                             frames=[1, 72], fps=24, engine="BLENDER_EEVEE"),
    }
    monkeypatch.setattr(server, "run_recipe", lambda name, params, timeout=None: results[name])
    return results


def test_render_preview_ends_with_open_folder_line(fake):
    text = server.render_preview(frames=[1])[0]
    folder = text.split("→ ", 1)[1].split("\n")[0].strip()
    assert text.endswith(f"\nOpen it: {open_command(folder)}")


def test_render_video_ends_with_open_file_line(fake):
    assert server.render_video().endswith(f"\nOpen it: {open_command(fake['render_video']['path'])}")


def test_remote_blender_gets_no_open_line(fake, monkeypatch):
    """블렌더가 다른 컴퓨터면 경로가 그쪽이라 이 컴퓨터에서 여는 명령을 주지 않는다."""
    monkeypatch.setenv("BLENDER_FX_HOST", "10.0.0.5")
    assert "Open it:" not in server.render_video()
    assert "Open it:" not in server.render_preview(frames=[1])[0]
