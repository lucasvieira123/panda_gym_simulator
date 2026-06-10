from __future__ import annotations

from typing import Any, Dict, List

import numpy as np

from panda_gym.envs.core import Task


QUAT_IDENTITY = np.array([0.0, 0.0, 0.0, 1.0])


class ConfigurableTask(Task):
    """
    Configurable push-like task.

    This class creates a scene from YAML:
      - table
      - movable objects
      - fixed obstacles
      - visual target markers

    The goal is represented as a concatenation of target positions.
    If there is one target, goal shape is (3,).
    If there are N targets, goal shape is (3N,).

    The achieved goal is the concatenation of the current positions of
    the target objects.
    """

    def __init__(self, sim, config: Dict[str, Any]):
        super().__init__(sim)

        self.config = config
        self.task_config = config.get("task", {})
        self.scene_config = config.get("scene", {})
        self.objects_config = config.get("objects", [])
        self.goals_config = config.get("goals", {})
        self.obstacles_config = config.get("obstacles", [])

        self.reward_type = self.task_config.get("reward_type", "dense")
        self.success_threshold = float(self.task_config.get("success_threshold", 0.05))

        self.targets = self.goals_config.get("targets", [])
        self.target_object_names = [target["object"] for target in self.targets]

        self.goal = self._build_goal_vector()

        with self.sim.no_rendering():
            self._create_scene()
            self._create_objects(self.objects_config)
            self._create_objects(self.obstacles_config, default_mass=0.0)
            self._create_goal_markers()

    def _create_scene(self) -> None:
        table = self.scene_config.get("table")

        if table:
            self.sim.create_table(
                length=float(table.get("length", 1.1)),
                width=float(table.get("width", 0.7)),
                height=float(table.get("height", 0.4)),
                x_offset=float(table.get("x_offset", -0.3)),
                lateral_friction=float(table.get("lateral_friction", 1.0)),
                spinning_friction=float(table.get("spinning_friction", 0.001)),
            )

    def _create_objects(self, objects: List[Dict[str, Any]], default_mass: float | None = None) -> None:
        for obj in objects:
            obj_type = obj.get("type", "box")
            name = obj["name"]
            position = np.array(
                obj.get("initial_position", obj.get("position", [0.0, 0.0, 0.02])),
                dtype=float,
            )
            color = np.array(obj.get("color", [0.2, 0.2, 0.9, 1.0]), dtype=float)
            mass = float(obj.get("mass", default_mass if default_mass is not None else 1.0))
            lateral_friction = float(obj.get("lateral_friction", 1.0))
            spinning_friction = float(obj.get("spinning_friction", 0.001))
            ghost = bool(obj.get("ghost", False))

            if obj_type == "box":
                size = np.array(obj.get("size", [0.04, 0.04, 0.04]), dtype=float)
                self.sim.create_box(
                    body_name=name,
                    half_extents=size / 2.0,
                    mass=mass,
                    position=position,
                    rgba_color=color,
                    lateral_friction=lateral_friction,
                    spinning_friction=spinning_friction,
                    ghost=ghost,
                )

            elif obj_type == "sphere":
                self.sim.create_sphere(
                    body_name=name,
                    radius=float(obj.get("radius", 0.02)),
                    mass=mass,
                    position=position,
                    rgba_color=color,
                    lateral_friction=lateral_friction,
                    spinning_friction=spinning_friction,
                    ghost=ghost,
                )

            elif obj_type == "cylinder":
                self.sim.create_cylinder(
                    body_name=name,
                    radius=float(obj.get("radius", 0.02)),
                    height=float(obj.get("height", 0.04)),
                    mass=mass,
                    position=position,
                    rgba_color=color,
                    lateral_friction=lateral_friction,
                    spinning_friction=spinning_friction,
                    ghost=ghost,
                )

            else:
                raise ValueError(f"Tipo de objeto não suportado: {obj_type}")

    def _create_goal_markers(self) -> None:
        for target in self.targets:
            if not target.get("visual_marker", True):
                continue

            object_name = target["object"]
            marker_name = self._marker_name(object_name)
            position = np.array(target["position"], dtype=float)

            self.sim.create_box(
                body_name=marker_name,
                half_extents=np.array([0.02, 0.02, 0.02]),
                mass=0.0,
                position=position,
                rgba_color=np.array([0.1, 0.9, 0.1, 0.3]),
                ghost=True,
            )

    def reset(self) -> None:
        self.goal = self._build_goal_vector()

        for obj in self.objects_config:
            self.sim.set_base_pose(
                body=obj["name"],
                position=np.array(obj.get("initial_position", [0.0, 0.0, 0.02]), dtype=float),
                orientation=np.array(obj.get("initial_orientation", QUAT_IDENTITY), dtype=float),
            )

        for obs in self.obstacles_config:
            self.sim.set_base_pose(
                body=obs["name"],
                position=np.array(obs.get("position", [0.0, 0.0, 0.02]), dtype=float),
                orientation=np.array(obs.get("orientation", QUAT_IDENTITY), dtype=float),
            )

        for target in self.targets:
            if not target.get("visual_marker", True):
                continue

            self.sim.set_base_pose(
                body=self._marker_name(target["object"]),
                position=np.array(target["position"], dtype=float),
                orientation=QUAT_IDENTITY,
            )

    def get_obs(self) -> np.ndarray:
        obs_parts = []

        for obj in self.objects_config:
            name = obj["name"]
            position = self.sim.get_base_position(name)
            velocity = self.sim.get_base_velocity(name)

            obs_parts.append(position)
            obs_parts.append(velocity)

        if not obs_parts:
            return np.array([], dtype=np.float32)

        return np.concatenate(obs_parts).astype(np.float32)

    def get_achieved_goal(self) -> np.ndarray:
        achieved_parts = []

        for object_name in self.target_object_names:
            achieved_parts.append(self.sim.get_base_position(object_name))

        return np.concatenate(achieved_parts).astype(np.float32)

    def is_success(self, achieved_goal: np.ndarray, desired_goal: np.ndarray, info: Dict[str, Any] | None = None) -> np.ndarray:
        achieved_goal = np.asarray(achieved_goal, dtype=float).reshape(-1, 3)
        desired_goal = np.asarray(desired_goal, dtype=float).reshape(-1, 3)

        distances = np.linalg.norm(achieved_goal - desired_goal, axis=1)

        tolerances = np.array(
            [float(target.get("tolerance", self.success_threshold)) for target in self.targets],
            dtype=float,
        )

        return np.array(np.all(distances < tolerances), dtype=bool)

    def compute_reward(self, achieved_goal: np.ndarray, desired_goal: np.ndarray, info: Dict[str, Any] | None = None) -> np.ndarray:
        achieved_goal = np.asarray(achieved_goal, dtype=float).reshape(-1, 3)
        desired_goal = np.asarray(desired_goal, dtype=float).reshape(-1, 3)

        distances = np.linalg.norm(achieved_goal - desired_goal, axis=1)
        total_distance = np.sum(distances)

        if self.reward_type == "dense":
            return np.array(-total_distance, dtype=np.float32)

        if self.reward_type == "sparse":
            success = self.is_success(achieved_goal, desired_goal, info)
            return np.array(0.0 if bool(success) else -1.0, dtype=np.float32)

        raise ValueError(f"reward_type inválido: {self.reward_type}")

    def _build_goal_vector(self) -> np.ndarray:
        goal_parts = []

        for target in self.targets:
            goal_parts.append(np.array(target["position"], dtype=float))

        return np.concatenate(goal_parts).astype(np.float32)

    # Permite mudar o objetivo de um objeto em tempo de execução, para criar variações do ambiente sem reiniciar a simulação.
    def set_goal_for_object(
    self,
    object_name: str,
    position,
    tolerance=None,
    visual_marker: bool = True,
    ) -> None:
        """
        Muda o objetivo de um objeto em tempo de execução.

        Atualiza:
        - a lista de targets;
        - self.goal;
        - o marcador visual do alvo, se existir.
        """
        position_arr = np.array(position, dtype=float)

        found = False

        for target in self.targets:
            if target["object"] == object_name:
                target["position"] = position_arr.tolist()

                if tolerance is not None:
                    target["tolerance"] = float(tolerance)

                target["visual_marker"] = visual_marker
                found = True
                break

        if not found:
            self.targets.append(
                {
                    "object": object_name,
                    "position": position_arr.tolist(),
                    "tolerance": float(tolerance if tolerance is not None else self.success_threshold),
                    "visual_marker": visual_marker,
                }
            )

            if object_name not in self.target_object_names:
                self.target_object_names.append(object_name)

        # Atualiza o desired_goal usado pelo ambiente.
        self.goal = self._build_goal_vector()

        # Move o marcador visual, se ele existir.
        if visual_marker:
            marker_name = self._marker_name(object_name)

            try:
                self.sim.set_base_pose(
                    body=marker_name,
                    position=position_arr,
                    orientation=QUAT_IDENTITY,
                )
            except Exception:
                # Se o marcador ainda não existir, cria um novo.
                self.sim.create_box(
                    body_name=marker_name,
                    half_extents=np.array([0.02, 0.02, 0.02]),
                    mass=0.0,
                    position=position_arr,
                    rgba_color=np.array([0.1, 0.9, 0.1, 0.3]),
                    ghost=True,
                )

    @staticmethod
    def _marker_name(object_name: str) -> str:
        return f"target_{object_name}"
