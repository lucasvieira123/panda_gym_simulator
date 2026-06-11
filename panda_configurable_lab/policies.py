from __future__ import annotations

from .behaviors import Behavior, GreedyGoalBehavior, ScriptedBehavior, make_behavior


class SimplePolicy:
    """
    Wrapper fino sobre Behavior.

    Responsabilidade:
      - Instanciar o Behavior correto via make_behavior(name)
      - Propagar gain para o behavior ativo
      - Gerenciar a troca automática de behavior quando ScriptedBehavior termina
      - Ajustar ee_tracking da task com base no tipo de behavior ativo
    """

    def __init__(self, name: str = "random", gain: float = 5.0):
        self.name     = name
        self._gain    = gain
        self._behavior: Behavior = make_behavior(name, gain)

    # ── gain propagado para o behavior ativo ─────────────────────────────────

    @property
    def gain(self) -> float:
        return self._gain

    @gain.setter
    def gain(self, value: float) -> None:
        self._gain = value
        self._behavior.gain = value

    # ── interface pública ─────────────────────────────────────────────────────

    def act(self, env, observation):
        # GreedyGoal rastreia o ee; todos os outros rastreiam o objeto configurado
        if hasattr(env, "task") and hasattr(env.task, "set_ee_tracking"):
            env.task.set_ee_tracking(isinstance(self._behavior, GreedyGoalBehavior))

        action = self._behavior.act(env, observation)

        # Quando ScriptedBehavior termina, troca automaticamente para policy_after
        if isinstance(self._behavior, ScriptedBehavior):
            next_name = self._behavior.next_policy
            if next_name is not None:
                self.switch_to(next_name)

        return action

    def reset_phase(self) -> None:
        """Reinicia o estado interno do behavior ativo."""
        if isinstance(self._behavior, ScriptedBehavior):
            policy_after = self._behavior._policy_after
            self.switch_to(policy_after)
        else:
            self._behavior.reset()

    def switch_to(self, name: str, gain: float | None = None) -> None:
        """Troca o behavior ativo, resetando estado interno."""
        self.name      = name
        self._gain     = gain if gain is not None else self._gain
        self._behavior = make_behavior(name, self._gain)

    def switch_inner_behavior(self, name: str) -> None:
        """
        Troca o behavior interno sem substituir a policy ativa.

        Se a policy for self_adaptive, altera o behavior do MAPE-K interno.
        Caso contrário, equivale a switch_to().
        """
        from .behaviors import SelfAdaptiveBehavior
        if isinstance(self._behavior, SelfAdaptiveBehavior):
            b = self._behavior
            if b._mape_k is not None:
                b._mape_k._inner.switch_to(name)
            else:
                b._pending_inner = name   # aplicado no primeiro act()
        else:
            self.switch_to(name)

    def load_script(self, script: list, policy_after: str = "hold") -> None:
        """Carrega uma sequência de ações primitivas e ativa o ScriptedBehavior."""
        self._behavior = ScriptedBehavior(gain=self._gain)
        self._behavior.load(script, policy_after)
        self.name = "scripted"
