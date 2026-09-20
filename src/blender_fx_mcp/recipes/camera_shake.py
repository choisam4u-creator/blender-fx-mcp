# 카메라 흔들림: 지정 프레임부터 몇 프레임 동안 흔들리다 잦아든다. 충돌·폭발 순간에 쓴다.
# PARAMS: frame, strength(m), duration(프레임), seed


def main():
    p = PARAMS
    sc = scene()
    cam = sc.camera
    if cam is None:
        raise FxError(L("카메라가 없습니다. 먼저 camera 나 destroy 로 장면을 만드세요.",
                        "There is no camera. Use the camera tool or destroy first."))
    frame = max(2, int(p.get("frame", 12)))
    strength = max(0.0, float(p.get("strength", 0.3)))
    duration = max(2, int(p.get("duration", 20)))
    rng = random.Random(int(p.get("seed", 1)))

    base_loc = cam.location.copy()
    base_rot = cam.rotation_euler.copy()
    if cam.animation_data:
        cam.animation_data_clear()
    prefs = bpy.context.preferences.edit
    old_interp = prefs.keyframe_new_interpolation_type
    prefs.keyframe_new_interpolation_type = "LINEAR"
    try:
        cam.keyframe_insert("location", frame=frame - 1)
        cam.keyframe_insert("rotation_euler", frame=frame - 1)
        for i in range(duration):
            t = i / duration
            amp = strength * (1.0 - t) ** 2
            cam.location = base_loc + Vector([rng.uniform(-1.0, 1.0) * amp for _ in range(3)])
            cam.rotation_euler = Euler((
                base_rot.x + rng.uniform(-1.0, 1.0) * amp * 0.06,
                base_rot.y + rng.uniform(-1.0, 1.0) * amp * 0.06,
                base_rot.z + rng.uniform(-1.0, 1.0) * amp * 0.04,
            ))
            cam.keyframe_insert("location", frame=frame + i)
            cam.keyframe_insert("rotation_euler", frame=frame + i)
        cam.location = base_loc
        cam.rotation_euler = base_rot
        cam.keyframe_insert("location", frame=frame + duration)
        cam.keyframe_insert("rotation_euler", frame=frame + duration)
    finally:
        prefs.keyframe_new_interpolation_type = old_interp
    sc.frame_set(sc.frame_start)
    return dict(frame=frame, duration=duration, strength=strength)


run_guarded(main)
