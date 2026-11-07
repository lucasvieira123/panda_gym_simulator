import json
from datetime import datetime
from pathlib import Path


class RunEventLog:
    """Writes the run's pipeline events as JSON lines, flushing each one to survive process termination."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self._path, "a", encoding="utf-8")

    @property
    def path(self) -> str:
        return str(self._path)

    def write(self, event: str, **fields) -> None:
        record = {"time": datetime.now().isoformat(timespec="milliseconds"), "event": event, **fields}
        self._file.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        self._file.flush()

    def close(self) -> None:
        self._file.close()
