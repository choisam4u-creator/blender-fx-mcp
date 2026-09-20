# 계속 타오르는 불 / 피어오르는 연기 (Mantaflow). target 이 있으면 그 표면에서, 없으면 at 위치의 공에서 나온다.
# PARAMS: kind(fire|smoke|both), target, at, radius, power, frames, start_frame, end_frame, resolution, cache_dir

EMIT_ROLES = ("emit_domain", "emit_flow", "emit_obstacle")


def cleanup_emit():
    for o in list(bpy.data.objects):
        if o.get(FX_TAG) in EMIT_ROLES:
            remove_object(o)
    for o in bpy.data.objects:
        m = o.modifiers.get("FX_Emit")
        if m is not None:
            o.modifiers.remove(m)


def main():
    p = PARAMS
    kind = p.get("kind", "fire")
    if kind not in ("fire", "smoke", "both"):
        raise FxError(L(f"kind 는 fire / smoke / both 중 하나여야 합니다. 받은 값: {kind}",
                        f"kind must be fire / smoke / both, got: {kind}"))
    fire = kind in ("fire", "both")
    frames = max(12, int(p.get("frames", 72)))
    start = max(1, int(p.get("start_frame") or 1))
    end = int(p.get("end_frame") or 0) or frames
    power = max(0.1, float(p.get("power", 1.0)))
    resolution = int(p.get("resolution", 0) or 0)  # 0 이면 대상 크기에 맞춰 자동
    cache_dir = p.get("cache_dir") or os.path.join(os.path.expanduser("~"), "blender-fx-output", "cache_emit")
    os.makedirs(cache_dir, exist_ok=True)

    sc = scene()
    cleanup_emit()
    target_name = p.get("target")
    radius = float(p.get("radius") or 0.0)
    if target_name:
        t = get_target(target_name)
        unhide(t)
        lo, hi = world_bbox(t)
        size = hi - lo
        center = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
        radius = radius or max(size.x, size.y) / 2
        flow_obj = t
        mod = t.modifiers.new("FX_Emit", "FLUID")
        # 같은 모양의 복사본을 장애물로 두면 불이 건물 안이 아니라 표면 바깥에서만 생겨 벽을 타고 오른다
        shell = t.copy()
        shell.name = f"FX_EmitObstacle_{t.name}"
        shell[FX_TAG] = "emit_obstacle"
        shell.modifiers.clear()
        shell.hide_render = True
        shell.display_type = "WIRE"
        link(shell)
        smod = shell.modifiers.new("FX_EmitObstacle", "FLUID")
        smod.fluid_type = "EFFECTOR"
        smod.effector_settings.effector_type = "COLLISION"
        smod.effector_settings.use_effector = True
    else:
        a = p.get("at") or [0.0, 0.0, 0.5]
        center = Vector((float(a[0]), float(a[1]), float(a[2])))
        radius = radius or 0.5
        lo = Vector((center.x - radius, center.y - radius, center.z - radius))
        hi = Vector((center.x + radius, center.y + radius, center.z + radius))
        size = hi - lo
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=radius)
        flow_obj = new_mesh_object("FX_EmitFlow", bm, Matrix.Translation(center), tag="emit_flow")
        bm.free()
        flow_obj.display_type = "WIRE"
        flow_obj.hide_render = True
        mod = flow_obj.modifiers.new("FX_Emit", "FLUID")

    mod.fluid_type = "FLOW"
    fs = mod.flow_settings
    fs.flow_type = "BOTH" if fire else "SMOKE"
    fs.flow_behavior = "INFLOW"
    fs.use_initial_velocity = True
    fs.velocity_normal = 1.2 * power
    fs.velocity_random = 0.4 * power
    fs.density = 1.0
    fs.smoke_color = (0.15, 0.14, 0.13) if fire else (0.35, 0.35, 0.36)
    # 표면 바깥 띠에서 불이 난다. 띠가 복셀 하나보다 얇으면 벽의 불이 사라지므로 크기에 비례
    fs.surface_distance = max(0.5, max(size.x, size.y, size.z) * 0.08)
    fs.subframes = 1
    if fire:
        fs.fuel_amount = 0.5 * power
        fs.temperature = 1.2
    fs.use_inflow = False
    fs.keyframe_insert("use_inflow", frame=1)
    fs.use_inflow = True
    fs.keyframe_insert("use_inflow", frame=start)
    if end < frames:
        fs.use_inflow = False
        fs.keyframe_insert("use_inflow", frame=end + 1)

    # 도메인: 대상 폭의 2.5배, 위로는 대상 높이 + 폭의 1.5배 (너무 크면 같은 해상도에서 불이 뭉개진다)
    ground_z = lo.z
    w = max(size.x, size.y, radius * 2) * 2.5 * max(1.0, power ** 0.5)
    h = (hi.z - lo.z) + max(size.x, size.y, radius * 2) * 1.5 * max(1.0, power ** 0.5)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * w, v.co.y * w, (v.co.z + 0.5) * h))
    dom = new_mesh_object("FX_EmitDomain", bm, Matrix.Translation((center.x, center.y, ground_z)), tag="emit_domain")
    bm.free()
    dom.display_type = "WIRE"
    if resolution <= 0:
        # 불이 나는 띠가 격자 몇 칸은 되어야 벽에 불이 붙는다
        resolution = int(min(128, max(32, round(max(w, h) / max(0.12, radius * 0.30)))))
    resolution = max(16, min(resolution, 256))

    dmod = dom.modifiers.new("Fluid", "FLUID")
    dmod.fluid_type = "DOMAIN"
    ds = dmod.domain_settings
    ds.domain_type = "GAS"
    ds.resolution_max = resolution
    ds.use_adaptive_domain = True
    ds.cache_type = "ALL"
    ds.cache_frame_start = 1
    ds.cache_frame_end = frames
    ds.cache_directory = cache_dir
    ds.use_noise = bool(p.get("noise", False))
    ds.vorticity = float(p.get("vorticity", 0.35))
    ds.use_dissolve_smoke = True
    ds.dissolve_speed = int(p.get("dissolve", 160))
    for attr, key, default in (("alpha", "buoyancy_density", None), ("beta", "buoyancy_heat", None)):
        if p.get(key) is not None:
            try:
                setattr(ds, attr, float(p[key]))
            except Exception:
                pass
    if fire:
        ds.flame_smoke = 0.8
        ds.flame_max_temp = 3.0
        ds.burning_rate = float(p.get("burn_rate", 0.9))
        ds.flame_vorticity = 0.6
    dom.data.materials.clear()
    mat = smoke_material(fire, name="FX_EmitSmoke")
    vol = next((n for n in mat.node_tree.nodes if n.type == "VOLUME_PRINCIPLED"), None)
    if vol is not None:
        vol.inputs["Density"].default_value = float(p.get("density", 3.5))
    dom.data.materials.append(mat)

    effectors = 0
    if p.get("smoke_collision"):
        others = [o for o in mesh_objects() if o.get(FX_TAG) in ("chunk", None) and o is not flow_obj and not o.hide_viewport]
        effectors = add_fluid_effectors([o for o in others if o.get(FX_TAG) == "chunk"])

    sc.frame_start = 1
    sc.frame_end = frames
    ensure_ground(ground_z)
    ensure_camera(Vector((center.x - w / 2, center.y - w / 2, ground_z)), Vector((center.x + w / 2, center.y + w / 2, ground_z + h * 0.7)))
    ensure_light()
    bake_fluid(dom)
    cache_files = count_cache_files(cache_dir)
    if cache_files == 0:
        raise FxError(L("연기 굽기 결과가 비어 있습니다. resolution 을 낮추거나 frames 를 줄여 다시 시도하세요.",
                        "The smoke bake produced nothing. Lower resolution or frames and try again."))
    sc.frame_set(1)
    return dict(kind=kind, target=target_name, smoke_effectors=effectors, at=[round(v, 2) for v in center], radius=round(radius, 2), frames=frames,
                emit_frames=[start, end], resolution=resolution, domain_size_m=[round(w, 1), round(w, 1), round(h, 1)],
                cache_files=cache_files, cache_dir=cache_dir)


run_guarded(main)
