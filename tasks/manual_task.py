from typing import Callable

import numpy as np
import pybullet

from ._object_task import _ObjectTask


class ManualTask(_ObjectTask):
    def __init__(
        self,
        sim,
        get_ee_position: Callable[[], np.ndarray],
        get_object_position: Callable[[], np.ndarray],
        target_goal_cfg: dict,
        object_cfg: dict,
        task_cfg: dict = None,
    ) -> None:
        super().__init__(sim, get_ee_position, get_object_position, target_goal_cfg, object_cfg, task_cfg)
        _task = task_cfg or {}
        self.move_speed    = _task.get("move_speed", 0.5)
        self._gripper_open = True

    def reset(self) -> None:
        self._gripper_open = True
        super().reset()

    # ── action ───────────────────────────────────────────────────────────────

    def compute_action(self) -> np.ndarray:
        dx, dy, dz = 0.0, 0.0, 0.0
        s = self.move_speed

        keys = pybullet.getKeyboardEvents()

        if ord(' ') in keys and keys[ord(' ')] & pybullet.KEY_WAS_TRIGGERED:
            self._gripper_open = not self._gripper_open
            print(f"[Garra] {'ABERTA' if self._gripper_open else 'FECHADA'}")

        if pybullet.B3G_UP_ARROW    in keys and keys[pybullet.B3G_UP_ARROW]    & pybullet.KEY_IS_DOWN: dx += s
        if pybullet.B3G_DOWN_ARROW  in keys and keys[pybullet.B3G_DOWN_ARROW]  & pybullet.KEY_IS_DOWN: dx -= s
        if pybullet.B3G_LEFT_ARROW  in keys and keys[pybullet.B3G_LEFT_ARROW]  & pybullet.KEY_IS_DOWN: dy += s
        if pybullet.B3G_RIGHT_ARROW in keys and keys[pybullet.B3G_RIGHT_ARROW] & pybullet.KEY_IS_DOWN: dy -= s
        if ord('q') in keys and keys[ord('q')] & pybullet.KEY_IS_DOWN: dz += s
        if ord('e') in keys and keys[ord('e')] & pybullet.KEY_IS_DOWN: dz -= s

        if self._goal_mode != "options" and self._goal_reached() and not self._all_done():
            self._advance_goal()

        gripper = 1.0 if self._gripper_open else -1.0
        return np.array([dx, dy, dz, gripper], dtype=np.float32)
