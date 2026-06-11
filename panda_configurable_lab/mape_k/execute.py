from __future__ import annotations

from typing import List


class Executor:
    """
    E — Execute

    Responsabilidade:
      Receber os planos do Plan e aplicar cada ação sobre a política interna
      e o Knowledge.

    Ações suportadas:
      reset_phase   — reseta a fase da política interna
      cautious_mode — ativa gain reduzido por N steps
        params: steps (int), gain_factor (float)

    tick() é chamado uma vez por step para manter o efeito do cautious_mode
    nos steps seguintes ao da detecção.

    Para adicionar uma nova ação:
      1. Adicionar o nome em plan_options.yaml (campo 'action').
      2. Adicionar o elif correspondente em _apply().
      Não é necessário alterar plan.py nem analyzer.py.
    """

    DEFAULT_CAUTIOUS_STEPS       = 20
    DEFAULT_CAUTIOUS_GAIN_FACTOR = 0.4

    def execute(self, plans: List[dict], knowledge, inner_policy) -> None:
        """Aplica a sequência de ações de cada plano recebido."""
        for plan in plans:
            goal_old = [round(v, 3) for v in plan["goal"]["old"]] if plan["goal"]["old"] else None
            goal_new = [round(v, 3) for v in plan["goal"]["new"]]
            print(
                f"[MAPE-K/Execute] step={plan['step']}"
                f"  executando '{plan['id']}'"
                f"\n  goal anterior : {goal_old}"
                f"\n  novo goal     : {goal_new}"
            )
            for action_def in plan.get("actions", []):
                self._apply(action_def, knowledge, inner_policy)

            knowledge.events_log.append({
                "step"    : plan["step"],
                "event"   : plan["analysis"],
                "plan_id" : plan["id"],
                "old_goal": plan["goal"]["old"],
                "new_goal": plan["goal"]["new"],
            })
            print()

    def tick(self, knowledge, inner_policy, default_gain: float) -> None:
        """
        Chamado uma vez por step para manter efeitos ativos:
          - decai gain cauteloso
          - reverte behavior temporário quando steps esgotam
        """
        # gain cauteloso
        if knowledge.cautious_steps_remaining > 0:
            inner_policy.gain = default_gain * knowledge.cautious_factor
            knowledge.cautious_steps_remaining -= 1
            if knowledge.cautious_steps_remaining == 0:
                inner_policy.gain = default_gain
                print(
                    f"[MAPE-K/Execute] step={knowledge.step_count}"
                    f"  cautious_mode encerrado — gain normal restaurado"
                )
        else:
            inner_policy.gain = default_gain

        # behavior temporário — sempre reverte para hold ao fim dos steps
        if knowledge.temp_behavior_remaining > 0:
            knowledge.temp_behavior_remaining -= 1
            if knowledge.temp_behavior_remaining == 0:
                inner_policy.switch_to("hold")
                print(
                    f"[MAPE-K/Execute] step={knowledge.step_count}"
                    f"  behavior temporário encerrado — revertendo para 'hold'"
                )

    # ── Aplicadores de ação ───────────────────────────────────────────────────

    def _apply(self, action_def: dict, knowledge, inner_policy) -> None:
        action = action_def.get("action", "")

        if action == "switch_behavior":
            name  = action_def.get("name", "")
            steps = action_def.get("steps")

            if steps is not None:
                knowledge.temp_behavior_remaining = int(steps)

            inner_policy.switch_to(name)
            print(
                f"[MAPE-K/Execute]   → switch_behavior '{name}'"
                + (f"  por {steps} steps (depois: hold)" if steps else "")
            )

        elif action == "reset_phase":
            inner_policy.reset_phase()
            print(f"[MAPE-K/Execute]   → reset_phase  (política: '{knowledge.current_policy}')")

        elif action == "cautious_mode":
            steps  = int(action_def.get("steps",       self.DEFAULT_CAUTIOUS_STEPS))
            factor = float(action_def.get("gain_factor", self.DEFAULT_CAUTIOUS_GAIN_FACTOR))
            knowledge.cautious_factor          = factor
            knowledge.cautious_steps_remaining = steps
            print(f"[MAPE-K/Execute]   → cautious_mode  {steps} steps  (gain × {factor})")

        else:
            print(f"[MAPE-K/Execute]   → ação desconhecida: '{action}' — ignorada")
