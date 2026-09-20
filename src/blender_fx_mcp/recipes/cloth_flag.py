# 깃발(천 시뮬레이션): 깃대에 한쪽을 고정한 천이 바람에 펄럭인다. PARAMS: at, width, height, pole_height, wind_strength, frames


def main():
    p = PARAMS
    for o in list(bpy.data.objects):
        if o.get(FX_TAG) in ("flag", "pole"):
            remove_object(o)
    a = p.get("at") or [0.0, 0.0, 0.0]
    at = Vector((float(a[0]), float(a[1]), float(a[2])))
    width = float(p.get("width", 3.0))
    height = float(p.get("height", 2.0))
    pole_h = float(p.get("pole_height") or height * 2.5)
    wind_strength = float(p.get("wind_strength", 6.0))
    frames = max(12, int(p.get("frames") or min(scene().frame_end, 96)))
    sc = scene()
    set_frame_end(frames)

    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=12, radius1=0.05, radius2=0.04, depth=pole_h)
    pole = new_mesh_object("FX_FlagPole", bm, Matrix.Translation((at.x, at.y, at.z + pole_h / 2)), tag="pole")
    bm.free()
    pole.data.materials.append(simple_material("FX_Pole", (0.6, 0.6, 0.62), roughness=0.4))

    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=28, y_segments=18, size=0.5)
    top = at.z + pole_h - 0.05
    for v in bm.verts:
        v.co = Vector((0.06 + (v.co.x + 0.5) * width, 0.0, top - (0.5 - v.co.y) * height))
    flag = new_mesh_object("FX_Flag", bm, Matrix.Translation((at.x, at.y, 0.0)), tag="flag")
    bm.free()
    flag.data.materials.append(simple_material("FX_FlagCloth", (0.85, 0.15, 0.12), roughness=0.8))

    # 깃대 쪽 세로줄을 고정
    xs = [v.co.x for v in flag.data.vertices]
    min_x = min(xs)
    pinned = [v.index for v in flag.data.vertices if abs(v.co.x - min_x) < 1e-4]
    vg = flag.vertex_groups.new(name="FX_Pin")
    vg.add(pinned, 1.0, "REPLACE")

    mod = flag.modifiers.new("FX_Cloth", "CLOTH")
    s = mod.settings
    s.vertex_group_mass = "FX_Pin"
    s.quality = 5
    s.mass = 0.3
    s.tension_stiffness = 5.0
    s.compression_stiffness = 5.0
    s.shear_stiffness = 5.0
    s.bending_stiffness = 0.05
    s.air_damping = 1.0
    mod.point_cache.frame_start = 1
    mod.point_cache.frame_end = frames

    if not any(o.get(FX_TAG) == "wind" for o in bpy.data.objects):
        wind = make_force_field("FX_Wind", "wind", "WIND", Vector((at.x - 4.0, at.y, top - height / 2)))
        wind.rotation_euler = Vector((1.0, 0.0, 0.0)).to_track_quat("Z", "Y").to_euler()
        wind.field.strength = wind_strength
        wind.field.noise = 0.5
        wind.field.flow = 0.3

    ensure_ground(at.z)
    ensure_camera(Vector((at.x - 1.0, at.y - 1.0, at.z)), Vector((at.x + width + 1.0, at.y + 1.0, top + 0.5)))
    ensure_light()
    method = bake_pointcaches(sc.frame_end)

    # 실제로 펄럭였는지: 마지막 프레임에서 끝 정점 위치 비교
    dg = bpy.context.evaluated_depsgraph_get()
    sc.frame_set(1)
    v0 = flag.evaluated_get(dg).data.vertices[-1].co.copy()
    sc.frame_set(sc.frame_end)
    dg = bpy.context.evaluated_depsgraph_get()
    v1 = flag.evaluated_get(dg).data.vertices[-1].co.copy()
    sc.frame_set(1)
    return dict(width=width, height=height, pole_height=pole_h, pinned=len(pinned), frames=frames, bake=method,
                tip_moved_m=round((v1 - v0).length, 2))


run_guarded(main)
