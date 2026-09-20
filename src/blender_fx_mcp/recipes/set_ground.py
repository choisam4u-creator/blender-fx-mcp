# 바닥 재질·크기. PARAMS: material(asphalt|concrete|grass|sand|dirt|snow), size(m), z


def main():
    p = PARAMS
    kind = p.get("material", "concrete")
    size = float(p.get("size") or 0.0)
    z = p.get("z")

    g = next((o for o in bpy.data.objects if o.get(FX_TAG) == "ground"), None)
    if g is None:
        lo, _hi = fx_bbox(None)
        g = ensure_ground(lo.z if z is None else float(z))
    if g is None:
        raise FxError(L("바다가 바닥을 대신하고 있어 바닥 재질을 바꿀 수 없습니다. 먼저 reset 하세요.",
                        "The ocean is acting as the ground, so the ground material cannot be changed. Reset first."))
    unhide(g)
    if z is not None:
        g.location.z = float(z)
    if size > 0:
        cur = max(g.dimensions.x, 1e-6)
        f = size / cur
        g.scale = (g.scale.x * f, g.scale.y * f, 1.0)
        view_layer_update()

    mat = ground_material(kind)
    g.data.materials.clear()
    g.data.materials.append(mat)
    g["fx_ground_material"] = kind
    view_layer_update()
    return dict(material=kind, size_m=round(g.dimensions.x, 1), z=round(g.location.z, 2))


run_guarded(main)
