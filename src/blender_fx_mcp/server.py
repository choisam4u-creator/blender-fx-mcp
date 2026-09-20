"""blender-fx MCP 서버. AI 가 말로 시키면 블렌더 FX 를 만든다.

도구는 검증된 레시피(recipes/*.py)를 블렌더 안 수신기로 보내 실행한다.
AI 는 코드를 짜지 않고 도구와 값만 고른다.
메시지 언어는 환경변수 BLENDER_FX_LANG (ko 기본 / en) 으로 고른다.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from mcp.server.mcpserver import Image, MCPServer

from . import bridge
from .bridge import BlenderError
from .i18n import is_en, t

RECIPES = Path(__file__).parent / "recipes"
LONG = 1800.0  # 굽기가 오래 걸리는 도구의 대기 시간(초)

INSTRUCTIONS = """블렌더 FX 도구 상자 / Blender FX toolbox. Answer in the user's language.
사용자는 블렌더를 모르는 감독이고, 당신이 손이다.

① doctor 로 준비 확인 ② list_objects 로 대상 확인, 남의 모델은 import_model + inspect_mesh 로 상태 점검
③ 효과: destroy(파괴) / explode(폭발) / water(물) / fire·smoke(불·연기) / particles(비·눈·불꽃·재) /
   ocean(바다) / cloth_flag(깃발)
④ 연출: camera, camera_shake, set_look(하늘), set_ground(바닥), wind, set_timing(슬로모션),
   set_physics(중력·정밀도), set_render(샘플·모션블러)
⑤ 되돌릴 수 있게: 위험한 작업 전에 snapshot, 마음에 안 들면 restore
⑥ 마무리: render_video(mp4), save_blend, export_model(glb/fbx/obj/abc)

돌아온 미리보기 프레임을 보고 무엇이 보이는지 쉬운 말로 설명한다.
사용자의 지시("더 잘게", "맞은 데만 부서지게", "물을 옆으로 쏴", "꿀처럼", "중력 절반")를 인자로 바꿔 다시 실행한다.
실패 메시지는 무엇을 바꾸면 되는지까지 들어 있으니 그대로 전달하면 된다."""

mcp = MCPServer("blender-fx", instructions=INSTRUCTIONS)


# ---------- 내부 도우미 ----------

def out_root() -> Path:
    root = Path(os.environ.get("BLENDER_FX_OUT", "~/blender-fx-output")).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    return root


def snapshot_dir() -> Path:
    d = out_root() / "snapshots"
    d.mkdir(parents=True, exist_ok=True)
    return d


def new_run_dir(label: str) -> Path:
    safe = re.sub(r"[^\w\-]+", "_", label)[:40]
    d = out_root() / f"{time.strftime('%Y%m%d-%H%M%S')}_{safe}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def build_code(recipe: str, params: dict) -> str:
    """PARAMS 한 줄 + 공용 도우미 + 레시피를 이어 붙인다."""
    common = (RECIPES / "_common.py").read_text(encoding="utf-8")
    body = (RECIPES / f"{recipe}.py").read_text(encoding="utf-8")
    return f"PARAMS = {params!r}\n" + common + "\n" + body + "\n"


def parse_results(stdout: str) -> list[dict]:
    out = []
    for line in stdout.splitlines():
        if line.startswith("FX_RESULT "):
            out.append(json.loads(line[len("FX_RESULT "):]))
    return out


def parse_result(stdout: str) -> dict:
    results = parse_results(stdout)
    if not results:
        tail = stdout.strip()[-600:]
        raise BlenderError(t(
            "블렌더가 결과 줄(FX_RESULT)을 돌려주지 않았습니다. 출력 끝부분: ",
            "Blender returned no FX_RESULT line. End of output: ",
        ) + (tail or t("(비어 있음)", "(empty)")))
    return results[-1]


def run_recipe(recipe: str, params: dict, timeout: float | None = None) -> dict:
    params = {k: v for k, v in params.items() if v is not None}
    params.setdefault("_lang", "en" if is_en() else "ko")
    stdout = bridge.run_python(build_code(recipe, params), timeout=timeout)
    res = parse_result(stdout)
    if not res.get("ok"):
        msg = res.get("error", t("(원인 없음)", "(no reason given)"))
        if res.get("traceback"):
            msg += "\n" + res["traceback"]
        raise BlenderError(msg)
    return res


def _fail(e: Exception) -> str:
    return t(f"실패: {e}", f"Failed: {e}")


def _images(paths: list[str]) -> list:
    return [Image(path=p) for p in paths if os.path.exists(p)]


def _render(label: str, quality: str = "preview", frame_count: int = 3, frames: list[int] | None = None):
    run_dir = new_run_dir(label)
    params = dict(out_dir=str(run_dir), quality=quality, frame_count=frame_count)
    if frames:
        params["frames"] = list(frames)
    return run_recipe("render", params, timeout=LONG), run_dir


def _preview_note(rend: dict) -> str:
    if rend.get("missing_in_preview"):
        return t(" (빠른 미리보기라 하늘·연기·물은 보이지 않습니다. render_preview(quality=\"smoke\") 로 보세요.)",
                 " (Fast preview: sky, smoke and water are not shown. Use render_preview(quality=\"smoke\").)")
    return ""


def _notes(res: dict) -> str:
    items = res.get("notes") or []
    return ("\n" + "\n".join(f"- {n}" for n in items)) if items else ""


def _cache_dirs() -> dict:
    root = out_root()
    return dict(fluid=str(root / "cache_fluid"), liquid=str(root / "cache_liquid"), emit=str(root / "cache_emit"))


# ---------- 점검·조회 ----------

@mcp.tool()
def doctor() -> str:
    """Check prerequisites (python, mcp, uv, Blender, receiver add-on, connection, output folder).
    준비물 점검. 뭔가 안 될 때 먼저 부른다."""
    from .doctor import format_report, run_checks
    return format_report(run_checks())


@mcp.tool()
def ping_blender() -> str:
    """Check the socket connection to Blender.
    블렌더 수신기와 연결되는지 확인한다."""
    try:
        bridge.ping()
        return t(f"연결됨 ({bridge.host()}:{bridge.port()})", f"Connected ({bridge.host()}:{bridge.port()})")
    except BlenderError as e:
        return _fail(e)


@mcp.tool()
def list_objects() -> str:
    """List mesh objects with their names and sizes.
    장면에 있는 메시 이름과 크기(m)를 돌려준다. 효과의 target 을 고를 때 쓴다."""
    try:
        return json.dumps(run_recipe("list_objects", {}), ensure_ascii=False, indent=1)
    except BlenderError as e:
        return _fail(e)


@mcp.tool()
def inspect_mesh(target: str, decimate_to: int = 0) -> str:
    """Diagnose a mesh before fracturing it: closed?, volume, concavity, face count, repair preview.
    부수기 전에 모델 상태를 본다. 닫혀 있는지, 부피, 오목한 정도, 면 수, 수리하면 얼마나 나아지는지.
    남이 만든 모델을 가져왔을 때 destroy 전에 부르면 문제를 미리 알 수 있다."""
    try:
        res = run_recipe("inspect_mesh", dict(target=target, decimate_to=decimate_to or None), timeout=LONG)
    except BlenderError as e:
        return _fail(e)
    return json.dumps(res, ensure_ascii=False, indent=1)


# ---------- 장면 만들기 ----------

@mcp.tool()
def make_demo_building(floors: int = 3, width: float = 4.0, depth: float = 4.0, floor_height: float = 3.0,
                       name: str = "Building", style: str = "plain", windows_per_side: int = 3, ground: str = ""):
    """Create a practice building with ground, camera and light. Returns one preview frame.
    연습용 건물과 바닥·카메라·조명을 만든다. 부술 오브젝트가 없을 때 쓴다.
    style: "plain" 민무늬 / "windows" 벽을 실제로 파낸 창문 건물.
    ground: asphalt/concrete/grass/sand/dirt/snow, 비우면 기본."""
    try:
        res = run_recipe("demo_scene", dict(floors=floors, width=width, depth=depth, floor_height=floor_height,
                                            name=name, style=style, windows_per_side=windows_per_side,
                                            ground=ground or None))
        rend, _ = _render(f"demo_{name}", frames=[1])
    except BlenderError as e:
        return _fail(e)
    s = res["size_m"]
    text = t(
        f"건물 '{res['target']}' 생성: {s[0]}×{s[1]}×{s[2]}m, {res['floors']}층, 모양 {res['style']}, "
        f"창문 {res['windows']}개, 바닥 {res['ground']}, 부피 {res['volume_m3']}m³, 닫힌 메시 {res['closed']}.",
        f"Created '{res['target']}': {s[0]}×{s[1]}×{s[2]}m, {res['floors']} floors, style {res['style']}, "
        f"{res['windows']} windows, ground {res['ground']}, volume {res['volume_m3']}m³, closed {res['closed']}.",
    )
    if res.get("overlapping"):
        text += t(f" 주의: {res['overlapping']} 이(가) 건물 자리에 겹쳐 있습니다.",
                  f" Note: {res['overlapping']} overlaps the building.")
    return [text + _preview_note(rend)] + _images(rend["paths"])


@mcp.tool()
def import_model(path: str, name: str = "", size: float = 0.0, on_ground: bool = True, center: bool = True):
    """Import a 3D model (glb/gltf/fbx/obj/stl/usd/blend), join it into one mesh and stand it on the ground.
    외부 모델을 가져와 하나의 메시로 합치고 바닥에 세운다.
    size: 가장 긴 변을 이 길이(m)로 맞춤(0이면 원본). 가져온 뒤 inspect_mesh 로 상태를 보고 destroy 한다."""
    try:
        res = run_recipe("import_model", dict(path=path, name=name or None, size=size,
                                              on_ground=on_ground, center=center), timeout=LONG)
        rend, _ = _render(f"import_{res['name']}", frames=[1])
    except BlenderError as e:
        return _fail(e)
    s = res["size_m"]
    text = t(
        f"가져오기 완료: '{res['name']}' {s[0]}×{s[1]}×{s[2]}m, 정점 {res['vertices']}개, 면 {res['faces']}개 "
        f"(메시 {res['joined']}개를 하나로 합침).",
        f"Imported '{res['name']}': {s[0]}×{s[1]}×{s[2]}m, {res['vertices']} vertices, {res['faces']} faces "
        f"(joined {res['joined']} meshes).",
    )
    return [text + _preview_note(rend)] + _images(rend["paths"])


@mcp.tool()
def export_model(path: str, names: list[str] | None = None, bake_physics: bool = False) -> str:
    """Export to glb/gltf/fbx/obj, or .abc (Alembic) which also carries the animated water surface.
    장면을 내보낸다. .abc 로 하면 물 표면과 조각 움직임이 프레임마다 구워져 다른 프로그램에서 그대로 보인다.
    bake_physics=True 면 조각 물리를 키프레임으로 굽는다(되돌릴 수 없으니 먼저 snapshot).
    연기(볼륨)는 어떤 형식으로도 나가지 않는다."""
    try:
        res = run_recipe("export_model", dict(path=path, names=names or [], bake_physics=bake_physics), timeout=LONG)
    except BlenderError as e:
        return _fail(e)
    mb = res["size_bytes"] / 1_000_000
    text = t(f"내보내기 완료: {res['path']} ({mb:.1f}MB, 오브젝트 {res['objects']}개)",
             f"Exported: {res['path']} ({mb:.1f}MB, {res['objects']} objects)")
    if res["baked_chunks"]:
        text += t(f". 조각 {res['baked_chunks']}개의 물리를 키프레임으로 구웠습니다.",
                  f". Baked physics to keyframes for {res['baked_chunks']} chunks.")
    return text


# ---------- 파괴·폭발 ----------

@mcp.tool()
def destroy(
    target: str,
    impact: str = "left",
    material: str = "concrete",
    pieces: int = 120,
    pattern: str = "impact",
    focus: float = 0.5,
    time_scale: float = 1.0,
    frames: int = 72,
    impact_height: float = 0.35,
    impact_power: float = 0.04,
    dust: str = "low",
    glue: str = "none",
    collision: str = "auto",
    interior: str = "auto",
    repair: bool = True,
    shell_thickness: float = 0.0,
    density: float = 0.0,
    friction: float = -1.0,
    bounce: float = -1.0,
    neighbors: int = 10,
    decimate_to: int = 20000,
    seed: int = 1,
    preview_frames: int = 5,
):
    """Fracture any mesh into Voronoi chunks and collapse it with real physics. Works on imported models.
    아무 메시나 보로노이(돌 깨지듯 다각형) 조각으로 부수고 물리로 무너뜨린다. 미리보기 프레임을 돌려준다.

    target: 부술 메시 이름
    impact: 충격 방향 left / right / front / back / top / none(충격체 없이)
    material: concrete / brick / glass / wood / stone / metal / ice / plaster (무게·마찰·튐·속 색)
    pieces: 조각 수 (50~400 권장). 많을수록 잘게 부서지고 느려진다
    pattern: 조각이 촘촘해지는 곳. impact(맞은 곳) / uniform(고르게) / radial(중심에서) / slabs(층층이)
    focus: 0~1. pattern 의 집중도. 1이면 맞은 곳만 아주 잘게
    impact_power: 충격체 무게 = 대상 전체 무게 × 이 값 (0.02 약하게, 0.04 보통, 0.15 폭발처럼)
    glue: none / weak / medium / strong. 조각을 붙여 두면 맞은 곳만 무너지고 나머지는 버틴다
    collision: auto / convex(빠름) / mesh(오목한 모양 정확) / box / sphere
    interior: 부순 단면 재질. auto(재질에 맞춰) / none / 다른 material 이름
    repair: 구멍 난 메시를 자동 수리 (남의 모델에 특히 필요)
    shell_thickness: 껍데기뿐인 모델에 줄 두께(m). 닫히지 않은 모델에서만 쓰임
    density / friction / bounce: 재질 프리셋을 덮어쓰는 값 (0 또는 음수면 프리셋 그대로)
    neighbors: 셀 이웃 수. 기본이면 충분하다
    decimate_to: 면이 이 수보다 많으면 줄여서 부순다
    결과의 volume_kept 가 1.0 에 가까우면 물리적으로 맞게 쪼개진 것이다."""
    params = dict(
        target=target, impact=impact, material=material, pieces=pieces, pattern=pattern, focus=focus,
        time_scale=time_scale, frames=frames, impact_height=impact_height, impact_power=impact_power,
        dust=dust, glue=glue, collision=collision, interior=interior, repair=repair,
        shell_thickness=shell_thickness, neighbors=neighbors, decimate_to=decimate_to, seed=seed,
        density=density or None, friction=friction if friction >= 0 else None,
        bounce=bounce if bounce >= 0 else None,
    )
    try:
        res = run_recipe("destroy", params, timeout=LONG)
        rend, run_dir = _render(f"destroy_{target}", frame_count=preview_frames)
    except BlenderError as e:
        return _fail(e)
    moved = int(res["moved_ratio"] * 100)
    text = t(
        f"'{res['target']}' 파괴: 조각 {res['pieces']}개({res['pattern']}, focus {res['focus']}), 재질 {res['material']}, "
        f"충격 {res['impact']}, {res['frames']}프레임. 무게 약 {res['total_mass_kg']}kg, 접착 {res['glue']}({res['glue_constraints']}개), "
        f"먼지 {res['dust']}. 움직인 조각 {moved}%, 최대 낙하 {res['max_fall_m']}m. "
        f"부피 보존 {res['volume_kept']} (1.0 이면 완벽), 열린 조각 {res['open_chunks']}개. "
        f"미리보기 {rend['frames']} → {run_dir}",
        f"Destroyed '{res['target']}': {res['pieces']} chunks ({res['pattern']}, focus {res['focus']}), "
        f"material {res['material']}, impact {res['impact']}, {res['frames']} frames. Mass ~{res['total_mass_kg']}kg, "
        f"glue {res['glue']} ({res['glue_constraints']} joints), dust {res['dust']}. {moved}% of chunks moved, "
        f"max drop {res['max_fall_m']}m. Volume kept {res['volume_kept']} (1.0 is perfect), "
        f"{res['open_chunks']} open chunks. Preview {rend['frames']} → {run_dir}",
    )
    if res["moved_ratio"] < 0.1:
        text += t(" 거의 안 움직였습니다. impact_power 를 올리거나 glue 를 낮추세요.",
                  " Almost nothing moved. Raise impact_power or lower glue.")
    return [text + _notes(res) + _preview_note(rend)] + _images(rend["paths"])


@mcp.tool()
def explode(
    target: str = "",
    at: list[float] | None = None,
    radius: float = 0.0,
    power: float = 1.0,
    fire: bool = True,
    frames: int = 72,
    burst_frame: int = 12,
    resolution: int = 48,
    pieces: int = 120,
    material: str = "concrete",
    pattern: str = "radial",
    dust: str = "low",
    glue: str = "none",
    smoke_collision: bool = False,
    preview_frames: int = 5,
):
    """Explosion: fracture the target, blow the chunks outward, and add smoke and fire.
    폭발. target 을 주면 그 물건을 조각내 안에서 터뜨리고, 없으면 at 위치에 연기·불만 만든다.
    power 0.5 작게 / 1 보통 / 2 크게. resolution 32 빠름 / 48 보통 / 96 고화질.
    smoke_collision=True 면 연기가 조각을 통과하지 않고 부딪힌다(느려짐)."""
    try:
        if target:
            run_recipe("destroy", dict(
                target=target, impact="none", hold_until=max(1, burst_frame - 1), material=material,
                pieces=pieces, frames=frames, dust=dust, glue=glue, pattern=pattern,
            ), timeout=LONG)
        res = run_recipe("explode", dict(
            target=target or None, at=at, radius=radius, power=power, fire=fire, frames=frames,
            burst_frame=burst_frame, resolution=resolution, smoke_collision=smoke_collision,
            cache_dir=_cache_dirs()["fluid"],
        ), timeout=LONG)
        rend, run_dir = _render(f"explode_{target or 'point'}", quality="smoke", frame_count=preview_frames)
    except BlenderError as e:
        return _fail(e)
    text = t(
        f"폭발: 중심 {res['center']}, 반지름 {res['radius']}m, {res['burst_frame']}프레임에 터짐, 세기 {res['power']}, "
        f"불 {'있음' if res['fire'] else '없음'}, 연기 해상도 {res['resolution']}. ",
        f"Explosion: center {res['center']}, radius {res['radius']}m, bursts at frame {res['burst_frame']}, "
        f"power {res['power']}, fire {'on' if res['fire'] else 'off'}, smoke resolution {res['resolution']}. ",
    )
    if res.get("chunks"):
        pct = int((res["moved_ratio"] or 0) * 100)
        text += t(f"조각 {res['chunks']}개 중 {pct}% 가 날아감. ", f"{pct}% of {res['chunks']} chunks were thrown. ")
    if res.get("smoke_effectors"):
        text += t(f"조각 {res['smoke_effectors']}개가 연기를 막음. ", f"{res['smoke_effectors']} chunks block the smoke. ")
    text += t(f"미리보기 {rend['frames']} → {run_dir}", f"Preview {rend['frames']} → {run_dir}")
    return [text] + _images(rend["paths"])


# ---------- 물 ----------

@mcp.tool()
def water(
    mode: str = "drop",
    at: list[float] | None = None,
    size: float = 0.0,
    shape: str = "sphere",
    direction_deg: float = 0.0,
    pitch_deg: float = -90.0,
    speed: float = 0.0,
    liquid: str = "water",
    frames: int = 60,
    start_frame: int = 1,
    duration: int = 0,
    resolution: int = 64,
    viscosity: float = -1.0,
    surface_tension: float = -1.0,
    gravity_scale: float = 1.0,
    obstacles: list[str] | None = None,
    source_object: str = "",
    spray: bool = False,
    smoothing: int = 2,
    particle_radius: float = 2.0,
    domain_at: list[float] | None = None,
    domain_size: float = 0.0,
    preview_frames: int = 5,
):
    """Liquid you aim: drop it, shoot it sideways, pour a stream, fill a pool, or turn any mesh into water.
    물을 원하는 방향·모양·점성으로 만든다.

    mode: drop(덩어리가 떨어짐) / stream(호스처럼 계속 뿜음) / pool(바닥에 물이 차 있음) / object(내 메시가 물이 됨)
    at: 물이 나오는 위치 [x, y, z] (m). 비우면 대상 위
    size: 물 덩어리 반지름 또는 pool 깊이(m). 계산 격자보다 작으면 물이 안 생기니 오류로 알려 준다
    shape: sphere(공) / box(상자) / column(기둥)
    direction_deg: 나가는 방향. 0=+Y 쪽, 90=+X 쪽, 180=-Y, 270=-X
    pitch_deg: 0=수평, -90=바로 아래, +90=위로
    speed: 처음 속도(m/s). 0이면 그냥 떨어진다
    liquid: water / oil / honey / lava / mercury / slime (점성·표면장력·색 프리셋)
    viscosity, surface_tension: 프리셋을 덮어쓰는 숫자 (음수면 프리셋 그대로)
    gravity_scale: 0이면 무중력에서 떠다니는 물방울
    duration: stream 일 때 몇 프레임 동안 뿜을지
    obstacles: 물이 부딪힐 물건 이름 목록. 비우면 보이는 메시 전부(바닥판 제외)
    source_object: mode="object" 일 때 물이 될 메시 이름
    spray: 물보라·거품 알갱이 계산 켜기
    resolution: 32 빠름 / 64 보통 / 128 고화질(느리고 메모리 많이 씀)
    결과의 drift 로 물이 실제로 어느 쪽으로 갔는지 확인할 수 있다."""
    try:
        res = run_recipe("water", dict(
            mode=mode, at=at, size=size or None, shape=shape, direction_deg=direction_deg, pitch_deg=pitch_deg,
            speed=speed, liquid=liquid, frames=frames, start_frame=start_frame, duration=duration or None,
            resolution=resolution, viscosity=viscosity if viscosity >= 0 else None,
            surface_tension=surface_tension if surface_tension >= 0 else None, gravity_scale=gravity_scale,
            obstacles=obstacles or None, source_object=source_object or None, spray=spray,
            smoothing=smoothing, particle_radius=particle_radius,
            domain_at=domain_at, domain_size=domain_size or None, cache_dir=_cache_dirs()["liquid"],
        ), timeout=LONG)
        rend, run_dir = _render(f"water_{mode}_{liquid}", quality="smoke", frame_count=preview_frames)
    except BlenderError as e:
        return _fail(e)
    text = t(
        f"물({res['liquid']}, {res['mode']}): 위치 {res['at']}, 크기 {res['size']}m, 방향 {res['direction_deg']}° "
        f"기울기 {res['pitch_deg']}° 속도 {res['speed']}m/s, 점성 {res['viscosity']}, 중력 ×{res['gravity_scale']}, "
        f"해상도 {res['resolution']}, 공간 {res['domain_size_m']}m, 장애물 {res['effectors']}개. "
        f"물이 간 방향 {res['drift']} (x,y,z m). 미리보기 {rend['frames']} → {run_dir}",
        f"Water ({res['liquid']}, {res['mode']}): at {res['at']}, size {res['size']}m, direction {res['direction_deg']}° "
        f"pitch {res['pitch_deg']}° speed {res['speed']}m/s, viscosity {res['viscosity']}, gravity ×{res['gravity_scale']}, "
        f"resolution {res['resolution']}, domain {res['domain_size_m']}m, {res['effectors']} obstacles. "
        f"Water moved {res['drift']} (x,y,z m). Preview {rend['frames']} → {run_dir}",
    )
    return [text] + _images(rend["paths"])


@mcp.tool()
def splash(target: str = "", at: list[float] | None = None, radius: float = 0.0, drop_height: float = 0.0,
           velocity: float = 3.0, frames: int = 48, resolution: int = 64, preview_frames: int = 5):
    """Drop a blob of water on something (shortcut for water(mode="drop")).
    물 덩어리를 위에서 떨어뜨린다. water 의 간단 버전. 더 세밀한 제어는 water 를 쓴다."""
    at_pos = at
    if not at_pos and target:
        at_pos = None  # water 가 대상 위로 알아서 잡는다
    return water(mode="drop", at=at_pos, size=radius, speed=velocity, pitch_deg=-90.0,
                 frames=frames, resolution=resolution,
                 obstacles=[target] if target else None, preview_frames=preview_frames)


# ---------- 불·연기·파티클·환경 ----------

def _emit(kind: str, target: str, at, radius: float, power: float, frames: int, start_frame: int,
          end_frame: int, resolution: int, smoke_collision: bool, density: float, dissolve: int,
          vorticity: float, noise: bool, preview_frames: int):
    try:
        res = run_recipe("emit", dict(kind=kind, target=target or None, at=at, radius=radius or None, power=power,
                                      frames=frames, start_frame=start_frame, end_frame=end_frame or None,
                                      resolution=resolution or None, smoke_collision=smoke_collision,
                                      density=density, dissolve=dissolve, vorticity=vorticity, noise=noise,
                                      cache_dir=_cache_dirs()["emit"]), timeout=LONG)
        rend, run_dir = _render(f"{kind}_{target or 'point'}", quality="smoke", frame_count=preview_frames)
    except BlenderError as e:
        return _fail(e)
    where = t(f"대상 {res['target']}", f"target {res['target']}") if res["target"] else t(f"위치 {res['at']}", f"at {res['at']}")
    label = {"fire": t("불", "Fire"), "smoke": t("연기", "Smoke")}[kind]
    text = t(
        f"{label}: {where}, {res['emit_frames'][0]}~{res['emit_frames'][1]}프레임 동안 뿜음, 해상도 {res['resolution']}(자동), "
        f"공간 {res['domain_size_m']}m. 미리보기 {rend['frames']} → {run_dir}",
        f"{label}: {where}, emitting frames {res['emit_frames'][0]}-{res['emit_frames'][1]}, "
        f"resolution {res['resolution']} (auto), domain {res['domain_size_m']}m. Preview {rend['frames']} → {run_dir}",
    )
    return [text] + _images(rend["paths"])


@mcp.tool()
def fire(target: str = "", at: list[float] | None = None, radius: float = 0.0, power: float = 1.0, frames: int = 72,
         start_frame: int = 1, end_frame: int = 0, resolution: int = 0, smoke_collision: bool = False,
         density: float = 3.5, dissolve: int = 160, vorticity: float = 0.35, noise: bool = False,
         preview_frames: int = 4):
    """Continuous fire with smoke, burning on a target's surface or at a point.
    계속 타오르는 불. target 을 주면 그 표면이 타고, 없으면 at 위치에서 탄다.
    resolution 0 이면 대상 크기에 맞춰 자동으로 정한다(건물이면 알아서 높게).
    density 연기 농도, dissolve 사라지는 속도(클수록 오래 남음), vorticity 소용돌이, noise 디테일."""
    return _emit("fire", target, at, radius, power, frames, start_frame, end_frame, resolution,
                 smoke_collision, density, dissolve, vorticity, noise, preview_frames)


@mcp.tool()
def smoke(target: str = "", at: list[float] | None = None, radius: float = 0.0, power: float = 1.0, frames: int = 72,
          start_frame: int = 1, end_frame: int = 0, resolution: int = 0, smoke_collision: bool = False,
          density: float = 3.5, dissolve: int = 160, vorticity: float = 0.35, noise: bool = False,
          preview_frames: int = 4):
    """Rising smoke without fire (chimney, smouldering debris, fog column).
    피어오르는 연기. 인자는 fire 와 같다."""
    return _emit("smoke", target, at, radius, power, frames, start_frame, end_frame, resolution,
                 smoke_collision, density, dissolve, vorticity, noise, preview_frames)


@mcp.tool()
def particles(kind: str = "snow", target: str = "", at: list[float] | None = None, area: float = 0.0, count: int = 0,
              frames: int = 0, start_frame: int = 1, height: float = 0.0, size: float = 0.0, gravity: float = -1.0,
              drag: float = -1.0, lifetime: int = 0, speed: float = -1.0, preview_frames: int = 3):
    """Rain, snow, sparks or ash particles.
    비·눈·불꽃·재. kind: rain / snow / sparks / ash.
    size 알갱이 크기, gravity 중력 비율, drag 공기 저항, lifetime 수명(프레임), speed 튀어나가는 속도.
    음수/0 이면 프리셋 그대로."""
    try:
        res = run_recipe("particles", dict(kind=kind, target=target or None, at=at, area=area or None,
                                           count=count or None, frames=frames or None, start_frame=start_frame,
                                           height=height or None, size=size or None,
                                           gravity=gravity if gravity >= 0 else None,
                                           drag=drag if drag >= 0 else None, lifetime=lifetime or None,
                                           speed=speed if speed >= 0 else None), timeout=LONG)
        rend, _ = _render(f"particles_{kind}", frame_count=preview_frames)
    except BlenderError as e:
        return _fail(e)
    text = t(
        f"파티클 {res['kind']}: {res['count']}개, {res['frames'][0]}~{res['frames'][1]}프레임 발생, 수명 {res['lifetime']}, "
        f"크기 {res['size']}, 중력 {res['gravity']}, 저항 {res['drag']}.",
        f"Particles {res['kind']}: {res['count']}, frames {res['frames'][0]}-{res['frames'][1]}, "
        f"lifetime {res['lifetime']}, size {res['size']}, gravity {res['gravity']}, drag {res['drag']}.",
    )
    return [text + _preview_note(rend)] + _images(rend["paths"])


@mcp.tool()
def wind(direction_deg: float = 90.0, strength: float = 3.0, turbulence: float = 0.0) -> str:
    """Wind force that pushes particles, cloth and smoke.
    바람. direction_deg 0=+Y 쪽, 90=+X 쪽. strength 1 산들 / 3 보통 / 8 강풍. turbulence 흔들림(0~3)."""
    try:
        res = run_recipe("wind", dict(direction_deg=direction_deg, strength=strength, turbulence=turbulence),
                         timeout=LONG)
    except BlenderError as e:
        return _fail(e)
    return t(f"바람: 방향 {res['direction_deg']}°, 세기 {res['strength']}, 난류 {res['turbulence']} ({res['objects']}).",
             f"Wind: direction {res['direction_deg']}°, strength {res['strength']}, turbulence {res['turbulence']}.")


@mcp.tool()
def ocean(size: float = 60.0, wave_scale: float = 1.5, choppiness: float = 1.2, wind_velocity: float = 25.0,
          frames: int = 0, preview_frames: int = 3):
    """Animated ocean surface. Hides the flat ground while it exists.
    바다 표면. size 넓이(m), wave_scale 파도 높이(0.5 잔잔 / 1.5 보통 / 4 거침)."""
    try:
        res = run_recipe("ocean", dict(size=size, wave_scale=wave_scale, choppiness=choppiness,
                                       wind_velocity=wind_velocity, frames=frames or None), timeout=LONG)
        rend, _ = _render("ocean", frame_count=preview_frames)
    except BlenderError as e:
        return _fail(e)
    text = t(f"바다 {res['size_m']}m: 파도 {res['wave_scale']}, 뾰족함 {res['choppiness']}, 바람 {res['wind_velocity']}.",
             f"Ocean {res['size_m']}m: waves {res['wave_scale']}, choppiness {res['choppiness']}, wind {res['wind_velocity']}.")
    return [text + _preview_note(rend)] + _images(rend["paths"])


@mcp.tool()
def cloth_flag(at: list[float] | None = None, width: float = 3.0, height: float = 2.0, wind_strength: float = 6.0,
               frames: int = 0, preview_frames: int = 3):
    """A cloth flag on a pole, flapping in the wind.
    깃대에 걸린 깃발이 바람에 펄럭인다. at 은 깃대 밑 위치."""
    try:
        res = run_recipe("cloth_flag", dict(at=at, width=width, height=height, wind_strength=wind_strength,
                                            frames=frames or None), timeout=LONG)
        rend, _ = _render("flag", frame_count=preview_frames)
    except BlenderError as e:
        return _fail(e)
    text = t(f"깃발 {res['width']}×{res['height']}m, 깃대 {res['pole_height']}m, 끝이 {res['tip_moved_m']}m 움직임.",
             f"Flag {res['width']}×{res['height']}m, pole {res['pole_height']}m, tip moved {res['tip_moved_m']}m.")
    return [text + _preview_note(rend)] + _images(rend["paths"])


# ---------- 연출 ----------

@mcp.tool()
def set_ground(material: str = "concrete", size: float = 0.0, z: float | None = None):
    """Set the ground material: asphalt, concrete, grass, sand, dirt or snow.
    바닥 재질을 바꾼다. size 는 한 변 길이(m), z 는 높이."""
    try:
        res = run_recipe("set_ground", dict(material=material, size=size or None, z=z))
        rend, _ = _render(f"ground_{material}", frames=[1])
    except BlenderError as e:
        return _fail(e)
    text = t(f"바닥 {res['material']}: 한 변 {res['size_m']}m, 높이 {res['z']}m.",
             f"Ground {res['material']}: {res['size_m']}m wide, height {res['z']}m.")
    return [text + _preview_note(rend)] + _images(rend["paths"])


@mcp.tool()
def camera(preset: str = "medium", target: str = "", distance_factor: float = 0.0, height: float | None = None,
           angle_deg: float | None = None, lens: float = 0.0):
    """Frame the shot: wide, medium, closeup, low, high, top, front or side.
    카메라 구도. angle_deg 0=정면, 90=오른쪽, -90=왼쪽. height 0=바닥, 1=꼭대기. lens mm."""
    try:
        res = run_recipe("camera", dict(preset=preset, target=target or None, distance_factor=distance_factor or None,
                                        height=height, angle_deg=angle_deg, lens=lens or None))
        rend, _ = _render(f"camera_{preset}", frames=[1])
    except BlenderError as e:
        return _fail(e)
    text = t(f"카메라 {res['preset']}: 위치 {res['location']}, 렌즈 {res['lens']}mm.",
             f"Camera {res['preset']}: at {res['location']}, lens {res['lens']}mm.")
    return [text + _preview_note(rend)] + _images(rend["paths"])


@mcp.tool()
def camera_shake(frame: int = 12, strength: float = 0.3, duration: int = 20, seed: int = 1) -> str:
    """Shake the camera at an impact, settling down over time.
    카메라 흔들림. strength m 단위(0.1 살짝, 0.3 보통, 0.8 강하게)."""
    try:
        res = run_recipe("camera_shake", dict(frame=frame, strength=strength, duration=duration, seed=seed))
    except BlenderError as e:
        return _fail(e)
    return t(f"카메라 흔들림: {res['frame']}프레임부터 {res['duration']}프레임, 세기 {res['strength']}m.",
             f"Camera shake: from frame {res['frame']} for {res['duration']} frames, strength {res['strength']}m.")


@mcp.tool()
def set_look(preset: str = "day", sun_strength: float = 1.0, sky: str = "flat", hdri: str = ""):
    """Lighting and sky: day, sunset, night, overcast or studio; flat colour, procedural sky, or your own HDRI file.
    조명·하늘. sky="procedural" 은 진짜 하늘 텍스처(EEVEE/Cycles 에서만 보임).
    hdri 는 가지고 있는 .hdr/.exr 파일 경로. 인터넷에서 받아오지는 않는다."""
    try:
        res = run_recipe("set_look", dict(preset=preset, sun_strength=sun_strength, sky=sky, hdri=hdri or None))
        rend, _ = _render(f"look_{preset}", quality="smoke", frames=[1])
    except BlenderError as e:
        return _fail(e)
    text = t(f"분위기 {res['preset']}: 태양 {res['sun_energy']}, 고도 {res['sun_elevation_deg']}°, 하늘 {res['sky_mode']}.",
             f"Look {res['preset']}: sun {res['sun_energy']}, elevation {res['sun_elevation_deg']}°, sky {res['sky_mode']}.")
    return [text] + _images(rend["paths"])


@mcp.tool()
def set_timing(frame_start: int = 0, frame_end: int = 0, fps: int = 0, slow_from: int = 0, slow_to: int = 0,
               slow_factor: float = 0.25, global_slow: float = 0.0) -> str:
    """Frame range, fps and slow motion.
    프레임 범위·fps·슬로모션. 0 은 '그대로'.
    slow_from~slow_to 구간 슬로모션은 리지드바디·연기·물에만 걸린다(파티클 제외).
    global_slow(0.25 = 4배 느리게)는 장면 전체 시간을 늘려 파티클까지 전부 느려진다. 대신 길이가 늘어난다."""
    try:
        res = run_recipe("set_timing", dict(frame_start=frame_start or None, frame_end=frame_end or None,
                                            fps=fps or None, slow_from=slow_from or None, slow_to=slow_to or None,
                                            slow_factor=slow_factor, global_slow=global_slow or None), timeout=LONG)
    except BlenderError as e:
        return _fail(e)
    text = t(f"타이밍: 프레임 {res['frame_range'][0]}~{res['frame_range'][1]}, {res['fps']}fps.",
             f"Timing: frames {res['frame_range'][0]}-{res['frame_range'][1]}, {res['fps']}fps.")
    if res.get("slow_motion"):
        sm = res["slow_motion"]
        text += t(f" 구간 슬로모션 {sm['frames'][0]}~{sm['frames'][1]} ×{sm['factor']} ({sm['applied_to']}).",
                  f" Range slow motion {sm['frames'][0]}-{sm['frames'][1]} ×{sm['factor']} ({sm['applied_to']}).")
    if res.get("global_slow"):
        g = res["global_slow"]
        text += t(f" 전체 슬로모션 ×{g['factor']} (파티클 포함), 길이 {g['new_frame_end']}프레임.",
                  f" Global slow motion ×{g['factor']} (particles included), length now {g['new_frame_end']} frames.")
    return text


@mcp.tool()
def set_physics(gravity: float = -1.0, gravity_deg: float = 0.0, substeps: int = 0, solver_iterations: int = 0,
                speed: float = -1.0, fps: int = 0, rebake: bool = True) -> str:
    """Global physics: gravity strength and tilt, simulation accuracy, playback speed.
    물리 전역 설정. gravity 9.81 이 지구, 1.62 가 달, 0 이면 무중력.
    gravity_deg 는 중력을 기울이는 각도. substeps/solver_iterations 를 올리면 정확해지고 느려진다.
    speed 는 물리 진행 속도(0.5 = 절반). 바꾸면 시뮬레이션을 다시 굽는다."""
    try:
        res = run_recipe("set_physics", dict(gravity=gravity if gravity >= 0 else None, gravity_deg=gravity_deg,
                                             substeps=substeps or None, solver_iterations=solver_iterations or None,
                                             speed=speed if speed >= 0 else None, fps=fps or None, rebake=rebake),
                         timeout=LONG)
    except BlenderError as e:
        return _fail(e)
    return t(
        f"물리: 중력 {res['gravity']}, 하위단계 {res['substeps']}, 반복 {res['solver_iterations']}, "
        f"속도 {res['speed']}, {res['fps']}fps. 다시 구움 {res['rebaked']}.",
        f"Physics: gravity {res['gravity']}, substeps {res['substeps']}, iterations {res['solver_iterations']}, "
        f"speed {res['speed']}, {res['fps']}fps. Rebaked {res['rebaked']}.",
    )


@mcp.tool()
def set_render(samples: int = 0, motion_blur: bool | None = None, shutter: float = 0.5, width: int = 0,
               height: int = 0, exposure: float | None = None, view_transform: str = "", look: str = "",
               fps: int = 0, transparent_background: bool | None = None) -> str:
    """Render quality: samples, motion blur, resolution, exposure and film look.
    렌더 설정. samples 높을수록 깨끗하고 느림. motion_blur 는 빠른 물체를 흐리게(영화 느낌).
    view_transform/look 은 필름 룩(예: "AgX", "High Contrast"). transparent_background 는 배경 빼기."""
    try:
        res = run_recipe("set_render", dict(samples=samples or None, motion_blur=motion_blur, shutter=shutter,
                                            width=width or None, height=height or None, exposure=exposure,
                                            view_transform=view_transform or None, look=look or None,
                                            fps=fps or None, transparent_background=transparent_background))
    except BlenderError as e:
        return _fail(e)
    return t(f"렌더 설정: {res['resolution'][0]}×{res['resolution'][1]}, {res['fps']}fps, 노출 {res['exposure']}, "
             f"룩 {res['view_transform']}/{res['look']}. 바뀐 것: {res['changed']}",
             f"Render settings: {res['resolution'][0]}×{res['resolution'][1]}, {res['fps']}fps, exposure {res['exposure']}, "
             f"look {res['view_transform']}/{res['look']}. Changed: {res['changed']}")


# ---------- 저장·되돌리기 ----------

@mcp.tool()
def snapshot(name: str = "") -> str:
    """Save the current scene as a snapshot you can go back to.
    지금 장면을 저장한다. 되돌리고 싶을 수 있는 작업 전에 부른다."""
    try:
        label = re.sub(r"[^\w\-]+", "_", name)[:40] or time.strftime("%Y%m%d-%H%M%S")
        res = run_recipe("snapshot", dict(path=str(snapshot_dir() / f"{label}.blend")), timeout=LONG)
    except BlenderError as e:
        return _fail(e)
    return t(f"스냅샷 저장: {label} ({res['size_bytes'] / 1_000_000:.1f}MB, 오브젝트 {res['objects']}개). "
             f"지금 있는 스냅샷: {res['snapshots']}",
             f"Snapshot saved: {label} ({res['size_bytes'] / 1_000_000:.1f}MB, {res['objects']} objects). "
             f"Snapshots: {res['snapshots']}")


@mcp.tool()
def list_snapshots() -> str:
    """List saved snapshots.
    저장해 둔 스냅샷 목록."""
    d = snapshot_dir()
    items = sorted((f.stem, round(f.stat().st_size / 1_000_000, 1),
                    time.strftime("%Y-%m-%d %H:%M", time.localtime(f.stat().st_mtime)))
                   for f in d.glob("*.blend"))
    if not items:
        return t(f"스냅샷이 없습니다. snapshot 으로 먼저 저장하세요. (폴더: {d})",
                 f"No snapshots yet. Save one with the snapshot tool. (folder: {d})")
    return t("스냅샷 목록:\n", "Snapshots:\n") + "\n".join(f"- {n} ({mb}MB, {when})" for n, mb, when in items)


@mcp.tool()
def restore(name: str) -> str:
    """Go back to a snapshot. The current scene is auto-saved as "before_restore" first, so this is undoable.
    스냅샷으로 되돌린다. 되돌리기 직전 상태가 before_restore 로 자동 저장되므로 되돌리기도 되돌릴 수 있다."""
    label = re.sub(r"[^\w\-]+", "_", name)[:40]
    auto = True
    try:
        run_recipe("snapshot", dict(path=str(snapshot_dir() / "before_restore.blend")), timeout=LONG)
    except BlenderError:
        auto = False
    try:
        res = run_recipe("restore", dict(path=str(snapshot_dir() / f"{label}.blend")), timeout=300.0)
    except BlenderError as e:
        return _fail(e)
    text = t(
        f"되돌리기 완료: {label} (오브젝트 {res['objects']}개, 메시 {res['meshes']}개, "
        f"프레임 {res['frame_range'][0]}~{res['frame_range'][1]}, 카메라 {res['camera']}).",
        f"Restored: {label} ({res['objects']} objects, {res['meshes']} meshes, "
        f"frames {res['frame_range'][0]}-{res['frame_range'][1]}, camera {res['camera']}).",
    )
    text += t(" 직전 상태는 before_restore 로 저장해 두었습니다." if auto else " 직전 상태는 저장하지 못했습니다.",
              " The previous state was saved as before_restore." if auto else " The previous state could not be saved.")
    return text


@mcp.tool()
def save_blend(name: str = "fx_scene") -> str:
    """Save the scene as a .blend file you can open in Blender yourself.
    현재 장면을 .blend 로 저장한다."""
    try:
        run_dir = new_run_dir(f"blend_{name}")
        res = run_recipe("save_blend", dict(path=str(run_dir / f"{name}.blend")), timeout=LONG)
    except BlenderError as e:
        return _fail(e)
    return t(f"저장 완료: {res['path']} ({res['size_bytes'] / 1_000_000:.1f}MB). {res['note']}",
             f"Saved: {res['path']} ({res['size_bytes'] / 1_000_000:.1f}MB). "
             f"Fluid caches live in the cache folder, not inside the .blend.")


# ---------- 렌더·정리 ----------

@mcp.tool()
def render_preview(frame_count: int = 5, quality: str = "preview", width: int = 640, height: int = 360,
                   frames: list[int] | None = None):
    """Re-render the current scene. quality: preview (fast, no sky/smoke/water), smoke (shows them), final (high quality).
    현재 장면을 다시 렌더한다."""
    try:
        run_dir = new_run_dir(f"render_{quality}")
        params = dict(out_dir=str(run_dir), frame_count=frame_count, quality=quality, width=width, height=height)
        if frames:
            params["frames"] = list(frames)
        rend = run_recipe("render", params, timeout=LONG)
    except BlenderError as e:
        return _fail(e)
    text = t(f"렌더 ({rend['engine']}, {rend['size'][0]}×{rend['size'][1]}): 프레임 {rend['frames']} → {run_dir}",
             f"Render ({rend['engine']}, {rend['size'][0]}×{rend['size'][1]}): frames {rend['frames']} → {run_dir}")
    return [text + _preview_note(rend)] + _images(rend["paths"])


@mcp.tool()
def render_video(quality: str = "smoke", width: int = 1280, height: int = 720, fps: int = 0,
                 frame_start: int = 0, frame_end: int = 0, name: str = "") -> str:
    """Render the whole scene to an mp4 video.
    장면 전체를 mp4 로 렌더한다. 72프레임 720p 기준 1~3분."""
    try:
        run_dir = new_run_dir(f"video_{name or quality}")
        res = run_recipe("render_video", dict(
            out_path=str(run_dir / f"{name or 'fx'}.mp4"), quality=quality, width=width, height=height,
            fps=fps or None, frame_start=frame_start or None, frame_end=frame_end or None,
        ), timeout=max(LONG, 3600.0))
    except BlenderError as e:
        return _fail(e)
    mb = res["size_bytes"] / 1_000_000
    return t(
        f"영상: {res['path']} ({mb:.1f}MB, {res['size'][0]}×{res['size'][1]}, {res['fps']}fps, "
        f"프레임 {res['frames'][0]}~{res['frames'][1]}, {res['engine']})",
        f"Video: {res['path']} ({mb:.1f}MB, {res['size'][0]}×{res['size'][1]}, {res['fps']}fps, "
        f"frames {res['frames'][0]}-{res['frames'][1]}, {res['engine']})",
    )


@mcp.tool()
def clear_caches() -> str:
    """Clear baked caches and free disk space.
    구운 캐시와 캐시 폴더를 비운다. 다음 도구 호출 때 다시 굽는다."""
    try:
        res = run_recipe("clear_caches", dict(cache_dirs=list(_cache_dirs().values())), timeout=LONG)
    except BlenderError as e:
        return _fail(e)
    return t(f"캐시 정리: {res['freed_mb']}MB 비움, 유체 도메인 {res['fluid_domains']}개 초기화.",
             f"Caches cleared: freed {res['freed_mb']}MB, reset {res['fluid_domains']} fluid domains.")


@mcp.tool()
def reset_destroy(target: str = "") -> str:
    """Remove everything this toolbox created and bring the originals back.
    이 도구가 만든 것(조각·먼지·연기·물·파티클·바다·깃발·접착)을 지우고 원본을 되살린다."""
    try:
        res = run_recipe("reset", dict(target=target or None), timeout=LONG)
    except BlenderError as e:
        return _fail(e)
    return t(f"정리 완료: 오브젝트 {res['removed']}개 제거, 원본 복구.",
             f"Cleanup done: removed {res['removed']} objects, originals restored.")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
