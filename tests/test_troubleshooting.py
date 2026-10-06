# docs/troubleshooting.md 가 실제 오류 문장과 어긋나지 않는지 점검한다. 블렌더 없이 돈다.
import re
from pathlib import Path

import pytest

from blender_fx_mcp import bridge

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "troubleshooting.md"
SRC = ROOT / "src" / "blender_fx_mcp"

# (오류를 내는 파일, 문서에도 그대로 있어야 하는 문장 조각). 소스 문장을 바꾸면 문서도 같이 고친다
PHRASES = [
    ("bridge.py", "블렌더에 연결할 수 없습니다"),
    ("bridge.py", "Cannot connect to Blender"),
    ("bridge.py", "안에 응답하지 않았습니다(시간 초과)"),
    ("bridge.py", "Blender did not respond within"),
    ("bridge.py", "블렌더가 빈 응답을 보냈습니다."),
    ("bridge.py", "Blender sent an empty response."),
    ("bridge.py", "블렌더 오류: "),
    ("bridge.py", "Blender error: "),
    ("bridge.py", "BLENDER_FX_TIMEOUT"),
    ("server.py", "빠른 미리보기라 하늘·연기·물은 보이지 않습니다."),
    ("server.py", "Fast preview: sky, smoke and water are not shown."),
    ("recipes/water.py", "보다 작아 물이 생기지 않습니다."),
    ("recipes/water.py", "so no liquid forms."),
    ("recipes/water.py", "물 굽기 결과가 비어 있습니다."),
    ("recipes/water.py", "The liquid bake produced nothing."),
    ("recipes/emit.py", "연기 굽기 결과가 비어 있습니다."),
    ("recipes/emit.py", "The smoke bake produced nothing."),
    ("recipes/render.py", "카메라도 오브젝트도 없어 렌더할 수 없습니다."),
    ("recipes/render.py", "There is no camera and no object, so nothing can be rendered."),
    ("recipes/destroy.py", "조각을 하나도 만들지 못했습니다."),
    ("recipes/destroy.py", "No chunks could be created."),
    ("recipes/import_model.py", "파일이 없습니다: "),
    ("recipes/import_model.py", "File not found: "),
    ("recipes/render_video.py", "영상 파일이 만들어지지 않았습니다."),
    ("recipes/render_video.py", "No video file was produced."),
]


def _doc():
    return DOC.read_text(encoding="utf-8")


def _anchors(text):
    """GitHub 가 ## 제목에서 만드는 앵커(소문자, 문장부호 빼기, 빈칸 → -)."""
    out = set()
    for title in re.findall(r"^#{1,6} (.+)$", text, re.M):
        a = re.sub(r"[^\w\- ]", "", title.strip().lower())
        out.add(a.replace(" ", "-"))
    return out


@pytest.mark.parametrize("src,phrase", PHRASES, ids=[p for _, p in PHRASES])
def test_error_phrase_in_source_and_doc(src, phrase):
    assert phrase in (SRC / src).read_text(encoding="utf-8"), f"{src} 에 더는 없는 문장: {phrase}"
    assert phrase in _doc(), f"troubleshooting.md 에 없는 오류 문장: {phrase}"


def test_every_bridge_error_is_documented():
    # bridge.py 의 모든 BlenderError 문장(한/영 첫머리)이 PHRASES 에 들어 있어야 한다
    src = (SRC / "bridge.py").read_text(encoding="utf-8")
    raises = src.count("raise BlenderError(")
    covered = {p for f, p in PHRASES if f == "bridge.py" and p != "BLENDER_FX_TIMEOUT"}
    assert len(covered) == 2 * raises


def test_links_in_error_messages_point_to_real_sections():
    anchors = _anchors(_doc())
    srcs = (SRC / "bridge.py").read_text(encoding="utf-8")
    linked = re.findall(r"TROUBLESHOOTING_URL\}#([^\"\s]+)", srcs)
    assert linked, "bridge.py 오류 문장에 문서 링크가 없음"
    for a in linked:
        assert a in anchors, f"문서에 없는 절: #{a}"


def test_url_points_to_this_file():
    assert bridge.TROUBLESHOOTING_URL.endswith("/blob/main/docs/troubleshooting.md")
    assert bridge.TROUBLESHOOTING_URL.startswith("https://github.com/choisam4u-creator/blender-fx-mcp/")


@pytest.mark.parametrize("lang,help_word", [("ko", "해결법:"), ("en", "Help:")])
def test_connection_error_carries_link(monkeypatch, lang, help_word):
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    monkeypatch.setenv("BLENDER_FX_PORT", "1")  # 아무도 안 듣는 포트

    def refuse(*a, **k):
        raise ConnectionRefusedError()

    monkeypatch.setattr(bridge.socket, "create_connection", refuse)
    with pytest.raises(bridge.BlenderError) as e:
        bridge.ping()
    assert f"{help_word} {bridge.TROUBLESHOOTING_URL}#connection-refused" in str(e.value)


def test_doctor_report_links_doc_only_when_something_is_wrong(monkeypatch):
    from blender_fx_mcp.doctor import format_report
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    ok = [{"name": "python", "ok": True, "detail": "3.13"}]
    bad = ok + [{"name": "receiver connection", "ok": False, "detail": "refused"}]
    assert bridge.TROUBLESHOOTING_URL not in format_report(ok)
    assert format_report(bad).endswith(f"Help: {bridge.TROUBLESHOOTING_URL}")


def test_readme_links_troubleshooting():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.count("docs/troubleshooting.md") >= 2  # 한국어·영어 절
