from pathlib import Path
import yaml

_CONFIGS_DIR = Path(__file__).parent.parent / "configs"


def load_manager_config() -> dict:
    adaptation_options = _load(_CONFIGS_DIR / "adaptation_options.yaml")
    plan_options       = _load(_CONFIGS_DIR / "plan_options.yaml")
    return {
        "adaptation_options": adaptation_options,
        "plan_options":       plan_options,
    }


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
