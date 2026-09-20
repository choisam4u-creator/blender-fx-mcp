# 구운 캐시(리지드바디·파티클·연기·물)를 지워 디스크와 메모리를 비운다. PARAMS: cache_dirs(목록)


def dir_size(path):
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def main():
    p = PARAMS
    free_bake()
    domains = 0
    for dom, _ds in fluid_domains():
        with bpy.context.temp_override(scene=scene(), object=dom, active_object=dom, selected_objects=[dom]):
            try:
                bpy.ops.fluid.free_all()
                domains += 1
            except Exception:
                pass
    freed = 0
    cleared = []
    for d in p.get("cache_dirs") or []:
        d = os.path.expanduser(d)
        if os.path.isdir(d):
            freed += dir_size(d)
            shutil.rmtree(d, ignore_errors=True)
            os.makedirs(d, exist_ok=True)
            cleared.append(d)
    return dict(freed_mb=round(freed / 1_000_000, 1), dirs=cleared, fluid_domains=domains)


run_guarded(main)
