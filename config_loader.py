from pathlib import Path
import yaml

CONFIGS_DIR = Path(__file__).parent / "configs"
ENVIRONMENTS_DIR = CONFIGS_DIR / "environments"


def load_config(simulation_file: str = "simulation.yaml"):
    sim_path = CONFIGS_DIR / simulation_file
    with open(sim_path) as f:
        sim_cfg = yaml.safe_load(f)

    env_filename = sim_cfg["configs"]["environment_config"]
    env_path = ENVIRONMENTS_DIR / env_filename
    with open(env_path) as f:
        env_cfg = yaml.safe_load(f)

    target_goal_filename = sim_cfg["configs"]["target_goal_config"]
    target_goal_path = CONFIGS_DIR / target_goal_filename
    with open(target_goal_path) as f:
        target_goal_cfg = yaml.safe_load(f)

    scripts_cfg = None
    scripts_filename = sim_cfg["configs"].get("scripts_file")
    if scripts_filename:
        scripts_path = CONFIGS_DIR / scripts_filename
        with open(scripts_path) as f:
            scripts_cfg = yaml.safe_load(f)

    return sim_cfg, env_cfg, target_goal_cfg, scripts_cfg