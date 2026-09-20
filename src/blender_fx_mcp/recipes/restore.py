# 스냅샷으로 되돌리기. 블렌더가 그 .blend 파일을 연다(지금 장면은 버려진다). PARAMS: path


def main():
    path = os.path.expanduser(PARAMS["path"])
    if not path.lower().endswith(".blend"):
        path += ".blend"
    if not os.path.exists(path):
        raise FxError(L(f"스냅샷 파일이 없습니다: {path}", f"Snapshot file not found: {path}"))
    # 파일을 열면 지금 장면의 bpy 데이터는 모두 무효가 된다. 이 뒤로는 새로 읽는다.
    bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
    sc = bpy.context.scene
    meshes = [o.name for o in bpy.data.objects if o.type == "MESH"]
    return dict(
        path=path, objects=len(bpy.data.objects), meshes=len(meshes),
        frame_range=[sc.frame_start, sc.frame_end], fps=sc.render.fps,
        camera=sc.camera.name if sc.camera else None,
    )


run_guarded(main)
