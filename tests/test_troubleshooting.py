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
    ("bridge.py", "명령 도중 블렌더와의 연결이 끊겼습니다"),
    ("bridge.py", "The connection to Blender dropped during the command"),
    ("bridge.py", "블렌더 응답이 중간에 끊겼습니다"),
    ("bridge.py", "Blender's response was cut off"),
    ("bridge.py", "블렌더 수신기가 알 수 없는 응답을 보냈습니다"),
    ("bridge.py", "The Blender receiver sent an unexpected response"),
    ("bridge.py", "은(는) 쓸 수 없습니다"),
    ("bridge.py", "is not valid ("),
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
    ("server.py", "뿐이라 굽기를 시작하지 않았습니다(물·연기 캐시는 수 GB)."),
    ("server.py", "of disk space is left, so the bake was not started (water and smoke caches take several GB)."),
    ("doctor.py", "출력 폴더 여유 공간"),
    ("doctor.py", "output folder free space"),
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
    bad = ok + [{"id": "connection", "name": "receiver connection", "ok": False, "detail": "refused"}]
    assert bridge.TROUBLESHOOTING_URL not in format_report(ok)
    assert format_report(bad).endswith(f"Help: {bridge.TROUBLESHOOTING_URL}#connection-refused")


def test_readme_links_troubleshooting():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.count("docs/troubleshooting.md") >= 2  # 한국어·영어 절


def test_doctor_client_help_points_to_real_section():
    from blender_fx_mcp import doctor
    assert doctor.CLIENT_HELP.startswith(bridge.TROUBLESHOOTING_URL + "#")
    assert doctor.CLIENT_HELP.split("#", 1)[1] in _anchors(_doc())


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_doctor_client_fix_carries_help_link(monkeypatch, tmp_path, lang):
    from blender_fx_mcp import doctor
    monkeypatch.setenv("BLENDER_FX_LANG", lang)
    monkeypatch.setattr(doctor, "client_configs", lambda: [("Claude Code", str(tmp_path / "none.json"))])
    c = next(x for x in doctor.run_checks() if x["id"] == "client")
    assert not c["ok"] and c["fix"].endswith(doctor.CLIENT_HELP)


def test_client_section_lists_every_config_doctor_reads():
    # doctor 가 찾는 설정 파일 이름이 문서의 표에도 있어야 사용자가 같은 곳을 본다
    from blender_fx_mcp import doctor
    doc = _doc()
    section = doc.split("## Tools not visible in the client", 1)[1].split("\n## ", 1)[0]
    for _client, path in doctor.client_configs():
        assert path.replace("\\", "/").rsplit("/", 1)[-1] in section, path


# 첫 설치 ~ 첫 렌더 단계 수의 상한(2026-10-13: 준비 4단계 + 첫 명령 1). 늘리려면 이 수와 README 를 함께 고치고 PR 에 이유를 적는다
MAX_FIRST_RENDER_STEPS = 5


def _first_render_steps(section: str) -> list[str]:
    """README 절의 `<!-- setup-steps: … -->` 번호 단계들 + 첫 명령(인용문) 단락."""
    block = re.search(r"<!-- setup-steps: [\w, ]+ -->\n(.*?)\n\n", section, re.S).group(1)
    steps = re.split(r"\n(?=\d\. )", block)
    first = re.search(r"\n> [^\n]+\n\n([^\n]+)\n", section[section.index("<!-- setup-steps"):]).group(1)
    return [*steps, first]


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_readme_first_render_steps_are_few_and_each_links_a_fix(lang):
    """README 빠른 시작이 첫 렌더까지 몇 단계인지 세어 상한을 두고, 단계마다 막혔을 때 볼 해결법 절이 실제로 있어야 한다."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split("\n## English\n", 1)[0 if lang == "ko" else 1]
    steps = _first_render_steps(section)
    assert len(steps) <= MAX_FIRST_RENDER_STEPS, f"{lang}: 첫 렌더까지 {len(steps)}단계(상한 {MAX_FIRST_RENDER_STEPS})"
    assert [s[:2] for s in steps[:-1]] == [f"{i}." for i in range(1, len(steps))]
    anchors = _anchors(_doc())
    for step in steps:
        links = re.findall(r"docs/troubleshooting\.md#([\w-]+)", step)
        assert links, f"{lang}: 막혔을 때 볼 해결법 링크가 없는 단계: {step[:60]!r}"
        assert set(links) <= anchors, f"{lang}: 없는 절 {set(links) - anchors}"


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_uv_step_does_not_need_doctor(lang):
    """doctor 도 uv 로 돈다. uv 설치 단계는 doctor 에 기대지 않고 OS 별 명령을 직접 준다."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split("\n## English\n", 1)[0 if lang == "ko" else 1]
    uv_step = _first_render_steps(section)[0]
    assert "brew install uv" in uv_step and "astral.sh/uv/install.sh" in uv_step and "doctor" not in uv_step
    assert 'install.ps1 | iex"' in _doc().split("## uv not found", 1)[1].split("\n## ", 1)[0]


# 서버가 블렌더에 보내기 전에 막는 오류(범위·선택지·순서). 실제로 만든 문장의 값이 아닌 부분이 문서에서 검색돼야 한다
# (문서 첫머리가 "오류 문장 앞부분을 Ctrl+F 로 찾으세요" 이므로)
REJECTIONS = [
    (lambda s: s.check_ranges("set_timing", {"fps": -24}), "은(는) 범위 밖입니다. 가능한 범위:", "is out of range. Allowed:"),
    (lambda s: s.check_choices("destroy", {"material": "rubber"}), "은(는) 쓸 수 없습니다. 가능한 값:", "is not allowed. Choose one of:"),
    (lambda s: s.check_order("set_timing", {"frame_start": 100, "frame_end": 50}),
     "보다 같거나 커야 합니다. 장면은 바꾸지 않았습니다.", "The scene was not changed."),
    (lambda s: s.check_order("set_timing", {"slow_from": 40, "slow_to": 20}), "보다 커야 합니다.", "must be greater than"),
    (lambda s: s.check_finite({"power": float("nan")}), "에 유한한 숫자를 주세요", "must be a finite number"),
    (lambda s: s.check_points({"at": [1, 2]}), "은(는) [x, y, z] 숫자 세 개로 주세요", "as three numbers [x, y, z]"),
]


@pytest.mark.parametrize("call,ko,en", REJECTIONS, ids=[en for _, _, en in REJECTIONS])
def test_server_rejections_are_searchable_in_the_doc(monkeypatch, call, ko, en):
    from blender_fx_mcp import server
    for lang, stem in (("ko", ko), ("en", en)):
        monkeypatch.setenv("BLENDER_FX_LANG", lang)
        with pytest.raises(bridge.BlenderError) as err:
            call(server)
        assert stem in str(err.value), f"서버 문장이 바뀜({lang}): {err.value}"
        assert stem in _doc(), f"troubleshooting.md 에서 찾을 수 없는 서버 오류 문장: {stem}"
    assert "argument-value-rejected" in _anchors(_doc())


def test_every_server_check_has_a_documented_rejection():
    """새 검사 함수(check_*)를 더하면 위 REJECTIONS 에도 문장을 더한다."""
    from blender_fx_mcp import server
    checks = {n for n in dir(server) if n.startswith("check_") and callable(getattr(server, n))}
    src = (ROOT / "tests" / "test_troubleshooting.py").read_text(encoding="utf-8")
    assert checks <= {n for n in checks if f"s.{n}(" in src}, checks


# 문서의 인용 오류 문장(`> …`)마다 그 문구가 실제 소스 문자열에 있는지. 숫자·[…]·'…'·(…)·… 는 자리표시로 보고(괄호 안은 끼워 만든 말이 많음),
# 영문 식별자(at·BLENDER_FX_TIMEOUT·GB·ConnectionResetError)는 f-string 자리표시 {…} 와도 맞는다고 본다.
# 문서를 손으로 맞추다 실제 문장과 어긋나면 사용자가 Ctrl+F 로 못 찾는다(PHRASES 는 고른 문장만 지킨다).
QUOTE_EXEMPT = {
    # 셸이 내는 문장(우리 소스가 아님)
    "zsh: command not found: uvx",
    "'uvx' is not recognized as an internal or external command",
    # t() 로 고른 말(같거나 커야/커야)을 끼워 만드는 문장: REJECTIONS 가 실제로 만든 문장으로 확인한다
    "… 보다 같거나 커야 합니다. 장면은 바꾸지 않았습니다.",
    "… 보다 커야 합니다. 장면은 바꾸지 않았습니다.",
}
_PLACEHOLDER = r"…|\([^()]*\)|\d+(?:\.\d+)?|\[[^\]]*\]|'[^']*'|\bnan\b"


def _quotes():
    return [line[2:].strip() for line in _doc().splitlines() if line.startswith("> ")]


def _fragments(quote):
    """자리표시로 자른 조각 중 검색에 쓸 만한 것(4자 이상)."""
    return [f.strip(" .,:()") for f in re.split(_PLACEHOLDER, quote) if len(f.strip(" .,:()")) >= 4]


def _fragment_regex(fragment):
    parts = re.split(r"([A-Za-z_][A-Za-z0-9_]*)", fragment)
    return "".join(f"(?:{re.escape(p)}|\\{{[^{{}}]*\\}})" if i % 2 else re.escape(p) for i, p in enumerate(parts))


def _source_text():
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(SRC.rglob("*.py")))


def _missing_fragments(quote, source):
    return [f for f in _fragments(quote) if not re.search(_fragment_regex(f), source)]


@pytest.mark.parametrize("quote", [q for q in _quotes() if q not in QUOTE_EXEMPT])
def test_every_quoted_error_exists_in_source(quote):
    assert _fragments(quote), f"자리표시만 있는 인용 문장: {quote!r}"
    missing = _missing_fragments(quote, _source_text())
    assert not missing, f"troubleshooting.md 의 인용 {quote!r} 중 소스에 없는 문구 {missing} — 실제 오류 문장과 맞추세요"


def test_quote_exemptions_are_still_quoted():
    assert QUOTE_EXEMPT <= set(_quotes()), f"문서에서 사라진 예외: {QUOTE_EXEMPT - set(_quotes())}"
    assert len(_quotes()) - len(QUOTE_EXEMPT) >= 40, "훑는 인용이 너무 적음"


def test_quote_checker_catches_a_drifted_sentence():
    # 변이: 문서만 고친 문장은 잡고, 숫자·인자 이름이 들어간 실제 문장은 통과
    source = 'raise FxError(L(f"물 덩어리({a:.2f}m)가 격자 한 칸보다 작습니다.", f"Give {name} as three numbers (got {v!r})"))'
    assert _missing_fragments("물 덩어리(0.10m)가 격자 한 칸보다 작습니다.", source) == []
    assert _missing_fragments("Give at as three numbers (got [1, 2]).", source) == []
    assert _missing_fragments("물 덩어리(0.10m)가 격자 한 칸보다 훨씬 작습니다.", source) == ["가 격자 한 칸보다 훨씬 작습니다"]
    assert _missing_fragments("Give at as four numbers.", source) == ["Give at as four numbers"]
