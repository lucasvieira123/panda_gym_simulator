# from __future__ import annotations
from os import PathLike
from typing import  List
import time
import pandas as pd
from drone_telemetry import TelemetryBus, TelemetryTick
import pandas as pd

from constants import DEJAVU_CONF_PATH
from utils import load_config



class DroneBehaviorSimulator:
    def __init__(self, bus: TelemetryBus) -> None:
        self.bus = bus
        self.cfg = load_config(DEJAVU_CONF_PATH)
        self.csv_path =  self.cfg["simulation_replay"]["csv_trace"]
        self.tick_seconds =  self.cfg["simulation_replay"]["tick_seconds"]

        

    def load_ticks(self, csv_path: str) -> List[TelemetryTick]:
        df = pd.read_csv(csv_path)

        # # garante ordenação
        # df = df[df["execution"] == execution].sort_values(["execution", "t"], ascending=True)

        ticks: List[TelemetryTick] = []
        for _, r in df.iterrows():
            action = r["action"]
            action = None if action == "-" else str(action)

            ticks.append(
                TelemetryTick(
                    # execution=int(r["execution"]),
                    # t=int(r["t"]),
                    h=float(r["h"]),
                    dt=float(r["dt"]),
                    delta_dt=float(r["delta_dt"]),
                    b=float(r["b"]),
                    armed=bool(r["armed"]),
                    wind_speed=float(r["wind_speed"]),
                    humidity=float(r["humidity"]),
                    vibration=float(r["vibration"]),
                    action=action,
                )
            )
        return ticks

    def run(self):
        ticks = self.load_ticks(self.csv_path)
        for tick in ticks:
            self.bus.publish(tick)
            if self.tick_seconds > 0:
                time.sleep(self.tick_seconds)
    
    def get_initial_context(self):
        df = pd.read_csv(self.csv_path)
        # df.drop(columns=["execution", "t"], inplace=True)
        initial_context=df.iloc[0].to_dict()
        
        return initial_context
    