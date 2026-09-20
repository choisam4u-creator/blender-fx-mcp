# 장면(또는 지정 오브젝트)을 glb/fbx/obj 로 내보낸다. bake_physics 면 조각의 물리 움직임을 키프레임으로 구워 애니메이션째 내보낸다.
# PARAMS: path, names(목록, 비우면 보이는 것 전부), bake_physics


def main():
    p = PARAMS
    path = os.path.expanduser(p["path"])
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    ext = os.path.splitext(path)[1].lower()
    sc = scene()
    names = p.get("names") or []
    if names:
        objs = [get_target(n) for n in names]
    else:
        skip = ("dust", "smoke_flow", "liquid_flow", "emit_flow", "blast", "wind", "turbulence", "cell", "glue")
        objs = [o for o in bpy.data.objects if o.type in ("MESH", "CAMERA", "LIGHT", "EMPTY")
                and not o.hide_render and o.get(FX_TAG) not in skip]
        if ext == ".abc":  # 알렘빅은 물 표면(도메인)도 함께 내보낸다
            objs += [o for o in bpy.data.objects if o.get(FX_TAG) == "liquid_domain" and o not in objs]
    if not objs:
        raise FxError(L("내보낼 오브젝트가 없습니다.", "There is nothing to export."))

    # 내보내기 도구들은 컨텍스트가 아니라 실제 선택 상태를 본다
    for o in bpy.data.objects:
        try:
            o.select_set(False)
        except Exception:
            pass
    for o in objs:
        try:
            o.select_set(True)
        except Exception:
            pass
    bpy.context.view_layer.objects.active = objs[0]

    baked = 0
    if p.get("bake_physics"):
        chunks = [o for o in objs if o.rigid_body is not None and o.rigid_body.type == "ACTIVE"]
        if chunks:
            with bpy.context.temp_override(scene=sc, view_layer=bpy.context.view_layer, active_object=chunks[0], object=chunks[0],
                                           selected_objects=chunks, selected_editable_objects=chunks):
                bpy.ops.rigidbody.bake_to_keyframes(frame_start=sc.frame_start, frame_end=sc.frame_end, step=1)
            baked = len(chunks)

    with bpy.context.temp_override(scene=sc, view_layer=bpy.context.view_layer, active_object=objs[0], object=objs[0],
                                   selected_objects=objs, selected_editable_objects=objs):
        if ext in (".glb", ".gltf"):
            bpy.ops.export_scene.gltf(filepath=path, use_selection=True, export_format="GLB" if ext == ".glb" else "GLTF_SEPARATE", export_animations=True)
        elif ext == ".fbx":
            try:
                bpy.ops.wm.fbx_export(filepath=path, selected_objects_only=True)
            except AttributeError:
                bpy.ops.export_scene.fbx(filepath=path, use_selection=True)
        elif ext == ".obj":
            bpy.ops.wm.obj_export(filepath=path, export_selected_objects=True)
        elif ext == ".abc":
            # 알렘빅은 물 표면과 조각 움직임을 프레임마다 굽어서 내보낸다 (다른 프로그램으로 가져가기 좋음)
            bpy.ops.wm.alembic_export(filepath=path, selected=True,
                                      start=sc.frame_start, end=sc.frame_end, flatten=False)
        else:
            raise FxError(L(f"지원하지 않는 형식: {ext}. glb/gltf/fbx/obj/abc 만 됩니다.",
                            f"Unsupported format: {ext}. Only glb/gltf/fbx/obj/abc are supported."))
    if not os.path.exists(path):
        raise FxError(L("내보낸 파일이 만들어지지 않았습니다.", "The export file was not created."))
    return dict(path=path, size_bytes=os.path.getsize(path), objects=len(objs), baked_chunks=baked)


run_guarded(main)
