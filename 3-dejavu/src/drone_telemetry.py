from dataclasses import dataclass
from typing import Callable, Optional, List
import pandas as pd

# ---------- 1) Modelo do "tick" ----------
@dataclass(frozen=True)
class TelemetryTick:
    h: float
    dt: float
    delta_dt: float
    b: float
    armed: bool
    wind_speed: float
    humidity: float
    vibration: float
    action: Optional[str]  # None quando não houve ação naquele tick


# ---------- 2) Bus (publish/subscribe) ----------
class TelemetryBus:
    def __init__(self) -> None:
        self._subs: List[Callable[[TelemetryTick], None]] = []

    def subscribe(self, fn: Callable[[TelemetryTick], None]) -> None:
        self._subs.append(fn)

    def publish(self, tick: TelemetryTick) -> None:
        for fn in self._subs:
            fn(tick)
