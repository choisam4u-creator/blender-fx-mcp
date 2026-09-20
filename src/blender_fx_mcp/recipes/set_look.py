# 조명·하늘 분위기 프리셋. PARAMS: preset, sun_strength(배수), sky(flat|procedural), hdri(파일 경로)

# (태양 세기, 고도 deg, 방위 deg, 태양 색, 태양 퍼짐 rad, 하늘 색, 하늘 세기, 노출, 하늘 텍스처용 고도)
LOOKS = {
    "day": (4.0, 50, 35, (1.0, 0.98, 0.92), 0.02, (0.45, 0.58, 0.78), 1.0, 0.0, 50),
    "sunset": (3.5, 12, 60, (1.0, 0.62, 0.35), 0.03, (0.45, 0.28, 0.22), 0.45, 0.0, 2),
    "night": (0.35, 40, 20, (0.55, 0.65, 1.0), 0.02, (0.02, 0.03, 0.07), 0.6, 0.6, -8),
    "overcast": (1.6, 60, 35, (0.92, 0.95, 1.0), 1.0, (0.62, 0.64, 0.67), 1.2, 0.0, 60),
    "studio": (3.0, 45, 30, (1.0, 1.0, 1.0), 0.1, (0.3, 0.3, 0.3), 1.0, 0.0, 45),
}


def main():
    p = PARAMS
    preset = p.get("preset", "day")
    if preset not in LOOKS:
        raise FxError(L(f"preset 은 {list(LOOKS)} 중 하나여야 합니다. 받은 값: {preset}",
                        f"preset must be one of {list(LOOKS)}, got: {preset}"))
    energy, elev, azim, color, spread, sky, sky_strength, exposure, sky_elev = LOOKS[preset]
    energy *= float(p.get("sun_strength") or 1.0)
    sky_mode = p.get("sky", "flat")
    if sky_mode not in ("flat", "procedural"):
        raise FxError(L(f"sky 는 flat / procedural 중 하나여야 합니다. 받은 값: {sky_mode}",
                        f"sky must be flat or procedural, got: {sky_mode}"))
    sc = scene()

    sun = next((o for o in bpy.data.objects if o.type == "LIGHT" and o.data.type == "SUN"), None)
    if sun is None:
        ensure_light()
        sun = next((o for o in bpy.data.objects if o.type == "LIGHT" and o.data.type == "SUN"), None)
    sun.data.energy = energy
    sun.data.color = color
    sun.data.angle = spread
    # 고도·방위: X 축으로 (90-고도) 기울이고 Z 축으로 방위 회전
    sun.rotation_euler = (math.radians(90.0 - elev), 0.0, math.radians(azim))

    used = apply_world(sky_mode, sky, sky_strength, sky_elev, azim, p.get("hdri"))
    if used != "flat":
        # 하늘 자체가 밝게 비추므로 태양을 줄인다. 안 그러면 두 번 비춰 하얗게 날아간다
        energy *= 0.45
        sun.data.energy = energy
    try:
        sc.view_settings.exposure = exposure
    except Exception:
        pass
    return dict(preset=preset, sun_energy=energy, sun_elevation_deg=elev, sky=list(sky), sky_mode=used)


run_guarded(main)
