# 미리보기·최종 렌더 레시피. 프레임 몇 장을 PNG 로 저장하고 경로를 돌려준다.
# PARAMS: out_dir, frame_count 또는 frames(목록), width, height, quality(preview|final)


def pick_frames(n, start, end):
    if n <= 1:
        return [end]
    return sorted({int(round(start + i * (end - start) / (n - 1))) for i in range(n)})


def main():
    p = PARAMS
    sc = scene()
    r = sc.render
    out_dir = p["out_dir"]
    os.makedirs(out_dir, exist_ok=True)
    frames = p.get("frames") or pick_frames(int(p.get("frame_count", 5)), sc.frame_start, sc.frame_end)
    width = int(p.get("width", 640))
    height = int(p.get("height", 360))
    quality = p.get("quality", "preview")

    if sc.camera is None:
        objs = [o for o in mesh_objects() if o.get(FX_TAG) != "ground"]
        if not objs:
            raise FxError(L("카메라도 오브젝트도 없어 렌더할 수 없습니다.",
                            "There is no camera and no object, so nothing can be rendered."))
        lo, hi = world_bbox(objs[0])
        for o in objs[1:]:
            a, b = world_bbox(o)
            lo = Vector((min(lo.x, a.x), min(lo.y, a.y), min(lo.z, a.z)))
            hi = Vector((max(hi.x, b.x), max(hi.y, b.y), max(hi.z, b.z)))
        ensure_camera(lo, hi)
    ensure_light()

    old = dict(engine=r.engine, x=r.resolution_x, y=r.resolution_y, pct=r.resolution_percentage, fmt=r.image_settings.file_format, path=r.filepath)
    r.resolution_x = width
    r.resolution_y = height
    r.resolution_percentage = 100
    r.image_settings.file_format = "PNG"

    engine = apply_render_quality(quality)

    paths = []
    for f in frames:
        sc.frame_set(int(f))
        path = os.path.join(out_dir, f"frame_{int(f):04d}.png")
        r.filepath = path
        with bpy.context.temp_override(scene=sc):
            bpy.ops.render.render(write_still=True)
        paths.append(path)

    # 설정 되돌리기
    try:
        r.engine = old["engine"]
    except Exception:
        pass
    r.resolution_x, r.resolution_y, r.resolution_percentage = old["x"], old["y"], old["pct"]
    r.image_settings.file_format = old["fmt"]
    r.filepath = old["path"]
    sc.frame_set(sc.frame_start)
    # 하늘 텍스처·HDRI·연기·물은 워크벤치(빠른 미리보기)에서 안 보인다. 그럴 때 알려 준다
    fancy_sky = False
    if sc.world is not None and sc.world.use_nodes:
        fancy_sky = any(n.type in ("TEX_SKY", "TEX_ENVIRONMENT") for n in sc.world.node_tree.nodes)
    volumes = any(o.get(FX_TAG) in ("smoke_domain", "emit_domain", "liquid_domain") for o in bpy.data.objects)
    return dict(frames=[int(f) for f in frames], paths=paths, engine=engine, size=[width, height],
                quality=quality, fancy_sky=fancy_sky, has_volumes=volumes,
                missing_in_preview=bool(engine == "BLENDER_WORKBENCH" and (fancy_sky or volumes)))


run_guarded(main)
