from os import PathLike
from pathlib import Path
import pandas as pd
from schema import Optional
from typing import Optional, List

from drone_behavior_simulator import TelemetryTick
from sismic.io import import_from_yaml
from sismic.interpreter import Interpreter
import re

from constants import DEJAVU_CONF_PATH
from utils import load_config

PATTERN = re.compile(r"^\s*(?P<action>.*?)\s*\(\s*(?P<scenario>.*?)\s*\)\s*$")
RED   = "\033[31m"
GREEN = "\033[32m"
RESET = "\033[0m"


class StateMachineEngine:
    def __init__(self, _initial_context: dict) -> None:
        self.cfg = load_config(DEJAVU_CONF_PATH)

        self.state_machine = import_from_yaml(filepath=self.cfg["scenario_state_machine_yaml"])
        self.itp = Interpreter(self.state_machine, initial_context=_initial_context)

        self.monitored_scenarios_df = pd.DataFrame(columns=_initial_context.keys())
        # self.monitored_scenarios_df = pd.DataFrame([_initial_context])
        # self.monitored_scenarios_df["anticipated_scenario"] = "-"
        # self.monitored_scenarios_df["SAT"] = "-"


        # self.itp = Interpreter(self.state_machine, initial_context={"armed": False, "h": 0, "dt": 0, "b": 0, "delta_dt": 0, "wind_speed": 0, "humidity": 0, "vibration": 0, "action": None})
        # self.itp = Interpreter(self.state_machine)
        
        self.initialize_state_machine()

    def parse_action_and_scenario(self, s: str):

        if s is None:
            return None, None

        m = PATTERN.match(s)
        if not m:
            # não tem parênteses -> só action
            return s.strip(), None
        return m.group("action").strip(), m.group("scenario").strip()
    
    def update_monitored_scenarios(self):
        new_context = self.itp.context.copy()
        action = new_context["action"]
        action, scenario = self.parse_action_and_scenario(action)

        new_context.update({
            "action": action,
            "anticipated_scenario": scenario,
            "SAT": None
            })
        self.monitored_scenarios_df = pd.concat([self.monitored_scenarios_df, pd.DataFrame([new_context])], ignore_index=True)

    def initialize_state_machine(self):
        ms=self.itp.execute()
        print("State machine initialized.")

        print(f"{GREEN}INITIAL STATE: {ms[0].entered_states[1]}{RESET}")


        # self.print_step(ms)

        # print("MACROSTEP:", ms)
        # print("CURRENT STATE:", self.state_infos())

    def update_context(self, runtime_data_tick: TelemetryTick):
        self.itp.context.update({
            "armed": runtime_data_tick.armed,
            "h": runtime_data_tick.h,
            "dt": runtime_data_tick.dt,
            "b": runtime_data_tick.b,
            "wind_speed": runtime_data_tick.wind_speed,
            "humidity": runtime_data_tick.humidity,
            "vibration": runtime_data_tick.vibration,
            "delta_dt": runtime_data_tick.delta_dt,
            "action": runtime_data_tick.action})
    
    def there_is_transition_to_execute(self) -> bool:
        return self.itp._external_queue
    
    def state_infos(self, state_name) -> str:
        if state_name == "INIT" or "FINAL":
            return state_name
        st = self.itp.statechart.state_for(state_name)
        inv = list(st.invariants)[0]
        state_infos = f"{st.name} ({inv})"
        return state_infos
    
    # def print_path(self):
    #     print("CURRENT STATE:", self.state_infos())
    #     print("external_queue raw:", self.itp._external_queue)

    def get_transition_infos(self, transition):
        source_state_name = transition.source
        target_state_name = transition.target
        guard = transition.guard
        event = transition.event
        return source_state_name, target_state_name, guard, event
    
    def arrived_error_state(self, transition) -> bool:
        source_state_name, target_state_name, _, _=self.get_transition_infos(transition)
        is_error = ("ERR" in source_state_name.upper()) or ("ERR" in target_state_name.upper())
        return  is_error

    def print_step(self, ms):
        if not ms.transitions:
            return
        
        executed_transition = ms.transitions[0]
        source_state_name, target_state_name, guard, event = self.get_transition_infos(executed_transition)
        is_error = self.arrived_error_state(executed_transition)
        
        # self.monitored_scenarios_df.loc[self.monitored_scenarios_df.index[-1], "SAT"] = not is_error

        color = RED if is_error else GREEN

        print(f"{color}Transition executed: {self.state_infos(source_state_name)} --[{guard} / {event}]--> {self.state_infos(target_state_name)}{RESET}")


    
    def execute_transition_path(self):
        ms = None
        for _ in range(2):
                ms = self.itp.execute_once()
                if ms is None:
                    break
                self.print_step(ms)
        if ms is None:
            self.monitored_scenarios_df.loc[self.monitored_scenarios_df.index[-2], "SAT"] = False
        else:
            executed_transition = ms.transitions[0]
            is_error = self.arrived_error_state(executed_transition)
            self.monitored_scenarios_df.loc[self.monitored_scenarios_df.index[-2], "SAT"] = not is_error
        # self.update_monitored_scenarios()
    
    def execute_new_context_path(self):
          # Execute the state
        for _ in range(2):
            ms = self.itp.execute_once()
            if ms is None:
                break
            self.print_step(ms)
        # print("PRECONDITIONS:", self.itp.context)
        # self.update_monitored_scenarios()

    def add_transition_to_execute_after(self):
        self.itp.queue(self.itp.context["action"])
        # print("Action:", self.itp.context["action"])
        print("Action to execute after:", self.itp._external_queue)
        # self.update_monitored_scenarios()

    def check_state_machine(self, runtime_data_tick: TelemetryTick) -> list:
        
        # print("TICK RECEIVED:", runtime_data_tick)
        
        self.update_context(runtime_data_tick)

        print("CONTEXT UPDATED:", self.itp.context)
        self.update_monitored_scenarios()

        if self.there_is_transition_to_execute():
            print("There is action to execute:", self.itp._external_queue)
            self.execute_transition_path()
            print("POSTCONDITION:", self.itp.context)
            # self.update_monitored_scenarios()

        self.execute_new_context_path()    
    
        if self.itp.context["action"] is not None:
            print("PRECONDITIONS:", self.itp.context)
            self.add_transition_to_execute_after()

        # Return the current state
        return self.monitored_scenarios_df.copy()


class AntecipatedScenarioMonitor:
    
    def __init__(self, initial_context: dict) -> None:
        self.cfg = load_config(DEJAVU_CONF_PATH)
        self.latest: Optional[TelemetryTick] = None
        self.history_runtime_data: List[TelemetryTick] = []  # opcional (pode desligar se ficar grande)
        self.state_machine_engine = StateMachineEngine(initial_context)

        self.new_csv = self.next_csv_path(self.cfg["checked_scenarios_folder"])
        self.new_csv.write_text("", encoding="utf-8")


    def next_csv_path(self, folder: str, prefix: str = "checked_scenarios_", digits: int = 3) -> Path:
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)          # cria o diretório se não existir
        n_csv = len(list(folder.glob("*.csv")))            # conta quantos CSV existem
        next_n = n_csv + 1
        return folder / f"{prefix}{next_n:0{digits}d}.csv" # ex: checked_scenarios_001.csv

    def handle_runtime_data(self, runtime_data_tick: TelemetryTick) -> None:
        self.latest = runtime_data_tick
        self.history_runtime_data.append(runtime_data_tick)

        checked_scenarios_df = self.state_machine_engine.check_state_machine(runtime_data_tick)
        checked_scenarios_df.to_csv(self.new_csv, index=False)

        rows_false = checked_scenarios_df[checked_scenarios_df["SAT"] == False]
        if not rows_false.empty:
            print(f"{RED}=== ALERT: Unexpected Scenario Detected! ==={RESET}")
            print(f"{RED} {rows_false} {RESET}")


        # act = runtime_data_tick.action if runtime_data_tick.action else "-"

        # print(f"[exec={runtime_data_tick.execution} t={runtime_data_tick.t:02d}] action={act:15s} h={runtime_data_tick.h:6.1f} b={runtime_data_tick.b:5.1f} vib={runtime_data_tick.vibration:.2f}")
