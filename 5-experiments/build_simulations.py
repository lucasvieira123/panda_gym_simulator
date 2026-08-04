"""
build_simulations.py — define e cria as simulações em batch.

Execute:
    python experiments/build_simulations.py

Isso limpa e recria experiments/simulations/ com uma subpasta por cenário.
Cada subpasta é completamente auto-suficiente: contém os 4 arquivos de
configuração que o managing precisa. O execute_simulations.py lê essas
pastas e executa o managing uma vez por simulação.
"""

import os
import shutil
import yaml

_EXPERIMENTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SIMULATIONS_DIR = os.path.join(_EXPERIMENTS_DIR, "simulations")


# ── configurações base ───────────────────────────────────────────────────────

BASE_SIMULATION = {
    "seed": 42,
    "episodes": 1,
    "max_steps": 1000,
    "render_mode": "human",  # "rgb_array": headless — sem GUI
    "step_delay": 0,
    "verbose": True,
    "environment_config": "environment.yaml",
    "target_goal_config": "target_goal.yaml",
    "scripts_file":       "scripts.yaml",
    "traces_dir": None,        # preenchido por create_experiment()
    "distance_threshold":   0.05,
    "grasp_height_offset":  0.0,
    "approach_height":      0.1,
    "phase_threshold":      0.02,
    "approach_offset":      0.05,
    "push_speed":           0.3,
    "move_speed":           0.5,
}

BASE_ENVIRONMENT = {
    "robot": {
        "control_type": "ee",
        "block_gripper": False,
        "base_position": [-0.6, 0.0, 0.0],
    },
    "scene": {
        "table": {
            "length":           1.1,
            "width":            0.7,
            "height":           0.4,
            "x_offset":        -0.3,
            "lateral_friction": 3.0,
            "spinning_friction": 0.001,
        }
    },
    "objects": [
        {
            "name":              "object_1",
            "type":              "box",
            "size":              [0.04, 0.04, 0.04],
            "mass":              1.0,
            "initial_position":  [0.03, 0.0, 0.02],
            "color":             [0.1, 0.2, 0.9, 1.0],
            "lateral_friction":  0.124,
            "spinning_friction": 0.001,
        }
    ],
    "obstacles": [
        {
            "name":     "obstacle_1",
            "type":     "box",
            "size":     [0.02, 0.30, 0.02],
            "position": [0.09, 0.0, 0.04],
            "color":    [0.8, 0.2, 0.2, 0.9],
            "mass":     0.0,
        }
    ],
}

BASE_TARGET_GOAL = {
    "mode": "goal_sequence",
    "targets": [
        {"name": "target",   "position": [0.15,   0.0,  0.02]},
        {"name": "target_1", "position": [0.15,   0.10, 0.02]},
        {"name": "target_2", "position": [-0.10,  0.0,  0.02]},
        {"name": "target_3", "position": [-0.10,  0.1,  0.02]},
    ],
}

BASE_SCRIPTS = {
    "script_1": {
        "waypoints": [
            [0.03,  0.0,  0.12,  1.0],
            [0.03,  0.0,  0.02,  1.0],
            [0.03,  0.0,  0.02, -1.0],
            [0.03,  0.0,  0.12, -1.0],
            [0.15,  0.0,  0.12, -1.0],
            [0.15,  0.0,  0.02, -1.0],
            [0.15,  0.0,  0.02,  1.0],
        ]
    },
    "reach_only": {
        "waypoints": [
            [0.15,  0.0,  0.12,  1.0],
            [0.15,  0.0,  0.02,  1.0],
        ]
    },
    "left_right": {
        "waypoints": [
            [0.05,  0.00, 0.25,  1.0],
            [0.05, -0.20, 0.25,  1.0],
            [0.05,  0.20, 0.25,  1.0],
            [0.05,  0.00, 0.25,  1.0],
        ]
    },
}


# ── função de criação ────────────────────────────────────────────────────────

def create_simulation(name, sim_cfg, env_cfg, tgt_cfg, scripts_cfg):
    """Cria a pasta experiments/simulations/<name>/ com os 4 YAMLs completos."""
    folder = os.path.join(_SIMULATIONS_DIR, name)
    os.makedirs(folder, exist_ok=True)

    sim = {**sim_cfg, "traces_dir": folder}

    _save(folder, "simulation.yaml",          sim)
    _save(folder, sim["environment_config"],   env_cfg)
    _save(folder, sim["target_goal_config"],   tgt_cfg)
    _save(folder, sim["scripts_file"],         scripts_cfg)


def _save(folder, filename, data):
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)


# ── simulações ───────────────────────────────────────────────────────────────
# Varie os parâmetros aqui. Cada entrada vira uma subpasta em simulations/.

FRICTION_VALUES = [0.10, 0.120, 0.124, 0.125, 0.126]

if __name__ == "__main__":
    if os.path.exists(_SIMULATIONS_DIR):
        shutil.rmtree(_SIMULATIONS_DIR)

    for friction in FRICTION_VALUES:
        name = f"lateral_friction_{friction:.3f}"

        env = {
            **BASE_ENVIRONMENT,
            "objects": [
                {**BASE_ENVIRONMENT["objects"][0], "lateral_friction": friction}
            ],
        }

        create_simulation(
            name        = name,
            sim_cfg     = BASE_SIMULATION,
            env_cfg     = env,
            tgt_cfg     = BASE_TARGET_GOAL,
            scripts_cfg = BASE_SCRIPTS,
        )
        print(f"[build] criado: {name}")

    print(f"\n{len(FRICTION_VALUES)} experimentos em {_SIMULATIONS_DIR}")
