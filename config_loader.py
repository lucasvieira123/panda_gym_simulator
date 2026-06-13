from pathlib import Path
import yaml

CONFIGS_DIR = Path(__file__).parent / "configs"
ENVIRONMENTS_DIR = CONFIGS_DIR / "environments"


def load_config(simulation_file: str = "simulation.yaml") -> dict:
    simulation_path = CONFIGS_DIR / simulation_file
    with open(simulation_path) as f:
        simulation_cfg = yaml.safe_load(f)

    env_path = ENVIRONMENTS_DIR / simulation_cfg["environment_config"]
    with open(env_path) as f:
        environment_cfg = yaml.safe_load(f)

    target_goal_path = CONFIGS_DIR / simulation_cfg["target_goal_config"]
    with open(target_goal_path) as f:
        target_goal_cfg = yaml.safe_load(f)

    scripts_cfg = {}
    scripts_filename = simulation_cfg.get("scripts_file")
    if scripts_filename:
        with open(CONFIGS_DIR / scripts_filename) as f:
            scripts_cfg = yaml.safe_load(f) or {}

    adaptation_cfg = {}
    adaptation_filename = simulation_cfg.get("adaptation_options_file")
    if adaptation_filename:
        with open(CONFIGS_DIR / adaptation_filename) as f:
            adaptation_cfg = yaml.safe_load(f) or {}

    situations_cfg = {}
    situations_filename = simulation_cfg.get("situations_file")
    if situations_filename:
        with open(CONFIGS_DIR / situations_filename) as f:
            situations_cfg = yaml.safe_load(f) or {}

    return {
        "simulation":        simulation_cfg,
        "environment":       environment_cfg,
        "target_goal":       target_goal_cfg,
        "scripts":           scripts_cfg,
        "adaptation_options": adaptation_cfg,
        "situations":        situations_cfg,
    }