# 외부 모델(glb/gltf/fbx/obj/stl/usd/blend)을 가져와 하나의 메시로 합치고, 크기를 맞추고, 바닥에 세운다.
# PARAMS: path, name, size(가장 긴 변 m, 0이면 원본), on_ground, center


def import_file(path):
    ext = os.path.splitext(path)[1].lower()
    sc = scene()
    with bpy.context.temp_override(scene=sc):
        if ext in (".glb", ".gltf"):
            bpy.ops.import_scene.gltf(filepath=path)
        elif ext == ".fbx":
            try:
                bpy.ops.wm.fbx_import(filepath=path)
            except AttributeError:
                bpy.ops.import_scene.fbx(filepath=path)
        elif ext == ".obj":
            bpy.ops.wm.obj_import(filepath=path)
        elif ext == ".stl":
            bpy.ops.wm.stl_import(filepath=path)
        elif ext in (".usd", ".usda", ".usdc", ".usdz"):
            bpy.ops.wm.usd_import(filepath=path)
        elif ext == ".blend":
            with bpy.data.libraries.load(path, link=False) as (src, dst):
                dst.objects = list(src.objects)
            for o in dst.objects:
                if o is not None:
                    link(o)
        else:
            raise FxError(L(f"지원하지 않는 형식: {ext}. glb/gltf/fbx/obj/stl/usd/blend 만 됩니다.",
                            f"Unsupported format: {ext}. Only glb/gltf/fbx/obj/stl/usd/blend are supported."))


def main():
    p = PARAMS
    path = os.path.expanduser(p["path"])
    if not os.path.exists(path):
        raise FxError(L(f"파일이 없습니다: {path}", f"File not found: {path}"))
    name = p.get("name") or os.path.splitext(os.path.basename(path))[0]
    size = float(p.get("size") or 0.0)
    sc = scene()

    before = set(bpy.data.objects)
    import_file(path)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    if not meshes:
        kinds = sorted({o.type for o in new})
        for o in new:
            remove_object(o)
        raise FxError(L(f"가져온 파일에 메시가 없습니다. 들어 있던 것: {kinds or '없음'} ({os.path.getsize(path)} bytes)",
                        f"The imported file contains no mesh. It held: {kinds or 'nothing'} ({os.path.getsize(path)} bytes)"))

    # 부모 변환을 세계 좌표로 굳힌 뒤 하나로 합친다
    for o in meshes:
        o.matrix_world = o.matrix_world.copy()
        o.parent = None
    view_layer_update()
    new_names = [o.name for o in new]
    obj = meshes[0]
    if len(meshes) > 1:
        with bpy.context.temp_override(scene=sc, view_layer=bpy.context.view_layer, active_object=obj, object=obj,
                                       selected_objects=meshes, selected_editable_objects=meshes):
            bpy.ops.object.join()
    # 합치면서 사라진 오브젝트가 있으니 이름으로 다시 찾는다
    for n in new_names:
        o = bpy.data.objects.get(n)
        if o is not None and o.type != "MESH":
            remove_object(o)
    obj.name = name
    obj.data.name = name

    # 회전·크기를 메시에 적용해 조각내기·물리가 어긋나지 않게 한다
    with bpy.context.temp_override(scene=sc, view_layer=bpy.context.view_layer, active_object=obj, object=obj,
                                   selected_objects=[obj], selected_editable_objects=[obj]):
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    view_layer_update()

    lo, hi = world_bbox(obj)
    dims = hi - lo
    longest = max(dims.x, dims.y, dims.z, 1e-6)
    if size > 0:
        f = size / longest
        obj.scale = (f, f, f)
        with bpy.context.temp_override(scene=sc, view_layer=bpy.context.view_layer, active_object=obj, object=obj,
                                       selected_objects=[obj], selected_editable_objects=[obj]):
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        view_layer_update()
        lo, hi = world_bbox(obj)
        dims = hi - lo
    if p.get("center", True):
        obj.location.x -= (lo.x + hi.x) / 2
        obj.location.y -= (lo.y + hi.y) / 2
    if p.get("on_ground", True):
        obj.location.z -= lo.z
    view_layer_update()
    lo, hi = world_bbox(obj)
    ensure_ground(lo.z)
    ensure_camera(lo, hi, reframe=True)
    ensure_light()
    return dict(name=obj.name, size_m=[round(dims.x, 2), round(dims.y, 2), round(dims.z, 2)],
                vertices=len(obj.data.vertices), faces=len(obj.data.polygons), joined=len(meshes), source=path)


run_guarded(main)
