class SimHUD:
    """Exibe o estado da simulação como texto 3D na janela do PyBullet."""

    _LABELS = [
        "header", "task", "action",
        "ee_pos", "ee_vel", "garra",
        "cube_pos", "target",
        "dist_ee_cube", "dist_cube_tgt",
        "reward", "sucesso", "obstacle",
    ]
    _X     = -0.3
    _Y     =  0.8
    _Z_TOP =  0.75
    _Z_STEP = 0.07

    def __init__(self, physics_client) -> None:
        self._client = physics_client
        self._ids: dict = {}

    def render(self, msg: dict) -> None:
        ee_pos    = msg["ee_position"]
        ee_vel    = msg["ee_velocity"]
        fingers   = msg["fingers_width"]
        cube_pos  = msg["cube_position"]
        tgt_pos   = msg["target_position"]
        gripper   = "ABERTA" if fingers > 0.02 else "FECHADA"
        success   = msg["is_success"]

        action_str = ""
        if "action" in msg:
            a = msg["action"]
            action_str = f"[{a[0]:+.3f}, {a[1]:+.3f}, {a[2]:+.3f}, {a[3]:+.3f}]"

        lines = [
            (f"Ep {msg['episode']:>2} | Step {msg['step']:>3}",                                      [1.0, 1.0, 1.0]),
            (f"Task   : {msg.get('current_task', '?')}",                                              [0.5, 0.9, 1.0]),
            (f"Action : {action_str}",                                                                [0.5, 0.9, 1.0]),
            (f"EE pos : [{ee_pos[0]:+.3f}, {ee_pos[1]:+.3f}, {ee_pos[2]:+.3f}]",                   [1.0, 1.0, 1.0]),
            (f"EE vel : [{ee_vel[0]:+.3f}, {ee_vel[1]:+.3f}, {ee_vel[2]:+.3f}]",                   [1.0, 1.0, 1.0]),
            (f"Garra  : {fingers:.3f} m  ({gripper})",                                               [1.0, 0.8, 0.2] if gripper == "ABERTA" else [0.4, 1.0, 0.4]),
            (f"Cubo   : [{cube_pos[0]:+.3f}, {cube_pos[1]:+.3f}, {cube_pos[2]:+.3f}]",             [1.0, 1.0, 1.0]),
            (f"Target : [{tgt_pos[0]:+.3f}, {tgt_pos[1]:+.3f}, {tgt_pos[2]:+.3f}]",               [1.0, 1.0, 1.0]),
            (f"Dist EE->Cubo    : {msg['dist_ee_to_cube']:.4f} m",                                  [1.0, 1.0, 1.0]),
            (f"Dist Cubo->Target: {msg['dist_cube_to_target']:.4f} m",                              [1.0, 1.0, 1.0]),
            (f"Reward : {msg['reward']:+.4f}",                                                       [1.0, 1.0, 1.0]),
            (f"Sucesso: {success}",                                                                   [0.4, 1.0, 0.4] if success else [1.0, 1.0, 1.0]),
            (f"Obst.  : {'SIM' if msg['obstacle_in_path'] else 'nao'}  (count: {msg['obstacle_count_in_path']})",
                                                                                                      [1.0, 0.4, 0.4] if msg["obstacle_in_path"] else [1.0, 1.0, 1.0]),
        ]

        for label, (text, color) in zip(self._LABELS, lines):
            idx   = self._LABELS.index(label)
            pos   = [self._X, self._Y, self._Z_TOP - idx * self._Z_STEP]
            self._update(label, text, pos, color)

    def _update(self, key: str, text: str, position: list, color: list) -> None:
        kwargs = dict(textPosition=position, textColorRGB=color, textSize=1.3, lifeTime=0)
        if key in self._ids:
            self._client.addUserDebugText(text, replaceItemUniqueId=self._ids[key], **kwargs)
        else:
            self._ids[key] = self._client.addUserDebugText(text, **kwargs)
