# 정리 도구(clear_snapshots·clear_caches)가 무엇을 지웠고 디스크가 얼마나 남았는지 말하는지. 블렌더 없이 돈다.
import os
import time

import pytest

from blender_fx_mcp import bridge, disk, server


@pytest.fixture
def snaps(monkeypatch, tmp_path):
    """이름 → 저장 시각(오래된 것이 작은 수)으로 스냅샷 파일을 만든다."""
    monkeypatch.setenv("BLENDER_FX_OUT", str(tmp_path))
    monkeypatch.delenv("BLENDER_FX_HOST", raising=False)
    monkeypatch.setattr(disk, "free_bytes", lambda p: 20 * 1024**3)
    d = tmp_path / "snapshots"
    d.mkdir()
    now = time.time()

    def make(*names, size=1_000_000):
        for i, n in enumerate(names):
            f = d / f"{n}.blend"
            f.write_bytes(b"0" * size)
            os.utime(f, (now - 1000 + i, now - 1000 + i))
        return d

    return make


def test_clear_snapshots_keeps_newest_and_before_restore(snaps, monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "ko")
    d = snaps("before_restore", "s1", "s2", "s3", "s4")  # before_restore 가 가장 오래됐어도 남는다
    (d / "s1.blend1").write_bytes(b"0" * 500_000)  # 같은 이름으로 다시 저장할 때 블렌더가 남기는 이전 판
    text = server.clear_snapshots(keep=2)
    assert sorted(p.name for p in d.iterdir()) == ["before_restore.blend", "s3.blend", "s4.blend"]
    assert text.startswith("스냅샷 2개 지움(2.5MB): s2, s1. 남긴 것: s4, s3"), text
    assert "출력 폴더 디스크 여유: 20.0GB." in text


def test_clear_snapshots_english_and_keep_zero(snaps, monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    d = snaps("before_restore", "a", "b")
    text = server.clear_snapshots(keep=0)
    assert [p.name for p in d.iterdir()] == ["before_restore.blend"]
    assert text.startswith("Deleted 2 snapshots (2.0MB): b, a. Kept: none (+ before_restore is always kept)."), text


def test_clear_snapshots_nothing_to_delete(snaps, monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    d = snaps("a", "b")
    assert server.clear_snapshots().startswith("No snapshots to delete (2 saved, keeping up to 5).")
    assert len(list(d.iterdir())) == 2


@pytest.mark.parametrize("keep", [-1, 1001, 2.5, True, "3"])
def test_clear_snapshots_rejects_bad_keep_and_deletes_nothing(snaps, monkeypatch, keep):
    monkeypatch.setenv("BLENDER_FX_LANG", "ko")
    d = snaps("a", "b")
    text = server.clear_snapshots(keep=keep)
    assert text.startswith("실패: keep=") and "0~1000 사이 정수로 다시 시키세요" in text, text
    assert len(list(d.iterdir())) == 2


def test_list_snapshots_total_and_cleanup_hint(snaps, monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    snaps("a", "b")
    text = server.list_snapshots()
    assert "\n2 in total, 2.0MB." in text and "clear_snapshots" not in text, text
    snaps("c", "d", "e", "f")
    text = server.list_snapshots()
    assert "6 in total, 6.0MB. Delete old ones with clear_snapshots (keeps the newest 5 and before_restore)." in text


def _fake_clear(monkeypatch, freed_mb):
    monkeypatch.setattr(server, "run_recipe", lambda recipe, params, timeout=None:
                        {"freed_mb": freed_mb, "fluid_domains": 1, "dirs": []})


def test_clear_caches_reports_freed_and_free_space(snaps, monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "ko")
    _fake_clear(monkeypatch, 2048.0)
    assert server.clear_caches() == "캐시 정리: 2048.0MB 비움, 유체 도메인 1개 초기화. 출력 폴더 디스크 여유: 20.0GB."
    _fake_clear(monkeypatch, 0)
    assert server.clear_caches().startswith("캐시 정리: 캐시 폴더에 지울 파일이 없었습니다(유체 도메인 1개 초기화).")


def test_clear_caches_says_what_next_when_still_low(snaps, monkeypatch):
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    monkeypatch.setattr(disk, "free_bytes", lambda p: 300 * 1024**2)
    _fake_clear(monkeypatch, 10.0)
    text = server.clear_caches()
    assert "Free disk space for the output folder: 0.3GB, still not enough to bake (1.0GB needed)." in text
    assert "clear_snapshots" in text and "BLENDER_FX_OUT" in text, text


def test_clear_caches_no_disk_line_for_remote_blender(snaps, monkeypatch):
    """블렌더가 다른 컴퓨터면 이 컴퓨터의 디스크 여유는 상관없으니 붙이지 않는다."""
    monkeypatch.setenv("BLENDER_FX_LANG", "en")
    monkeypatch.setenv("BLENDER_FX_HOST", "studio-mac.local")
    assert not bridge.is_local()
    _fake_clear(monkeypatch, 10.0)
    assert server.clear_caches() == "Caches cleared: freed 10.0MB, reset 1 fluid domains."
