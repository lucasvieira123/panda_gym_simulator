from pathlib import Path

_ROOT = Path(__file__).parent.parent

DEJAVU_DIR      = _ROOT / "3-dejavu"
CONFIGS_DIR     = DEJAVU_DIR / "configs"
DEJAVU_SRC_DIR  = DEJAVU_DIR / "src"

ASM_LOCAL          = CONFIGS_DIR / "arm" / "asm.json"
STATE_MACHINE_PATH = CONFIGS_DIR / "arm" / "scenario_state_machine.yaml"
CATALOGUE_PATH     = CONFIGS_DIR / "arm" / "scenario_catalogue.json"

ASM_SAMPLES = {
    "ARM": _ROOT / "1-manager" / "configs" / "arm" / "asm.json",
}

CATALOGUE_SAMPLES = {
    "ARM": CATALOGUE_PATH,
}
