# 모델 건강 진단: 닫혀 있나, 부피는 얼마나, 조각내기에 적합한가. PARAMS: target, decimate_to


def main():
    p = PARAMS
    obj = get_target(p.get("target"))
    bm, ratio, _ = bm_from_object(obj, int(p.get("decimate_to") or 0), repair=False)
    health = mesh_health(bm)

    # 볼록한가? 볼록 껍질 부피와 비교하면 오목한 정도를 알 수 있다
    convex_ratio = None
    try:
        hull = bm.copy()
        r = bmesh.ops.convex_hull(hull, input=hull.verts[:])
        # 껍질 안쪽에 남은 원래 geometry 를 지워야 부피가 맞는다
        junk = list(r.get("geom_interior", [])) + list(r.get("geom_unused", []))
        if junk:
            bmesh.ops.delete(hull, geom=junk, context="VERTS")
        bmesh.ops.recalc_face_normals(hull, faces=hull.faces[:])
        hv = abs(hull.calc_volume(signed=False))
        hull.free()
        if hv > 1e-9:
            convex_ratio = round(health["volume_m3"] / hv, 3)
    except Exception:
        pass

    repaired = repair_bm(bm.copy() if False else bm)  # 수리해 보고 얼마나 나아지는지 본다
    bm.free()

    lo, hi = world_bbox(obj)
    s = hi - lo
    scale = obj.matrix_world.to_scale()
    notes = []
    if not health["closed"]:
        notes.append(L("메시가 닫혀 있지 않습니다. 파괴하면 단면이 비어 보일 수 있습니다. repair=True 또는 shell_thickness 를 쓰세요.",
                       "The mesh is not closed. Fractured pieces may look hollow. Use repair=True or shell_thickness."))
    if health["non_manifold_edges"]:
        notes.append(L("면이 3개 이상 붙은 모서리가 있습니다(비다양체). 조각이 이상해질 수 있습니다.",
                       "Some edges have more than two faces (non-manifold). Chunks may come out wrong."))
    if convex_ratio is not None and convex_ratio < 0.75:
        notes.append(L("오목한 모양입니다. collision='mesh' 를 쓰면 충돌이 정확해지지만 느려집니다.",
                       "This shape is concave. collision='mesh' is more accurate but slower."))
    if health["faces"] > 20000:
        notes.append(L("면이 매우 많습니다. 조각내기 전에 자동으로 줄입니다(decimate_to).",
                       "Very high face count. It will be decimated before fracturing (decimate_to)."))
    if abs(scale.x - 1) > 0.01 or abs(scale.y - 1) > 0.01 or abs(scale.z - 1) > 0.01:
        notes.append(L(f"크기 값이 1이 아닙니다 {tuple(round(v, 2) for v in scale)}. 물리가 어긋날 수 있어 파괴 시 자동으로 적용합니다.",
                       f"Object scale is not 1 {tuple(round(v, 2) for v in scale)}. It will be applied before fracturing."))

    return dict(target=obj.name, size_m=[round(s.x, 2), round(s.y, 2), round(s.z, 2)],
                decimated_ratio=round(ratio, 3), convex_ratio=convex_ratio,
                repair_preview=dict(merged_verts=repaired["merged_verts"], filled_faces=repaired["filled_faces"],
                                    closed_after=repaired["after"]["closed"], volume_after=repaired["after"]["volume_m3"]),
                notes=notes, **health)


run_guarded(main)
