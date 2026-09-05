from typing import Callable

import numpy as np

from .._object_task import _ObjectTask
from utils import ts

_SAFE_HEIGHT   = 0.15   # clearance above object before descending
_APPROACH_DIST = 0.10   # lateral distance from object center to start approach
_LIFT_HEIGHT   = 0.15   # final transport height (same as normal lift)

_PHASE_BOOST    = 0
_PHASE_RISE     = 1
_PHASE_DESCEND  = 2
_PHASE_APPROACH = 3
_PHASE_CLOSE    = 4
_PHASE_LIFT     = 5
_PHASE_DONE     = 6


def _rotate_vec(quat: np.ndarray, v: np.ndarray) -> np.ndarray:
    x, y, z, w = quat
    return np.array([
        (1 - 2*(y*y + z*z))*v[0] + 2*(x*y - w*z)*v[1] + 2*(x*z + w*y)*v[2],
        2*(x*y + w*z)*v[0] + (1 - 2*(x*x + z*z))*v[1] + 2*(y*z - w*x)*v[2],
        2*(x*z - w*y)*v[0] + 2*(y*z + w*x)*v[1] + (1 - 2*(x*x + y*y))*v[2],
    ])


def _face_aligned_approach_xy(obj_xy: np.ndarray, target_xy: np.ndarray,
                               quat: np.ndarray, dist: float) -> np.ndarray:
    ref = obj_xy - target_xy
    ref_norm = np.linalg.norm(ref)
    ref_dir = ref / ref_norm if ref_norm > 1e-6 else np.array([1.0, 0.0])

    body_axes = [
        np.array([1, 0, 0]), np.array([-1, 0, 0]),
        np.array([0, 1, 0]), np.array([0, -1, 0]),
        np.array([0, 0, 1]), np.array([0, 0, -1]),
    ]
    world_normals = [_rotate_vec(quat, ax) for ax in body_axes]

    best_score = -np.inf
    best_dir = ref_dir

    for n in world_normals:
        horiz = np.sqrt(n[0]**2 + n[1]**2)
        if horiz < 0.5:
            continue
        nxy = np.array([n[0], n[1]]) / horiz
        alignment = float(np.dot(nxy, ref_dir))
        score = horiz * 0.4 + alignment * 0.6
        if score > best_score:
            best_score = score
            best_dir = nxy

    return obj_xy + (-best_dir) * dist


class HeavyLiftTask(_ObjectTask):

    return_to       = "TRANSPORT_OBJECT"
    current_subtask = "HEAVY_LIFT"

    def __init__(
        self,
        sim,
        robot,
        fingers_indices,
        get_ee_position: Callable[[], np.ndarray],
        get_object_position: Callable[[], np.ndarray],
        get_object_orientation: Callable[[], np.ndarray],
        target_goal_cfg: dict,
        object_cfg: dict,
        task_cfg: dict = None,
    ) -> None:
        super().__init__(sim, get_ee_position, get_object_position, target_goal_cfg, object_cfg, task_cfg)
        self._robot                 = robot
        self._fingers_indices       = fingers_indices
        self.get_object_orientation = get_object_orientation
        _cfg = task_cfg or {}
        self.boosted_friction    = _cfg.get("incremental_friction",    10.0)
        self.boosted_joint_force = _cfg.get("incremental_joint_force", 500.0)
        self.threshold           = _cfg.get("phase_threshold",         0.02)
        self._phase           = _PHASE_BOOST
        self._approach_xy: np.ndarray | None = None
        self._base_z: float | None           = None
        self._close_ticks     = 0

    def reset(self) -> None:
        self._phase       = _PHASE_BOOST
        self._approach_xy = None
        self._base_z      = None
        self._close_ticks = 0
        super().reset()

    def _reset_object(self) -> None:
        pass

    def compute_action(self) -> np.ndarray:
        ee_pos  = np.array(self.get_ee_position())
        obj_pos = np.array(self.get_object_position())
        target  = np.array(self.goal[:3])

        if self._phase == _PHASE_BOOST:
            for link in self._fingers_indices:
                self.sim.set_lateral_friction("panda", int(link), self.boosted_friction)
            self._robot.joint_forces[:7] = self.boosted_joint_force
            print(f"[{ts()}][HeavyLift] lateralFriction → {self.boosted_friction} | joint_forces[:7] → {self.boosted_joint_force} ✓")
            self._phase = _PHASE_RISE
            gripper = 1.0
            dest    = ee_pos

        elif self._phase == _PHASE_RISE:
            if self._approach_xy is None:
                quat = self.get_object_orientation()
                self._approach_xy = _face_aligned_approach_xy(obj_pos[:2], target[:2], quat, _APPROACH_DIST)
                face_deg = np.degrees(np.arctan2(
                    obj_pos[1] - self._approach_xy[1],
                    obj_pos[0] - self._approach_xy[0],
                ))
                print(f"[{ts()}][HeavyLift] quat={np.round(quat,2)} → face {face_deg:.1f}°")

            rise_pos = np.array([self._approach_xy[0], self._approach_xy[1], obj_pos[2] + _SAFE_HEIGHT])
            gripper  = 1.0
            dest     = rise_pos
            if np.linalg.norm(ee_pos - rise_pos) < self.threshold:
                print(f"[{ts()}][HeavyLift] RISE ✓ — descendo para lateral")
                self._phase = _PHASE_DESCEND

        elif self._phase == _PHASE_DESCEND:
            descent_pos = np.array([self._approach_xy[0], self._approach_xy[1], obj_pos[2]])
            gripper = 1.0
            dest    = descent_pos
            if np.linalg.norm(ee_pos - descent_pos) < self.threshold:
                print(f"[{ts()}][HeavyLift] DESCEND ✓ — avançando para face")
                self._phase = _PHASE_APPROACH

        elif self._phase == _PHASE_APPROACH:
            grasp_pos = np.array([obj_pos[0], obj_pos[1], obj_pos[2]])
            gripper   = 1.0
            dest      = grasp_pos
            if np.linalg.norm(ee_pos - grasp_pos) < self.threshold:
                print(f"[{ts()}][HeavyLift] APPROACH ✓ — fechando gripper")
                self._phase = _PHASE_CLOSE

        elif self._phase == _PHASE_CLOSE:
            gripper = -1.0
            dest    = ee_pos
            if self._base_z is None:
                self._base_z = obj_pos[2]
            self._close_ticks += 1
            if self._close_ticks >= 2:
                print(f"[{ts()}][HeavyLift] CLOSE ✓ — levantando")
                self._phase = _PHASE_LIFT

        elif self._phase == _PHASE_LIFT:
            target_z = self._base_z + _LIFT_HEIGHT
            lift_pos = np.array([ee_pos[0], ee_pos[1], target_z])
            gripper  = -1.0
            dest     = lift_pos
            if abs(ee_pos[2] - target_z) < self.threshold:
                print(f"[{ts()}][HeavyLift] LIFT ✓ — retornando ao fluxo normal")
                self._phase = _PHASE_DONE

        else:  # _PHASE_DONE
            gripper = -1.0
            dest    = ee_pos

        direction = dest - ee_pos
        dist = np.linalg.norm(direction)
        if dist > 0:
            direction = direction / dist

        return np.array([direction[0], direction[1], direction[2], gripper], dtype=np.float32)

    @property
    def done(self) -> bool:
        return self._phase == _PHASE_DONE
