# 레시피 "실패 = 장면 그대로" 점검: 대표 잘못된 인자로 레시피를 실패시키고, 장면 요약이 실패 전과 같은지 본다.
# explode·set_timing 에서 "검사 전에 장면부터 바꿔 반쯤 바뀐 채 남는" 결함이 두 번 나와, 레시피마다 한 번에 훑는다.
import json
import os
import subprocess
import tempfile

import pytest

from blender_fx_mcp.headless import CLEAN_SCENE, blender_command, find_blender
from blender_fx_mcp.server import build_code, parse_results

BLENDER = find_blender()
pytestmark = pytest.mark.skipif(BLENDER is None, reason="블렌더 실행 파일이 없어 건너뜀")

# 장면 요약: 오브젝트 이름·역할·모디파이어, 프레임 범위, fps, 렌더 크기. 실패한 호출 앞뒤로 같아야 한다
SUMMARY = '''
import bpy as _bpy, json as _json
_sc = _bpy.context.scene
print("FX_RESULT " + _json.dumps(dict(summary=dict(
    objects=sorted([o.name, str(o.get("fx_role", "")), sorted(m.name for m in o.modifiers),
                    o.rigid_body is not None] for o in _bpy.data.objects),
    frames=[_sc.frame_start, _sc.frame_end], fps=_sc.render.fps,
    size=[_sc.render.resolution_x, _sc.render.resolution_y]))))
'''

# 효과가 이미 있는 장면을 흉내 낸다: 유체는 bpy 에서 굽지 못하므로 역할 표시만 단 빈 객체로 둔다(정리 함수가 지우는 대상)
STAND_INS = '''
import bpy as _bpy
for _role in ("smoke_domain", "blast", "emit_domain", "emit_flow", "liquid_domain", "liquid_flow"):
    _o = _bpy.data.objects.new("Old_" + _role, None)
    _o["fx_role"] = _role
    _bpy.context.scene.collection.objects.link(_o)
'''

# (레시피, 잘못된 인자, 오류에 들어갈 말). 검사 순서상 장면을 바꿀 수 있는 지점 뒤에서 나는 오류를 고른다
BAD_CALLS = [
    ("destroy", {"target": "없는건물"}, "없는건물"),
    ("destroy", {"target": "Edges"}, "면이 없어"),
    ("explode", {"target": "없는건물"}, "없는건물"),
    ("emit", {"target": "없는건물"}, "없는건물"),
    ("water", {"mode": "object"}, "source_object"),
    ("water", {"mode": "object", "source_object": "없는물체"}, "없는물체"),
    ("water", {"obstacles": ["없는벽"]}, "없는벽"),
    ("water", {"size": 0.01, "resolution": 16}, "resolution"),
    ("set_timing", {"frame_start": 90, "frame_end": 30, "fps": 60}, "frame_end(30)"),
    ("set_timing", {"fps": 30, "slow_from": 20, "slow_to": 10}, "slow_to(10)"),
    ("render_video", {"out_path": "OUT/v.mp4", "frame_start": 40, "frame_end": 10, "fps": 60}, "frame_end(10)"),
    ("set_look", {"preset": "없는룩"}, "preset"),
    ("set_look", {"preset": "day", "sky": "없는하늘"}, "sky"),
    ("camera", {"preset": "없는각도"}, "preset"),
    ("particles", {"kind": "없는종류"}, "kind"),
    ("export_model", {"path": "OUT/scene.xyz", "bake_physics": True}, ".xyz"),
    ("import_model", {"path": "OUT/model.glb", "parts": ["없는부품"]}, "parts"),
]


def _run(code):
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        script = f.name
    try:
        proc = subprocess.run(blender_command(BLENDER, script), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=900)
    finally:
        os.unlink(script)
    return parse_results(proc.stdout), proc


def test_failed_recipes_leave_the_scene_unchanged(tmp_path):
    glb = str(tmp_path / "model.glb")
    edges = ('import bpy as _bpy\n_me = _bpy.data.meshes.new("Edges")\n'
             '_me.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0)], [(0, 1), (1, 2)], [])\n'
             '_bpy.context.scene.collection.objects.link(_bpy.data.objects.new("Edges", _me))\n')
    code = CLEAN_SCENE + build_code("demo_scene", {}) + build_code("export_model", {"path": glb}) \
        + build_code("destroy", {"target": "Building", "pieces": 12, "frames": 24}) \
        + build_code("set_timing", {"frame_start": 5, "frame_end": 40, "fps": 24}) + STAND_INS + edges
    for recipe, params, _ in BAD_CALLS:
        params = {k: (v.replace("OUT", str(tmp_path)) if isinstance(v, str) else v) for k, v in params.items()}
        code += SUMMARY + build_code(recipe, params) + SUMMARY
    results, proc = _run(code)
    assert len(results) == 4 + 3 * len(BAD_CALLS), proc.stdout[-2000:] + proc.stderr[-2000:]
    assert all(r["ok"] for r in results[:4]), results[:4]
    rest = results[4:]
    changed = []
    for i, (recipe, params, word) in enumerate(BAD_CALLS):
        before, res, after = rest[3 * i:3 * i + 3]
        if res.get("ok") or word not in res.get("error", ""):
            changed.append((recipe, params, "오류가 기대와 다름", str(res.get("error", res))[:200]))
        if before != after:
            b, a = before["summary"], after["summary"]
            diff = {k: (b[k], a[k]) for k in b if b[k] != a[k]}
            if "objects" in diff:
                bo, ao = {json.dumps(o) for o in b["objects"]}, {json.dumps(o) for o in a["objects"]}
                diff["objects"] = dict(gone=sorted(bo - ao), new=sorted(ao - bo))
            changed.append((recipe, params, diff))
    assert not changed, "실패했는데 장면이 바뀌었거나 오류가 다른 레시피:\n" + "\n".join(map(str, changed))


def test_failed_fluid_recipes_leave_no_cache_folder(tmp_path):
    """물·연기·폭발이 인자·장면 검사에서 실패하면 캐시 폴더도 만들지 않는다(doctor 의 폴더 크기 안내가 빈 폴더를 세지 않게)."""
    code = CLEAN_SCENE + build_code("demo_scene", {})
    calls = [(recipe, params) for recipe, params, _ in BAD_CALLS if recipe in ("water", "emit", "explode")]
    for i, (recipe, params) in enumerate(calls):
        code += build_code(recipe, dict(params, cache_dir=str(tmp_path / f"cache_{i}_{recipe}")))
    results, proc = _run(code)
    assert len(results) == 1 + len(calls), proc.stdout[-2000:] + proc.stderr[-2000:]
    assert all(not r["ok"] for r in results[1:]), results[1:]
    assert sorted(p.name for p in tmp_path.iterdir()) == [], "실패한 호출이 남긴 캐시 폴더"
