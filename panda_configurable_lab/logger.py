from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List


class ExperimentLogger:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.steps_path = self.output_dir / "steps.jsonl"
        self.events_path = self.output_dir / "events.jsonl"
        self.summary_path = self.output_dir / "summary.csv"

        self.summaries: List[Dict[str, Any]] = []

        for path in [self.steps_path, self.events_path, self.summary_path]:
            if path.exists():
                path.unlink()

    def log_step(self, record: Dict[str, Any]) -> None:
        with self.steps_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(self._json_safe(record), ensure_ascii=False) + "\n")

    def log_event(self, record: Dict[str, Any]) -> None:
        with self.events_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(self._json_safe(record), ensure_ascii=False) + "\n")

    def add_summary(self, record: Dict[str, Any]) -> None:
        self.summaries.append(self._json_safe(record))

    def flush(self) -> None:
        if not self.summaries:
            return

        fieldnames = sorted({key for row in self.summaries for key in row.keys()})

        with self.summary_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.summaries)

    def _json_safe(self, value: Any) -> Any:
        if hasattr(value, "tolist"):
            return value.tolist()

        if isinstance(value, dict):
            return {key: self._json_safe(val) for key, val in value.items()}

        if isinstance(value, list):
            return [self._json_safe(item) for item in value]

        if isinstance(value, tuple):
            return [self._json_safe(item) for item in value]

        if isinstance(value, (str, int, float, bool)) or value is None:
            return value

        return str(value)
