# 렌더 설정: 샘플 수, 모션블러, 해상도, 노출, 필름 룩.
# PARAMS: samples, motion_blur, shutter, width, height, exposure, view_transform, look, fps, transparent_background


def main():
    p = PARAMS
    sc = scene()
    r = sc.render
    changed = {}

    if p.get("width") or p.get("height"):
        if p.get("width"):
            r.resolution_x = int(p["width"])
        if p.get("height"):
            r.resolution_y = int(p["height"])
        changed["resolution"] = [r.resolution_x, r.resolution_y]
    if p.get("fps"):
        r.fps = int(p["fps"])
        changed["fps"] = r.fps

    if p.get("samples"):
        n = max(1, int(p["samples"]))
        if hasattr(sc, "eevee"):
            sc.eevee.taa_render_samples = n
        if hasattr(sc, "cycles"):
            sc.cycles.samples = n
        changed["samples"] = n

    if p.get("motion_blur") is not None:
        on = bool(p["motion_blur"])
        applied = []
        for holder in (r, getattr(sc, "eevee", None), getattr(sc, "cycles", None)):
            if holder is None:
                continue
            for attr in ("use_motion_blur", "motion_blur_position"):
                if attr == "use_motion_blur" and hasattr(holder, attr):
                    try:
                        setattr(holder, attr, on)
                        applied.append(type(holder).__name__)
                    except Exception:
                        pass
        shutter = float(p.get("shutter") or 0.5)
        for holder in (r, getattr(sc, "eevee", None), getattr(sc, "cycles", None)):
            if holder is None:
                continue
            for attr in ("motion_blur_shutter", "blur_shutter", "shutter_speed"):
                if hasattr(holder, attr):
                    try:
                        setattr(holder, attr, shutter)
                    except Exception:
                        pass
        changed["motion_blur"] = dict(on=on, shutter=shutter, applied=sorted(set(applied)))

    vs = sc.view_settings
    if p.get("exposure") is not None:
        vs.exposure = float(p["exposure"])
        changed["exposure"] = vs.exposure
    if p.get("view_transform"):
        try:
            vs.view_transform = p["view_transform"]
            changed["view_transform"] = vs.view_transform
        except TypeError:
            changed["view_transform_error"] = [i.identifier for i in vs.bl_rna.properties["view_transform"].enum_items]
    if p.get("look"):
        try:
            vs.look = p["look"]
            changed["look"] = vs.look
        except TypeError:
            changed["look_error"] = [i.identifier for i in vs.bl_rna.properties["look"].enum_items][:12]
    if p.get("transparent_background") is not None:
        r.film_transparent = bool(p["transparent_background"])
        changed["transparent_background"] = r.film_transparent

    return dict(changed=changed, resolution=[r.resolution_x, r.resolution_y], fps=r.fps,
                exposure=round(vs.exposure, 3), view_transform=vs.view_transform, look=vs.look,
                engine=sc.render.engine)


run_guarded(main)
