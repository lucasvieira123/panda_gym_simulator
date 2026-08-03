# src/settings.py
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]  # ajuste conforme sua estrutura
DEJAVU_CONF_PATH = PROJECT_ROOT / "res" / "dejavu_conf.yaml"