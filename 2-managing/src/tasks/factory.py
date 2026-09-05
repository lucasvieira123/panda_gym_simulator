from panda_gym.envs.robots.panda import Panda
from panda_gym.pybullet import PyBullet

from .api_task import APITask
from .hold_task import HoldTask
from .manual_task import ManualTask
from .pick_and_place_task import PickAndPlaceTask
from .push_task import PushTask
from .reach_task import ReachTask
from .scripted_task import ScriptedTask
from .terminal_task import TerminalTask
from .object_delivery import (
    ApproachObjectTask, GraspObjectTask, LiftObjectTask,
    TransportObjectTask, PlaceObjectTask, RetryGraspTask, AbortTask,
    VacuumAssistTask, HeavyLiftTask,
)


def _get_object_cfg(configs: dict, name: str) -> dict:
    objects = configs["environment"].get("objects", [])
    try:
        return next(o for o in objects if o["name"] == name)
    except StopIteration:
        raise ValueError(f"Objeto '{name}' não encontrado no environment config")


def create_pick_and_place(sim: PyBullet, robot: Panda, configs: dict, object_name: str = "object_1") -> PickAndPlaceTask:
    obj_cfg = _get_object_cfg(configs, object_name)
    return PickAndPlaceTask(
        sim=sim,
        get_ee_position=robot.get_ee_position,
        get_object_position=lambda: sim.get_base_position(obj_cfg["name"]),
        target_goal_cfg=configs["target_goal"],
        object_cfg=obj_cfg,
        task_cfg=configs["simulation"],
    )


def create_reach(sim: PyBullet, robot: Panda, configs: dict, object_name: str = "object_1") -> ReachTask:
    obj_cfg = _get_object_cfg(configs, object_name)
    return ReachTask(
        sim=sim,
        get_ee_position=robot.get_ee_position,
        target_goal_cfg=configs["target_goal"],
        task_cfg=configs["simulation"],
        object_cfg=obj_cfg,
    )


def create_scripted(sim: PyBullet, robot: Panda, configs: dict, script_name: str, object_name: str = "object_1") -> ScriptedTask:
    obj_cfg  = _get_object_cfg(configs, object_name)
    scripts  = configs.get("scripts", {})
    if script_name not in scripts:
        raise ValueError(f"Script '{script_name}' não encontrado em scripts.yaml. Disponíveis: {list(scripts.keys())}")
    waypoints = scripts[script_name]["waypoints"]
    return ScriptedTask(
        sim=sim,
        get_ee_position=robot.get_ee_position,
        get_object_position=lambda: sim.get_base_position(obj_cfg["name"]),
        target_goal_cfg=configs["target_goal"],
        object_cfg=obj_cfg,
        waypoints=waypoints,
        script_name=script_name,
        task_cfg=configs["simulation"],
    )


def create_hold(sim: PyBullet, robot: Panda, configs: dict, object_name: str = "object_1") -> HoldTask:
    obj_cfg = _get_object_cfg(configs, object_name)
    return HoldTask(
        sim=sim,
        get_ee_position=robot.get_ee_position,
        get_object_position=lambda: sim.get_base_position(obj_cfg["name"]),
        target_goal_cfg=configs["target_goal"],
        object_cfg=obj_cfg,
        task_cfg=configs["simulation"],
    )


def create_manual(sim: PyBullet, robot: Panda, configs: dict, object_name: str = "object_1") -> ManualTask:
    obj_cfg = _get_object_cfg(configs, object_name)
    return ManualTask(
        sim=sim,
        get_ee_position=robot.get_ee_position,
        get_object_position=lambda: sim.get_base_position(obj_cfg["name"]),
        target_goal_cfg=configs["target_goal"],
        object_cfg=obj_cfg,
        task_cfg=configs["simulation"],
    )


def create_push(sim: PyBullet, robot: Panda, configs: dict, object_name: str = "object_1") -> PushTask:
    obj_cfg = _get_object_cfg(configs, object_name)
    return PushTask(
        sim=sim,
        get_ee_position=robot.get_ee_position,
        get_object_position=lambda: sim.get_base_position(obj_cfg["name"]),
        target_goal_cfg=configs["target_goal"],
        object_cfg=obj_cfg,
        task_cfg=configs["simulation"],
    )


def create_api_task(sim: PyBullet, robot: Panda, configs: dict, object_name: str = "object_1") -> APITask:
    obj_cfg = _get_object_cfg(configs, object_name)
    return APITask(
        sim=sim,
        get_ee_position=robot.get_ee_position,
        get_object_position=lambda: sim.get_base_position(obj_cfg["name"]),
        target_goal_cfg=configs["target_goal"],
        object_cfg=obj_cfg,
        task_cfg=configs["simulation"],
    )


def create_terminal(sim: PyBullet, robot: Panda, configs: dict, object_name: str = "object_1") -> TerminalTask:
    obj_cfg = _get_object_cfg(configs, object_name)
    return TerminalTask(
        sim=sim,
        get_ee_position=robot.get_ee_position,
        get_object_position=lambda: sim.get_base_position(obj_cfg["name"]),
        target_goal_cfg=configs["target_goal"],
        object_cfg=obj_cfg,
        task_cfg=configs["simulation"],
    )


def create_safe_abort(sim: PyBullet, robot: Panda, configs: dict, object_name: str = "object_1") -> AbortTask:
    obj_cfg = _get_object_cfg(configs, object_name)
    return AbortTask(
        sim=sim,
        get_ee_position=robot.get_ee_position,
        get_object_position=lambda: sim.get_base_position(obj_cfg["name"]),
        target_goal_cfg=configs["target_goal"],
        object_cfg=obj_cfg,
        task_cfg=configs.get("simulation"),
    )


def create_heavy_lift(sim: PyBullet, robot: Panda, configs: dict, object_name: str = "object_1") -> HeavyLiftTask:
    obj_cfg = _get_object_cfg(configs, object_name)
    return HeavyLiftTask(
        sim=sim,
        robot=robot,
        fingers_indices=robot.fingers_indices,
        get_ee_position=robot.get_ee_position,
        get_object_position=lambda: sim.get_base_position(obj_cfg["name"]),
        get_object_orientation=lambda: sim.get_base_orientation(obj_cfg["name"]),
        target_goal_cfg=configs["target_goal"],
        object_cfg=obj_cfg,
        task_cfg=configs.get("simulation"),
    )


def create_vacuum_assist(sim: PyBullet, robot: Panda, configs: dict, object_name: str = "object_1") -> VacuumAssistTask:
    obj_cfg = _get_object_cfg(configs, object_name)
    return VacuumAssistTask(
        sim=sim,
        fingers_indices=robot.fingers_indices,
        get_ee_position=robot.get_ee_position,
        get_object_position=lambda: sim.get_base_position(obj_cfg["name"]),
        target_goal_cfg=configs["target_goal"],
        object_cfg=obj_cfg,
        task_cfg=configs.get("simulation"),
    )


def create_retry_grasp(sim: PyBullet, robot: Panda, configs: dict, object_name: str = "object_1") -> RetryGraspTask:
    obj_cfg = _get_object_cfg(configs, object_name)
    return RetryGraspTask(
        sim=sim,
        get_ee_position=robot.get_ee_position,
        get_object_position=lambda: sim.get_base_position(obj_cfg["name"]),
        target_goal_cfg=configs["target_goal"],
        object_cfg=obj_cfg,
        task_cfg=configs.get("simulation"),
    )


def create_object_delivery(
    sim: PyBullet,
    robot: Panda,
    configs: dict,
    object_name: str = "object_1",
) -> "ObjectDeliverySequence":
    """Cria a sequência ASM completa: approach → grasp → lift → transport → place."""
    from .object_delivery.sequence import ObjectDeliverySequence
    obj_cfg = _get_object_cfg(configs, object_name)
    return ObjectDeliverySequence(
        sim=sim,
        get_ee_position=robot.get_ee_position,
        get_object_position=lambda: sim.get_base_position(obj_cfg["name"]),
        target_goal_cfg=configs["target_goal"],
        object_cfg=obj_cfg,
        task_cfg=configs.get("simulation"),
    )
