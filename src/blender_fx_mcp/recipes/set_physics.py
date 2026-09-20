# 물리 전역 설정: 중력, 계산 정밀도, 속도. PARAMS: gravity, gravity_deg, substeps, solver_iterations, speed, fps, rebake


def main():
    p = PARAMS
    sc = scene()
    changed = {}

    if p.get("gravity") is not None:
        g = float(p["gravity"])
        deg = float(p.get("gravity_deg") or 0.0)  # 0이면 똑바로 아래
        tilt = math.radians(max(-90.0, min(90.0, deg)))
        sc.gravity = (math.sin(tilt) * g, 0.0, -math.cos(tilt) * g)
        sc.use_gravity = g != 0.0
        changed["gravity"] = [round(v, 3) for v in sc.gravity]
        for _dom, ds in fluid_domains():
            try:
                ds.gravity = sc.gravity
            except Exception:
                pass

    rbw = sc.rigidbody_world
    if rbw is not None:
        if p.get("substeps"):
            rbw.substeps_per_frame = max(1, min(int(p["substeps"]), 1000))
            changed["substeps"] = rbw.substeps_per_frame
        if p.get("solver_iterations"):
            rbw.solver_iterations = max(1, min(int(p["solver_iterations"]), 1000))
            changed["solver_iterations"] = rbw.solver_iterations
        if p.get("speed") is not None:
            rbw.time_scale = float(p["speed"])
            changed["speed"] = rbw.time_scale
    if p.get("fps"):
        sc.render.fps = int(p["fps"])
        changed["fps"] = sc.render.fps

    rebaked = False
    if p.get("rebake", True) and changed:
        free_bake()
        bake_pointcaches(sc.frame_end)
        for dom, _ds in fluid_domains():
            bake_fluid(dom)
        rebaked = True
    sc.frame_set(sc.frame_start)
    return dict(changed=changed, rebaked=rebaked,
                gravity=[round(v, 3) for v in sc.gravity], fps=sc.render.fps,
                substeps=rbw.substeps_per_frame if rbw else None,
                solver_iterations=rbw.solver_iterations if rbw else None,
                speed=round(rbw.time_scale, 3) if rbw else None)


run_guarded(main)
