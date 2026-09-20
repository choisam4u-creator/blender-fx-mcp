# 바람: 파티클·천·연기를 미는 힘장. PARAMS: direction_deg(0=+Y 쪽으로, 90=+X 쪽으로), strength, turbulence, at


def main():
    p = PARAMS
    for o in list(bpy.data.objects):
        if o.get(FX_TAG) in ("wind", "turbulence"):
            remove_object(o)
    strength = float(p.get("strength", 3.0))
    turb = float(p.get("turbulence", 0.0))
    deg = float(p.get("direction_deg", 90.0))
    lo, hi = fx_bbox(None)
    a = p.get("at")
    center = Vector((float(a[0]), float(a[1]), float(a[2]))) if a else Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, (lo.z + hi.z) / 2))

    d = Vector((math.sin(math.radians(deg)), math.cos(math.radians(deg)), 0.0))
    wind = make_force_field("FX_Wind", "wind", "WIND", center - d * 5.0)
    wind.rotation_euler = d.to_track_quat("Z", "Y").to_euler()  # 바람 힘장은 자기 Z 축 방향으로 분다
    wind.field.strength = strength
    wind.field.flow = 0.2
    wind.field.noise = 0.3
    wind.empty_display_type = "SINGLE_ARROW"
    wind.empty_display_size = 2.0
    made = ["FX_Wind"]
    if turb > 0:
        t = make_force_field("FX_Turbulence", "turbulence", "TURBULENCE", center)
        t.field.strength = turb
        t.field.size = 2.0
        t.field.flow = 0.5
        made.append("FX_Turbulence")
    # 이미 구운 시뮬레이션이 있으면 다시 굽는다
    if scene().rigidbody_world is not None or any(o.particle_systems for o in bpy.data.objects):
        free_bake()
        bake_pointcaches(scene().frame_end)
    return dict(direction_deg=deg, strength=strength, turbulence=turb, objects=made)


run_guarded(main)
