_SEP  = "═" * 72
_LINE = "─" * 72
_BOX  = "─" * 67


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
) -> str:
    flag = "   *** CENÁRIO NÃO ANTECIPADO ***" if unanticipated else ""
    lines = [
        _SEP,
        f"[ep={episode}  step={step:04d}]  subtask={subtask}{flag}",
        _LINE,
        "Parâmetros SM:",
        f"  task_started={sm_params.get('task_started',0):<3}  "
        f"object_available={sm_params.get('object_available',0):<3}  "
        f"gripper_width_cm={sm_params.get('gripper_width_cm',0)}",
        f"  dist_ee_obj={sm_params.get('distance_ee_object_cm',0):<6}  "
        f"grasp_completed={sm_params.get('grasp_completed',0):<3}  "
        f"finger_contacts={sm_params.get('finger_contacts',0)}",
        f"  grasp_attempts={sm_params.get('grasp_attempts',0):<3}  "
        f"lift_height_cm={sm_params.get('object_lift_height_cm',0):<6}  "
        f"dist_obj_goal={sm_params.get('distance_object_goal_cm',0)}",
        f"  task_aborted={sm_params.get('task_aborted',0)}",
        "",
        "State Machine:",
    ]

    if action_queued:
        lines.append(f"  ação → {action_queued}  [nova neste tick]")

    if transitions:
        for tr in transitions:
            mark    = "✗  UNSAT" if tr["is_error"] else "✓"
            trigger = tr["guard"] or tr["event"] or "—"
            lines.append(f"  {tr['source']} ──[{trigger}]──► {tr['target']}   {mark}")
    else:
        lines.append("  (sem transições neste tick)")

    sat_str = "False  *** UNSAT ***" if sat is False else str(sat)
    lines.append(f"  Estado ativo: {active_state}   SAT: {sat_str}")

    return "\n".join(lines)


def format_pipeline_detect(detected_df) -> str:
    lines = ["", "DejaVu Pipeline:"]
    if detected_df is None or (hasattr(detected_df, "empty") and detected_df.empty):
        lines.append("  [DETECT]  nenhuma violação encontrada no CSV.")
        return "\n".join(lines)

    scenario = "?"
    if "anticipated_scenario" in detected_df.columns:
        scenario = detected_df["anticipated_scenario"].dropna().iloc[0] if not detected_df["anticipated_scenario"].dropna().empty else "?"

    rows_false = detected_df[detected_df["SAT"] == False] if "SAT" in detected_df.columns else detected_df
    n_rows = len(detected_df)

    lines += [
        f"  ┌─ DETECT {'─' * _BOX.__len__()}",
        f"  │  Cenário violado   : {scenario}",
        f"  │  Linhas capturadas : {n_rows}  ({len(rows_false)} com SAT=False)",
        f"  └{'─' * 69}",
    ]
    return "\n".join(lines)


def format_pipeline_identify(identified: dict | None) -> str:
    if not identified:
        return "  [IDENTIFY]  nenhum cenário identificado."
    lines = [
        f"  ┌─ IDENTIFY {'─' * _BOX.__len__()}",
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
        f"  ┌─ DIAGNOSE {'─' * _BOX.__len__()}",
        f"  │  Nome  : {diagnosed.get('name', '?')}",
        f"  │  Given : {diagnosed.get('given', '?')}",
        f"  │  Do    : {diagnosed.get('do', '?')}",
        f"  └{'─' * 69}",
    ]
    return "\n".join(lines)


def format_pipeline_similarities(similarities: list | None) -> str:
    if not similarities:
        return ""
    lines = [f"  ┌─ SIMILARITIES {'─' * _BOX.__len__()}"]
    for i, s in enumerate(similarities[:5], 1):
        result = s.get("similarity_result", {})
        score  = result.get("similarity", result.get("score", "?"))
        cand   = s.get("candidate", {})
        name   = cand.get("name", f"candidate_{i}")
        lines.append(f"  │  [{i}] {name:<40} score={score}")
    lines.append(f"  └{'─' * 69}")
    return "\n".join(lines)


def format_pipeline_adaptation(adaptation: str | None) -> str:
    if not adaptation:
        return ""
    lines = [
        f"  ┌─ ADAPTATION {'─' * _BOX.__len__()}",
        f"  │  Estratégia aplicada: {adaptation}",
        f"  └{'─' * 69}",
    ]
    return "\n".join(lines)
