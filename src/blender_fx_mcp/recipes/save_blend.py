# 현재 장면을 .blend 파일로 저장한다(복사본 저장이라 열려 있는 파일은 그대로). PARAMS: path


def main():
    path = os.path.expanduser(PARAMS["path"])
    if not path.lower().endswith(".blend"):
        path += ".blend"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path, copy=True)
    return dict(
        path=path, size_bytes=os.path.getsize(path),
        note="연기·물 캐시는 .blend 안이 아니라 cache_dir 폴더에 있습니다. 옮길 때 같이 옮기세요.",
    )


run_guarded(main)
