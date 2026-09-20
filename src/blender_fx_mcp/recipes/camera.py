# 카메라 구도 프리셋. 대상(또는 이 도구가 만든 것 전체)을 기준으로 거리·높이·방향·렌즈를 정한다.
# PARAMS: preset, target, distance_factor, height, angle_deg, lens

# (거리 배수, 높이 비율 0=바닥 1=꼭대기, 방위각 deg 0=정면(-Y) 90=오른쪽(+X), 렌즈 mm)
PRESETS = {
    "wide": (3.2, 0.5, -35.0, 28),
    "medium": (2.2, 0.45, -35.0, 35),
    "closeup": (1.3, 0.4, -30.0, 50),
    "low": (2.2, 0.06, -30.0, 28),
    "high": (2.6, 1.4, -35.0, 35),
    "top": (2.2, 3.0, 0.0, 35),
    "front": (2.6, 0.45, 0.0, 35),
    "side": (2.6, 0.45, 90.0, 35),
}


def main():
    p = PARAMS
    preset = p.get("preset", "medium")
    if preset not in PRESETS:
        raise FxError(L(f"preset 은 {list(PRESETS)} 중 하나여야 합니다. 받은 값: {preset}",
                        f"preset must be one of {list(PRESETS)}, got: {preset}"))
    lo, hi = fx_bbox(p.get("target") or None)
    center = (lo + hi) / 2
    size = max((hi - lo).x, (hi - lo).y, (hi - lo).z, 1.0)
    dist_f, h_f, az_deg, lens = PRESETS[preset]
    dist = size * float(p.get("distance_factor") or dist_f)
    h_val = p.get("height")
    h = lo.z + (hi.z - lo.z) * (float(h_val) if h_val is not None else h_f)
    a_val = p.get("angle_deg")
    az = math.radians(float(a_val) if a_val is not None else az_deg)
    lens = float(p.get("lens") or lens)

    sc = scene()
    cam = sc.camera
    if cam is None:
        cam = ensure_camera(lo, hi)
    if cam.animation_data:
        cam.animation_data_clear()  # 이전 흔들림 제거
    if preset == "top":
        loc = Vector((center.x, center.y + 0.01, hi.z + dist))
    else:
        loc = Vector((center.x, center.y, h)) + Vector((math.sin(az), -math.cos(az), 0.0)) * dist
    cam.location = loc
    aim = Vector((center.x, center.y, lo.z + (hi.z - lo.z) * 0.4))
    cam.rotation_euler = (aim - loc).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    cam.data.clip_end = max(100.0, dist * 4.0)
    return dict(preset=preset, location=[round(v, 2) for v in loc], lens=lens, target_size_m=round(size, 2))


run_guarded(main)
