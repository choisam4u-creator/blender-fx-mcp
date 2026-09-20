# 물: 방향·속도·모양·점성을 정해서 떨어뜨리거나 쏘거나 채운다 (Mantaflow 액체).
# PARAMS: mode(drop|stream|pool|object), source_object, at, size, shape(sphere|box|column),
#         direction_deg, pitch_deg, speed, start_frame, duration, liquid, viscosity, surface_tension,
#         gravity_scale, obstacles, spray, resolution, frames, domain_size, domain_at,
#         smoothing, particle_radius, flip_ratio, cache_dir

MODES = ("drop", "stream", "pool", "object")
SHAPES = ("sphere", "box", "column")
# (점성 켜기, 점성 값, 표면장력, 색, 투명도)
LIQUIDS = {
    "water": (False, 0.0, 0.0, (0.55, 0.75, 0.95), 0.72),
    "oil": (True, 0.05, 0.0, (0.20, 0.16, 0.06), 0.85),
    "honey": (True, 2.0, 0.6, (0.85, 0.55, 0.10), 0.88),
    "lava": (True, 8.0, 0.4, (0.95, 0.25, 0.05), 1.0),
    "mercury": (True, 0.01, 2.5, (0.75, 0.76, 0.78), 1.0),
    "slime": (True, 0.6, 1.2, (0.35, 0.80, 0.30), 0.85),
}


def liquid_material(name, color, alpha, emissive=False):
    mat = simple_material(name, color, roughness=0.05, alpha=alpha)
    b = principled(mat)
    set_input(b, "Transmission Weight", 0.6 if alpha < 0.95 else 0.0)
    set_input(b, "IOR", 1.33)
    if emissive:
        set_input(b, "Emission Color", (1.0, 0.35, 0.05, 1.0))
        set_input(b, "Emission Strength", 6.0)
    return mat


def direction_vector(direction_deg, pitch_deg):
    """0도 = +Y 쪽, 90도 = +X 쪽. pitch 0 = 수평, -90 = 아래, +90 = 위."""
    a = math.radians(direction_deg)
    p = math.radians(max(-90.0, min(90.0, pitch_deg)))
    return Vector((math.sin(a) * math.cos(p), math.cos(a) * math.cos(p), math.sin(p)))


def make_source_mesh(shape, size, name, at, tag="liquid_flow"):
    bm = bmesh.new()
    if shape == "sphere":
        bmesh.ops.create_icosphere(bm, subdivisions=3, radius=size)
    elif shape == "box":
        bmesh.ops.create_cube(bm, size=size * 2.0)
    else:  # column: 세로로 긴 기둥
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=16,
                              radius1=size, radius2=size, depth=size * 4.0)
    o = new_mesh_object(name, bm, Matrix.Translation(at), tag=tag)
    bm.free()
    o.display_type = "WIRE"
    o.hide_render = True
    return o


def main():
    p = PARAMS
    mode = p.get("mode", "drop")
    if mode not in MODES:
        raise FxError(L(f"mode 는 {list(MODES)} 중 하나여야 합니다. 받은 값: {mode}",
                        f"mode must be one of {list(MODES)}, got: {mode}"))
    shape = p.get("shape", "sphere")
    if shape not in SHAPES:
        raise FxError(L(f"shape 은 {list(SHAPES)} 중 하나여야 합니다. 받은 값: {shape}",
                        f"shape must be one of {list(SHAPES)}, got: {shape}"))
    liquid = p.get("liquid", "water")
    if liquid not in LIQUIDS:
        raise FxError(L(f"liquid 는 {list(LIQUIDS)} 중 하나여야 합니다. 받은 값: {liquid}",
                        f"liquid must be one of {list(LIQUIDS)}, got: {liquid}"))

    sc = scene()
    frames = max(12, int(p.get("frames", 60)))
    resolution = max(16, min(int(p.get("resolution", 64)), 320))
    start = max(1, int(p.get("start_frame") or 1))
    duration = int(p.get("duration") or max(1, frames // 2))
    speed = float(p.get("speed", 0.0))
    direction_deg = float(p.get("direction_deg", 0.0))
    pitch_deg = float(p.get("pitch_deg", -90.0 if mode == "drop" else 0.0))
    gravity_scale = float(p.get("gravity_scale", 1.0))
    cache_dir = p.get("cache_dir") or os.path.join(os.path.expanduser("~"), "blender-fx-output", "cache_liquid")
    os.makedirs(cache_dir, exist_ok=True)

    use_visc, visc, tension, color, alpha = LIQUIDS[liquid]
    if p.get("viscosity") is not None:
        visc = float(p["viscosity"])
        use_visc = visc > 0
    if p.get("surface_tension") is not None:
        tension = float(p["surface_tension"])

    cleanup_liquid()
    set_frame_end(frames)
    sc.frame_start = 1

    # 1) 물이 나올 곳
    source_name = p.get("source_object")
    if mode == "object":
        if not source_name:
            raise FxError(L("mode='object' 에는 source_object 이름이 필요합니다.",
                            "mode='object' needs a source_object name."))
        flow = get_target(source_name)
        flo, fhi = world_bbox(flow)
        at = (flo + fhi) / 2
        size = max((fhi - flo).length / 2, 0.1)
        own_flow = False
    else:
        a = p.get("at")
        at = Vector((float(a[0]), float(a[1]), float(a[2]))) if a else None
        size = float(p.get("size") or 0.0)
        own_flow = True

    # 2) 물이 부딪힐 물건
    names = p.get("obstacles")
    if names:
        obstacles = [get_target(n) for n in names]
    else:
        obstacles = [o for o in mesh_objects()
                     if o.get(FX_TAG) not in ("liquid_domain", "liquid_flow", "dust", "cell")
                     and not o.hide_viewport and (mode != "object" or o.name != source_name)]
    # 바닥판은 아주 넓어서 크기 계산에 넣으면 물 공간이 쓸데없이 커진다.
    # 도메인 바닥이 이미 바닥 역할을 하므로 장애물에서도 뺀다.
    ground = next((o for o in bpy.data.objects if o.get(FX_TAG) == "ground"), None)
    obstacles = [o for o in obstacles if o is not ground]
    ob_lo = ob_hi = None
    for o in obstacles:
        a2, b2 = world_bbox(o)
        ob_lo = a2 if ob_lo is None else Vector((min(ob_lo.x, a2.x), min(ob_lo.y, a2.y), min(ob_lo.z, a2.z)))
        ob_hi = b2 if ob_hi is None else Vector((max(ob_hi.x, b2.x), max(ob_hi.y, b2.y), max(ob_hi.z, b2.z)))
    if ob_lo is None:
        ob_lo, ob_hi = Vector((-2.0, -2.0, 0.0)), Vector((2.0, 2.0, 2.0))

    if size <= 0:
        size = max(0.25, min((ob_hi - ob_lo).x, (ob_hi - ob_lo).y) * 0.25)
    if at is None:
        if mode == "pool":
            at = Vector(((ob_lo.x + ob_hi.x) / 2, (ob_lo.y + ob_hi.y) / 2, ob_lo.z))
        else:
            at = Vector(((ob_lo.x + ob_hi.x) / 2, (ob_lo.y + ob_hi.y) / 2, ob_hi.z + size * 2.0))

    # 3) 물이 살 공간(도메인): 장애물 + 출발점 + 날아갈 거리를 모두 담는다
    d = direction_vector(direction_deg, pitch_deg)
    travel = max(0.0, speed) * (frames / float(sc.render.fps)) * 0.6
    end = at + d * travel
    pts = [ob_lo, ob_hi, at, end, at + Vector((size, size, size)), at - Vector((size, size, size))]
    lo = Vector((min(v.x for v in pts), min(v.y for v in pts), min(v.z for v in pts)))
    hi = Vector((max(v.x for v in pts), max(v.y for v in pts), max(v.z for v in pts)))
    pad = max(size * 2.0, (hi - lo).length * 0.12, 0.5)
    lo -= Vector((pad, pad, 0.0))
    hi += Vector((pad, pad, pad))
    ground_z = min(lo.z, ob_lo.z)
    lo.z = ground_z
    if p.get("domain_at") and p.get("domain_size"):
        da = p["domain_at"]
        dsz = float(p["domain_size"])
        c = Vector((float(da[0]), float(da[1]), float(da[2])))
        lo = Vector((c.x - dsz / 2, c.y - dsz / 2, c.z))
        hi = Vector((c.x + dsz / 2, c.y + dsz / 2, c.z + dsz))
    dsize = hi - lo

    # 물 덩어리가 격자 한 칸보다 작으면 물이 아예 안 생긴다
    voxel = max(dsize.x, dsize.y, dsize.z) / float(resolution)
    if mode != "pool" and size < voxel * 1.5:
        need = int(math.ceil(max(dsize.x, dsize.y, dsize.z) / (size / 1.5)))
        raise FxError(L(
            f"물 덩어리({size:.2f}m)가 계산 격자 한 칸({voxel:.2f}m)보다 작아 물이 생기지 않습니다. "
            f"size 를 키우거나 resolution 을 {need} 이상으로 올리세요.",
            f"The water source ({size:.2f}m) is smaller than one simulation cell ({voxel:.2f}m), so no liquid forms. "
            f"Increase size, or raise resolution to at least {need}."))

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * dsize.x, v.co.y * dsize.y, (v.co.z + 0.5) * dsize.z))
    dom = new_mesh_object("FX_LiquidDomain", bm,
                          Matrix.Translation(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)), tag="liquid_domain")
    bm.free()
    dom.display_type = "WIRE"
    dmod = dom.modifiers.new("Fluid", "FLUID")
    dmod.fluid_type = "DOMAIN"
    ds = dmod.domain_settings
    ds.domain_type = "LIQUID"
    ds.resolution_max = resolution
    ds.cache_type = "ALL"
    ds.cache_frame_start = 1
    ds.cache_frame_end = frames
    ds.cache_directory = cache_dir
    ds.use_mesh = True
    ds.use_collision_border_top = False
    ds.use_fractions = True  # 얇은 장애물도 물을 막는다
    for attr, val in (("mesh_smoothen_pos", int(p.get("smoothing", 2))),
                      ("mesh_smoothen_neg", int(p.get("smoothing", 2))),
                      ("mesh_particle_radius", float(p.get("particle_radius", 2.0))),
                      ("flip_ratio", float(p.get("flip_ratio", 0.97))),
                      ("use_viscosity", use_visc),
                      ("viscosity_value", visc),
                      ("surface_tension", tension),
                      ("gravity", (0.0, 0.0, -9.81 * gravity_scale))):
        try:
            setattr(ds, attr, val)
        except Exception:
            continue
    if p.get("spray"):
        for attr in ("use_spray_particles", "use_foam_particles", "use_bubble_particles"):
            try:
                setattr(ds, attr, True)
            except Exception:
                pass
    dom.data.materials.clear()
    dom.data.materials.append(liquid_material(f"FX_Liquid_{liquid}", color, alpha, emissive=(liquid == "lava")))

    # 4) 물 덩어리 / 뿜는 입구
    if mode == "pool":
        depth = max(0.05, float(p.get("size") or 0.0) or dsize.z * 0.25)
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co = Vector((v.co.x * (dsize.x * 0.98), v.co.y * (dsize.y * 0.98), (v.co.z + 0.5) * depth))
        flow = new_mesh_object("FX_LiquidFlow", bm,
                               Matrix.Translation(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)), tag="liquid_flow")
        bm.free()
        flow.display_type = "WIRE"
        flow.hide_render = True
    elif own_flow:
        flow = make_source_mesh(shape, size, "FX_LiquidFlow", at)

    fmod = flow.modifiers.get("FX_LiquidFlow") or flow.modifiers.new("FX_LiquidFlow", "FLUID")
    fmod.fluid_type = "FLOW"
    fs = fmod.flow_settings
    fs.flow_type = "LIQUID"
    fs.flow_behavior = "INFLOW" if mode == "stream" else "GEOMETRY"
    if speed > 0:
        fs.use_initial_velocity = True
        fs.velocity_coord = tuple(d * speed)
    fs.subframes = int(p.get("subframes", 1))
    if mode == "stream":
        stop = min(frames, start + duration)
        if start > 1:
            fs.use_inflow = False
            fs.keyframe_insert("use_inflow", frame=start - 1)
        fs.use_inflow = True
        fs.keyframe_insert("use_inflow", frame=start)
        fs.keyframe_insert("use_inflow", frame=stop)
        if stop < frames:
            fs.use_inflow = False
            fs.keyframe_insert("use_inflow", frame=stop + 1)
    else:
        stop = start

    effectors = add_fluid_effectors(obstacles, limit=int(p.get("obstacle_limit", 80)))

    ensure_ground(ground_z)
    ensure_camera(lo, hi)
    ensure_light()
    bake_fluid(dom)
    cache_files = count_cache_files(cache_dir)
    if cache_files == 0:
        raise FxError(L("물 굽기 결과가 비어 있습니다. resolution 을 낮추거나 frames 를 줄여 다시 시도하세요.",
                        "The liquid bake produced nothing. Lower resolution or frames and try again."))

    # 물이 실제로 어디까지 갔는지 (방향이 먹혔는지 숫자로 확인)
    sc.frame_set(min(frames, max(start + 6, frames // 2)))
    view_layer_update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = dom.evaluated_get(dg)
    verts = [dom.matrix_world @ v.co for v in ev.data.vertices]
    if verts:
        wlo = Vector((min(v.x for v in verts), min(v.y for v in verts), min(v.z for v in verts)))
        whi = Vector((max(v.x for v in verts), max(v.y for v in verts), max(v.z for v in verts)))
        wc = (wlo + whi) / 2
        drift = wc - at
    else:
        wlo = whi = wc = drift = Vector((0.0, 0.0, 0.0))
    sc.frame_set(1)

    return dict(mode=mode, liquid=liquid, shape=shape, at=[round(v, 2) for v in at], size=round(size, 2),
                direction_deg=direction_deg, pitch_deg=pitch_deg, speed=speed,
                viscosity=visc, surface_tension=tension, gravity_scale=gravity_scale,
                frames=frames, emit_frames=[start, stop], resolution=resolution,
                domain_size_m=[round(dsize.x, 1), round(dsize.y, 1), round(dsize.z, 1)],
                obstacles=len(obstacles), effectors=effectors, spray=bool(p.get("spray")),
                water_center=[round(v, 2) for v in wc], drift=[round(v, 2) for v in drift],
                water_verts=len(verts), cache_files=cache_files, cache_dir=cache_dir)


run_guarded(main)
