# 외부 모델(glb/gltf/fbx/obj/stl/usd/blend)을 가져와 하나의 메시로 합치고, 크기를 맞추고, 바닥에 세운다.
# PARAMS: path, name, size(가장 긴 변 m, 0이면 원본), on_ground, center, parts(남길 부품 이름 목록)


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
    new_names = [o.name for o in new]
    if not meshes:
        kinds = sorted({o.type for o in new})
        for o in new:
            remove_object(o)
        raise FxError(L(f"가져온 파일에 메시가 없습니다. 들어 있던 것: {kinds or '없음'} ({os.path.getsize(path)} bytes)",
                        f"The imported file contains no mesh. It held: {kinds or 'nothing'} ({os.path.getsize(path)} bytes)"))

    # 뼈대에 묶인(스킨) 메시는 모디파이어를 먼저 구워야 지금 자세 그대로 남는다.
    # 그리고 부모를 뗀 "뒤에" 세계 위치를 되돌려 놔야 한다. 순서가 반대면 부모가 주던
    # 위치·크기가 통째로 날아가 부품이 제자리를 벗어난다.
    for o in list(meshes):
        mw = o.matrix_world.copy()
        if o.modifiers:
            dg = bpy.context.evaluated_depsgraph_get()
            baked = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
            old_me = o.data
            o.data = baked
            o.modifiers.clear()
            if old_me.users == 0:
                bpy.data.meshes.remove(old_me)
        o.parent = None
        o.matrix_world = mw
    view_layer_update()

    # 면이 하나도 없는 메시는 부술 수 없다. 리깅 조작용 위젯(WGT-…)이나 선만 있는 것들이
    # 여기 해당하는데, .blend 하나에 132개가 들어 있던 적도 있다. 자동으로 뺀다.
    solid = [o for o in meshes if len(o.data.polygons) > 0]
    empty_parts = [o.name for o in meshes if o not in solid]
    if solid and empty_parts:
        for o in meshes:
            if o not in solid:
                remove_object(o)
        meshes = solid
        view_layer_update()

    # 파일 안에 무엇이 들어 있었는지 남긴다. 눈에 안 보이는 껍데기 구 같은 게 섞여 있으면
    # 그대로 합쳤을 때 진짜 모델을 통째로 삼킨다(실제로 캐릭터가 구가 된 적이 있다).
    parts = []
    for o in meshes:
        d = o.dimensions
        parts.append(dict(name=o.name, size_m=[round(d.x, 2), round(d.y, 2), round(d.z, 2)],
                          vertices=len(o.data.vertices), faces=len(o.data.polygons)))

    def short(names, keep=8):
        names = list(names)
        if len(names) <= keep:
            return str(names)
        return str(names[:keep])[:-1] + f", …외 {len(names) - keep}개]"

    wanted = p.get("parts") or []
    dropped = []
    if wanted:
        keys = [str(w).lower() for w in wanted]
        keep = [o for o in meshes if any(k in o.name.lower() for k in keys)]
        if not keep:
            raise FxError(L(f"parts 에 맞는 부품이 없습니다. 파일 안 부품: {short([q['name'] for q in parts])}",
                            f"No part matched 'parts'. Parts in the file: {short([q['name'] for q in parts])}"))
        dropped = [o.name for o in meshes if o not in keep]
        for o in meshes:
            if o not in keep:
                remove_object(o)
        meshes = keep
        view_layer_update()

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

    # glTF/GLB 는 저장할 때 꼭짓점을 쪼개 둔다. 그대로 두면 모든 면이 따로 놀아
    # "닫히지 않은 메시"가 되고 조각내기가 망가진다. 여기서 다시 붙인다.
    weld = bmesh.new()
    weld.from_mesh(obj.data)
    before_verts = len(weld.verts)
    size_hint = max((max(v.co[i] for v in weld.verts) - min(v.co[i] for v in weld.verts)) for i in range(3)) if weld.verts else 1.0
    bmesh.ops.remove_doubles(weld, verts=weld.verts[:], dist=max(1e-6, size_hint * 1e-5))
    bmesh.ops.recalc_face_normals(weld, faces=weld.faces[:])
    merged = before_verts - len(weld.verts)
    health = mesh_health(weld)
    weld.to_mesh(obj.data)
    weld.free()
    obj.data.update()
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
    notes = []
    if not health["closed"]:
        notes.append(L("가져온 모델이 닫혀 있지 않습니다(구멍이나 두께 없는 면). destroy 가 자동 수리하지만, "
                       "껍데기뿐이면 shell_thickness 로 두께를 주세요.",
                       "The imported model is not closed (holes or zero-thickness faces). destroy repairs it "
                       "automatically, but for pure shells set shell_thickness."))
    if len(obj.data.polygons) > 20000:
        notes.append(L(f"면이 {len(obj.data.polygons)}개로 많습니다. 조각낼 때 자동으로 줄입니다.",
                       f"{len(obj.data.polygons)} faces is a lot; it will be decimated when fracturing."))
    if empty_parts:
        notes.append(L(f"면이 없는 부품 {len(empty_parts)}개를 자동으로 뺐습니다(리깅 조작용 위젯 등): {short(empty_parts)}",
                       f"Dropped {len(empty_parts)} face-less parts automatically (rig widgets etc.): {short(empty_parts)}"))
    if dropped:
        notes.append(L(f"부품 {len(dropped)}개를 뺐습니다: {short(dropped)}",
                       f"Dropped {len(dropped)} parts: {short(dropped)}"))
    elif len(parts) > 1:
        # 면이 아주 적은데 덩치는 제일 큰 부품은 보이지 않는 충돌용 껍데기일 때가 많다
        biggest = max(parts, key=lambda q: max(q["size_m"]))
        others = max((max(q["size_m"]) for q in parts if q is not biggest), default=0.0)
        if biggest["faces"] <= 200 and others > 0 and max(biggest["size_m"]) > others * 1.5:
            notes.append(L(
                f"'{biggest['name']}' 는 면이 {biggest['faces']}개뿐인데 가장 큽니다. 보이지 않는 충돌용 껍데기일 수 있고, "
                f"그대로 합치면 진짜 모델을 삼킵니다. parts 로 원하는 부품만 고르세요. 파일 안 부품: {short([q['name'] for q in parts])}",
                f"'{biggest['name']}' has only {biggest['faces']} faces yet is the largest. It may be an invisible "
                f"collision proxy that swallows the real model. Pick parts explicitly. Parts: {short([q['name'] for q in parts])}"))
        else:
            notes.append(L(f"부품 {len(parts)}개를 하나로 합쳤습니다: {short([q['name'] for q in parts])}",
                           f"Joined {len(parts)} parts into one: {short([q['name'] for q in parts])}"))
    return dict(name=obj.name, size_m=[round(dims.x, 2), round(dims.y, 2), round(dims.z, 2)],
                vertices=len(obj.data.vertices), faces=len(obj.data.polygons), joined=len(meshes),
                merged_verts=merged, closed=health["closed"], volume_m3=health["volume_m3"],
                parts=parts, dropped_parts=dropped, empty_parts=empty_parts, notes=notes, source=path)


run_guarded(main)
