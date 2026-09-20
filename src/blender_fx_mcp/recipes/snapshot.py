# 장면 스냅샷 저장. PARAMS: path, dir(목록을 만들 폴더)


def main():
    p = PARAMS
    path = os.path.expanduser(p["path"])
    if not path.lower().endswith(".blend"):
        path += ".blend"
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path, copy=True)
    sc = scene()
    items = sorted(f for f in os.listdir(d) if f.endswith(".blend"))
    return dict(
        path=path, size_bytes=os.path.getsize(path), snapshots=items,
        objects=len(bpy.data.objects), frame_range=[sc.frame_start, sc.frame_end],
    )


run_guarded(main)
