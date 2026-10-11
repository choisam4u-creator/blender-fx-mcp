# SPDX-License-Identifier: MIT
# 스냅샷으로 되돌리기. 블렌더가 그 .blend 파일을 연다(지금 장면은 버려진다). PARAMS: path


def main():
    path = os.path.expanduser(PARAMS["path"])
    if not path.lower().endswith(".blend"):
        path += ".blend"
    if not os.path.exists(path):
        d = os.path.dirname(path)
        names = sorted(f[:-6] for f in os.listdir(d) if f.lower().endswith(".blend")) if os.path.isdir(d) else []
        want = os.path.splitext(os.path.basename(path))[0]
        close = difflib.get_close_matches(want, names, n=3, cutoff=0.5)
        if names:
            raise FxError(L(f"스냅샷 파일이 없습니다: {path}. 있는 스냅샷: {', '.join(close or names[:10])}. "
                            "이 중 하나의 이름으로 restore 를 다시 시키세요(전체 목록은 list_snapshots).",
                            f"Snapshot file not found: {path}. Existing snapshots: {', '.join(close or names[:10])}. "
                            "Ask restore again with one of these names (full list: list_snapshots)."))
        raise FxError(L(f"스냅샷 파일이 없습니다: {path}. 저장된 스냅샷이 하나도 없습니다. 되돌리고 싶은 상태에서 snapshot 으로 먼저 저장하세요.",
                        f"Snapshot file not found: {path}. There are no snapshots yet. Save one with snapshot first, at the state you want to return to."))
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
