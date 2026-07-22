from pathlib import Path
import yaml

_DEFAULT_CONFIGS_DIR      = Path(__file__).parent / "configs"
_DEFAULT_ENVIRONMENTS_DIR = _DEFAULT_CONFIGS_DIR / "environments"


def load_config(simulation_file: str = "simulation.yaml", config_dir=None) -> dict:
    if config_dir:
        configs_dir      = Path(config_dir)
        environments_dir = Path(config_dir)
    else:
        configs_dir      = _DEFAULT_CONFIGS_DIR
        environments_dir = _DEFAULT_ENVIRONMENTS_DIR

    simulation_path = configs_dir / simulation_file
    with open(simulation_path) as f:
        simulation_cfg = yaml.safe_load(f)

    env_path = environments_dir / simulation_cfg["environment_config"]
    with open(env_path) as f:
        environment_cfg = yaml.safe_load(f)

    target_goal_path = configs_dir / simulation_cfg["target_goal_config"]
    with open(target_goal_path) as f:
        target_goal_cfg = yaml.safe_load(f)

    scripts_cfg = {}
    scripts_filename = simulation_cfg.get("scripts_file")
    if scripts_filename:
        with open(configs_dir / scripts_filename) as f:
            scripts_cfg = yaml.safe_load(f) or {}

    adaptation_cfg = {}
    adaptation_filename = simulation_cfg.get("adaptation_options_file")
    if adaptation_filename:
        with open(configs_dir / adaptation_filename) as f:
            adaptation_cfg = yaml.safe_load(f) or {}

    situations_cfg = {}
    situations_filename = simulation_cfg.get("situations_file")
    if situations_filename:
        with open(configs_dir / situations_filename) as f:
            situations_cfg = yaml.safe_load(f) or {}

    return {
        "simulation":        simulation_cfg,
        "environment":       environment_cfg,
        "target_goal":       target_goal_cfg,
        "scripts":           scripts_cfg,
        "adaptation_options": adaptation_cfg,
        "situations":        situations_cfg,
    }