from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.tree import _tree

from constants import DEJAVU_CONF_PATH
from utils import load_config

class UnanticipatedScenarioDiagnoser:

    def __init__(self) -> None:
        self.cfg = load_config(DEJAVU_CONF_PATH)
        self.all_checked_scenarios_df = self.load_all_checked_scenarios(self.cfg["checked_scenarios_folder"])
        self.classifier = DecisionTreeClassifier(random_state=42, max_depth=3)

    def load_all_checked_scenarios(self, folder: str) -> pd.DataFrame:
        folder_path = Path(folder)

        dfs = []
        for csv_path in sorted(folder_path.glob("*.csv")):
            df = pd.read_csv(csv_path)
            df["execution"] = csv_path.stem  # ex: "checked_scenarios_001"
            dfs.append(df)

        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    def filter_scenario_and_next(self, violated_scenario_name: str) -> pd.DataFrame:
        df = self.all_checked_scenarios_df

        kept = []

        # se tiver 'execution', garante que row+1 não cruza de um CSV pro outro
        if "execution" in df.columns:
            for _, g in df.groupby("execution", sort=False):
                # guarda o índice original pra voltar pro df principal
                g2 = g.reset_index()  # cria coluna 'index' com o índice original

                mask = g2["anticipated_scenario"].astype(str).str.contains(violated_scenario_name, na=False)
                hits = g2.index[mask]

                take_pos = sorted({p for i in hits for p in (i, i+1) if p < len(g2)})
                kept.extend(g2.loc[take_pos, "index"].tolist())

            # remove duplicados mantendo a ordem
            kept = list(dict.fromkeys(kept))
            return df.loc[kept].copy()

        # fallback se não existir 'execution'
        dfr = df.reset_index(drop=True)
        mask = dfr["anticipated_scenario"].astype(str).str.contains(violated_scenario_name, na=False)
        hits = dfr.index[mask]
        take_pos = sorted({p for i in hits for p in (i, i+1) if p < len(dfr)})
        return dfr.iloc[take_pos].copy()
    
    def extract_rules(self, clf, feature_names, class_names=None):
        tree = clf.tree_

        if class_names is None:
            class_names = [str(c) for c in getattr(clf, "classes_", [])] or None

        rules = []

        def recurse(node, conditions):
            feat_id = tree.feature[node]

            # nó interno
            if feat_id != _tree.TREE_UNDEFINED:
                feat = feature_names[feat_id]
                thr = int(tree.threshold[node])

                left = tree.children_left[node]
                right = tree.children_right[node]

                recurse(left,  conditions + [f"{feat} <= {thr}"])
                recurse(right, conditions + [f"{feat} > {thr}"])
                return

            # folha
            value = tree.value[node][0]               # contagem por classe
            total = float(value.sum())
            proba = (value / total) if total > 0 else np.zeros_like(value)

            pred_idx = int(np.argmax(value))
            pred = class_names[pred_idx] if class_names else str(pred_idx)

            rules.append({
                "if": conditions,  # lista (fácil de dar join / filtrar)
                "then": pred,
                "proba": { (class_names[i] if class_names else str(i)): float(round(proba[i], 4))
                        for i in range(len(proba)) },
                "samples": int(tree.n_node_samples[node]),
            })

        recurse(0, [])
        return rules

    def diagnosis(self, detected_unanticipated_scenarios_df: pd.DataFrame,
                 identified_unanticipated_scenarios_dict: pd.DataFrame) -> pd.DataFrame:
        
        violated_scenario_name = detected_unanticipated_scenarios_df["anticipated_scenario"].iloc[0]

        filtered_df = self.filter_scenario_and_next(violated_scenario_name)
        train_df = filtered_df.drop(columns=["action","anticipated_scenario","execution"])
        train_df["SAT"] = train_df["SAT"].astype("boolean").fillna(False)
        
        X = train_df.drop(columns=["SAT"])
        y = train_df["SAT"]

        self.classifier.fit(X, y)
        # regras = export_text(self.classifier, feature_names=list(X.columns))
        # print(regras)
        rules = self.extract_rules(self.classifier, feature_names=list(X.columns))

        for r in rules: # Força 'then' ser string "True" ou "False"
            r["then"] = "True" if str(r["then"]) in ("1", "1.0", "True", "true") else "False"

        false_rules = [
            {"if": r["if"], "proba": r["proba"]}
            for r in rules
            if str(r.get("then")) == "False"]
        
        # achata todas as condições (listas) em uma lista só
        all_conditions = [cond for fr in false_rules for cond in fr["if"]]

        # string final com AND
        unanticipated_conditions_str = " AND ".join(all_conditions)

        diagnosed_unanticipated_scenario_dict = identified_unanticipated_scenarios_dict.copy()

        diagnosed_unanticipated_scenario_dict.update({"name": "diagnosed_"+ diagnosed_unanticipated_scenario_dict["name"],
                                                      "given": diagnosed_unanticipated_scenario_dict["given"]+" AND " +unanticipated_conditions_str,
                                                      "do":"TBD"})    
       


        return diagnosed_unanticipated_scenario_dict