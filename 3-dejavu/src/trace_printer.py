import json as _json
from datetime import datetime

_COL  = 46   # largura da coluna esquerda — igual ao Manager
_BOX  = "─" * 67

# Dicts exibidos no bloco de contexto (mesma ordem do Manager)
_CTX_DICTS     = ("obstacles", "objects", "scripts", "target_goal", "scene", "robot_config")
_PAIRED_CTX    = {"fingers_width", "dist_ee_to_cube", "dist_cube_to_target", "finger_contacts"}


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:.4f}"
    if isinstance(v, list):
        return "[" + ", ".join(_fmt(x) for x in v) + "]"
    return str(v)


def _row(left: str, right: str = "x") -> str:
    return f"  {left:<{_COL}}  {right}"


def format_tick(
    episode,
    step: int,
    subtask: str,
    sm_params: dict,
    active_state: str,
    sat,
    transitions: list[dict],
    action_queued: str | None,
    unanticipated: bool,
    context_params: dict | None = None,
) -> str:
    now    = _ts()
    pre    = f"[step={step:4d} {now}]"
    lines: list[str] = [""]   # linha em branco entre ticks

    # ── Cabeçalho ────────────────────────────────────────────────────────────
    reward_str = f"  reward={context_params.get('reward', 0):.4f}" if context_params else ""
    flag       = "  *** CENÁRIO NÃO ANTECIPADO ***" if unanticipated else ""
    lines.append(f"{pre}[DejaVu] ep={episode}  subtask={subtask}{reward_str}{flag}")

    # ── Tabela de percepção ──────────────────────────────────────────────────
    if context_params:
        ctx = context_params
        g   = lambda k, d=0: ctx.get(k, d)
        cube = [g("cube_x", 0.0), g("cube_y", 0.0), g("cube_z", 0.0)]

        lines.append(f"{pre}[Perception]")
        lines.append(f"  {'CONTEXTO':<{_COL}}  PARÂMETROS SM")
        lines.append(f"  {'-' * _COL}  {'-' * 38}")

        # Pares diretos CONTEXTO ↔ PARÂMETROS SM (mesmos 6 do Manager)
        pairs = [
            (f"fingers_width         = {g('fingers_width', 0):.4f} m",
             f"gripper_width_cm      = {sm_params.get('gripper_width_cm', 0)} cm"),
            (f"dist_ee_to_cube       = {g('dist_ee_to_cube', 0):.4f} m",
             f"distance_ee_object_cm = {sm_params.get('distance_ee_object_cm', 0)} cm"),
            (f"dist_cube_to_target   = {g('dist_cube_to_target', 0):.4f} m  (3D)",
             f"distance_obj_goal_cm  = {sm_params.get('distance_object_goal_cm', 0)} cm  (XY)"),
            (f"cube_position (z)     = {cube[2]:.4f} m",
             f"object_lift_height_cm = {sm_params.get('object_lift_height_cm', 0)} cm"),
            (f"cube_position (xy)    = [{cube[0]:.3f}, {cube[1]:.3f}]",
             f"grasp_completed       = {sm_params.get('grasp_completed', 0)}"),
            (f"finger_contacts (raw) = {int(g('finger_contacts', 0))}",
             f"finger_contacts       = {sm_params.get('finger_contacts', 0)}"),
        ]
        for left, right in pairs:
            lines.append(_row(left, right))

        # SM sem equivalente no contexto  (x | SM)
        for right in [
            f"grasp_attempts        = {sm_params.get('grasp_attempts', 0)}",
            f"task_started          = {sm_params.get('task_started', 0)}",
            f"object_available      = {sm_params.get('object_available', 0)}",
            f"task_aborted          = {sm_params.get('task_aborted', 0)}",
        ]:
            lines.append(_row("x", right))

        # Contexto sem equivalente SM  (ctx | x) — mesma ordem do Manager
        ee_pos = [g("ee_x", 0.0), g("ee_y", 0.0), g("ee_z", 0.0)]
        ee_vel = [g("ee_vx", 0.0), g("ee_vy", 0.0), g("ee_vz", 0.0)]
        tgt    = [g("target_x", 0.0), g("target_y", 0.0), g("target_z", 0.0)]
        action = [g("action_x", 0.0), g("action_y", 0.0), g("action_z", 0.0), g("action_gripper", 0.0)]
        ja     = [g(f"j{i}", 0.0) for i in range(7)]
        jv     = [g(f"jv{i}", 0.0) for i in range(7)]
        c_rot  = [g("cube_roll", 0.0), g("cube_pitch", 0.0), g("cube_yaw", 0.0)]
        c_vel  = [g("cube_vx", 0.0), g("cube_vy", 0.0), g("cube_vz", 0.0)]

        for k, v in [
            ("episode",                ctx.get("episode", "?")),
            ("step",                   ctx.get("step", "?")),
            ("ee_position",            ee_pos),
            ("ee_velocity",            ee_vel),
            ("target_position",        tgt),
            ("reward",                 g("reward", 0.0)),
            ("is_success",             ctx.get("is_success", False)),
            ("obstacle_in_path",       ctx.get("obstacle_in_path", False)),
            ("obstacle_count_in_path", int(g("obstacle_count_in_path", 0))),
        ]:
            lines.append(_row(f"{k:<22} = {_fmt(v)}"))

        for k in _CTX_DICTS:
            v = ctx.get(k)
            if v is not None:
                lines.append(_row(f"{k:<22} = {_fmt(v)}"))

        for k, v in [
            ("current_task",        ctx.get("current_task", "")),
            ("current_subtask",     ctx.get("current_subtask", "")),
            ("active_target_name",  ctx.get("active_target_name", "")),
        ]:
            lines.append(_row(f"{k:<22} = {v}"))

        for k, v in [
            ("action",               action),
            ("joint_angles",         ja),
            ("joint_velocities",     jv),
            ("cube_rotation",        c_rot),
            ("cube_linear_velocity", c_vel),
        ]:
            lines.append(_row(f"{k:<22} = {_fmt(v)}"))

        v = ctx.get("obstacle_positions", {})
        lines.append(_row(f"{'obstacle_positions':<22} = {_fmt(v)}"))

    # ── State Machine ────────────────────────────────────────────────────────
    if action_queued:
        lines.append(f"{pre}[SM] ação→ {action_queued}  [nova neste tick]")

    if transitions:
        for tr in transitions:
            mark    = "✗  UNSAT" if tr["is_error"] else "✓"
            trigger = tr["guard"] or tr["event"] or "—"
            lines.append(f"{pre}[SM] {tr['source']} ──[{trigger}]──► {tr['target']}   {mark}")
    else:
        lines.append(f"{pre}[SM] (sem transições neste tick)")

    sat_str = "False  *** UNSAT ***" if sat is False else str(sat)
    lines.append(f"{pre}[SM] estado={active_state}   SAT={sat_str}")

    return "\n".join(lines)


def format_pipeline_detect(detected_df) -> str:
    lines = ["", "DejaVu Pipeline:"]
    if detected_df is None or (hasattr(detected_df, "empty") and detected_df.empty):
        lines.append("  [DETECT]  nenhuma violação encontrada no CSV.")
        return "\n".join(lines)

    scenario = "?"
    if "anticipated_scenario" in detected_df.columns:
        vals = detected_df["anticipated_scenario"].dropna()
        scenario = vals.iloc[0] if not vals.empty else "?"

    rows_false = detected_df[detected_df["SAT"] == False] if "SAT" in detected_df.columns else detected_df

    lines += [
        f"  ┌─ DETECT {'─' * len(_BOX)}",
        f"  │  Cenário violado   : {scenario}",
        f"  │  Linhas capturadas : {len(detected_df)}  ({len(rows_false)} com SAT=False)",
        f"  └{'─' * 69}",
    ]
    return "\n".join(lines)


def format_pipeline_identify(identified: dict | None) -> str:
    if not identified:
        return "  [IDENTIFY]  nenhum cenário identificado."
    lines = [
        f"  ┌─ IDENTIFY {'─' * len(_BOX)}",
        f"  │  Nome  : {identified.get('name', '?')}",
        f"  │  Given : {identified.get('given', '?')}",
        f"  │  When  : {identified.get('when', '?')}",
        f"  │  Do    : {identified.get('do', '?')}",
        f"  │  Then  : {identified.get('then', '?')}",
        f"  └{'─' * 69}",
    ]
    return "\n".join(lines)


def format_pipeline_diagnose(diagnosed: dict | None) -> str:
    if not diagnosed:
        return ""
    lines = [
        f"  ┌─ DIAGNOSE {'─' * len(_BOX)}",
        f"  │  Nome  : {diagnosed.get('name', '?')}",
        f"  │  Given : {diagnosed.get('given', '?')}",
        f"  │  When  : {diagnosed.get('when', '?')}",
        f"  │  Do    : {diagnosed.get('do', '?')}",
        f"  │  Then  : {diagnosed.get('then', '?')}",
        f"  └{'─' * 69}",
    ]
    return "\n".join(lines)


def format_pipeline_similarities(similarities: list | None) -> str:
    if not similarities:
        return ""
    lines = [f"  ┌─ SIMILARITIES {'─' * len(_BOX)}"]
    for i, s in enumerate(similarities, 1):
        score = s.get("similarity_result", "?")
        cand  = s.get("candidate", {})
        name  = cand.get("name", f"candidate_{i}")
        score_str = f"{score:.5f}" if isinstance(score, float) else str(score)
        lines.append(f"  │  [{i}] {name:<40} score={score_str}")
    lines.append(f"  └{'─' * 69}")
    return "\n".join(lines)


def format_pipeline_adaptation(adaptation: str | None) -> str:
    if not adaptation:
        return ""
    lines = [
        f"  ┌─ ADAPTATION {'─' * len(_BOX)}",
        f"  │  Estratégia aplicada: {adaptation}",
        f"  └{'─' * 69}",
    ]
    return "\n".join(lines)
