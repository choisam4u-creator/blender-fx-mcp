# 파괴 레시피: 메시를 수리하고 보로노이로 조각내어 물리로 무너뜨린다.
# PARAMS: target, impact, material, pieces, pattern, focus, time_scale, frames, impact_height, impact_power,
#         dust, glue, glue_neighbors, glue_max, seed, collision, interior, repair, shell_thickness,
#         decimate_to, density, friction, bounce, margin, hold_until

MATERIALS = {
    # 밀도(kg/m³), 마찰, 튐, 속 재질 색
    "concrete": dict(density=2400.0, friction=0.80, restitution=0.05, interior=(0.42, 0.41, 0.39)),
    "brick": dict(density=1900.0, friction=0.85, restitution=0.05, interior=(0.45, 0.22, 0.16)),
    "glass": dict(density=2500.0, friction=0.50, restitution=0.30, interior=(0.55, 0.70, 0.75)),
    "wood": dict(density=600.0, friction=0.60, restitution=0.10, interior=(0.52, 0.36, 0.18)),
    "stone": dict(density=2700.0, friction=0.90, restitution=0.04, interior=(0.30, 0.29, 0.28)),
    "metal": dict(density=7800.0, friction=0.45, restitution=0.20, interior=(0.55, 0.56, 0.58)),
    "ice": dict(density=917.0, friction=0.12, restitution=0.15, interior=(0.70, 0.85, 0.92)),
    "plaster": dict(density=1100.0, friction=0.75, restitution=0.05, interior=(0.88, 0.87, 0.84)),
}
# 조각 하나당 먼지 알갱이 수
DUST_LEVELS = {"none": 0, "low": 25, "high": 70}
# 접착 세기: 조각 평균 무게에 곱해 "이 충격을 넘으면 끊어진다" 값을 만든다
GLUE_LEVELS = {"none": 0.0, "weak": 0.4, "medium": 1.5, "strong": 6.0}
PATTERNS = ("uniform", "impact", "radial", "slabs")
COLLISIONS = ("auto", "convex", "mesh", "box", "sphere")
# 충격체가 날아오는 쪽 (건물 중심 기준 바깥 방향)
SIDES = {
    "left": (-1.0, 0.0, 0.0),
    "right": (1.0, 0.0, 0.0),
    "front": (0.0, -1.0, 0.0),
    "back": (0.0, 1.0, 0.0),
    "top": (0.0, 0.0, 1.0),
    "none": None,  # 충격체 없음 (폭발 등 다른 힘으로 무너뜨릴 때)
}


def interior_material(name, color, roughness=1.0):
    return simple_material(name, color, roughness=roughness)


def impact_anchor(lo, hi, side, height_frac):
    """맞는 지점(조각을 촘촘하게 할 곳)."""
    center = (lo + hi) / 2
    size = hi - lo
    z = lo.z + max(0.0, min(1.0, height_frac)) * size.z
    if side == "top":
        return Vector((center.x, center.y, hi.z))
    d = SIDES.get(side)
    if d is None:
        return Vector((center.x, center.y, z))
    d = Vector(d)
    return Vector((center.x + d.x * size.x / 2, center.y + d.y * size.y / 2, z))


def surface_aim(obj, lo, hi, side, height_frac):
    """충격체가 실제로 닿을 표면 점을 찾는다(세계 좌표). 못 찾으면 None.

    바운딩 박스 면을 그대로 조준하면 팔을 벌린 사람처럼 얄팍한 모델에서 허공을 친다.
    실제로 광선을 쏴서 맞는 자리를 찾고, 요청한 높이에서 빗나가면 높이를 훑는다.
    (T 포즈 캐릭터에서 조각이 하나도 안 움직이던 원인)
    """
    center = (lo + hi) / 2
    size = hi - lo
    reach = max(size.x, size.y, size.z) * 2.0 + 1.0
    try:
        inv = obj.matrix_world.inverted()
    except Exception:
        return None
    mw = obj.matrix_world

    def shoot(origin_w, dir_w):
        try:
            ok, loc, _n, _i = obj.ray_cast(inv @ origin_w, (inv.to_3x3() @ dir_w).normalized(),
                                           distance=reach * 3.0)
        except Exception:
            return None
        return (mw @ loc) if ok else None

    if side == "top":
        for dx, dy in ((0.0, 0.0), (0.25, 0.0), (-0.25, 0.0), (0.0, 0.25), (0.0, -0.25)):
            hit = shoot(Vector((center.x + dx * size.x, center.y + dy * size.y, hi.z + reach)),
                        Vector((0.0, 0.0, -1.0)))
            if hit is not None:
                return hit
        return None

    d = SIDES.get(side)
    if d is None:
        return None
    d = Vector(d)
    want = max(0.02, min(0.98, height_frac))
    fracs = [want] + [i / 12.0 for i in range(11, 0, -1)]
    for f in fracs:
        z = lo.z + f * size.z
        hit = shoot(Vector((center.x, center.y, z)) + d * reach, -d)
        if hit is not None:
            return hit
    return None


def add_impactor(lo, hi, side, height_frac, frames_in, mass, aim=None):
    """충격체(무거운 공)를 만들어 건물 쪽으로 날린다. 처음 몇 프레임은 손으로 움직이고 그 뒤 물리에 맡긴다."""
    d = Vector(SIDES[side])
    center = (lo + hi) / 2
    size = hi - lo
    radius = max(0.3, 0.22 * min(size.x, size.y))
    # 손으로 움직이는 동안 물체 안으로 파고들면, 물리가 켜지는 순간 겹침이 풀리며 폭발한다.
    # 그래서 표면에 닿는 지점까지만 데려가고 그 뒤는 물리에 맡긴다.
    if aim is not None:
        # 실제 표면 점을 찾았으면 거기서 공 반지름만큼 떨어진 자리까지만 데려간다
        step = Vector((0.0, 0.0, 1.0)) if side == "top" else d
        end = aim + step * radius
        start = end + step * (radius * 5.0)
    elif side == "top":
        surface = hi.z + radius
        start = Vector((center.x, center.y, surface + radius * 5.0))
        end = Vector((center.x, center.y, surface))
    else:
        z = lo.z + max(radius, height_frac * size.z)
        half = abs(d.x) * size.x / 2 + abs(d.y) * size.y / 2
        base = Vector((center.x, center.y, z))
        start = base + d * (half + radius + radius * 5.0)
        end = base + d * (half + radius)

    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=radius)
    o = new_mesh_object("FX_Impactor", bm, Matrix.Translation(start), tag="impactor")
    bm.free()
    add_rigid_bodies([o], "ACTIVE")
    rb = o.rigid_body
    rb.collision_shape = "SPHERE"
    rb.mass = mass
    rb.friction = 0.5
    rb.restitution = 0.1

    f0 = scene().frame_start
    prefs = bpy.context.preferences.edit
    old_interp = prefs.keyframe_new_interpolation_type
    prefs.keyframe_new_interpolation_type = "LINEAR"
    method = "kinematic_launch"
    try:
        o.location = start
        o.keyframe_insert("location", frame=f0)
        o.location = end
        o.keyframe_insert("location", frame=f0 + frames_in)
        rb.kinematic = True
        rb.keyframe_insert("kinematic", frame=f0 + frames_in)
        rb.kinematic = False
        rb.keyframe_insert("kinematic", frame=f0 + frames_in + 1)
    except Exception:
        method = "drop"
        if o.animation_data:
            o.animation_data_clear()
        o.location = Vector((center.x, center.y, hi.z + radius * 4.0))
        rb.kinematic = False
    finally:
        prefs.keyframe_new_interpolation_type = old_interp
    return o, radius, method


def main():
    p = PARAMS
    target = get_target(p.get("target"))
    material = p.get("material", "concrete")
    if material not in MATERIALS:
        raise FxError(L(f"material 은 {list(MATERIALS)} 중 하나여야 합니다. 받은 값: {material}",
                        f"material must be one of {list(MATERIALS)}, got: {material}"))
    side = p.get("impact", "left")
    if side not in SIDES:
        raise FxError(L(f"impact 는 {list(SIDES)} 중 하나여야 합니다. 받은 값: {side}",
                        f"impact must be one of {list(SIDES)}, got: {side}"))
    pattern = p.get("pattern", "impact")
    if pattern not in PATTERNS:
        raise FxError(L(f"pattern 은 {list(PATTERNS)} 중 하나여야 합니다. 받은 값: {pattern}",
                        f"pattern must be one of {list(PATTERNS)}, got: {pattern}"))
    collision = p.get("collision", "auto")
    if collision not in COLLISIONS:
        raise FxError(L(f"collision 은 {list(COLLISIONS)} 중 하나여야 합니다. 받은 값: {collision}",
                        f"collision must be one of {list(COLLISIONS)}, got: {collision}"))
    dust = p.get("dust", "low")
    if dust not in DUST_LEVELS:
        raise FxError(L(f"dust 는 {list(DUST_LEVELS)} 중 하나여야 합니다. 받은 값: {dust}",
                        f"dust must be one of {list(DUST_LEVELS)}, got: {dust}"))
    glue = p.get("glue", "none")
    if glue not in GLUE_LEVELS:
        raise FxError(L(f"glue 는 {list(GLUE_LEVELS)} 중 하나여야 합니다. 받은 값: {glue}",
                        f"glue must be one of {list(GLUE_LEVELS)}, got: {glue}"))

    pieces = max(2, min(int(p.get("pieces", 120)), 1500))
    frames = max(12, int(p.get("frames", 72)))
    time_scale = float(p.get("time_scale", 1.0))
    seed = int(p.get("seed", 1))
    height_frac = min(1.0, max(0.0, float(p.get("impact_height", 0.35))))
    impact_power = float(p.get("impact_power", 0.06))
    hold_until = int(p.get("hold_until", 0))
    focus = float(p.get("focus", 0.5))
    decimate_to = int(p.get("decimate_to", 20000))
    shell_thickness = float(p.get("shell_thickness", 0.0))
    do_repair = bool(p.get("repair", True))
    interior_kind = p.get("interior", "auto")
    margin = float(p.get("margin", 0.02))

    m = MATERIALS[material]
    density = float(p.get("density") or m["density"])
    friction = float(p.get("friction")) if p.get("friction") is not None else m["friction"]
    bounce = float(p.get("bounce")) if p.get("bounce") is not None else m["restitution"]

    sc = scene()
    cleanup_fx(target.name)
    unhide(target)
    view_layer_update()
    free_bake()

    lo, hi = world_bbox(target)
    ensure_ground(lo.z)
    ensure_camera(lo, hi)
    ensure_light()

    # 1) 메시 읽기·수리
    source = target
    solidified = None
    bm, ratio, repair_info = bm_from_object(source, decimate_to, repair=do_repair)
    health = mesh_health(bm)
    if not health["closed"] and shell_thickness > 0:
        bm.free()
        solidified = solidify_object(target, shell_thickness)
        bm, ratio, repair_info = bm_from_object(solidified, decimate_to, repair=do_repair)
        health = mesh_health(bm)
    if len(bm.faces) == 0:
        bm.free()
        if solidified is not None:
            remove_object(solidified)
        raise FxError(L(f"'{target.name}' 에 면이 없어 조각낼 수 없습니다.",
                        f"'{target.name}' has no faces, so it cannot be fractured."))

    # 2) 재질 슬롯: 겉면 + 속면
    mats = [mm for mm in target.data.materials if mm is not None]
    if not mats:
        mats = [simple_material(f"FX_Ext_{material}", (0.55, 0.53, 0.50), roughness=0.9)]
    interior_index = len(mats)
    if interior_kind == "none":
        interior_index = 0
        all_mats = mats
    else:
        color = m["interior"] if interior_kind == "auto" else MATERIALS.get(interior_kind, m)["interior"]
        all_mats = mats + [interior_material(f"FX_Int_{interior_kind}", color)]

    # 3) 수리된 메시를 임시 오브젝트로 만들고, 보로노이 셀과 불리언(교집합) 해서 조각을 만든다
    local_lo = Vector((min(v.co.x for v in bm.verts), min(v.co.y for v in bm.verts), min(v.co.z for v in bm.verts)))
    local_hi = Vector((max(v.co.x for v in bm.verts), max(v.co.y for v in bm.verts), max(v.co.z for v in bm.verts)))
    prep = new_mesh_object(f"FX_Prep_{target.name}", bm, target.matrix_world.copy(), tag="cell")
    bm.free()
    if solidified is not None:
        remove_object(solidified)
    prep.hide_render = True
    for mm in all_mats:
        prep.data.materials.append(mm)
    # 겹치거나 맞닿은 덩어리를 먼저 하나의 solid 로 정리한다. 이걸 빼먹으면 셀 불리언이
    # 빈 결과를 내서 조각이 통째로 사라진다(무료 에셋에서 흔함).
    resolved, source_volume, prep_closed = resolve_solid(prep, local_lo, local_hi)
    prep_health = object_health(prep)
    # 완전히 닫히지 않아도 구멍이 몇 개뿐이면 안쪽 판정을 쓴다. 안 쓰면 씨앗이 허공에 떨어져
    # 요청한 조각 수가 안 나온다(캐릭터 모델에서 60개 요청에 50개).
    use_inside = prep_closed or nearly_closed(prep_health)

    rng = random.Random(seed)
    # 표면에 딱 붙은 씨앗은 얇아서 버려지는 조각을 만든다. 크기에 비례해 살짝 안쪽만 쓴다.
    seed_margin = max(local_hi.x - local_lo.x, local_hi.y - local_lo.y, local_hi.z - local_lo.z) * 0.002
    anchor = impact_anchor(lo, hi, side, height_frac)
    aim = surface_aim(prep, lo, hi, side, height_frac)
    if aim is not None:
        anchor = aim
    mw_inv = target.matrix_world.inverted() if abs(target.matrix_world.determinant()) > 1e-12 else Matrix.Identity(4)
    # 조각 하나의 예상 반지름. 씨앗끼리 이보다 가까우면 종잇장 같은 조각이 나온다.
    min_sep = (source_volume / max(pieces, 1)) ** (1.0 / 3.0) * 0.55 if source_volume > 1e-9 else 0.0
    seeds = voronoi_seeds(local_lo, local_hi, pieces, pattern, focus, mw_inv @ anchor, rng,
                          inside=inside_tester(prep, margin=seed_margin) if use_inside else None,
                          min_sep=min_sep)
    cell_objs = voronoi_cell_objects(local_lo, local_hi, seeds, target.matrix_world,
                                     all_mats[interior_index] if interior_index < len(all_mats) else all_mats[0])
    coll = get_collection("FX_Chunks")
    cells_built = len(cell_objs)
    # 정리가 안 된 메시(부품끼리 관통)는 셀 불리언에서 자기교차 처리를 켜야 조각이 안 사라진다
    chunks = boolean_chunks(prep, cell_objs, all_mats, coll, f"{target.name}_chunk", use_self=not resolved)
    for c in cell_objs:
        remove_object(c)
    remove_object(prep)
    view_layer_update()
    if not chunks:
        raise FxError(L("조각을 하나도 만들지 못했습니다. pieces 를 줄이거나 repair=True 로 다시 시도하세요.",
                        "No chunks could be created. Lower pieces or try repair=True."))

    chunk_volume = 0.0
    open_chunks = 0
    for o in chunks:
        o["fx_chunk_of"] = target.name  # 임시 오브젝트가 아니라 진짜 주인 이름을 적어야 정리가 된다
        center_origin(o)
        vol, closed = mesh_volume(o)
        o["fx_volume"] = vol
        chunk_volume += vol
        if not closed:
            open_chunks += 1
    view_layer_update()
    add_rigid_bodies(chunks, "ACTIVE")

    # 4) 물리 값
    shape = collision
    if shape == "auto":
        shape = "CONVEX_HULL"
    else:
        shape = {"convex": "CONVEX_HULL", "mesh": "MESH", "box": "BOX", "sphere": "SPHERE"}[shape]
    total_mass = 0.0
    for o in chunks:
        rb = o.rigid_body
        vol = max(float(o.get("fx_volume", 0.0)), 1e-6)
        rb.mass = max(0.2, density * vol)
        rb.collision_shape = shape
        rb.friction = friction
        rb.restitution = bounce
        rb.collision_margin = margin
        rb.use_margin = margin > 0
        # 맞기 전까지 잠들어 있어야 구조가 서 있는다. 접착 제약은 깨어날 때 이웃도 같이 깨운다
        rb.use_deactivation = True
        rb.deactivate_linear_velocity = 0.4
        rb.deactivate_angular_velocity = 0.5
        if hold_until > 0:
            rb.use_start_deactivated = False
            rb.kinematic = True
            rb.keyframe_insert("kinematic", frame=1)
            rb.keyframe_insert("kinematic", frame=hold_until)
            rb.kinematic = False
            rb.keyframe_insert("kinematic", frame=hold_until + 1)
        else:
            rb.use_start_deactivated = True
        total_mass += rb.mass

    avg_mass = total_mass / max(len(chunks), 1)
    glued = glue_chunks(chunks, GLUE_LEVELS[glue] * avg_mass,
                        max_neighbors=int(p.get("glue_neighbors", 4)),
                        max_constraints=int(p.get("glue_max", 600))) if glue != "none" else 0

    sc.frame_start = 1
    sc.frame_end = frames
    frames_in = hold_until if hold_until > 0 else 12
    if side == "none":
        radius, method = 0.0, "none"
    else:
        _imp, radius, method = add_impactor(lo, hi, side, height_frac, aim=aim, frames_in=frames_in,
                                            mass=max(300.0, total_mass * impact_power))

    size = hi - lo
    dust_total = add_dust(chunks, DUST_LEVELS[dust], f_impact=sc.frame_start + frames_in,
                          size_ref=max(size.x, size.y, size.z))

    rbw = sc.rigidbody_world
    rbw.time_scale = time_scale
    rbw.substeps_per_frame = int(p.get("substeps") or rbw.substeps_per_frame or 10)
    rbw.solver_iterations = int(p.get("solver_iterations") or rbw.solver_iterations or 10)
    rbw.point_cache.frame_start = 1
    rbw.point_cache.frame_end = frames

    target.hide_render = True
    target.hide_viewport = True

    bake_method = bake_pointcaches(frames)

    start_pos = {o.name: o.matrix_world.translation.copy() for o in chunks}
    sc.frame_set(frames)
    view_layer_update()
    moved = sum(1 for o in chunks if (o.matrix_world.translation - start_pos[o.name]).length > 0.05)
    max_fall = max((start_pos[o.name].z - o.matrix_world.translation.z) for o in chunks) if chunks else 0.0
    sc.frame_set(1)

    volume_kept = round(chunk_volume / source_volume, 3) if source_volume > 1e-9 else None
    notes = []
    if volume_kept is not None and not (0.85 <= volume_kept <= 1.15):
        notes.append(L(f"조각 부피 합이 원본의 {int(volume_kept * 100)}% 입니다. 메시가 닫혀 있지 않거나 조각이 겹칠 수 있습니다.",
                       f"Chunk volume is {int(volume_kept * 100)}% of the original. The mesh may be open or chunks may overlap."))
    if len(chunks) < pieces * 0.8:
        notes.append(L(f"요청한 {pieces}개 중 {len(chunks)}개만 만들어졌습니다(빈 셀은 버림). 모양이 복잡하면 생깁니다.",
                       f"Only {len(chunks)} of {pieces} requested chunks were created (empty cells dropped)."))
    if open_chunks:
        notes.append(L(f"조각 {open_chunks}개가 닫히지 않았습니다. 무게는 어림값입니다.",
                       f"{open_chunks} chunks are not closed; their mass is estimated."))
    was_shell = not repair_info["before"]["closed"] if repair_info else not health["closed"]
    if was_shell and total_mass > 0:
        light = max(50, int(total_mass / 20 / max(source_volume, 1e-6)))
        notes.append(L(
            f"이 모델은 원래 속이 빈 껍데기입니다. 무게는 속이 꽉 찬 것으로 계산해 {round(total_mass)}kg 입니다. "
            f"가볍게 하려면 density 를 낮추세요(예: density={light} 이면 약 {round(total_mass / 20)}kg).",
            f"This model is a hollow shell. Mass assumes a solid body, giving {round(total_mass)}kg. "
            f"Lower it with density (e.g. density={light} gives about {round(total_mass / 20)}kg)."))
    if ratio < 1.0:
        notes.append(L(f"면이 많아 {int(ratio * 100)}% 로 줄여서 조각냈습니다.",
                       f"The mesh was decimated to {int(ratio * 100)}% before fracturing."))

    return dict(
        target=target.name, pieces=len(chunks), requested=pieces, material=material, impact=side, frames=frames,
        time_scale=time_scale, total_mass_kg=round(total_mass), impactor_radius_m=round(radius, 2),
        impactor=method, bake=bake_method, moved_ratio=round(moved / max(len(chunks), 1), 2),
        dust=dust, dust_particles=dust_total, glue=glue, glue_constraints=glued,
        max_fall_m=round(max_fall, 2), pattern=pattern, focus=focus, collision=shape,
        density=density, friction=friction, bounce=bounce, interior=interior_kind,
        mesh_closed=health["closed"], open_chunks=open_chunks, cells_built=cells_built,
        empty_cells=cells_built - len(chunks), solid_resolved=resolved,
        source_volume_m3=round(source_volume, 3),
        chunk_volume_m3=round(chunk_volume, 3), volume_kept=volume_kept,
        repaired=dict(merged_verts=repair_info["merged_verts"], filled_faces=repair_info["filled_faces"]) if repair_info else None,
        notes=notes,
    )


run_guarded(main)
