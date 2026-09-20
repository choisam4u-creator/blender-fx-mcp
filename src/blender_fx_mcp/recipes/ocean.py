# 바다 표면(Ocean 모디파이어). 파도가 시간에 따라 움직인다. PARAMS: size(m), wave_scale, choppiness, wind_velocity, frames, z, resolution


def main():
    p = PARAMS
    for o in list(bpy.data.objects):
        if o.get(FX_TAG) == "ocean":
            remove_object(o)
    size = float(p.get("size", 60.0))
    frames = max(12, int(p.get("frames") or min(scene().frame_end, 96)))
    z = float(p.get("z", 0.0))
    sc = scene()
    set_frame_end(frames)
    # 바닥 평면이 있으면 숨긴다 (바다가 바닥)
    for o in bpy.data.objects:
        if o.get(FX_TAG) == "ground":
            o.hide_render = True
            o.hide_viewport = True

    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=size / 2)
    ocean = new_mesh_object("FX_Ocean", bm, Matrix.Translation((0.0, 0.0, z)), tag="ocean")
    bm.free()
    mod = ocean.modifiers.new("FX_Ocean", "OCEAN")
    mod.geometry_mode = "GENERATE"
    mod.spatial_size = int(size)
    mod.repeat_x = 1
    mod.repeat_y = 1
    mod.resolution = int(p.get("resolution", 10))
    try:
        mod.viewport_resolution = int(p.get("resolution", 10))
    except Exception:
        pass
    mod.wave_scale = float(p.get("wave_scale", 1.5))
    mod.choppiness = float(p.get("choppiness", 1.2))
    mod.wind_velocity = float(p.get("wind_velocity", 25.0))
    mod.depth = 200.0
    mod.use_foam = True
    mod.foam_coverage = 0.1
    mod.random_seed = 1
    mod.time = 0.0
    mod.keyframe_insert("time", frame=1)
    mod.time = frames / float(sc.render.fps) * float(p.get("speed", 1.0))
    mod.keyframe_insert("time", frame=frames)
    if ocean.animation_data and ocean.animation_data.action:
        try:
            for fc in ocean.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
        except Exception:
            pass
    ocean.data.materials.append(water_material())

    half = size * 0.25
    ensure_camera(Vector((-half, -half, z)), Vector((half, half, z + 2.0)))
    ensure_light()
    sc.frame_set(1)
    return dict(size_m=size, wave_scale=mod.wave_scale, choppiness=mod.choppiness, wind_velocity=mod.wind_velocity, frames=frames)


run_guarded(main)
