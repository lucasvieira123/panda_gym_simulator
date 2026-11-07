RELEASED_MIN_WIDTH_M = 0.06  # mesma condição do Then de PLACE_OBJECT no ASM: gripper_width_cm >= 6


def physical_outcome(msg: dict, distance_threshold: float) -> dict:
    """
    Objetivo global da tarefa: objeto dentro do limite de distância do alvo e garra aberta.

    Não usa is_success, que só indica o fim da sequência de ações. Também não exige zero
    contatos: com a garra aberta, o cubo pode continuar encostado em um dedo.
    """
    placed   = msg["dist_cube_to_target"] <= distance_threshold
    released = msg["fingers_width"] >= RELEASED_MIN_WIDTH_M
    return {
        "object_within_threshold": bool(placed),
        "gripper_open":            bool(released),
        "global_goal_achieved":    bool(placed and released),
    }
