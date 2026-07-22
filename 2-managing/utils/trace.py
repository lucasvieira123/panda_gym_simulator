import os
from datetime import datetime

_MANAGING_DIR       = os.path.dirname(os.path.dirname(__file__))
_DEFAULT_TRACES_DIR = os.path.join(_MANAGING_DIR, "traces")


def _resolve_traces_dir(traces_dir: str) -> str:
    """Resolve traces_dir: se relativo, ancora em managing/; se absoluto, usa direto."""
    if os.path.isabs(traces_dir):
        return traces_dir
    return os.path.join(_MANAGING_DIR, traces_dir)


class TraceWriter:
    """
    Abre um arquivo de trace com timestamp na pasta traces/ e escreve linhas nele.

    Uso como context manager (recomendado):
        with TraceWriter() as writer:
            log_step(..., writer=writer)

    Uso manual:
        writer = TraceWriter()
        log_step(..., writer=writer)
        writer.close()
    """

    def __init__(self, traces_dir: str = _DEFAULT_TRACES_DIR) -> None:
        traces_dir = _resolve_traces_dir(traces_dir)
        os.makedirs(traces_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._path = os.path.join(traces_dir, f"trace_{ts}.log")
        self._file = open(self._path, "w", encoding="utf-8")

    @property
    def path(self) -> str:
        return self._path

    def write(self, text: str) -> None:
        self._file.write(text + "\n")
        self._file.flush()

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> "TraceWriter":
        return self

    def __exit__(self, *args) -> None:
        self.close()
