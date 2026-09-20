# 최종 영상 렌더: 프레임 범위를 mp4(H.264)로 뽑는다.
# PARAMS: out_path, quality(smoke|final|preview), width, height, fps, frame_start, frame_end


def main():
    p = PARAMS
    sc = scene()
    r = sc.render
    out_path = os.path.expanduser(p["out_path"])
    if not out_path.lower().endswith(".mp4"):
        out_path += ".mp4"
    out_dir = os.path.dirname(out_path)
    os.makedirs(out_dir, exist_ok=True)
    quality = p.get("quality", "smoke")
    width = int(p.get("width", 1280))
    height = int(p.get("height", 720))
    f0 = int(p.get("frame_start") or sc.frame_start)
    f1 = int(p.get("frame_end") or sc.frame_end)
    if f1 < f0:
        raise FxError(L(f"frame_end({f1}) 가 frame_start({f0}) 보다 작습니다.",
                        f"frame_end({f1}) is smaller than frame_start({f0})."))
    if sc.camera is None:
        raise FxError(L("카메라가 없습니다. 먼저 destroy / explode / splash 로 장면을 만드세요.",
                        "There is no camera. Build a scene first with destroy / explode / splash."))
    ensure_light()

    old = dict(engine=r.engine, x=r.resolution_x, y=r.resolution_y, pct=r.resolution_percentage,
               fmt=r.image_settings.file_format, path=r.filepath, fs=sc.frame_start, fe=sc.frame_end, fps=r.fps)
    r.resolution_x = width
    r.resolution_y = height
    r.resolution_percentage = 100
    engine = apply_render_quality(quality)
    # 블렌더 5.x 는 먼저 media_type 을 VIDEO 로 바꿔야 FFMPEG 형식이 열린다
    old_media = getattr(r.image_settings, "media_type", None)
    if old_media is not None:
        r.image_settings.media_type = "VIDEO"
    r.image_settings.file_format = "FFMPEG"
    r.ffmpeg.format = "MPEG4"
    r.ffmpeg.codec = "H264"
    r.ffmpeg.constant_rate_factor = "MEDIUM"
    if int(p.get("fps") or 0) > 0:
        r.fps = int(p["fps"])
    r.filepath = out_path
    sc.frame_start = f0
    sc.frame_end = f1

    before = set(os.listdir(out_dir))
    try:
        with bpy.context.temp_override(scene=sc):
            bpy.ops.render.render(animation=True)
    finally:
        try:
            r.engine = old["engine"]
        except Exception:
            pass
        r.resolution_x, r.resolution_y, r.resolution_percentage = old["x"], old["y"], old["pct"]
        if old_media is not None:
            r.image_settings.media_type = old_media
        r.image_settings.file_format = old["fmt"]
        r.filepath = old["path"]
        sc.frame_start, sc.frame_end = old["fs"], old["fe"]
        r.fps = old["fps"]

    # 블렌더가 파일 이름에 프레임 범위를 붙일 수 있어 새로 생긴 mp4 를 찾는다
    candidates = [os.path.join(out_dir, f) for f in os.listdir(out_dir) if f.lower().endswith(".mp4") and (f not in before or os.path.join(out_dir, f) == out_path)]
    if not candidates:
        raise FxError(L("영상 파일이 만들어지지 않았습니다. 블렌더의 FFmpeg 출력이 막혀 있을 수 있습니다.",
                        "No video file was produced. Blender's FFmpeg output may be unavailable."))
    path = max(candidates, key=os.path.getmtime)
    return dict(path=path, size_bytes=os.path.getsize(path), frames=[f0, f1], engine=engine, fps=r.fps, size=[width, height])


run_guarded(main)
