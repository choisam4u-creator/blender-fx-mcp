"""블렌더를 창 없이(백그라운드) 띄워 레시피를 소켓 없이 실행한다. 개발·테스트용.

사용:
  uv run blender-fx-headless demo destroy render
  BLENDER_FX_BLENDER=/path/to/blender uv run blender-fx-headless destroy
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .server import build_code, out_root, parse_results

CANDIDATES = [
    "/Applications/Blender.app/Contents/MacOS/Blender",
    "/usr/local/bin/blender",
    "/usr/bin/blender",
]

STEPS = {
    "demo": ("demo_scene", {}),
    "demo-windows": ("demo_scene", {"style": "windows", "ground": "asphalt"}),
    "ground": ("set_ground", {"material": "grass"}),
    "sky": ("set_look", {"preset": "day", "sky": "procedural"}),
    "snapshot": ("snapshot", {}),
    "restore": ("restore", {}),
    "glue": ("destroy", {"target": "Building", "pieces": 80, "frames": 60, "glue": "strong", "impact_power": 0.03}),
    "destroy": ("destroy", {"target": "Building", "pieces": 80, "frames": 60}),
    "destroy-hold": ("destroy", {"target": "Building", "pieces": 80, "frames": 60, "impact": "none", "hold_until": 11}),
    "explode": ("explode", {"target": "Building", "frames": 60, "burst_frame": 12, "resolution": 40}),
    "splash": ("water", {"mode": "drop", "frames": 40, "resolution": 64}),
    "water-side": ("water", {"mode": "stream", "at": [-6.0, 0.0, 5.0], "size": 0.5, "direction_deg": 90,
                             "pitch_deg": -10, "speed": 9.0, "duration": 22, "frames": 40, "resolution": 64}),
    "physics": ("set_physics", {"gravity": 3.0, "substeps": 12}),
    "render-set": ("set_render", {"samples": 24, "motion_blur": True}),
    "inspect": ("inspect_mesh", {"target": "Building"}),
    "fire": ("emit", {"kind": "fire", "target": "Building", "frames": 48, "resolution": 64}),
    "smoke-plume": ("emit", {"kind": "smoke", "at": [0.0, 0.0, 0.5], "radius": 0.8, "frames": 48, "resolution": 40}),
    "cam": ("camera", {"preset": "low"}),
    "shake": ("camera_shake", {"frame": 12, "strength": 0.4, "duration": 16}),
    "look": ("set_look", {"preset": "sunset"}),
    "wind": ("wind", {"direction_deg": 90, "strength": 4.0, "turbulence": 1.0}),
    "snow": ("particles", {"kind": "snow", "frames": 48}),
    "rain": ("particles", {"kind": "rain", "frames": 48}),
    "sparks": ("particles", {"kind": "sparks", "at": [0.0, 0.0, 3.0], "start_frame": 5}),
    "ocean": ("ocean", {"size": 40, "frames": 48}),
    "flag": ("cloth_flag", {"at": [0.0, 0.0, 0.0], "frames": 48}),
    "slowmo": ("set_timing", {"slow_from": 14, "slow_to": 30, "slow_factor": 0.25}),
    "export": ("export_model", {}),
    "import": ("import_model", {"name": "Imported", "size": 6.0}),
    "clear": ("clear_caches", {}),
    "render": ("render", {"frame_count": 5, "quality": "preview"}),
    "smoke": ("render", {"frame_count": 5, "quality": "smoke"}),
    "video": ("render_video", {"quality": "smoke", "width": 640, "height": 360}),
    "save": ("save_blend", {}),
    "list": ("list_objects", {}),
}


def find_blender() -> str | None:
    env = os.environ.get("BLENDER_FX_BLENDER")
    for c in ([env] if env else []) + CANDIDATES:
        if c and Path(c).exists():
            return c
    return None


# 기본 장면의 큐브·카메라·조명을 지워 빈 장면에서 시작한다
CLEAN_SCENE = "import bpy\nfor _o in list(bpy.data.objects):\n    bpy.data.objects.remove(_o, do_unlink=True)\n"


def run_steps(steps: list[tuple[str, dict]], blender: str | None = None, timeout: float = 1800.0,
              clean: bool = True, extra_code: str = "") -> list[dict]:
    """레시피 여러 개를 블렌더 한 번 실행으로 돌리고 FX_RESULT 목록을 돌려준다.
    extra_code 는 레시피 앞에 끼워 넣을 파이썬(테스트용 장면 준비)."""
    blender = blender or find_blender()
    if not blender:
        raise FileNotFoundError("블렌더 실행 파일을 못 찾았습니다. BLENDER_FX_BLENDER 환경변수로 경로를 알려주세요.")
    code = (CLEAN_SCENE if clean else "") + (extra_code + "\n" if extra_code else "") \
        + "\n".join(build_code(r, p) for r, p in steps)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        script = f.name
    try:
        proc = subprocess.run(
            [blender, "--background", "--factory-startup", "--python", script],
            capture_output=True, text=True, timeout=timeout,
        )
    finally:
        os.unlink(script)
    results = parse_results(proc.stdout)
    if len(results) != len(steps):
        raise RuntimeError(
            f"결과 {len(results)}개 (기대 {len(steps)}개). 블렌더 출력 끝부분:\n"
            + proc.stdout[-1500:] + "\n" + proc.stderr[-1500:]
        )
    return results


def main() -> None:
    names = sys.argv[1:] or ["demo", "destroy", "render"]
    steps = []
    for n in names:
        if n not in STEPS:
            print(f"모르는 단계: {n}. 가능한 값: {list(STEPS)}")
            sys.exit(2)
        recipe, params = STEPS[n]
        params = dict(params)
        if recipe == "render":
            params["out_dir"] = str(out_root() / "headless")
        if recipe == "explode":
            params["cache_dir"] = str(out_root() / "cache_fluid")
        if recipe == "water":
            params["cache_dir"] = str(out_root() / "cache_liquid")
        if recipe == "render_video":
            params["out_path"] = str(out_root() / "headless" / "preview.mp4")
        if recipe == "save_blend":
            params["path"] = str(out_root() / "headless" / "scene.blend")
        if recipe == "emit":
            params["cache_dir"] = str(out_root() / "cache_emit")
        if recipe in ("export_model", "import_model"):
            params["path"] = str(out_root() / "headless" / "model.glb")
        if recipe == "clear_caches":
            params["cache_dirs"] = [str(out_root() / d) for d in ("cache_fluid", "cache_liquid", "cache_emit")]
        if recipe in ("snapshot", "restore"):
            params["path"] = str(out_root() / "snapshots" / "headless.blend")
        steps.append((recipe, params))
    for r in run_steps(steps):
        print(json.dumps(r, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
