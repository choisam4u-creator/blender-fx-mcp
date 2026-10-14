# SPDX-License-Identifier: MIT
# 프레임 범위·fps·슬로모션. 슬로모션은 리지드바디와 연기·물 도메인의 시간 배속을 구간만 낮춘다.
# PARAMS: frame_start, frame_end, fps, slow_from, slow_to, slow_factor, rebake


def main():
    p = PARAMS
    sc = scene()
    changed = {}
    # 순서·대상 검사는 장면을 바꾸기 전에 한다(실패했는데 길이·fps 가 바뀐 채 남지 않게)
    # 한쪽만 주면 블렌더가 다른 쪽을 따라 옮긴다(시작을 끝 뒤로 주면 끝도 밀림). 둘 다 줬는데 거꾸로면 멈춘다
    f0, f1 = int(p.get("frame_start") or 0), int(p.get("frame_end") or 0)
    if f0 and f1 and f1 < f0:
        raise FxError(L(f"frame_end({f1}) 가 frame_start({f0}) 보다 작습니다. 장면은 바꾸지 않았습니다. 두 값을 바꿔 다시 시키세요.",
                        f"frame_end({f1}) is smaller than frame_start({f0}). The scene was not changed. "
                        "Swap the two values and ask again."))
    slow_from = int(p.get("slow_from") or 0)
    slow_to = int(p.get("slow_to") or 0)
    factor = float(p.get("slow_factor") or 0.25)
    targets = []
    if slow_from and slow_to:
        if slow_to <= slow_from:
            raise FxError(L(f"slow_to({slow_to}) 는 slow_from({slow_from}) 보다 커야 합니다. 두 값을 바꿔 다시 시키세요.",
                            f"slow_to({slow_to}) must be greater than slow_from({slow_from}). Swap the two values and ask again."))
        if sc.rigidbody_world is not None:
            targets.append(("rigidbody_world", sc.rigidbody_world))
        for dom, ds in fluid_domains():
            targets.append((dom.name, ds))
        if not targets:
            raise FxError(L("슬로모션을 걸 시뮬레이션이 없습니다. 먼저 destroy / explode / splash 를 하세요.",
                            "There is no simulation to slow down. Run destroy / explode / splash first."))
    before = (sc.frame_start, sc.frame_end)
    if p.get("frame_start"):
        sc.frame_start = int(p["frame_start"])
        changed["frame_start"] = sc.frame_start
    if p.get("frame_end"):
        sc.frame_end = int(p["frame_end"])
        changed["frame_end"] = sc.frame_end
    # 한쪽만 줬는데 블렌더가 다른 쪽을 따라 옮겼으면 알린다(조용히 길이가 1프레임이 되는 것을 사용자가 모름)
    moved = {}
    if f0 and not f1 and sc.frame_end != before[1]:
        moved["frame_end"] = [before[1], sc.frame_end]
    if f1 and not f0 and sc.frame_start != before[0]:
        moved["frame_start"] = [before[0], sc.frame_start]
    if moved:
        changed["moved"] = moved
    if p.get("fps"):
        sc.render.fps = int(p["fps"])
        changed["fps"] = sc.render.fps

    # 전체 슬로모션: 장면 시간을 늘린다. 파티클까지 전부 느려지는 대신 길이가 늘어난다. 배율은 원래 속도 기준(1.0 이면 되돌림)
    if p.get("global_slow"):
        g = max(0.05, min(float(p["global_slow"]), 1.0))
        r = sc.render
        # 이미 늘린 장면이면 원래 길이로 되살린 뒤 늘린다(두 번 시키면 길이만 또 늘고 시간 배율은 그대로이던 문제).
        # 원래 길이는 장면에 적어 둔다(반올림한 frame_map 으로 되짚으면 0.75 같은 배율에서 한 프레임씩 어긋남).
        # 같은 호출에 frame_end 를 줬거나, 늘린 뒤 길이를 손으로 바꿨으면 지금 값을 기준으로 삼는다
        stretch = r.frame_map_new / r.frame_map_old if r.frame_map_old else 1.0
        if p.get("frame_end"):
            base_end = sc.frame_end
        elif sc.get("fx_slow_frame_end") == sc.frame_end and "fx_base_frame_end" in sc:
            base_end = int(sc["fx_base_frame_end"])
        else:
            base_end = int(round(sc.frame_end / stretch))
        r.frame_map_old = 100
        r.frame_map_new = int(round(100 / g))
        sc.frame_end = int(round(base_end / g))
        sc["fx_base_frame_end"] = base_end
        sc["fx_slow_frame_end"] = sc.frame_end
        changed["global_slow"] = dict(factor=g, frame_map=[r.frame_map_old, r.frame_map_new],
                                      new_frame_end=sc.frame_end)
        if p.get("rebake", True):
            free_bake()
            bake_pointcaches(sc.frame_end)
            for dom, _ds in fluid_domains():
                bake_fluid(dom)
            changed["rebaked"] = True

    keyed = []
    if targets:
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
    # changed 에 fps 가 있어도 겹치지 않게 합친다(전에는 fps 를 주면 늘 TypeError — 장면은 이미 바뀐 뒤)
    return {**changed, "frame_range": [sc.frame_start, sc.frame_end], "fps": sc.render.fps,
            "frame_map": [sc.render.frame_map_old, sc.render.frame_map_new]}


run_guarded(main)
