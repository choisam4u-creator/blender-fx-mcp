# 프레임 범위·fps·슬로모션. 슬로모션은 리지드바디와 연기·물 도메인의 시간 배속을 구간만 낮춘다.
# PARAMS: frame_start, frame_end, fps, slow_from, slow_to, slow_factor, rebake


def main():
    p = PARAMS
    sc = scene()
    changed = {}
    if p.get("frame_start"):
        sc.frame_start = int(p["frame_start"])
        changed["frame_start"] = sc.frame_start
    if p.get("frame_end"):
        sc.frame_end = int(p["frame_end"])
        changed["frame_end"] = sc.frame_end
    if p.get("fps"):
        sc.render.fps = int(p["fps"])
        changed["fps"] = sc.render.fps

    # 전체 슬로모션: 장면 시간을 늘린다. 파티클까지 전부 느려지는 대신 길이가 늘어난다
    if p.get("global_slow"):
        factor = max(0.05, min(float(p["global_slow"]), 1.0))
        r = sc.render
        r.frame_map_old = 100
        r.frame_map_new = int(round(100 / factor))
        sc.frame_end = int(round(sc.frame_end / factor))
        changed["global_slow"] = dict(factor=factor, frame_map=[r.frame_map_old, r.frame_map_new],
                                      new_frame_end=sc.frame_end)
        if p.get("rebake", True):
            free_bake()
            bake_pointcaches(sc.frame_end)
            for dom, _ds in fluid_domains():
                bake_fluid(dom)
            changed["rebaked"] = True

    slow_from = int(p.get("slow_from") or 0)
    slow_to = int(p.get("slow_to") or 0)
    factor = float(p.get("slow_factor") or 0.25)
    keyed = []
    if slow_from and slow_to:
        if slow_to <= slow_from:
            raise FxError(L(f"slow_to({slow_to}) 는 slow_from({slow_from}) 보다 커야 합니다.",
                            f"slow_to({slow_to}) must be greater than slow_from({slow_from})."))
        targets = []
        if sc.rigidbody_world is not None:
            targets.append(("rigidbody_world", sc.rigidbody_world))
        for dom, ds in fluid_domains():
            targets.append((dom.name, ds))
        if not targets:
            raise FxError(L("슬로모션을 걸 시뮬레이션이 없습니다. 먼저 destroy / explode / splash 를 하세요.",
                            "There is no simulation to slow down. Run destroy / explode / splash first."))
        for name, obj in targets:
            try:
                obj.time_scale = 1.0
                obj.keyframe_insert("time_scale", frame=slow_from - 1)
                obj.time_scale = factor
                obj.keyframe_insert("time_scale", frame=slow_from)
                obj.keyframe_insert("time_scale", frame=slow_to)
                obj.time_scale = 1.0
                obj.keyframe_insert("time_scale", frame=slow_to + 1)
                keyed.append(name)
            except Exception:
                continue
        changed["slow_motion"] = dict(frames=[slow_from, slow_to], factor=factor, applied_to=keyed)
        if p.get("rebake", True):
            free_bake()
            bake_pointcaches(sc.frame_end)
            for dom, _ds in fluid_domains():
                bake_fluid(dom)
            changed["rebaked"] = True
    sc.frame_set(sc.frame_start)
    return dict(frame_range=[sc.frame_start, sc.frame_end], fps=sc.render.fps,
                frame_map=[sc.render.frame_map_old, sc.render.frame_map_new], **changed)


run_guarded(main)
