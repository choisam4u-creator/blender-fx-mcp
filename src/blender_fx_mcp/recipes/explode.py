# 폭발 레시피: 연기·불(Mantaflow) + 순간 힘장(주변 조각을 날린다).
# target 이 있으면 그 건물 중심(높이 40%)에서 터진다. 조각은 destroy(impact="none", hold_until=burst_frame) 로 미리 만들어 둔다.
# PARAMS: target, at([x,y,z]), radius, power, fire, frames, burst_frame, resolution, cache_dir

EXPLODE_ROLES = ("smoke_domain", "smoke_flow", "blast")


def cleanup_explosion():
    for o in list(bpy.data.objects):
        if o.get(FX_TAG) in EXPLODE_ROLES:
            remove_object(o)


def blast_geometry(p):
    """폭발 중심, 반지름, 카메라용 상자, 바닥 높이를 정한다."""
    target = p.get("target")
    radius = float(p.get("radius") or 0.0)
    if target:
        t = get_target(target)
        lo, hi = world_bbox(t)
        size = hi - lo
        center = Vector((lo.x + size.x / 2, lo.y + size.y / 2, lo.z + size.z * 0.4))
        radius = radius or max(0.5, 0.45 * min(size.x, size.y))
        return center, radius, lo, hi, lo.z
    at = p.get("at") or [0.0, 0.0, 1.0]
    center = Vector((float(at[0]), float(at[1]), float(at[2])))
    radius = radius or 1.0
    ground_z = 0.0 if center.z >= 0.0 else center.z - radius
    lo = Vector((center.x - radius * 4, center.y - radius * 4, ground_z))
    hi = Vector((center.x + radius * 4, center.y + radius * 4, ground_z + radius * 6))
    return center, radius, lo, hi, ground_z


def make_domain(center, radius, ground_z, frames, resolution, cache_dir, fire, size):
    """연기가 살 수 있는 상자(도메인). 바닥에서 시작해 위로 넉넉히."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size, v.co.y * size, (v.co.z + 0.5) * size))
    dom = new_mesh_object("FX_SmokeDomain", bm, Matrix.Translation((center.x, center.y, ground_z)), tag="smoke_domain")
    bm.free()
    dom.display_type = "WIRE"

    mod = dom.modifiers.new("Fluid", "FLUID")
    mod.fluid_type = "DOMAIN"
    ds = mod.domain_settings
    ds.domain_type = "GAS"
    ds.resolution_max = int(resolution)
    ds.use_adaptive_domain = True
    ds.cache_type = "ALL"
    ds.cache_frame_start = 1
    ds.cache_frame_end = int(frames)
    ds.cache_directory = cache_dir
    ds.use_noise = False
    ds.vorticity = 0.3
    ds.use_dissolve_smoke = True
    ds.dissolve_speed = 120
    if fire:
        ds.flame_smoke = 1.0
        ds.flame_max_temp = 3.0
        ds.burning_rate = 0.6
        ds.flame_vorticity = 0.5

    dom.data.materials.clear()
    dom.data.materials.append(smoke_material(fire))
    return dom


def make_flow(center, radius, burst, power, fire):
    """터지는 순간 몇 프레임만 연기·불을 뿜는 공."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=radius)
    flow = new_mesh_object("FX_SmokeFlow", bm, Matrix.Translation(center), tag="smoke_flow")
    bm.free()
    flow.display_type = "WIRE"
    flow.hide_render = True
    mod = flow.modifiers.new("Fluid", "FLUID")
    mod.fluid_type = "FLOW"
    fs = mod.flow_settings
    fs.flow_type = "BOTH" if fire else "SMOKE"
    fs.flow_behavior = "INFLOW"
    fs.use_initial_velocity = True
    fs.velocity_normal = 3.5 * power
    fs.velocity_random = 1.2 * power
    fs.density = 2.0
    fs.smoke_color = (0.08, 0.075, 0.07)
    fs.subframes = 2
    if fire:
        fs.fuel_amount = 2.0
        fs.temperature = 2.5
    fs.use_inflow = False
    fs.keyframe_insert("use_inflow", frame=1)
    fs.use_inflow = True
    fs.keyframe_insert("use_inflow", frame=burst)
    fs.use_inflow = False
    fs.keyframe_insert("use_inflow", frame=burst + 5)
    return flow


def make_blast(center, radius, burst, strength):
    """3프레임만 켜지는 힘장. 리지드바디 조각을 밖으로 밀어낸다."""
    e = bpy.data.objects.new("FX_Blast", None)
    e[FX_TAG] = "blast"
    link(e)
    e.location = center
    e.empty_display_type = "SPHERE"
    e.empty_display_size = radius
    # 빈 오브젝트는 힘장 설정이 비어 있어 블렌더 명령으로 켜 줘야 한다
    if e.field is None:
        with bpy.context.temp_override(scene=scene(), object=e, active_object=e, selected_objects=[e]):
            bpy.ops.object.forcefield_toggle()
    f = e.field
    if f is None:
        raise FxError("힘장(force field)을 만들지 못했습니다.")
    f.type = "FORCE"
    f.shape = "POINT"
    f.falloff_type = "SPHERE"
    f.falloff_power = 1.0
    f.use_max_distance = True
    f.distance_max = radius * 8.0
    f.strength = 0.0
    f.keyframe_insert("strength", frame=max(1, burst - 1))
    f.strength = strength
    f.keyframe_insert("strength", frame=burst)
    f.keyframe_insert("strength", frame=burst + 4)
    f.strength = 0.0
    f.keyframe_insert("strength", frame=burst + 5)
    return e


def main():
    p = PARAMS
    frames = max(12, int(p.get("frames", 72)))
    burst = max(2, min(int(p.get("burst_frame", 12)), frames - 6))
    power = max(0.1, float(p.get("power", 1.0)))
    fire = bool(p.get("fire", True))
    resolution = max(16, min(int(p.get("resolution", 48)), 256))
    cache_dir = p.get("cache_dir") or os.path.join(os.path.expanduser("~"), "blender-fx-output", "cache_fluid")
    os.makedirs(cache_dir, exist_ok=True)

    sc = scene()
    cleanup_explosion()
    center, radius, lo, hi, ground_z = blast_geometry(p)
    ensure_ground(ground_z)
    ensure_camera(lo, hi)
    ensure_light()
    sc.frame_start = 1
    sc.frame_end = frames

    # 힘 크기: 주변 조각 무게에 비례 (없으면 가벼운 물건 기준).
    # 힘장은 프레임당 첫 서브스텝에만 걸려 실제로는 1/10 로 희석되므로 크게 잡는다.
    chunks = [o for o in bpy.data.objects if o.get(FX_TAG) == "chunk" and o.rigid_body is not None]
    total_mass = sum(o.rigid_body.mass for o in chunks)
    strength = power * (total_mass * 60.0 if total_mass > 0 else 40000.0)

    size = hi - lo
    dom_size = max(radius * 10.0, size.z * 2.2, size.x * 3.0, size.y * 3.0)
    dom = make_domain(center, radius, ground_z, frames, resolution, cache_dir, fire, dom_size)
    effectors = add_fluid_effectors(chunks) if p.get("smoke_collision") else 0
    make_flow(center, radius, burst, power, fire)
    make_blast(center, radius, burst, strength)

    # 조각 물리 다시 굽기 (힘장이 생겼으니), 그 다음 연기 굽기
    free_bake()
    rb_method = bake_pointcaches(frames)
    bake_fluid(dom)
    cache_files = count_cache_files(cache_dir)
    if cache_files == 0:
        raise FxError(L("연기 굽기 결과가 비어 있습니다. resolution 을 낮추거나 frames 를 줄여 다시 시도하세요.",
                        "The smoke bake produced nothing. Lower resolution or frames and try again."))

    start_pos = {o.name: o.matrix_world.translation.copy() for o in chunks}
    sc.frame_set(frames)
    view_layer_update()
    moved = sum(1 for o in chunks if (o.matrix_world.translation - start_pos[o.name]).length > 0.05)
    sc.frame_set(1)

    return dict(
        center=[round(v, 2) for v in center], radius=round(radius, 2), frames=frames, burst_frame=burst,
        power=power, fire=fire, resolution=resolution, chunks=len(chunks), blast_strength=round(strength),
        moved_ratio=round(moved / max(len(chunks), 1), 2) if chunks else None,
        rigid_bake=rb_method, cache_files=cache_files, cache_dir=cache_dir, smoke_effectors=effectors,
    )


run_guarded(main)
