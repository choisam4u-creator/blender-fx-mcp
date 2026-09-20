# 조각과 충격체를 지우고 원본을 되살린다. PARAMS: target(선택)


def main():
    n = cleanup_fx(PARAMS.get("target"))
    free_bake()
    scene().frame_set(scene().frame_start)
    return dict(removed=n)


run_guarded(main)
