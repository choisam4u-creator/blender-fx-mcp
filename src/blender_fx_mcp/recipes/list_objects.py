# 장면에 있는 메시 오브젝트 목록. 조각(chunk)은 개수만 센다.


def main():
    items = []
    chunk_count = 0
    for o in mesh_objects():
        role = o.get(FX_TAG)
        if role == "chunk":
            chunk_count += 1
            continue
        if role == "dust":  # 먼지 알갱이 원본은 내부용
            continue
        lo, hi = world_bbox(o)
        s = hi - lo
        items.append(dict(
            name=o.name,
            size_m=[round(s.x, 2), round(s.y, 2), round(s.z, 2)],
            location=[round(v, 2) for v in o.matrix_world.translation],
            fx_role=role,
            hidden=bool(o.hide_viewport or o.hide_render),
        ))
    sc = scene()
    return dict(
        objects=items, chunk_count=chunk_count,
        camera=sc.camera.name if sc.camera else None,
        frame_range=[sc.frame_start, sc.frame_end],
        blender=bpy.app.version_string,
    )


run_guarded(main)
