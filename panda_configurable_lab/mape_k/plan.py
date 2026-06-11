from __future__ import annotations

import os
from typing import List

import yaml


DEFAULT_PLAN_OPTIONS_PATH = os.path.join("configs", "plan_options.yaml")


class Planner:
    """
    P — Plan

    Responsabilidade:
      Receber as análises do Analyze, consultar plan_options.yaml e montar
      a sequência de ações a executar — sem aplicar nenhuma mudança.

    Given : string de análise produzida pelo Analyze
    Then  : lista de ações que o Execute irá aplicar

    Para adicionar uma nova situação:
      1. Adicionar o plano em plan_options.yaml com o 'given' correspondente.
      2. Garantir que as ações do 'then' estão implementadas em execute.py.
      Não é necessário alterar este arquivo.
    """

    def __init__(self, options_path: str = DEFAULT_PLAN_OPTIONS_PATH):
        self._options = self._load_options(options_path)
        # índice given → plano para lookup O(1)
        self._index = {
            opt["given"]: opt
            for opt in self._options
            if opt.get("enabled", True)
        }

    def plan(self, triggered: List[dict], state: dict, knowledge) -> List[dict]:
        """
        Para cada regra disparada pelo Analyze, localiza o plano correspondente
        e monta o dict de plano com contexto enriquecido para o Execute.
        """
        plans = []
        for rule in triggered:
            analysis = rule.get("then", "")
            option   = self._index.get(analysis)

            if option is None:
                print(f"[MAPE-K/Plan]    step={knowledge.step_count}  sem plano para '{analysis}' — ignorado")
                continue

            plan = {
                "id"      : option["id"],
                "analysis": analysis,
                "actions" : option.get("then", []),
                "step"    : knowledge.step_count,
                "policy"  : knowledge.current_policy,
                "goal"    : {
                    "old": knowledge.prev_desired_goal,
                    "new": state["goal"]["desired"],
                },
            }

            actions_desc = ", ".join(a["action"] for a in plan["actions"])
            print(
                f"[MAPE-K/Plan]    step={knowledge.step_count}"
                f"  '{option['id']}'  →  [{actions_desc}]"
            )
            plans.append(plan)

        return plans

    @staticmethod
    def _load_options(path: str) -> list:
        if not os.path.exists(path):
            print(f"[MAPE-K/Plan]    Arquivo de planos não encontrado: {path!r} — nenhum plano carregado.")
            return []
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        options = data.get("plans", [])
        enabled = [o for o in options if o.get("enabled", True)]
        print(f"[MAPE-K/Plan]    {len(enabled)}/{len(options)} plano(s) ativo(s) carregado(s) de {path!r}")
        return options
