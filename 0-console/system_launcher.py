import subprocess
from pathlib import Path

_ROOT         = Path(__file__).parent.parent
_VENV_ACTIVATE = _ROOT / ".venv" / "Scripts" / "activate.bat"

_COMPONENTS = {
    "managing": _ROOT / "2-managing",
    "manager":  _ROOT / "1-manager",
}


_ENTRY_POINTS = {
    "managing": "src/main.py",
    "manager":  "src/main.py",
}


def _launch(title: str, cwd: Path, entry: str) -> None:
    cmd = f'start "{title}" cmd /k pushd "{cwd}" ^&^& call "{_VENV_ACTIVATE}" ^&^& python {entry}'
    subprocess.Popen(cmd, shell=True)


def start_system() -> None:
    for title, cwd in _COMPONENTS.items():
        _launch(title, cwd, _ENTRY_POINTS[title])
