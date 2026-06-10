"""
main.py
-------
Entry point for the MAPE-K system running on PandaPickAndPlaceDense-v3.

The managed system is the panda-gym simulator.
The managing system is the MAPE-K loop (Monitor → Analyzer → Planner → Executor).

The Analyzer detects SNP-4 (object slip during transport).
The Planner responds with a 7-step sequential recovery plan (STRIPS-style).
The Executor drives the plan step-by-step until the grasp is recovered.

Usage
-----
    python main.py                        # headless, slip injected at step 60
    python main.py --render               # open PyBullet GUI
    python main.py --render --delay 0.1  # render + 100ms pause per step (slow motion)
    python main.py --verbose              # DEBUG logs de cada componente MAPE-K
    python main.py --no-inject            # wait for a natural slip (rare but possible)
    python main.py --steps 500            # run for N steps
"""
from __future__ import annotations

import argparse
import logging
import time
from collections import Counter

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-10s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


# ---------------------------------------------------------------------------
# Baseline (non-adaptive) controller
# ---------------------------------------------------------------------------

def normal_action(obs: "Observation") -> np.ndarray:
    """
    Naive pick-and-place controller.
    Three phases: approach object → close gripper → transport to goal.

    Deliberately simple so the grasp is marginal and a slip is plausible.
    The MAPE-K system kicks in when the slip is detected.
    """
    # Unit-vector helpers
    def move_toward(target: np.ndarray) -> np.ndarray:
        direction = target - obs.ee_pos
        dist = np.linalg.norm(direction)
        return direction / max(dist, 1e-6)

    # Phase 1: approach object (gripper open)
    if not obs.gripper_is_closed and obs.dist_ee_to_object > 0.05:
        return np.clip(np.append(move_toward(obs.object_pos), 1.0), -1.0, 1.0)

    # Phase 2: grasp (close gripper when close to object)
    if not obs.gripper_is_closed and obs.dist_ee_to_object <= 0.05:
        return np.array([0.0, 0.0, 0.0, -1.0])

    # Phase 3: transport to goal (gripper closed)
    return np.clip(np.append(move_toward(obs.desired_goal), -1.0), -1.0, 1.0)


# ---------------------------------------------------------------------------
# Fault injector — simulates SNP-4 (object slip)
# ---------------------------------------------------------------------------

def inject_slip(env) -> bool:
    """
    Applies a sudden force to the object via PyBullet, dislodging it
    from the gripper and triggering the MAPE-K slip detection.
    Returns True if injection succeeded.
    """
    try:
        import pybullet as p
        sim          = env.unwrapped.sim
        object_id    = sim._bodies_dict.get("object")
        physics_cli  = sim.physics_client

        if object_id is None:
            logger.warning("[Inject] Object body ID not found — skipping")
            return False

        p.applyExternalForce(
            objectUniqueId = object_id,
            linkIndex      = -1,
            forceObj       = [4.0, 3.0, -12.0],   # sudden downward diagonal
            posObj         = [0.0, 0.0, 0.0],
            flags          = p.WORLD_FRAME,
            physicsClientId = physics_cli,
        )
        logger.warning("[Inject] Slip injected via external force")
        return True

    except Exception as exc:
        logger.debug(f"[Inject] Could not inject: {exc}")
        return False


# ---------------------------------------------------------------------------
# Main MAPE-K loop
# ---------------------------------------------------------------------------

def run(n_steps: int, render: bool, inject: bool, delay: float) -> None:
    import gymnasium as gym
    import panda_gym  # noqa: F401  — registers panda environments

    from knowledge_base import KnowledgeBase
    from mape import Analyzer, Executor, Monitor, Planner

    env = gym.make(
        "PandaPickAndPlaceDense-v3",
        render_mode="human" if render else "rgb_array",
        max_episode_steps=500,
    )

    logger.info(f"  max_episode_steps do ambiente: {env.spec.max_episode_steps if env.spec else 'N/A (wrapper)'}")

    # Instantiate MAPE-K components, all sharing one KnowledgeBase
    kb       = KnowledgeBase()
    monitor  = Monitor(kb)
    analyzer = Analyzer(kb)
    planner  = Planner(kb)
    executor = Executor(kb)

    gym_obs, _  = env.reset()
    current_obs = monitor.observe(0, gym_obs, reward=0.0)
    episode     = 1
    injected    = False

    logger.info("=" * 60)
    logger.info("  MAPE-K started — PandaPickAndPlaceDense-v3")
    logger.info(f"  steps={n_steps}  render={render}  inject_slip={inject}  delay={delay}s")
    logger.info("=" * 60)

    for step in range(1, n_steps + 1):

        # ── Optional fault injection ───────────────────────────────────
        if inject and not injected and step == 60:
            injected = inject_slip(env)

        # ── Decide action ─────────────────────────────────────────────
        side_effects: dict = {}

        if kb.active_plan is not None:
            # E — Executor drives the action during plan execution
            action, side_effects = executor.tick(current_obs)

        else:
            # Normal MAPE-K cycle
            action = normal_action(current_obs)

            # A — Analyzer inspects the KB
            situations = analyzer.analyze()

            if situations:
                # P — Planner produces a plan
                plan = planner.plan(situations)

                if plan is not None:
                    # E — Executor activates and immediately starts the plan
                    executor.activate(plan)
                    action, side_effects = executor.tick(current_obs)

        # ── Step the environment ──────────────────────────────────────
        gym_obs, reward, terminated, truncated, info = env.step(
            np.clip(action, -1.0, 1.0)
        )

        # M — Monitor records the new state
        current_obs = monitor.observe(step, gym_obs, float(reward))

        # ── Per-step status log (sempre visível) ──────────────────────
        plan_status = (
            f"PLAN:{kb.active_plan.current_step.name}"
            if kb.active_plan else "NORMAL"
        )
        logger.info(
            f"[{step:04d}] ep={episode}  "
            f"ee=({current_obs.ee_pos[0]:+.3f},{current_obs.ee_pos[1]:+.3f},{current_obs.ee_pos[2]:+.3f})  "
            f"obj=({current_obs.object_pos[0]:+.3f},{current_obs.object_pos[1]:+.3f},{current_obs.object_pos[2]:+.3f})  "
            f"grip={current_obs.fingers_width:.3f}  "
            f"obj→goal={current_obs.dist_object_to_goal:.3f}  "
            f"mode={plan_status}"
        )

        # ── Slow-motion pause ─────────────────────────────────────────
        if delay > 0:
            time.sleep(delay)

        # ── Episode reset ─────────────────────────────────────────────
        need_reset = (
            terminated
            or truncated
            or side_effects.get("trigger_reset", False)
        )

        if need_reset:
            if info.get("is_success"):
                reason = "success"
            elif side_effects.get("trigger_reset"):
                reason = "plan-exhausted"
            else:
                reason = "timeout"

            logger.info(f"  ↺ Episode {episode} ended ({reason}) at step {step}")
            gym_obs, _ = env.reset()
            current_obs = monitor.observe(step, gym_obs, 0.0)
            analyzer.reset_episode()   # limpa flag de grasp tentado
            kb.episode += 1
            episode += 1
            injected = False   # allow re-injection in the next episode

    env.close()
    _report(kb, episode, n_steps)


# ---------------------------------------------------------------------------
# Final report
# ---------------------------------------------------------------------------

def _report(kb: "KnowledgeBase", episodes: int, total_steps: int) -> None:
    sep = "=" * 60
    print(f"\n{sep}")
    print("  MAPE-K Report — slip recovery")
    print(sep)
    print(f"  Total steps   : {total_steps}")
    print(f"  Episodes      : {episodes}")
    print(f"  Adaptations   : {kb.n_adaptations}")

    if kb.adaptation_log:
        print()
        counts = Counter(e.plan_name for e in kb.adaptation_log)
        for name, n in counts.most_common():
            print(f"    {n:3d}×  {name}")

        print()
        print("  Last 5 activation steps:")
        for ev in kb.adaptation_log[-5:]:
            print(f"    step={ev.step:04d}  {ev.plan_name}  ({ev.trigger})")

    print(sep)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MAPE-K + panda-gym slip recovery")
    p.add_argument("--steps",     type=int,   default=300,
                   help="Total simulation steps (default: 300)")
    p.add_argument("--render",    action="store_true",
                   help="Open PyBullet GUI")
    p.add_argument("--no-inject", action="store_true",
                   help="Disable artificial slip injection")
    p.add_argument("--delay",     type=float, default=0.0,
                   help="Pausa em segundos entre cada step (ex: 0.1 = slow motion)")
    p.add_argument("--verbose",   action="store_true",
                   help="Habilita logs DEBUG de todos os componentes MAPE-K")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        for name in ("main", "mapek", "monitor", "analyzer", "planner", "executor"):
            logging.getLogger(name).setLevel(logging.DEBUG)

    run(
        n_steps = args.steps,
        render  = args.render,
        inject  = not args.no_inject,
        delay   = args.delay,
    )
