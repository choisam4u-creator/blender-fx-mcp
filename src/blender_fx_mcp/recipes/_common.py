# 공용 도우미. 서버가 모든 레시피 앞에 `PARAMS = {...}` 한 줄과 이 파일을 붙여 블렌더로 보낸다.
# 블렌더 안에서 실행되므로 bpy 를 바로 쓴다. 외부 패키지는 쓰지 않는다.
import bpy
import bmesh
import json
import math
import os
import random
import traceback
import shutil
from mathutils import Vector, Matrix, Euler

FX_TAG = "fx_role"  # 이 도구가 만든 오브젝트 표시 (chunk / impactor / ground / camera / light)


class FxError(Exception):
    """사용자에게 그대로 보여줄 오류 (언어는 L() 로 고른다)"""


def L(ko, en):
    """메시지 언어 선택. 서버가 PARAMS['_lang'] 로 알려 준다 (ko 기본)."""
    try:
        return en if PARAMS.get("_lang") == "en" else ko
    except NameError:
        return ko


def emit_result(**data):
    # 서버는 표준 출력에서 이 줄을 찾아 결과로 쓴다
    print("FX_RESULT " + json.dumps(data, ensure_ascii=False))


def run_guarded(fn):
    try:
        result = fn()
        emit_result(ok=True, **(result or {}))
    except FxError as e:
        emit_result(ok=False, error=str(e))
    except Exception as e:  # 예상 못 한 오류: 원인 추적을 그대로 넘긴다
        emit_result(ok=False, error=f"{type(e).__name__}: {e}", traceback=traceback.format_exc()[-1500:])


def scene():
    return bpy.context.scene


def view_layer_update():
    bpy.context.view_layer.update()


def mesh_objects():
    return [o for o in bpy.data.objects if o.type == "MESH"]


def get_target(name):
    o = bpy.data.objects.get(name) if name else None
    if o is None or o.type != "MESH":
        names = [m.name for m in mesh_objects() if not m.get(FX_TAG)]
        raise FxError(L(f"'{name}' 이름의 메시 오브젝트가 없습니다. 지금 있는 메시: {names}",
                        f"No mesh object named '{name}'. Available meshes: {names}"))
    return o


def world_bbox(obj):
    # bound_box 는 깊이 그래프 평가 전엔 틀릴 수 있어 메시는 정점으로 직접 잰다
    if obj.type == "MESH" and len(obj.data.vertices) > 0:
        pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    else:
        pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def get_collection(name):
    sc = scene()
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
    if c.name not in [ch.name for ch in sc.collection.children_recursive]:
        sc.collection.children.link(c)
    return c


def link(obj, coll=None):
    (coll or scene().collection).objects.link(obj)


def new_mesh_object(name, bm, matrix=None, tag=None, coll=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    me.update()
    o = bpy.data.objects.new(name, me)
    if matrix is not None:
        o.matrix_world = matrix
    if tag:
        o[FX_TAG] = tag
    link(o, coll)
    return o


def remove_object(o):
    data = o.data
    bpy.data.objects.remove(o, do_unlink=True)
    if isinstance(data, bpy.types.Mesh) and data.users == 0:
        bpy.data.meshes.remove(data)


def unhide(o):
    o.hide_render = False
    o.hide_viewport = False
    try:
        o.hide_set(False)
    except Exception:
        pass


FX_CLEANUP_ROLES = (
    "chunk", "impactor", "dust", "smoke_domain", "smoke_flow", "blast", "liquid_domain", "liquid_flow",
    "emit_domain", "emit_flow", "emit_obstacle", "particles", "wind", "turbulence", "ocean", "flag", "pole", "glue",
    "cell",
)


def strip_fx_modifiers(obj):
    """이 도구가 사용자 오브젝트에 붙인 모디파이어(FX_ 로 시작)를 뗀다."""
    n = 0
    for m in list(obj.modifiers):
        if m.name.startswith("FX_"):
            obj.modifiers.remove(m)
            n += 1
    return n


def cleanup_fx(target_name=None):
    """이 도구가 만든 것을 지우고 원본을 되살린다. target_name 을 주면 그 대상의 조각만 지운다."""
    removed = 0
    for o in list(bpy.data.objects):
        role = o.get(FX_TAG)
        if role not in FX_CLEANUP_ROLES:
            continue
        if role == "chunk" and target_name and o.get("fx_chunk_of") != target_name:
            continue
        remove_object(o)
        removed += 1
    if target_name:
        t = bpy.data.objects.get(target_name)
        if t is not None:
            unhide(t)
            strip_fx_modifiers(t)
    else:
        for o in bpy.data.objects:
            strip_fx_modifiers(o)
    # 주인 없는 먼지 파티클 설정 정리
    for ps in list(bpy.data.particles):
        if ps.users == 0:
            bpy.data.particles.remove(ps)
    view_layer_update()
    return removed


def ensure_rbw():
    sc = scene()
    if sc.rigidbody_world is None:
        with bpy.context.temp_override(scene=sc):
            bpy.ops.rigidbody.world_add()
    return sc.rigidbody_world


def add_rigid_bodies(objs, body_type="ACTIVE"):
    todo = [o for o in objs if o.rigid_body is None]
    if not todo:
        return
    ensure_rbw()
    sc = scene()
    vl = bpy.context.view_layer
    try:
        with bpy.context.temp_override(
            scene=sc, view_layer=vl, selected_objects=todo, selected_editable_objects=todo,
            active_object=todo[0], object=todo[0],
        ):
            bpy.ops.rigidbody.objects_add(type=body_type)
    except Exception:
        # 한꺼번에 안 되면 하나씩
        for o in todo:
            with bpy.context.temp_override(scene=sc, view_layer=vl, active_object=o, object=o, selected_objects=[o]):
                bpy.ops.rigidbody.object_add(type=body_type)
    missing = [o.name for o in todo if o.rigid_body is None]
    if missing:
        raise FxError(L(f"리지드바디(물리)를 붙이지 못했습니다: {missing[:5]}",
                        f"Could not add rigid body physics to: {missing[:5]}"))


# ---------- 먼지 파티클 ----------

def ensure_dust_bit():
    """먼지 알갱이로 쓸 작은 공. 카메라 밖(땅 밑 깊숙이) 두고 파티클이 복제해 쓴다."""
    o = next((x for x in bpy.data.objects if x.get(FX_TAG) == "dust"), None)
    if o is not None:
        return o
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    o = new_mesh_object("FX_DustBit", bm, Matrix.Translation((0.0, 0.0, -500.0)), tag="dust")
    bm.free()
    o.data.materials.append(simple_material("FX_Dust", (0.72, 0.70, 0.66), roughness=1.0))
    return o


def add_dust(chunks, per_chunk, f_impact, size_ref, gravity=0.03, drag=0.35, size_scale=0.012, lifetime=45):
    """조각마다 먼지 파티클을 붙인다. 충돌 직후 잠깐 뿜어져 나와 천천히 가라앉는다."""
    if per_chunk <= 0 or not chunks:
        return 0
    bit = ensure_dust_bit()
    ps = bpy.data.particles.get("FX_DustSettings") or bpy.data.particles.new("FX_DustSettings")
    ps.type = "EMITTER"
    ps.count = per_chunk
    ps.frame_start = max(1, f_impact - 2)
    ps.frame_end = f_impact + 24
    ps.lifetime = lifetime
    ps.lifetime_random = 0.5
    ps.emit_from = "FACE"
    ps.distribution = "RAND"
    ps.use_emit_random = True
    ps.physics_type = "NEWTON"
    ps.normal_factor = 0.8
    ps.object_factor = 0.8  # 조각의 속도를 이어받는다
    ps.factor_random = 0.6
    ps.drag_factor = drag
    ps.effector_weights.gravity = gravity  # 먼지는 천천히 가라앉는다
    ps.render_type = "OBJECT"
    ps.instance_object = bit
    ps.particle_size = max(0.03, size_ref * size_scale)
    ps.size_random = 0.8
    for i, o in enumerate(chunks):
        mod = o.modifiers.new("FX_Dust", "PARTICLE_SYSTEM")
        mod.particle_system.settings = ps
        mod.particle_system.seed = i + 1
    for orphan in list(bpy.data.particles):
        if orphan.users == 0:
            bpy.data.particles.remove(orphan)
    return per_chunk * len(chunks)


# ---------- 메시 진단·수리 ----------

def decimate_bm(bm, matrix, target_faces):
    """면이 너무 많은 bmesh 를 줄인다. 임시 오브젝트에 Decimate 를 걸어 평가한다."""
    faces = len(bm.faces)
    if not target_faces or faces <= target_faces:
        return bm, 1.0
    ratio = target_faces / float(faces)
    me = bpy.data.meshes.new("FX_DecimateTmp")
    bm.to_mesh(me)
    tmp = bpy.data.objects.new("FX_DecimateTmp", me)
    tmp[FX_TAG] = "cell"
    tmp.matrix_world = matrix.copy()
    link(tmp)
    d = tmp.modifiers.new("FX_Decimate", "DECIMATE")
    d.ratio = ratio
    view_layer_update()
    dg = bpy.context.evaluated_depsgraph_get()
    out = bmesh.new()
    out.from_object(tmp, dg)
    remove_object(tmp)
    view_layer_update()
    bm.free()
    return out, ratio


def bm_from_object(obj, decimate_to=0, repair=True):
    """모디파이어까지 적용된 메시를 bmesh 로 읽는다.
    먼저 겹친 꼭짓점을 붙이고(수리) 그다음에 면 수를 줄인다. 순서가 반대면 결과가 망가진다."""
    view_layer_update()
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    bm.from_object(obj, dg)
    info = None
    if repair and bm.verts:
        info = repair_bm(bm)
    bm, ratio = decimate_bm(bm, obj.matrix_world, decimate_to)
    if ratio < 1.0 and repair:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm, ratio, info


def mesh_health(bm):
    open_edges = [e for e in bm.edges if len(e.link_faces) < 2]
    bad_edges = [e for e in bm.edges if len(e.link_faces) > 2]
    try:
        vol = abs(bm.calc_volume(signed=False))
    except Exception:
        vol = 0.0
    return dict(verts=len(bm.verts), faces=len(bm.faces), open_edges=len(open_edges),
                non_manifold_edges=len(bad_edges), closed=len(open_edges) == 0 and len(bad_edges) == 0,
                volume_m3=round(vol, 4))


def object_health(obj):
    """오브젝트의 메시 상태를 본다. mesh_health 와 같은 값을 돌려준다."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    h = mesh_health(bm)
    bm.free()
    return h


def nearly_closed(health):
    """완전히 닫히진 않았지만 '거의' 닫힌 메시인지. 게임용 캐릭터처럼 면 1만 개에
    구멍이 10개뿐인 경우가 많은데, 이런 것까지 '열린 메시'로 취급하면 씨앗을 물체 안에
    못 놓아서 요청한 조각 수가 안 나온다."""
    if health["closed"]:
        return True
    bad = health["open_edges"] + health["non_manifold_edges"]
    return bad <= max(4, int(health["faces"] * 0.01))


def drop_duplicate_faces(bm):
    """같은 꼭짓점으로 이루어진 면이 두 장 겹쳐 있으면 한 장을 지운다.

    게임용 모델은 가방·옷 같은 부품을 몸통에 겹쳐 붙여 파는 일이 흔하다. 그러면 모서리
    하나에 면이 3장 이상 붙어(비다양체) 조각내기가 어긋난다. 겹친 장만 걷어낸다.
    """
    seen = {}
    dup = []
    for f in bm.faces:
        key = frozenset(v.index for v in f.verts)
        if key in seen:
            dup.append(f)
        else:
            seen[key] = f
    if dup:
        bmesh.ops.delete(bm, geom=dup, context="FACES_ONLY")
    return len(dup)


def drop_nonmanifold_faces(bm, rounds=4):
    """모서리 하나에 면이 3장 이상 붙어 있으면(비다양체) 여분을 걷어낸다.

    가장 좁은 면부터 덜어내 2장만 남긴다. 이런 모서리가 남아 있으면 구멍 메우기가
    테두리를 따라가지 못해 끝까지 닫히지 않는다(캐릭터 모델에서 10개가 남았다).
    """
    removed = 0
    for _ in range(max(1, rounds)):
        bad = [e for e in bm.edges if len(e.link_faces) > 2]
        if not bad:
            break
        victims = set()
        for e in bad:
            faces = [f for f in e.link_faces if f.is_valid]
            if len(faces) <= 2:
                continue
            faces.sort(key=lambda f: f.calc_area())
            for f in faces[:len(faces) - 2]:
                victims.add(f)
        if not victims:
            break
        bmesh.ops.delete(bm, geom=list(victims), context="FACES_ONLY")
        removed += len(victims)
    return removed


def repair_bm(bm, fill_holes=True):
    """겹친 점 합치기 → 찌그러진 면 정리 → 겹친 면 걷어내기 → 법선 정리 → 구멍 메우기."""
    before = mesh_health(bm)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bm.verts.index_update()
    try:
        bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges[:])
        bm.verts.index_update()
    except Exception:
        pass
    dup_faces = drop_duplicate_faces(bm)
    dup_faces += drop_nonmanifold_faces(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    filled = 0
    if fill_holes:
        loose = [e for e in bm.edges if len(e.link_faces) < 2]
        if loose:
            try:
                r = bmesh.ops.holes_fill(bm, edges=loose, sides=0)
                filled = len(r.get("faces", []))
            except Exception:
                filled = 0
            # holes_fill 이 못 막고 남긴 테두리는 고리를 직접 걸어 막는다. 게임 모델은
            # 이 2차 시도로 마지막 구멍 몇 개가 닫힌다.
            filled += cap_holes(bm, 0)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    after = mesh_health(bm)
    return dict(merged_verts=before["verts"] - after["verts"], filled_faces=filled,
                duplicate_faces=dup_faces, before=before, after=after)


def solidify_object(obj, thickness):
    """열린 껍데기에 두께를 준다. 새 임시 오브젝트를 만들어 돌려준다(쓰고 나면 지울 것)."""
    tmp = obj.copy()
    tmp.data = obj.data.copy()
    tmp.name = f"FX_Solid_{obj.name}"
    link(tmp)
    m = tmp.modifiers.new("FX_Solidify", "SOLIDIFY")
    m.thickness = thickness
    m.offset = 0.0
    m.use_even_offset = True
    view_layer_update()
    return tmp


# ---------- 보로노이 조각내기 ----------

def inside_tester(obj, margin=0.0):
    """점이 메시 안에 있는지 판단하는 함수. 닫힌 메시에서만 믿을 만하다.

    margin 을 주면 표면에서 그만큼 안쪽으로 들어온 점만 안쪽으로 친다.
    표면에 딱 붙은 씨앗은 면도날처럼 얇은 조각을 만들고, 그런 조각은 버려져서
    사용자가 요청한 개수보다 적게 나온다.

    넘기는 점 p 는 오브젝트의 로컬 좌표다. closest_point_on_mesh 가 로컬 좌표를 받기
    때문이고, 씨앗도 로컬 상자 안에서 만들기 때문이다. 세계 좌표를 넣으면 물체가
    원점에서 떨어져 있을 때 전부 "바깥"으로 판정되어 씨앗이 거의 안 놓인다.
    """

    def inside(p):
        try:
            ok, loc, nor, _idx = obj.closest_point_on_mesh(p)
        except Exception:
            return True
        if not ok:
            return True
        d = p - loc
        return d.dot(nor) < 0.0 and d.length >= margin

    return inside


def voronoi_seeds(lo, hi, count, pattern, focus, impact_point, rng, inside=None, min_sep=0.0):
    """조각 씨앗 점을 뿌린다. pattern 이 어디를 촘촘하게 할지 정한다.

    min_sep 은 씨앗끼리 최소 간격이다. 두 씨앗이 붙어 있으면 그 사이 셀이 종잇장처럼
    얇아져 조각이 만들어지지 않고 버려진다. 자리를 못 찾으면 간격을 스스로 줄인다.
    """
    size = hi - lo
    center = (lo + hi) / 2
    focus = max(0.0, min(float(focus), 1.0))
    span = max(size.x, size.y, size.z, 1e-6)
    pts = []
    tries = 0
    limit = count * 400  # 벽이 얇은 물건은 상자 대비 속이 좁아 시도를 넉넉히 줘야 한다
    sep = max(0.0, float(min_sep))
    stall = 0
    while len(pts) < count and tries < limit:
        tries += 1
        if sep > 0.0:
            stall += 1
            if stall > count * 8:  # 자리를 못 찾으면 간격을 절반으로 낮춘다
                sep *= 0.5
                stall = 0
                if sep < 1e-6:
                    sep = 0.0
        p = Vector((rng.uniform(lo.x, hi.x), rng.uniform(lo.y, hi.y), rng.uniform(lo.z, hi.z)))
        if pattern == "impact" and impact_point is not None and focus > 0:
            # 맞은 곳 근처를 촘촘하게. 전체를 덮되 가까운 점을 더 자주 받아들인다(거부 표본)
            dist = (p - impact_point).length / span
            accept = (1.0 - focus) + focus * math.exp(-2.5 * dist)
            if rng.random() > accept:
                continue
        elif pattern == "radial" and focus > 0:
            dist = (p - center).length / span
            accept = (1.0 - focus) + focus * math.exp(-2.5 * dist)
            if rng.random() > accept:
                continue
        elif pattern == "slabs":
            layers = max(2, int(round(count ** (1.0 / 3.0) * (1.0 + focus * 2.0))))
            step = size.z / layers
            p.z = lo.z + step * (0.5 + rng.randrange(layers)) + rng.uniform(-step * 0.12, step * 0.12)
        if inside is not None and not inside(p):
            continue
        if sep > 0.0 and any((p - q).length < sep for q in pts):
            continue
        pts.append(p)
        stall = 0
    if not pts:  # 안쪽 판정이 실패하면 상자 안 무작위로 되돌린다
        pts = [Vector((rng.uniform(lo.x, hi.x), rng.uniform(lo.y, hi.y), rng.uniform(lo.z, hi.z))) for _ in range(count)]
    return pts


def convex_hull_from_points(points):
    """점들을 감싸는 볼록 껍질 bmesh. 반드시 닫혀 있다. 못 만들면 None."""
    if len(points) < 4:
        return None
    bm = bmesh.new()
    for p in points:
        bm.verts.new(p)
    bm.verts.ensure_lookup_table()
    try:
        r = bmesh.ops.convex_hull(bm, input=bm.verts[:], use_existing_faces=False)
    except Exception:
        bm.free()
        return None
    seen = set()
    junk = []
    for g in list(r.get("geom_interior", [])) + list(r.get("geom_unused", [])):
        key = (type(g).__name__, g.index if hasattr(g, "index") else id(g), id(g))
        if id(g) in seen:
            continue
        seen.add(id(g))
        junk.append(g)
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    holes = [f for f in r.get("geom_holes", []) if isinstance(f, bmesh.types.BMFace) and f.is_valid]
    if holes:
        bmesh.ops.delete(bm, geom=holes, context="FACES")
    if len(bm.faces) < 4:
        bm.free()
        return None
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if not all(len(e.link_faces) == 2 for e in bm.edges):
        bm.free()
        return None
    return bm


def boundary_loops(bm):
    """면이 하나뿐인 모서리(구멍 테두리)를 고리 단위로 모은다."""
    edges = [e for e in bm.edges if len(e.link_faces) < 2]
    if not edges:
        return []
    edge_set = set(edges)
    adj = {}
    for e in edges:
        for v in e.verts:
            adj.setdefault(v, []).append(e)
    used = set()
    loops = []
    for e0 in edges:
        if e0 in used:
            continue
        start_v = e0.verts[0]
        v, e = start_v, e0
        loop = []
        ok = True
        while True:
            used.add(e)
            loop.append(v)
            v = e.other_vert(v)
            if v is start_v:
                break
            nxt = [x for x in adj.get(v, []) if x is not e and x in edge_set and x not in used]
            if len(nxt) != 1 or len(loop) > 4096:
                ok = False
                break
            e = nxt[0]
        if ok and len(loop) >= 3:
            loops.append(loop)
    return loops


def cap_holes(bm, material_index=0):
    """잘린 단면을 면으로 막는다. holes_fill 보다 안전하게 고리마다 하나씩 만든다."""
    made = 0
    for _ in range(6):
        loops = boundary_loops(bm)
        if not loops:
            break
        progressed = False
        for verts in loops:
            if len(verts) < 3 or len(set(verts)) != len(verts):
                continue
            try:
                f = bm.faces.new(verts)
            except ValueError:
                continue
            f.material_index = material_index
            made += 1
            progressed = True
        if not progressed:
            break
    if made:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return made


def is_closed(bm):
    return all(len(e.link_faces) == 2 for e in bm.edges) and len(bm.faces) > 3


def covering_cube_bm(lo, hi):
    """주어진 상자를 넉넉히 감싸는 큰 육면체 bmesh(로컬 좌표)."""
    size = hi - lo
    center = (lo + hi) / 2
    pad = max(size.x, size.y, size.z) * 1.2 + 1.0
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((center.x + v.co.x * (size.x + pad),
                       center.y + v.co.y * (size.y + pad),
                       center.z + v.co.z * (size.z + pad)))
    return bm


def resolve_solid(obj, lo, hi):
    """서로 겹치거나 맞닿아 있는 덩어리들을 불리언이 이해하는 하나의 solid 로 정리한다.

    무료 에셋은 바퀴가 몸통에 박혀 있거나 내용물이 바닥에 딱 붙어 있는 경우가 흔하다.
    그대로 두면 셀 불리언이 아무것도 못 만들어 조각과 부피가 통째로 사라진다
    (실측: 통 0.69, 수레 0.93). 여기서 한 번 정리하면 1.00 이 된다.
    되돌려주는 값은 (정리했는지, 정리 뒤 부피, 정리 뒤 닫혀 있는지).
    불리언 솔버는 결과를 닫힌 메시로 내놓기 때문에, 원본이 껍데기여도 여기서 닫히는 일이 많다.
    """
    h_before = object_health(obj)
    # 부피는 반올림하지 않은 값을 쓴다. mesh_health 는 소수점 4자리로 자르는데,
    # 5cm 짜리 물건(0.000125㎥)은 그 자리에서 잘려 보존율이 1.25 로 뜬다.
    before, closed = mesh_volume(obj)
    box_bm = covering_cube_bm(lo, hi)
    box = new_mesh_object("FX_ResolveBox", box_bm, obj.matrix_world.copy(), tag="cell")
    box_bm.free()
    slots = len(obj.data.materials)
    mod = obj.modifiers.new("fx_resolve", "BOOLEAN")
    mod.operation = "INTERSECT"
    mod.solver = "EXACT"
    mod.use_self = True
    mod.object = box
    view_layer_update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    obj.modifiers.remove(mod)
    remove_object(box)
    ok = False
    volume = before
    if len(me.polygons) >= 4 and len(me.vertices) >= 4:
        b = bmesh.new()
        b.from_mesh(me)
        h_after = mesh_health(b)
        v = abs(b.calc_volume(signed=False))
        v_closed = h_after["closed"]
        b.free()
        # 결과가 터무니없거나(부피가 절반 아래/1.5배 위) 원본보다 더 망가졌으면 원본을 그대로 쓴다.
        # 이미 비다양체인 메시에 이 연산을 걸면 모서리가 10개에서 8,390개로 늘어난 적이 있다.
        sane = before <= 1e-9 or 0.5 <= v / before <= 1.5
        not_worse = v_closed or h_after["non_manifold_edges"] <= h_before["non_manifold_edges"]
        if sane:
            # 메시를 바꾸지 않더라도 부피 기준은 솔버가 본 값을 쓴다.
            # 겹친 덩어리를 두 번 세는 원본 값으로 나누면 보존율이 거짓으로 낮게 나온다.
            volume = v
        if sane and not_worse:
            old = obj.data
            obj.data = me
            bpy.data.meshes.remove(old)
            while len(obj.data.materials) > slots:
                obj.data.materials.pop()
            view_layer_update()
            ok = True
            closed = v_closed
            me = None
    if me is not None:
        bpy.data.meshes.remove(me)
    return ok, volume, closed


def voronoi_cell_objects(lo, hi, seeds, matrix, interior_mat):
    """씨앗마다 볼록한 셀 다면체 오브젝트를 만든다.
    큰 상자를 이웃과의 중간 평면으로 잘라 만들기 때문에 항상 닫혀 있다."""
    objs = []
    n = len(seeds)
    for i, seed in enumerate(seeds):
        bm = covering_cube_bm(lo, hi)  # 정리 단계와 똑같은 상자에서 시작한다
        others = sorted(((seed - seeds[j]).length, j) for j in range(n) if j != i)
        ok = True
        # 씨앗에서 가장 먼 꼭짓점까지의 거리. 중간 평면이 이보다 멀면 더는 자를 수 없다(정확한 조기 종료)
        max_radius = max((v.co - seed).length for v in bm.verts)
        cuts = 0
        # 조기 종료 조건이 수학적으로 정확하므로 자르는 횟수를 따로 제한하지 않는다.
        # 제한을 두면 조각 수가 많을 때 셀이 덜 잘려 서로 겹치고 부피가 부풀었다(실측 1.172).
        for _d, j in others:
            if _d * 0.5 > max_radius:
                break  # 남은 이웃은 이 셀을 자를 수 없다
            direction = seeds[j] - seed
            if direction.length < 1e-6:
                continue
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            try:
                bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-6,
                                       plane_co=(seed + seeds[j]) / 2, plane_no=direction.normalized(),
                                       clear_outer=True)
            except Exception:
                ok = False
                break
            cap_holes(bm, 0)
            cuts += 1
            if len(bm.faces) < 4 or not bm.verts:
                ok = False
                break
            max_radius = max((v.co - seed).length for v in bm.verts)
        if not ok or len(bm.verts) < 4:
            bm.free()
            continue
        # 셀은 반평면들의 교집합이라 반드시 볼록하다. 꼭짓점만 뽑아 볼록 껍질을 새로 만들면
        # 자르는 도중 생긴 틈이 사라져 불리언이 실패하지 않는다.
        hull = convex_hull_from_points([v.co.copy() for v in bm.verts])
        bm.free()
        if hull is None:
            continue
        bm = hull
        o = new_mesh_object(f"FX_Cell_{i:04d}", bm, matrix.copy(), tag="cell")
        bm.free()
        o.hide_render = True
        o.display_type = "WIRE"
        o.data.materials.append(interior_mat)
        objs.append(o)
    return objs


def boolean_chunks(target, cell_objects, materials, coll, name_prefix, use_self=False):
    """대상 메시와 셀 다면체의 교집합으로 조각을 만든다. 블렌더의 정확 불리언을 쓴다.

    use_self 는 부품끼리 서로 관통하는 메시(캐릭터의 몸통·머리·가방처럼)에 필요하다.
    켜지 않으면 불리언이 빈 결과를 내서 조각이 통째로 사라진다(실측 0.405). 대신 느리다.
    """
    src = target.copy()
    src.data = target.data.copy()
    src.name = f"FX_Src_{target.name}"
    src[FX_TAG] = "cell"
    link(src)
    src.data.materials.clear()
    for m in materials:
        src.data.materials.append(m)
    mod = src.modifiers.new("FX_Bool", "BOOLEAN")
    mod.operation = "INTERSECT"
    mod.use_self = bool(use_self)
    try:
        mod.solver = "EXACT"
    except TypeError:
        pass
    try:
        mod.material_mode = "TRANSFER"
    except (TypeError, AttributeError):
        pass

    chunks = []
    for i, cell in enumerate(cell_objects):
        mod.object = cell
        view_layer_update()
        dg = bpy.context.evaluated_depsgraph_get()
        try:
            me = bpy.data.meshes.new_from_object(src.evaluated_get(dg))
        except Exception:
            continue
        if len(me.polygons) < 4 or len(me.vertices) < 4:
            bpy.data.meshes.remove(me)
            continue
        me.name = f"{name_prefix}_{i:04d}"
        o = bpy.data.objects.new(me.name, me)
        o.matrix_world = target.matrix_world.copy()
        o[FX_TAG] = "chunk"
        o["fx_chunk_of"] = target.name
        link(o, coll)
        chunks.append(o)
    remove_object(src)
    return chunks


def center_origin(obj):
    """오브젝트 원점을 메시 중심으로 옮긴다. 물리가 자연스러워진다."""
    me = obj.data
    if not me.vertices:
        return
    c = Vector((0.0, 0.0, 0.0))
    for v in me.vertices:
        c += v.co
    c /= len(me.vertices)
    for v in me.vertices:
        v.co -= c
    me.update()
    obj.matrix_world = obj.matrix_world @ Matrix.Translation(c)


def mesh_volume(obj):
    """오브젝트의 실제 부피(m³). 닫혀 있지 않으면 볼록 껍질로 어림잡는다."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    s = obj.matrix_world.to_scale()
    factor = abs(s.x * s.y * s.z)
    closed = is_closed(bm)
    vol = 0.0
    try:
        vol = abs(bm.calc_volume(signed=False)) if closed else 0.0
    except Exception:
        vol = 0.0
    if vol <= 1e-9:
        try:
            r = bmesh.ops.convex_hull(bm, input=bm.verts[:])
            junk = list(r.get("geom_interior", [])) + list(r.get("geom_unused", []))
            if junk:
                bmesh.ops.delete(bm, geom=junk, context="VERTS")
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
            vol = abs(bm.calc_volume(signed=False)) * 0.7
        except Exception:
            vol = 0.0
    bm.free()
    return vol * factor, closed


def ensure_constraint_collection():
    """리지드바디 제약(조각 접착)이 들어갈 컬렉션."""
    sc = scene()
    rbw = ensure_rbw()
    coll = bpy.data.collections.get("FX_Constraints")
    if coll is None:
        coll = bpy.data.collections.new("FX_Constraints")
        sc.collection.children.link(coll)
    elif coll.name not in {c.name for c in sc.collection.children_recursive}:
        sc.collection.children.link(coll)
    rbw.constraints = coll
    return coll


def glue_chunks(chunks, threshold, max_neighbors=4, max_constraints=600):
    """이웃한 조각끼리 접착(고정 제약)한다. 충격이 threshold 를 넘으면 그 접착만 끊어진다."""
    if len(chunks) < 2 or threshold <= 0:
        return 0
    coll = ensure_constraint_collection()
    sc = scene()
    vl = bpy.context.view_layer
    info = [(o, o.matrix_world.translation.copy(), max(o.dimensions) / 2 if max(o.dimensions) > 0 else 0.1) for o in chunks]
    pairs = set()
    for i, (_a, ca, ra) in enumerate(info):
        near = []
        for j, (_b, cb, rb) in enumerate(info):
            if i == j:
                continue
            d = (ca - cb).length
            if d < (ra + rb) * 1.25:
                near.append((d, j))
        near.sort()
        for _d, j in near[:max_neighbors]:
            pairs.add((min(i, j), max(i, j)))
            if len(pairs) >= max_constraints:
                break
        if len(pairs) >= max_constraints:
            break

    made = 0
    for i, j in sorted(pairs):
        a, ca, _ = info[i]
        b, cb, _ = info[j]
        e = bpy.data.objects.new(f"FX_Glue_{i:03d}_{j:03d}", None)
        e[FX_TAG] = "glue"
        e.empty_display_type = "PLAIN_AXES"
        e.empty_display_size = 0.1
        e.location = (ca + cb) / 2
        coll.objects.link(e)
        with bpy.context.temp_override(scene=sc, view_layer=vl, active_object=e, object=e, selected_objects=[e]):
            try:
                bpy.ops.rigidbody.constraint_add(type="FIXED")
            except Exception:
                continue
        rbc = e.rigid_body_constraint
        if rbc is None:
            continue
        rbc.object1 = a
        rbc.object2 = b
        rbc.use_breaking = True
        rbc.breaking_threshold = threshold
        rbc.disable_collisions = False
        made += 1
    return made


def free_bake():
    sc = scene()
    if sc.rigidbody_world is None:
        return
    try:
        with bpy.context.temp_override(scene=sc):
            bpy.ops.ptcache.free_bake_all()
    except Exception:
        pass


def bake_pointcaches(frames):
    """리지드바디·파티클 캐시를 굽는다. 안 되면 프레임을 한 장씩 밟아 채운다."""
    sc = scene()
    sc.frame_start = 1
    sc.frame_end = frames
    if sc.rigidbody_world is not None:
        sc.rigidbody_world.point_cache.frame_start = 1
        sc.rigidbody_world.point_cache.frame_end = frames
    try:
        with bpy.context.temp_override(scene=sc):
            bpy.ops.ptcache.bake_all(bake=True)
        return "bake_all"
    except Exception:
        for f in range(1, frames + 1):
            sc.frame_set(f)
        return "frame_step"


def set_engine(candidates):
    r = scene().render
    for eng in candidates:
        try:
            r.engine = eng
            return eng
        except TypeError:
            continue
    return r.engine


def apply_render_quality(quality):
    """preview: 워크벤치(빠름, 연기·물 안 보임) / smoke: EEVEE 저샘플(빠르고 볼륨 보임) / final: 고화질. 엔진 이름을 돌려준다."""
    sc = scene()
    if quality == "preview":
        engine = set_engine(["BLENDER_WORKBENCH"])
        sh = sc.display.shading
        chunks = [o for o in bpy.data.objects if o.get(FX_TAG) == "chunk"]
        has_mat = any(m is not None for o in chunks for m in o.data.materials) if chunks else True
        sh.color_type = "MATERIAL" if has_mat else "RANDOM"
        sh.light = "STUDIO"
        sh.show_shadows = True
        sh.show_cavity = True
        # 외곽선은 조각 경계를 보여 주지만, 작은 파티클(눈·비)은 검은 점으로 만든다
        sh.show_object_outline = not any(o.particle_systems for o in bpy.data.objects if o.get(FX_TAG) == "particles")
        return engine
    fast = quality == "smoke"
    engine = set_engine(["BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "CYCLES", "BLENDER_WORKBENCH"])
    if hasattr(sc, "eevee"):
        sc.eevee.taa_render_samples = 16 if fast else 32
        for attr, val in (("volumetric_tile_size", "8" if fast else "4"), ("volumetric_samples", 32 if fast else 64)):
            try:
                setattr(sc.eevee, attr, val)
            except Exception:
                pass
    if engine == "CYCLES" and hasattr(sc, "cycles"):
        sc.cycles.samples = 16 if fast else 64
    return engine


def bake_fluid(dom):
    """Mantaflow 도메인(연기·불·물)을 굽는다. 파이썬에서 부르면 끝날 때까지 기다린다."""
    sc = scene()
    with bpy.context.temp_override(scene=sc, object=dom, active_object=dom, selected_objects=[dom]):
        try:
            bpy.ops.fluid.free_all()
        except Exception:
            pass
        bpy.ops.fluid.bake_all()


def count_cache_files(cache_dir):
    n = 0
    for _root, _dirs, files in os.walk(cache_dir):
        n += sum(1 for f in files if f.endswith((".vdb", ".uni", ".raw", ".bobj.gz", ".obj")))
    return n


FX_CONTENT_ROLES = ("chunk", "smoke_domain", "liquid_domain", "emit_domain", "ocean", "flag", "particles")


def set_frame_end(frames):
    """효과가 이미 있으면 길이를 늘리기만 하고, 빈 장면이면(기본 250프레임) 이 효과 길이로 맞춘다."""
    sc = scene()
    has_fx = any(o.get(FX_TAG) in FX_CONTENT_ROLES for o in bpy.data.objects)
    sc.frame_start = 1
    sc.frame_end = max(sc.frame_end, frames) if has_fx else frames
    return sc.frame_end


def fx_bbox(target_name=None):
    """대상이 있으면 그 상자, 없으면 이 도구가 만든 것과 보이는 메시 전체의 합집합 상자."""
    if target_name:
        return world_bbox(get_target(target_name))
    objs = [o for o in mesh_objects() if o.get(FX_TAG) not in ("ground", "dust", "particles", "smoke_domain", "liquid_domain", "emit_domain") and not o.hide_viewport]
    if not objs:
        return Vector((-2.0, -2.0, 0.0)), Vector((2.0, 2.0, 4.0))
    lo, hi = world_bbox(objs[0])
    for o in objs[1:]:
        a, b = world_bbox(o)
        lo = Vector((min(lo.x, a.x), min(lo.y, a.y), min(lo.z, a.z)))
        hi = Vector((max(hi.x, b.x), max(hi.y, b.y), max(hi.z, b.z)))
    return lo, hi


def principled(mat):
    return next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)


def set_input(node, name, value):
    if node is not None and name in node.inputs:
        node.inputs[name].default_value = value


def simple_material(name, color, roughness=0.6, alpha=1.0, emission=None, emission_strength=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    b = principled(mat)
    set_input(b, "Base Color", (*color[:3], 1.0))
    set_input(b, "Roughness", roughness)
    set_input(b, "Alpha", alpha)
    if emission is not None:
        set_input(b, "Emission Color", (*emission[:3], 1.0))
        set_input(b, "Emission Strength", emission_strength)
    mat.diffuse_color = (*color[:3], alpha)
    if alpha < 1.0:
        for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
            try:
                setattr(mat, attr, val)
                break
            except Exception:
                continue
    return mat


def water_material():
    mat = simple_material("FX_Water", (0.55, 0.75, 0.95), roughness=0.05, alpha=0.75)
    b = principled(mat)
    set_input(b, "Transmission Weight", 0.6)
    set_input(b, "IOR", 1.33)
    return mat


def smoke_material(fire=True, name="FX_Smoke"):
    """볼륨 재질: 연기 + (불이면) 온도에 따른 빛."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    vol.inputs["Density"].default_value = 6.0
    vol.inputs["Color"].default_value = (0.30, 0.28, 0.26, 1.0)
    if fire:
        vol.inputs["Blackbody Intensity"].default_value = 1.5
    return mat


GROUND_MATERIALS = {
    # (기본색, 거칠기, 노이즈 크기, 울퉁불퉁 세기, 색 변화)
    "asphalt": ((0.045, 0.045, 0.050), 0.85, 60.0, 0.25, 0.25),
    "concrete": ((0.42, 0.41, 0.39), 0.90, 22.0, 0.12, 0.18),
    "grass": ((0.055, 0.22, 0.045), 0.95, 120.0, 0.45, 0.60),
    "sand": ((0.62, 0.50, 0.32), 1.00, 90.0, 0.30, 0.22),
    "dirt": ((0.20, 0.13, 0.085), 1.00, 45.0, 0.40, 0.35),
    "snow": ((0.90, 0.92, 0.96), 0.55, 30.0, 0.20, 0.10),
}


def ground_material(kind):
    """절차적 바닥 재질: 노이즈로 색을 흐트리고 울퉁불퉁하게 만든다."""
    if kind not in GROUND_MATERIALS:
        raise FxError(L(f"바닥 재질은 {list(GROUND_MATERIALS)} 중 하나여야 합니다. 받은 값: {kind}",
                        f"ground material must be one of {list(GROUND_MATERIALS)}, got: {kind}"))
    color, rough, noise_scale, bump, color_var = GROUND_MATERIALS[kind]
    mat = bpy.data.materials.get(f"FX_Ground_{kind}") or bpy.data.materials.new(f"FX_Ground_{kind}")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    bumpn = nt.nodes.new("ShaderNodeBump")
    noise.inputs["Scale"].default_value = noise_scale
    noise.inputs["Detail"].default_value = 8.0
    dark = [max(0.0, c * (1.0 - color_var)) for c in color]
    bright = [min(1.0, c * (1.0 + color_var) + 0.02) for c in color]
    ramp.color_ramp.elements[0].color = (*dark, 1.0)
    ramp.color_ramp.elements[1].color = (*bright, 1.0)
    bumpn.inputs["Strength"].default_value = bump
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], bumpn.inputs["Height"])
    nt.links.new(bumpn.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    set_input(bsdf, "Roughness", rough)
    mat.diffuse_color = (*color, 1.0)  # 워크벤치 미리보기용
    return mat


def apply_world(sky_mode, sky_color, strength, elev_deg, azim_deg, hdri_path=None):
    """하늘: flat(단색) / procedural(하늘 텍스처) / HDRI 파일. 엔진 없이도 워크벤치 배경색은 맞춘다."""
    sc = scene()
    world = sc.world
    if world is None:
        world = bpy.data.worlds.get("FX_World") or bpy.data.worlds.new("FX_World")
        sc.world = world
    world.use_nodes = True
    nt = world.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    bg.inputs["Color"].default_value = (*sky_color, 1.0)
    bg.inputs["Strength"].default_value = strength
    used = "flat"
    if hdri_path:
        path = os.path.expanduser(hdri_path)
        if not os.path.exists(path):
            raise FxError(L(f"HDRI 파일이 없습니다: {path}", f"HDRI file not found: {path}"))
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(path, check_existing=True)
        mapping = nt.nodes.new("ShaderNodeMapping")
        coord = nt.nodes.new("ShaderNodeTexCoord")
        mapping.inputs["Rotation"].default_value[2] = math.radians(azim_deg)
        nt.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
        nt.links.new(mapping.outputs["Vector"], env.inputs["Vector"])
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = max(strength, 1.0)
        used = "hdri"
    elif sky_mode == "procedural":
        try:
            sky = nt.nodes.new("ShaderNodeTexSky")
            for attr, val in (("sky_type", "NISHITA"), ("sun_elevation", math.radians(elev_deg)),
                              ("sun_rotation", math.radians(azim_deg)), ("sun_intensity", 1.0),
                              ("sun_size", math.radians(1.0)), ("altitude", 200.0),
                              ("air_density", 1.0), ("dust_density", 1.5)):
                try:
                    setattr(sky, attr, val)
                except Exception:
                    continue
            nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
            bg.inputs["Strength"].default_value = max(strength, 1.0)
            used = "procedural"
        except Exception:
            used = "flat"
    world.color = sky_color  # 워크벤치 배경
    return used


def make_force_field(name, tag, field_type, location):
    """빈 오브젝트에 힘장을 켠다. 빈 오브젝트는 처음엔 힘장 설정이 없어 블렌더 명령으로 켜 줘야 한다."""
    e = bpy.data.objects.new(name, None)
    e[FX_TAG] = tag
    link(e)
    e.location = location
    if e.field is None:
        with bpy.context.temp_override(scene=scene(), object=e, active_object=e, selected_objects=[e]):
            bpy.ops.object.forcefield_toggle()
    if e.field is None:
        raise FxError(f"힘장({field_type})을 만들지 못했습니다.")
    e.field.type = field_type
    return e


def cleanup_liquid():
    """물 도메인·입구를 지우고, 장애물로 붙였던 모디파이어를 뗀다."""
    for o in list(bpy.data.objects):
        if o.get(FX_TAG) in ("liquid_domain", "liquid_flow"):
            remove_object(o)
    for o in bpy.data.objects:
        for name in ("FX_LiquidObstacle", "FX_FluidEffector", "FX_LiquidFlow"):
            m = o.modifiers.get(name)
            if m is not None:
                o.modifiers.remove(m)


def add_fluid_effectors(objs, limit=60):
    """오브젝트를 연기·물이 부딪히는 장애물로 만든다. 많으면 굽기가 느려져 개수를 제한한다."""
    n = 0
    for o in objs[:limit]:
        if any(m.type == "FLUID" for m in o.modifiers):
            continue
        m = o.modifiers.new("FX_FluidEffector", "FLUID")
        m.fluid_type = "EFFECTOR"
        es = m.effector_settings
        es.effector_type = "COLLISION"
        es.use_effector = True
        try:
            es.use_plane_init = False
        except Exception:
            pass
        n += 1
    return n


def fluid_domains():
    out = []
    for o in bpy.data.objects:
        for m in o.modifiers:
            if m.type == "FLUID" and m.fluid_type == "DOMAIN":
                out.append((o, m.domain_settings))
    return out


def ensure_ground(z=0.0, half_size=40.0):
    g = next((o for o in bpy.data.objects if o.get(FX_TAG) == "ground"), None)
    # 바다가 있으면 바다가 바닥이다 (같은 높이의 평면은 파도를 뚫고 나온다)
    if any(o.get(FX_TAG) == "ocean" for o in bpy.data.objects):
        if g is not None:
            g.hide_render = True
            g.hide_viewport = True
        return g
    if g is None:
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=half_size)
        g = new_mesh_object("FX_Ground", bm, Matrix.Translation((0.0, 0.0, z)), tag="ground")
        bm.free()
    else:
        g.location.z = z
    add_rigid_bodies([g], "PASSIVE")
    g.rigid_body.collision_shape = "MESH"
    g.rigid_body.friction = 0.9
    return g


def frame_camera(cam, lo, hi):
    """카메라를 앞·왼쪽 위 3/4 구도로 옮겨 대상 전체가 보이게 한다. 파편이 옆으로 퍼지므로 넉넉히 뺀다."""
    center = (lo + hi) / 2
    size = max((hi - lo).x, (hi - lo).y, (hi - lo).z, 1.0)
    distance = size * 3.0
    cam.location = center + Vector((-1.0, -1.7, 0.6)).normalized() * distance
    aim = Vector((center.x, center.y, lo.z + (hi.z - lo.z) * 0.4))
    cam.rotation_euler = (aim - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 35
    cam.data.clip_end = max(100.0, distance * 4.0)


def ensure_camera(lo, hi, reframe=False):
    """카메라가 없으면 만든다. reframe=True 면 있는 카메라도 대상에 맞게 다시 잡는다."""
    sc = scene()
    if sc.camera is not None:
        if reframe:
            frame_camera(sc.camera, lo, hi)
        return sc.camera
    cam_data = bpy.data.cameras.new("FX_Camera")
    cam = bpy.data.objects.new("FX_Camera", cam_data)
    cam[FX_TAG] = "camera"
    link(cam)
    frame_camera(cam, lo, hi)
    sc.camera = cam
    return cam


def ensure_light():
    if any(o.type == "LIGHT" for o in bpy.data.objects):
        return
    ld = bpy.data.lights.new("FX_Sun", "SUN")
    ld.energy = 3.0
    lt = bpy.data.objects.new("FX_Sun", ld)
    lt[FX_TAG] = "light"
    link(lt)
    lt.rotation_euler = (math.radians(50), 0.0, math.radians(35))
