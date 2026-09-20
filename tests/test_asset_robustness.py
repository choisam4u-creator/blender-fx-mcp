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
