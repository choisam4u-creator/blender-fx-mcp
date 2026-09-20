# 무료 에셋에 흔한 결함(겹친 덩어리, 맞닿은 덩어리, 떨어진 덩어리)을 만들어 놓고
# 부피를 잃지 않고 조각나는지 검증한다. 이 셋은 실제로 조각이 통째로 사라지던 경우다.
import os

import pytest

from blender_fx_mcp.headless import find_blender, run_steps

BLENDER = find_blender()
pytestmark = pytest.mark.skipif(BLENDER is None, reason="블렌더 실행 파일이 없어 건너뜀")

HEAD = """
import bpy, bmesh
from mathutils import Matrix, Vector

def _add(bm, maker, loc, flip=False):
    tmp = bmesh.new()
    maker(tmp)
    bmesh.ops.translate(tmp, verts=tmp.verts[:], vec=Vector(loc))
    if flip:
        bmesh.ops.reverse_faces(tmp, faces=tmp.faces[:])
    me = bpy.data.meshes.new("tmp")
    tmp.to_mesh(me); tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)

def _finish(bm, name):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    o.location = (0.0, 0.0, 1.5)
    return o
"""

# 바퀴가 몸통에 박혀 있는 수레처럼, 덩어리끼리 겹친 메시
OVERLAP = HEAD + """
bm = bmesh.new()
_add(bm, lambda b: bmesh.ops.create_cube(b, size=1.2), (0, 0, 0))
for sx in (-1, 1):
    for sy in (-1, 1):
        _add(bm, lambda b: bmesh.ops.create_cone(b, cap_ends=True, segments=16,
             radius1=0.3, radius2=0.3, depth=0.16,
             matrix=Matrix.Rotation(1.5707963, 3, 'X')), (sx * 0.5, sy * 0.4, -0.5))
_finish(bm, "Asset")
"""

# 내용물이 통 바닥에 딱 붙어 있는 메시(벽 두께 0.1)
TOUCHING = HEAD + """
bm = bmesh.new()
_add(bm, lambda b: bmesh.ops.create_cube(b, size=1.6), (0, 0, 0))            # 겉
_add(bm, lambda b: bmesh.ops.create_cube(b, size=1.4), (0, 0, 0.1), flip=True)  # 속(빈 공간)
_add(bm, lambda b: bmesh.ops.create_cube(b, size=0.4), (0.2, 0.1, -0.5))     # 바닥에 놓인 내용물
_finish(bm, "Asset")
"""

# 완전히 떨어져 있는 두 덩어리
SEPARATE = HEAD + """
bm = bmesh.new()
_add(bm, lambda b: bmesh.ops.create_cube(b, size=1.0), (-0.9, 0, 0))
_add(bm, lambda b: bmesh.ops.create_cube(b, size=1.0), (0.9, 0, 0))
_finish(bm, "Asset")
"""


def _destroy(extra, pieces=40):
    results = run_steps([
        ("demo_scene", {"style": "plain"}),
        ("destroy", {"target": "Asset", "pieces": pieces, "frames": 10, "dust": "none", "seed": 3}),
    ], blender=BLENDER, extra_code=extra)
    for r in results:
        assert r["ok"], r
    return results[1]


@pytest.mark.parametrize("name,extra", [("겹침", OVERLAP), ("맞닿음", TOUCHING), ("분리", SEPARATE)])
def test_defective_assets_keep_their_volume(name, extra):
    """조각 부피의 합이 원본과 같아야 한다. 겹친 덩어리를 정리하지 않으면 0.69까지 떨어진다."""
    d = _destroy(extra)
    assert d["solid_resolved"] is True, d
    assert 0.98 <= d["volume_kept"] <= 1.02, (name, d)
    assert d["open_chunks"] == 0, (name, d)
    assert d["pieces"] >= 32, (name, d)  # 요청 40개의 80% 이상


def test_many_pieces_do_not_overlap():
    """조각을 아주 잘게 낼 때도 부피가 부풀면 안 된다.

    셀을 자르는 횟수에 상한을 두었을 때는 셀이 덜 잘려 서로 겹치고 1.172 까지 부풀었다.
    """
    d = _destroy(TOUCHING, pieces=200)
    assert d["pieces"] == 200, d
    assert 0.98 <= d["volume_kept"] <= 1.02, d
    assert d["open_chunks"] == 0, d


# 실제로 내려받은 게임 캐릭터(CC0). 이 컴퓨터에만 있어 없으면 건너뛴다.
REAL_CHARACTER = "/Users/sam/Desktop/Gpt_Codex/bonewright/tests/assets/quaternius_adventurer.glb"


@pytest.mark.skipif(not os.path.exists(REAL_CHARACTER), reason="실제 캐릭터 파일이 없어 건너뜀")
def test_real_skinned_character():
    """뼈대에 묶인 진짜 게임 캐릭터가 부피를 지키며 부서져야 한다.

    이 파일에는 보이지 않는 껍데기 구가 섞여 있어, 그냥 합치면 캐릭터가 구가 된다.
    부품끼리 서로 관통하기도 해서 자기교차 처리를 켜지 않으면 보존율이 0.405 로 떨어진다.
    """
    results = run_steps([
        ("import_model", {"path": REAL_CHARACTER, "name": "Hero", "size": 2.0,
                          "parts": ["Adventurer", "Backpack"]}),
        ("inspect_mesh", {"target": "Hero"}),
        ("destroy", {"target": "Hero", "pieces": 50, "frames": 8, "dust": "none"}),
    ], blender=BLENDER)
    for r in results:
        assert r["ok"], r
    imp, ins, d = results

    # 껍데기 구를 빼고 사람 비율이 나와야 한다(가로보다 세로가 훨씬 길다)
    assert imp["dropped_parts"] == ["Icosphere"], imp
    assert imp["size_m"][2] > max(imp["size_m"][0], imp["size_m"][1]) * 2, imp
    assert 0.05 < imp["volume_m3"] < 0.5, imp  # 2m 캐릭터는 0.1㎥ 언저리

    # 팔다리가 벌어진 캐릭터는 볼록할 수 없다
    assert ins["convex_ratio"] is not None and ins["convex_ratio"] < 0.8, ins

    assert 0.97 <= d["volume_kept"] <= 1.03, d
    assert d["pieces"] >= 42, d
    assert any("껍데기" in n or "hollow shell" in n for n in d["notes"]), d


# 같은 면이 두 장 겹쳐 있는 상자
DUP_FACES = HEAD + """
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.2)
bm.faces.ensure_lookup_table()
copies = [bm.verts.new(v.co.copy()) for v in bm.faces[0].verts]
bm.faces.new(copies)
bm.faces.ensure_lookup_table()
copies2 = [bm.verts.new(v.co.copy()) for v in bm.faces[1].verts]
bm.faces.new(list(reversed(copies2)))
_finish(bm, "Asset")
"""

# 5각 이상 n각형으로만 된 통
NGON = HEAD + """
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=9, radius1=0.6, radius2=0.6, depth=1.4)
_finish(bm, "Asset")
"""

# 크기 값이 음수(거울상)인 물건
MIRRORED = HEAD + """
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.2)
bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.3, radius2=0.0, depth=0.8,
                      matrix=Matrix.Translation((0.4, 0, 0.8)))
o = _finish(bm, "Asset")
o.scale = (-1.0, 1.0, 1.0)
"""

# 축마다 크기 값이 다른 물건
SQUASHED = HEAD + """
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
o = _finish(bm, "Asset")
o.scale = (3.0, 0.4, 1.7)
"""


@pytest.mark.parametrize("name,extra", [("겹친면", DUP_FACES), ("n각형", NGON),
                                        ("거울상", MIRRORED), ("납작", SQUASHED)])
def test_more_defect_shapes_keep_volume(name, extra):
    """겹친 면·n각형·음수 크기·비균등 크기에서도 부피가 보존되어야 한다."""
    d = _destroy(extra)
    assert 0.98 <= d["volume_kept"] <= 1.02, (name, d)
    assert d["open_chunks"] == 0, (name, d)
    assert d["pieces"] >= 36, (name, d)


def test_impact_hits_thin_wide_shape():
    """가로로 넓고 얄팍한 모양도 충격체가 실제로 맞아야 한다.

    예전에는 바운딩 박스 면만 보고 조준해서 팔 바깥 허공을 쳤고, 조각이 하나도
    움직이지 않았다(움직인 비율 0.0, 최대 낙하 0.0m).
    """
    extra = HEAD + """
bm = bmesh.new()
tmp = bmesh.new(); bmesh.ops.create_cube(tmp, size=1.0)
bmesh.ops.scale(tmp, verts=tmp.verts[:], vec=(0.3, 0.3, 2.0))
me = bpy.data.meshes.new("t"); tmp.to_mesh(me); tmp.free(); bm.from_mesh(me); bpy.data.meshes.remove(me)
tmp = bmesh.new(); bmesh.ops.create_cube(tmp, size=1.0)
bmesh.ops.scale(tmp, verts=tmp.verts[:], vec=(2.4, 0.25, 0.25))
bmesh.ops.translate(tmp, verts=tmp.verts[:], vec=Vector((0, 0, 0.6)))
me = bpy.data.meshes.new("a"); tmp.to_mesh(me); tmp.free(); bm.from_mesh(me); bpy.data.meshes.remove(me)
_finish(bm, "Asset")
"""
    results = run_steps([
        ("demo_scene", {"style": "plain"}),
        ("destroy", {"target": "Asset", "pieces": 40, "frames": 20, "dust": "none", "seed": 3}),
    ], blender=BLENDER, extra_code=extra)
    for r in results:
        assert r["ok"], r
    d = results[1]
    assert d["moved_ratio"] > 0.3, d
    assert d["max_fall_m"] > 0.1, d
    assert 0.98 <= d["volume_kept"] <= 1.02, d
