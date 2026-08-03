from datetime import datetime

_current_step: int = 0


def set_step(step: int) -> None:
    global _current_step
    _current_step = step


def ts() -> str:
    t = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    return f"step={_current_step:4d} {t}"
