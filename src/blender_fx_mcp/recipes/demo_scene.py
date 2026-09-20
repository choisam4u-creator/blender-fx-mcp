# 연습용 건물 하나와 바닥·카메라·조명을 만든다. 대상 오브젝트가 없을 때 쓴다.
# PARAMS: name, floors, width, depth, floor_height, style(plain|windows), windows_per_side, ground

EPS = 1e-4


def cut(bm, co, no):
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=Vector(co), plane_no=Vector(no))


def window_rects(w, d, floors, fh, cols):
    """창문 자리(축, 벽 좌표, 가로 구간, 세로 구간)를 미리 계산한다."""
    rows = []
    for f in range(floors):
        rows.append((f * fh + fh * 0.30, f * fh + fh * 0.72))
    spans = {"x": w, "y": d}
    rects = []
    for axis, span in spans.items():
        step = span / cols
        half = step * 0.30
        for c in range(cols):
            center = -span / 2 + step * (c + 0.5)
            for z0, z1 in rows:
                rects.append((axis, center - half, center + half, z0, z1))
    return rects, rows


def carve_windows(bm, w, d, floors, fh, cols, recess):
    """벽을 실제로 파내 창문을 만든다. 하나의 닫힌 껍데기를 유지한다."""
    rects, rows = window_rects(w, d, floors, fh, cols)
    # 창문 경계마다 벽을 잘라 격자를 만든다
    for axis, a0, a1, _z0, _z1 in rects:
        no = (1, 0, 0) if axis == "x" else (0, 1, 0)
        for a in (a0, a1):
            co = (a, 0, 0) if axis == "x" else (0, a, 0)
            cut(bm, co, no)
    for z0, z1 in rows:
        for z in (z0, z1):
            cut(bm, (0, 0, z), (0, 0, 1))

    # 격자 중에서 창문 칸을 고른다
    targets = []
    for f in bm.faces:
        c = f.calc_center_median()
        n = f.normal
        for axis, a0, a1, z0, z1 in rects:
            if not (z0 - EPS < c.z < z1 + EPS):
                continue
            if axis == "x":  # ±Y 벽 (앞/뒤)
                if abs(abs(c.y) - d / 2) > EPS or abs(n.y) < 0.9:
                    continue
                if a0 - EPS < c.x < a1 + EPS:
                    targets.append(f)
                    break
            else:  # ±X 벽 (좌/우)
                if abs(abs(c.x) - w / 2) > EPS or abs(n.x) < 0.9:
                    continue
                if a0 - EPS < c.y < a1 + EPS:
                    targets.append(f)
                    break

    made = 0
    for f in list(targets):
        if not f.is_valid:
            continue
        n = f.normal.copy()
        try:
            bmesh.ops.inset_individual(bm, faces=[f], thickness=min(recess, 0.08), depth=0.0, use_even_offset=True)
        except Exception:
            continue
        if not f.is_valid:
            continue
        bmesh.ops.translate(bm, verts=list(f.verts), vec=-n * recess)
        f.material_index = 1
        made += 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return made


def main():
    p = PARAMS
    name = p.get("name", "Building")
    floors = max(1, int(p.get("floors", 3)))
    w = float(p.get("width", 4.0))
    d = float(p.get("depth", 4.0))
    fh = float(p.get("floor_height", 3.0))
    cols = max(1, int(p.get("windows_per_side", 3)))
    style = p.get("style", "plain")
    if style not in ("plain", "windows"):
        raise FxError(L(f"style 은 plain / windows 중 하나여야 합니다. 받은 값: {style}",
                        f"style must be plain or windows, got: {style}"))
    h = floors * fh

    old = bpy.data.objects.get(name)
    if old is not None:
        cleanup_fx(name)
        remove_object(old)

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * w, v.co.y * d, (v.co.z + 0.5) * h))
    # 층 경계에 칼집을 내 두면 조각이 층을 따라 갈라지기 쉽다
    for i in range(1, floors):
        cut(bm, (0.0, 0.0, i * fh), (0.0, 0.0, 1.0))

    windows = carve_windows(bm, w, d, floors, fh, cols, recess=min(0.18, min(w, d) * 0.05)) if style == "windows" else 0
    obj = new_mesh_object(name, bm, Matrix.Identity(4))
    bm.free()
    obj["fx_demo"] = True

    obj.data.materials.append(simple_material("FX_Concrete", (0.55, 0.53, 0.50), roughness=0.9))
    if windows:
        glass = simple_material("FX_Glass", (0.04, 0.07, 0.10), roughness=0.08)
        set_input(principled(glass), "Metallic", 0.6)
        obj.data.materials.append(glass)

    view_layer_update()
    ensure_ground(0.0)
    if p.get("ground"):
        g = next((o for o in bpy.data.objects if o.get(FX_TAG) == "ground"), None)
        if g is not None:
            g.data.materials.clear()
            g.data.materials.append(ground_material(p["ground"]))

    lo, hi = world_bbox(obj)
    ensure_camera(lo, hi, reframe=True)
    ensure_light()
    scene().frame_set(1)

    overlapping = []
    for o in mesh_objects():
        if o is obj or o.get(FX_TAG):
            continue
        a, b = world_bbox(o)
        if a.x < hi.x and b.x > lo.x and a.y < hi.y and b.y > lo.y and a.z < hi.z and b.z > lo.z:
            overlapping.append(o.name)

    check = bmesh.new()
    check.from_mesh(obj.data)
    health = mesh_health(check)
    check.free()
    return dict(target=name, size_m=[w, d, h], floors=floors, overlapping=overlapping,
                style=style, windows=windows, ground=p.get("ground") or "default",
                faces=len(obj.data.polygons), closed=health["closed"], volume_m3=health["volume_m3"])


run_guarded(main)
