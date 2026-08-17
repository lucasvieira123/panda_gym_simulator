import re
import pandas as pd
import yaml

from constants import DEJAVU_CONF_PATH
from utils import load_config

_OP_NEG = {
    ">=": "<",
    "<=": ">",
    "==": "!=",
    "!=": "==",
    ">": "<=",
    "<": ">=",
}


class UnanticipatedScenarioIdentifier:

    def __init__(self):
        self.cfg = load_config(DEJAVU_CONF_PATH)
        self.modelling_anticipated_scenarios = load_config(self.cfg["anticipated_scenarios_path"])
       

    def get_scenario_by_name(self, name: str) -> dict:
        _, sc = self._get_scenario_with_key(name)
        return sc

    def _get_scenario_with_key(self, name: str) -> tuple[str, dict]:
        name_key = name.casefold().strip()
        scenarios = self.modelling_anticipated_scenarios.get("scenarios", {})
        for key, sc in scenarios.items():
            if sc.get("name", key).casefold().strip() == name_key:
                return key, sc
        raise KeyError(f"Cenário com name='{name}' não encontrado")
    
    def false_clauses(self, cond: str, context_row: pd.Series) -> list[str]:
        ctx = context_row.iloc[0].to_dict()  # {'h': 99.2, 'delta_dt': 10.0, ...}

        clauses = [c.strip() for c in cond.split(" AND ")]
        falses = [c for c in clauses if not eval(c, {}, ctx)]
        return falses 
    
    def negate_clause(self, clause: str) -> str:
        s = clause.strip()
        m = re.match(r"^(.*?)(>=|<=|==|!=|>|<)(.*)$", s)
        if not m:
            return f"not ({s})"  # fallback p/ casos mais complexos

        left, op, right = m.group(1).strip(), m.group(2), m.group(3).strip()
        return f"{left} {_OP_NEG[op]} {right}"
    
    def join_conditions_and(self, unanticipated_conditions) -> str:
        # if unanticipated_conditions is None:
        #     return "*"

        # já é string
        if isinstance(unanticipated_conditions, str):
            return unanticipated_conditions.strip()

        # lista/tupla de condições
        conds = [str(c).strip() for c in unanticipated_conditions if str(c).strip()]
        # if not conds:
        #     return "*"
        if len(conds) == 1:
            return conds[0]
        return " AND ".join(f"({c})" for c in conds)

    def identifies(self, unanticipated_scenarios_df: pd.DataFrame):
        
        #TODO só trata violacoes em post-conditions por enquanto

        cols = unanticipated_scenarios_df.columns[: unanticipated_scenarios_df.columns.get_loc("action")]  # até action
        
        precontext_df  = unanticipated_scenarios_df.loc[unanticipated_scenarios_df.index[0], cols].to_frame().T
        postcontext_df = unanticipated_scenarios_df.loc[unanticipated_scenarios_df.index[1], cols].to_frame().T
        violated_scenario_name = unanticipated_scenarios_df["anticipated_scenario"].iloc[0]

        violated_key, violated_scenario = self._get_scenario_with_key(violated_scenario_name)
        given = violated_scenario.get("given", {})
        when = violated_scenario.get("when", {})
        do = violated_scenario.get("do", {})
        then = violated_scenario.get("then", {})

        violated_conditions = self.false_clauses(then, postcontext_df)
        unanticipated_conditions = [self.negate_clause(violeted_condition) for violeted_condition in violated_conditions]

        new_given = self.join_conditions_and(unanticipated_conditions)

        return {
            "name":           violated_scenario_name + "_unanticipated",
            "anticipated_id": violated_key,
            "given":          new_given,
            "when":           when,
            "do":             do,
            "then":           then,
        }