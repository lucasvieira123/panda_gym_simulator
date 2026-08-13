from typing import Optional, List

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

        self._last_sat: bool | None = None

        # Transições executadas no último tick — lidas pelo trace_printer
        self.last_transitions: list[dict] = []
        self.last_action_queued: str | None = None
        self._prev_tick: dict | None = None

        self.initialize_state_machine()

    def parse_action_and_scenario(self, s: str):
        if s is None:
            return None, None
        # format: "action() (SCENARIO_NAME)"
        last_open = s.rfind(' (')
        if last_open != -1 and s.endswith(')'):
            scenario = s[last_open + 2:-1].strip()
            action_part = s[:last_open].strip()
            if action_part.endswith('()'):
                action_part = action_part[:-2].strip()
            return action_part, scenario
        return s.strip(), None
    
    def initialize_state_machine(self):
        ms=self.itp.execute()
        print("State machine initialized.")

        print(f"{GREEN}INITIAL STATE: {ms[0].entered_states[1]}{RESET}")


        # self.print_step(ms)

        # print("MACROSTEP:", ms)
        # print("CURRENT STATE:", self.state_infos())

    def update_context(self, runtime_data_tick: dict):
        self.itp.context.update(runtime_data_tick)
    
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

        color = RED if is_error else GREEN
        print(f"{color}Transition executed: {self.state_infos(source_state_name)} --[{guard} / {event}]--> {self.state_infos(target_state_name)}{RESET}")

        self.last_transitions.append({
            "source":   source_state_name,
            "target":   target_state_name,
            "guard":    guard or "",
            "event":    event or "",
            "is_error": is_error,
        })


    
    def execute_transition_path(self):
        ms = None
        for _ in range(2):
            ms = self.itp.execute_once()
            if ms is None:
                break
            self.print_step(ms)
        if ms is None:
            self._last_sat = False
        else:
            executed_transition = ms.transitions[0]
            is_error = self.arrived_error_state(executed_transition)
            self._last_sat = not is_error
    
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
        action = self.itp.context["action"]
        self.itp.queue(action)
        self.last_action_queued = action
        print("Action to execute after:", self.itp._external_queue)

    @staticmethod
    def _eval_context_guard(guard: str, context: dict | None) -> bool:
        if not guard or context is None:
            return False
        try:
            return bool(eval(guard, {"__builtins__": {}}, context))
        except Exception:
            return False

    def _synthesize_adaptive_events(self) -> list[str]:
        """
        Introspecção do SM: para cada estado ativo com transição orientada a evento,
        verifica rising edge (False→True) no guard de sucesso do PHI alvo.
        Genérico — deriva os eventos diretamente da estrutura do YAML, sem
        hardcode de campos de domínio.
        """
        events = []

        # ── ROLLBACK ──────────────────────────────────────────────────────────────
        # Código original com API Sismic errada: BasicState não possui atributo
        # .transitions — getattr retornava sempre None e o loop nunca executava.
        # Para reverter: descomenta o bloco abaixo e apaga o bloco novo.
        #
        # for state_name in self.itp.configuration:
        #     if state_name == "root":
        #         continue
        #     try:
        #         state = self.itp.statechart.state_for(state_name)
        #     except Exception:
        #         continue
        #     for transition in (getattr(state, "transitions", None) or []):
        #         if transition.event is None:
        #             continue
        #         if not transition.target:
        #             continue
        #         try:
        #             phi_state = self.itp.statechart.state_for(transition.target)
        #         except Exception:
        #             continue
        #         success = next(
        #             (t for t in (getattr(phi_state, "transitions", None) or [])
        #              if t.guard and "ERR" not in (t.target or "").upper()),
        #             None,
        #         )
        #         if success is None:
        #             continue
        #         now_ok  = self._eval_context_guard(success.guard, dict(self.itp.context))
        #         prev_ok = self._eval_context_guard(success.guard, self._prev_tick)
        #         if now_ok and not prev_ok:
        #             events.append(transition.event)
        # ──────────────────────────────────────────────────────────────────────────

        # API correta: transições ficam no Statechart, não no BasicState.
        # statechart.transitions_from(name) → list[Transition] com .event/.target/.guard
        sc = self.itp.statechart
        for state_name in self.itp.configuration:
            if state_name == "root":
                continue
            for transition in sc.transitions_from(state_name):
                if transition.event is None:
                    continue  # guard-based — SM já avança sozinho
                if not transition.target:
                    continue
                # Localiza a transição de sucesso (não-ERR) do PHI alvo
                success = next(
                    (t for t in sc.transitions_from(transition.target)
                     if t.guard and "ERR" not in (t.target or "").upper()),
                    None,
                )
                if success is None:
                    continue
                now_ok  = self._eval_context_guard(success.guard, dict(self.itp.context))
                prev_ok = self._eval_context_guard(success.guard, self._prev_tick)
                if now_ok and not prev_ok:  # rising edge
                    events.append(transition.event)
        return events

    def check_state_machine(self, runtime_data_tick: dict) -> list:
        self.last_transitions = []
        self.last_action_queued = None

        self.update_context(runtime_data_tick)

        if self.there_is_transition_to_execute():
            self.execute_transition_path()

        self.execute_new_context_path()

        if self.itp.context["action"] is not None:

            # ── ROLLBACK ──────────────────────────────────────────────────────
            # Comportamento original: dispara a ação com o contexto do tick atual.
            # Problema: percepção já reflete o resultado da ação (ex: gripper=3),
            # então guards de pré-condição (ex: gripper >= 6) falham e o SM trava.
            # Para reverter: descomenta as 3 linhas abaixo e apaga o bloco novo.
            # self.add_transition_to_execute_after()
            # self.execute_transition_path()
            # self.execute_new_context_path()
            # ──────────────────────────────────────────────────────────────────

            action_label = self.itp.context["action"]

            # Rebobina para o contexto do tick anterior (percepção pré-ação)
            # para que os guards de pré-condição sejam avaliados corretamente.
            # Após a ação disparar e os guards rodarem, restaura o tick atual.
            if self._prev_tick is not None:
                self.update_context(self._prev_tick)
                self.itp.context["action"] = action_label

            self.add_transition_to_execute_after()
            self.execute_transition_path()
            self.execute_new_context_path()

            self.update_context(runtime_data_tick)

        # ── ROLLBACK ──────────────────────────────────────────────────────────────
        # Comportamento original: SM trava em estados adaptativos (S10, S14) pois
        # managing envia current_subtask="" e nenhum evento Sismic é disparado.
        # Solução: introspecção do SM — detecta rising edge no guard do PHI alvo
        # e sintetiza o evento sem rewind de prev_tick (tick atual já é pós-estado).
        # Para reverter: apaga o bloco abaixo e os métodos _synthesize_adaptive_events
        # e _eval_context_guard; remove "current_subtask" de _SM_INITIAL e _sm_params.
        # ──────────────────────────────────────────────────────────────────────────
        if self.itp.context["action"] is None and not self.itp.context.get("current_subtask", ""):
            for event_label in self._synthesize_adaptive_events():
                self.itp.context["action"] = event_label
                self.add_transition_to_execute_after()
                self.execute_transition_path()
                self.execute_new_context_path()
            self.itp.context["action"] = None

        self._prev_tick = runtime_data_tick
        return self._last_sat


class AntecipatedScenarioMonitor:

    def __init__(self, initial_context: dict) -> None:
        self.latest: Optional[dict] = None
        self.history_runtime_data: List[dict] = []
        self.state_machine_engine = StateMachineEngine(initial_context)

    def handle_runtime_data(self, runtime_data_tick: dict) -> None:
        self.latest = runtime_data_tick
        self.history_runtime_data.append(runtime_data_tick)

        sat = self.state_machine_engine.check_state_machine(runtime_data_tick)

        if sat is False:
            print(f"{RED}=== ALERT: Unexpected Scenario Detected! ==={RESET}")
