# SPDX-License-Identifier: MIT
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
    # 크기를 안 주면(0) set_render 로 정한 장면 크기, 그것도 없으면 720p
    width = int(p.get("width") or 0)
    height = int(p.get("height") or 0)
    if not (width and height):
        if sc.get(USER_RES_TAG):
            width = width or r.resolution_x * r.resolution_percentage // 100
            height = height or r.resolution_y * r.resolution_percentage // 100
        else:
            width, height = width or 1280, height or 720
    f0 = int(p.get("frame_start") or sc.frame_start)
    f1 = int(p.get("frame_end") or sc.frame_end)
    if f1 < f0:
        # 한쪽만 줬으면 다른 쪽은 장면 값이라 "바꿔라"가 아니라 "함께 주라"가 다음 할 일이다
        if p.get("frame_start") and not p.get("frame_end"):
            raise FxError(L(f"frame_start({f0}) 가 장면 끝(frame_end {f1}) 뒤입니다. frame_end 도 함께 주어"
                            f"(예: frame_start={f0}, frame_end={f0 + 71}) 다시 시키세요. 장면은 바꾸지 않았습니다.",
                            f"frame_start ({f0}) is after the scene's end (frame_end {f1}). Give frame_end too "
                            f"(e.g. frame_start={f0}, frame_end={f0 + 71}) and ask again. The scene was not changed."))
        if p.get("frame_end") and not p.get("frame_start"):
            raise FxError(L(f"frame_end({f1}) 가 장면 시작(frame_start {f0}) 앞입니다. frame_start 도 함께 주어"
                            f"(예: frame_start=1, frame_end={f1}) 다시 시키세요. 장면은 바꾸지 않았습니다.",
                            f"frame_end ({f1}) is before the scene's start (frame_start {f0}). Give frame_start too "
                            f"(e.g. frame_start=1, frame_end={f1}) and ask again. The scene was not changed."))
        raise FxError(L(f"frame_end({f1}) 가 frame_start({f0}) 보다 작습니다. 두 값을 바꿔 다시 시키세요.",
                        f"frame_end({f1}) is smaller than frame_start({f0}). Swap the two values and ask again."))
    if sc.camera is None:
        raise FxError(L("카메라가 없습니다. 먼저 destroy / explode / splash 로 장면을 만드세요.",
                        "There is no camera. Build a scene first with destroy / explode / splash."))
    ensure_light()

    old = dict(engine=r.engine, x=r.resolution_x, y=r.resolution_y, pct=r.resolution_percentage,
               fmt=r.image_settings.file_format, path=r.filepath, fs=sc.frame_start, fe=sc.frame_end, fps=r.fps)
    samples = render_state()
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

    fps = r.fps  # 실제로 렌더한 fps(아래 finally 가 장면 값을 되돌리기 전에)
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
        restore_render_state(samples)

    # 블렌더가 파일 이름에 프레임 범위를 붙일 수 있어 새로 생긴 mp4 를 찾는다
    candidates = [os.path.join(out_dir, f) for f in os.listdir(out_dir) if f.lower().endswith(".mp4") and (f not in before or os.path.join(out_dir, f) == out_path)]
    if not candidates:
        raise FxError(L("영상 파일이 만들어지지 않았습니다. 블렌더의 FFmpeg 출력이 막혀 있을 수 있습니다. "
                        "render_preview 로 프레임 한 장이 나오는지 먼저 확인하고, 블렌더 창 Output 속성의 File Format 에 FFmpeg Video 가 있는지 보세요.",
                        "No video file was produced. Blender's FFmpeg output may be unavailable. "
                        "First check that render_preview makes a frame, then see whether FFmpeg Video is listed under File Format in the Output properties."))
    path = max(candidates, key=os.path.getmtime)
    return dict(path=path, size_bytes=os.path.getsize(path), frames=[f0, f1], engine=engine, fps=fps, size=[width, height])


run_guarded(main)
