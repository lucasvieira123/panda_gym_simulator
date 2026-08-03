import re
import pandas as pd
from pathlib import Path

from constants import DEJAVU_CONF_PATH
from utils import load_config

class UnanticipatedScenariosDetector:
    def __init__(self):
        self.cfg = load_config(DEJAVU_CONF_PATH)

    def detects(self) -> pd.DataFrame:
        def extract_id(p: Path) -> int:
            m = re.search(r"checked_scenarios_(\d+)\.csv$", p.name)
            return int(m.group(1)) if m else -1
        
        def pick_latest_checked_csv() -> Path:
            folder = Path(self.cfg["checked_scenarios_folder"])
            candidates = list(folder.glob("checked_scenarios_*.csv"))
            if not candidates:
                raise FileNotFoundError(f"Nenhum 'checked_scenarios_*.csv' em: {folder}")

            latest = max(candidates, key=extract_id)
            return latest
        
        def read_fail_rows() -> pd.DataFrame:
            latest_csv = pick_latest_checked_csv()
            df = pd.read_csv(latest_csv)
            i = df.index[df["SAT"] == False][0]   # único índice com falha
            return df.iloc[i:i+2]                 # falha + linha seguinte (se existir)
        
        return read_fail_rows()