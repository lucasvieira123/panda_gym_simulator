import os
import subprocess
import sys

_EXPERIMENTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SIMULATIONS_DIR = os.path.join(_EXPERIMENTS_DIR, "simulations")
_MANAGING_MAIN   = os.path.join(os.path.dirname(_EXPERIMENTS_DIR), "managing", "main.py")

folders = sorted(
    f for f in os.listdir(_SIMULATIONS_DIR)
    if os.path.isdir(os.path.join(_SIMULATIONS_DIR, f))
)

for name in folders:
    config_dir = os.path.join(_SIMULATIONS_DIR, name)
    print(f"\n[execute] iniciando: {name}")

    result = subprocess.run([
        sys.executable, _MANAGING_MAIN,
        "--config-dir", config_dir,
    ])

    if result.returncode != 0:
        print(f"[execute] ERRO em {name} (exit {result.returncode})")
    else:
        print(f"[execute] concluido: {name}")
