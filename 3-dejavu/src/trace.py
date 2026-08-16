import os
from datetime import datetime

_DEJAVU_DIR         = os.path.dirname(os.path.dirname(__file__))
_DEFAULT_TRACES_DIR = os.path.join(_DEJAVU_DIR, "traces")


class TraceWriter:
    def __init__(self, traces_dir: str = _DEFAULT_TRACES_DIR, ts: str | None = None) -> None:
        os.makedirs(traces_dir, exist_ok=True)
        if ts is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._path = os.path.join(traces_dir, f"trace_{ts}.log")
        self._file = open(self._path, "w", encoding="utf-8-sig")

    @property
    def path(self) -> str:
        return self._path

    def write(self, text: str) -> None:
        self._file.write(text)
        self._file.flush()

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> "TraceWriter":
        return self

    def __exit__(self, *args) -> None:
        self.close()
