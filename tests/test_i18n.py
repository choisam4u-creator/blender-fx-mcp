# 언어 고르기(i18n): BLENDER_FX_LANG > 로캘(LC_ALL → LC_MESSAGES → LANG) > 한국어. 블렌더 없이 돈다.
import pytest

from blender_fx_mcp import i18n


@pytest.mark.parametrize("env, want, source", [
    ({}, "ko", "default"),
    ({"LANG": "ko_KR.UTF-8"}, "ko", "LANG"),
    ({"LANG": "en_US.UTF-8"}, "en", "LANG"),
    ({"LANG": "de_DE.UTF-8"}, "en", "LANG"),            # 한국어가 아니면 영어
    ({"LANG": "C.UTF-8"}, "ko", "default"),             # 컨테이너·창 앱 기본값은 지금처럼 한국어
    ({"LANG": "POSIX"}, "ko", "default"),
    ({"LC_ALL": "ko_KR.UTF-8", "LANG": "en_US.UTF-8"}, "ko", "LC_ALL"),
    ({"LC_MESSAGES": "en_GB", "LANG": "ko_KR.UTF-8"}, "en", "LC_MESSAGES"),
    ({"LC_ALL": "", "LANG": "en_US.UTF-8"}, "en", "LANG"),  # 빈 값은 건너뜀
    ({"LANG": "sr_RS@latin"}, "en", "LANG"),
    ({"BLENDER_FX_LANG": "ko", "LANG": "en_US.UTF-8"}, "ko", "BLENDER_FX_LANG"),  # 명시가 이긴다
    ({"BLENDER_FX_LANG": "en", "LANG": "ko_KR.UTF-8"}, "en", "BLENDER_FX_LANG"),
    ({"BLENDER_FX_LANG": "  ", "LANG": "en_US.UTF-8"}, "en", "LANG"),
])
def test_language_choice(monkeypatch, env, want, source):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    assert i18n.lang().startswith(want) and i18n.is_en() == (want == "en")
    assert i18n.lang_source() == source
    assert i18n.t("가", "a") == ("a" if want == "en" else "가")


def test_locale_reaches_recipes_and_doctor_json(monkeypatch, capsys):
    import json

    from blender_fx_mcp import doctor, server
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    from blender_fx_mcp import bridge
    sent = []

    def capture(code, timeout=None):
        sent.append(code)
        raise bridge.BlenderError("stop")

    monkeypatch.setattr(bridge, "run_python", capture)
    with pytest.raises(bridge.BlenderError):
        server.run_recipe("list_objects", {})
    assert "'_lang': 'en'" in sent[0]  # 레시피 오류 문장도 로캘 언어로
    monkeypatch.setattr(doctor, "run_checks", lambda: [doctor._check("python", True, "3.11", "python")])
    with pytest.raises(SystemExit):
        doctor.main(["--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["lang"] == "en" and data["lang_source"] == "LANG"
