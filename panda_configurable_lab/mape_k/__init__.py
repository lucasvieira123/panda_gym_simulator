from __future__ import annotations

from typing import Any, Dict

from .knowledge import Knowledge
from .monitor   import Monitor
from .analyzer  import Analyzer, DEFAULT_RULES_PATH
from .plan      import Planner, DEFAULT_PLAN_OPTIONS_PATH
from .execute   import Executor


class MAPEKController:
    """
    Orquestrador MAPE-K — coordena os cinco componentes a cada step.

    M  monitor.py   — coleta estado + constrói contexto plano
    A  analyzer.py  — avalia regras Given/Then de adaptation_options.yaml
    P  plan.py      — consulta plan_options.yaml → monta sequência de ações
    E  execute.py   — aplica as ações na política interna + Knowledge
    K  knowledge.py — memória compartilhada entre todos os componentes
    """

    def __init__(
        self,
        initial_policy: str = "greedy_push",
        gain: float = 5.0,
        rules_path: str = DEFAULT_RULES_PATH,
        plan_path: str = DEFAULT_PLAN_OPTIONS_PATH,
    ):
        self.gain = gain
        self.k    = Knowledge(initial_policy=initial_policy)

        self._monitor_m  = Monitor()
        self._analyzer_a = Analyzer(rules_path=rules_path)
        self._planner_p  = Planner(options_path=plan_path)
        self._executor_e = Executor()

        # Import lazy para evitar import circular com policies.py
        from ..policies import SimplePolicy
        self._inner = SimplePolicy(name=initial_policy, gain=gain)

    def reset(self) -> None:
        initial = self.k.current_policy
        self.k  = Knowledge(initial_policy=initial)
        self._inner.reset_phase()
        self._inner.gain = self.gain

    def act(self, env, observation: Dict[str, Any]):
        # M — coleta estado completo e constrói contexto plano
        state   = self._monitor_m.collect(env, observation)
        context = self._monitor_m.build_context(state, self.k.prev_desired_goal, self.k.step_count)

        # A — avalia regras → lista de regras disparadas
        triggered = self._analyzer_a.analyze(context, self.k.step_count)

        # P — consulta plan_options → lista de planos com sequências de ações
        plans = self._planner_p.plan(triggered, state, self.k)

        # E — aplica as ações de cada plano
        self._executor_e.execute(plans, self.k, self._inner)

        # E (tick) — mantém efeitos ativos nos steps seguintes
        self._executor_e.tick(self.k, self._inner, self.gain)

        self.k.prev_desired_goal = list(state["goal"]["desired"])
        self.k.step_count += 1

        return self._inner.act(env, observation)
