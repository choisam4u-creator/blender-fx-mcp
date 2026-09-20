# 파티클 프리셋: 비 / 눈 / 불꽃 / 재. 같은 종류를 다시 부르면 이전 것을 바꾼다.
# PARAMS: kind(rain|snow|sparks|ash), at, target, area(m), count, frames, start_frame, height(m)

KINDS = ("rain", "snow", "sparks", "ash")


def cleanup_kind(kind):
    for o in list(bpy.data.objects):
        if o.get(FX_TAG) == "particles" and o.get("fx_kind") == kind:
            remove_object(o)
    ps = bpy.data.particles.get(f"FX_Particles_{kind}")
    if ps is not None and ps.users == 0:
        bpy.data.particles.remove(ps)


def make_bit(kind):
    bm = bmesh.new()
    if kind == "rain":
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=6, radius1=0.008, radius2=0.008, depth=0.3)
        mat = simple_material("FX_RainDrop", (0.75, 0.85, 0.95), roughness=0.1, alpha=0.6)
    elif kind == "snow":
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.04)
        mat = simple_material("FX_SnowFlake", (0.95, 0.96, 1.0), roughness=0.9)
    elif kind == "sparks":
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.015)
        mat = simple_material("FX_Spark", (1.0, 0.55, 0.15), roughness=0.5, emission=(1.0, 0.45, 0.1), emission_strength=30.0)
    else:
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.03)
        mat = simple_material("FX_Ash", (0.35, 0.33, 0.31), roughness=1.0)
    o = new_mesh_object(f"FX_ParticleBit_{kind}", bm, Matrix.Translation((0.0, 0.0, -500.0)), tag="particles")
    bm.free()
    o["fx_kind"] = kind
    o.data.materials.append(mat)
    return o


def main():
    p = PARAMS
    kind = p.get("kind", "snow")
    if kind not in KINDS:
        raise FxError(L(f"kind 는 {list(KINDS)} 중 하나여야 합니다. 받은 값: {kind}",
                        f"kind must be one of {list(KINDS)}, got: {kind}"))
    frames = max(12, int(p.get("frames") or min(scene().frame_end, 96)))
    start = max(1, int(p.get("start_frame") or 1))
    sc = scene()
    cleanup_kind(kind)
    set_frame_end(frames)

    lo, hi = fx_bbox(p.get("target") or None)
    size = hi - lo
    a = p.get("at")
    center = Vector((float(a[0]), float(a[1]), float(a[2]))) if a else Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
    area = float(p.get("area") or max(size.x, size.y, 4.0) * 3.0)
    height = float(p.get("height") or (hi.z - lo.z) + 6.0)
    ground_z = lo.z

    bit = make_bit(kind)
    ps = bpy.data.particles.new(f"FX_Particles_{kind}")
    ps.type = "EMITTER"
    ps.render_type = "OBJECT"
    ps.instance_object = bit
    ps.particle_size = 1.0
    ps.emit_from = "FACE"
    ps.distribution = "RAND"
    ps.use_emit_random = True
    ps.physics_type = "NEWTON"

    bm = bmesh.new()
    if kind == "sparks":
        count = int(p.get("count") or 600)
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.15)
        emitter = new_mesh_object("FX_ParticleEmitter_sparks", bm, Matrix.Translation(center if a else Vector((center.x, center.y, ground_z + size.z * 0.4))), tag="particles")
        ps.count = count
        ps.frame_start = start
        ps.frame_end = start + 6
        ps.lifetime = 25
        ps.lifetime_random = 0.5
        ps.normal_factor = 7.0
        ps.factor_random = 4.0
        ps.effector_weights.gravity = 0.7
        ps.size_random = 0.5
    else:
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=area / 2)
        top = ground_z + height
        emitter = new_mesh_object(f"FX_ParticleEmitter_{kind}", bm, Matrix.Translation((center.x, center.y, top)), tag="particles")
        ps.frame_start = start
        ps.frame_end = frames
        if kind == "rain":
            ps.count = int(p.get("count") or int(area * area * 25))
            ps.lifetime = max(12, int(height / 12.0 * sc.render.fps) + 4)
            ps.object_align_factor = (0.0, 0.0, -12.0)
            ps.normal_factor = 0.0
            ps.effector_weights.gravity = 0.3
        elif kind == "snow":
            ps.count = int(p.get("count") or int(area * area * 12))
            ps.lifetime = max(24, int(height / 0.8 * sc.render.fps) + 12)
            ps.object_align_factor = (0.0, 0.0, -0.8)
            ps.normal_factor = 0.0
            ps.factor_random = 0.3
            ps.brownian_factor = 0.4
            ps.drag_factor = 0.2
            ps.effector_weights.gravity = 0.02
            ps.size_random = 0.6
        else:  # ash: 천천히 떠다니며 가라앉는다
            ps.count = int(p.get("count") or int(area * area * 6))
            ps.lifetime = frames
            ps.object_align_factor = (0.0, 0.0, -0.3)
            ps.normal_factor = 0.0
            ps.factor_random = 0.5
            ps.brownian_factor = 0.6
            ps.drag_factor = 0.3
            ps.effector_weights.gravity = 0.01
            ps.size_random = 0.7
    bm.free()
    ps.count = min(ps.count, int(p.get("count") or 20000))  # 넓은 장면에서 수십만 개가 되는 걸 막는다
    # 사용자가 준 값으로 덮어쓴다 (안 주면 프리셋 그대로)
    for key, attr in (("size", "particle_size"), ("size_random", "size_random"), ("drag", "drag_factor"),
                      ("brownian", "brownian_factor"), ("lifetime", "lifetime"), ("speed", "normal_factor"),
                      ("randomness", "factor_random")):
        if p.get(key) is not None:
            try:
                setattr(ps, attr, type(getattr(ps, attr))(p[key]))
            except Exception:
                pass
    if p.get("gravity") is not None:
        ps.effector_weights.gravity = float(p["gravity"])
    emitter["fx_kind"] = kind
    emitter.show_instancer_for_render = False
    emitter.show_instancer_for_viewport = False
    mod = emitter.modifiers.new("FX_Particles", "PARTICLE_SYSTEM")
    mod.particle_system.settings = ps
    for orphan in list(bpy.data.particles):
        if orphan.users == 0:
            bpy.data.particles.remove(orphan)

    # 바닥에 닿으면 사라지게 (바다가 바닥이면 바닥 평면이 없다)
    ground = ensure_ground(ground_z)
    if ground is not None and ground.modifiers.get("FX_Collision") is None:
        ground.modifiers.new("FX_Collision", "COLLISION")
        ground.collision.use_particle_kill = True
    ensure_camera(lo, hi)
    ensure_light()
    method = bake_pointcaches(sc.frame_end)
    sc.frame_set(1)
    return dict(kind=kind, count=ps.count, frames=[int(ps.frame_start), int(ps.frame_end)], lifetime=ps.lifetime,
                area_m=round(area, 1), bake=method, size=round(ps.particle_size, 3),
                gravity=round(ps.effector_weights.gravity, 3), drag=round(ps.drag_factor, 3))


run_guarded(main)
