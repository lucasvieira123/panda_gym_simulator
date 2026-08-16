import csv
from datetime import datetime
from pathlib import Path


def _flatten(obj, prefix: str = "", sep: str = ".") -> dict:
    result = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_key = f"{prefix}{sep}{k}" if prefix else str(k)
            result.update(_flatten(v, new_key, sep))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            new_key = f"{prefix}{sep}{i}" if prefix else str(i)
            result.update(_flatten(v, new_key, sep))
    else:
        result[prefix] = obj
    return result


class AntecipatedScenarioDatasetRecorder:
    def __init__(self, output_dir: str, ts: str | None = None) -> None:
        if ts is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._dir   = Path(output_dir)
        self._path  = self._dir / f"antecipated_scenario_dataset_{ts}.csv"
        self._file  = None
        self._writer: csv.DictWriter | None = None
        self._count = 0

    @property
    def path(self) -> str:
        return str(self._path)

    def record(self, perception: dict, active_state: str = "", sat=None,
               active_scenario_name: str = "", active_scenario_type=None) -> None:
        row = _flatten(perception)
        row["active_state"]         = active_state
        row["active_scenario_name"] = active_scenario_name
        row["active_scenario_type"] = active_scenario_type
        row["sat"]                  = sat
        if self._writer is None:
            self._dir.mkdir(parents=True, exist_ok=True)
            self._file = open(self._path, "w", newline="", encoding="utf-8")
            self._writer = csv.DictWriter(
                self._file,
                fieldnames=list(row.keys()),
                extrasaction="ignore",
                restval="",
            )
            self._writer.writeheader()
        self._writer.writerow(row)
        self._file.flush()
        self._count += 1

    def save(self) -> None:
        if self._file is not None and not self._file.closed:
            self._file.close()
            print(f"[DatasetRecorder] {self._count} registros → {self._path}")
