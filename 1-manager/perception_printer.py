from ts import ts

_COL = 46  # largura da coluna RAW

_PAIRED_RAW_KEYS = {"fingers_width", "dist_ee_to_cube", "dist_cube_to_target",
                    "cube_position", "target_position"}


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:.4f}"
    if isinstance(v, list):
        return "[" + ", ".join(_fmt(x) for x in v) + "]"
    return str(v)


def print_perception(msg: dict, state) -> None:
    cube = msg.get("cube_position", [0, 0, 0])
    tgt  = msg.get("target_position", [0, 0, 0])

    # ── 1. linhas com equivalência directa (raw ↔ monitored) ─────────────────
    pairs = [
        (f"fingers_width         = {msg.get('fingers_width', 0):.4f} m",
         f"gripper_width_cm      = {state.gripper_width_cm} cm"),
        (f"dist_ee_to_cube       = {msg.get('dist_ee_to_cube', 0):.4f} m",
         f"distance_ee_object_cm = {state.distance_ee_object_cm} cm"),
        (f"dist_cube_to_target   = {msg.get('dist_cube_to_target', 0):.4f} m  (3D)",
         f"distance_obj_goal_cm  = {state.distance_object_goal_cm} cm  (XY)"),
        (f"cube_position (z)     = {cube[2]:.4f} m",
         f"object_lift_height_cm = {state.object_lift_height_cm} cm"),
        (f"cube_position (xy)    = [{cube[0]:.3f}, {cube[1]:.3f}]",
         f"grasp_completed       = {state.grasp_completed}"),
        (f"target_position (xy)  = [{tgt[0]:.3f}, {tgt[1]:.3f}]",
         f"finger_contacts       = {state.finger_contacts}"),
    ]

    # ── 2. monitored sem equivalente raw ─────────────────────────────────────
    mon_only = [
        f"grasp_attempts        = {state.grasp_attempts}",
    ]

    # ── 3. raw sem equivalente monitored ─────────────────────────────────────
    raw_only = [
        f"{k:<22} = {_fmt(v)}"
        for k, v in msg.items()
        if k not in _PAIRED_RAW_KEYS
    ]

    # ── print ─────────────────────────────────────────────────────────────────
    header  = f"  {'RAW PERCEPTION':<{_COL}}  MONITORED PARAMS"
    divider = f"  {'-' * _COL}  {'-' * 38}"
    print(f"[{ts()}][Perception]\n{header}\n{divider}")

    for left, right in pairs:
        print(f"  {left:<{_COL}}  {right}")

    for right in mon_only:
        print(f"  {'x':<{_COL}}  {right}")

    for left in raw_only:
        print(f"  {left:<{_COL}}  x")
