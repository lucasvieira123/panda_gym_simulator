from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.tree import _tree

from constants import DEJAVU_CONF_PATH, PROJECT_ROOT
from utils import load_config

_DROP_COLS = {
    "sat", "execution", "episode", "step", "exec",
    "active_state", "active_scenario_name", "active_scenario_type",
    "current_subtask", "current_task", "active_target_name", "tipo",
    "global_goal_achieved",
}


class UnanticipatedScenarioDiagnoser:

    def __init__(self) -> None:
        self.cfg = load_config(DEJAVU_CONF_PATH)
        self._dataset_folder = str(PROJECT_ROOT / self.cfg["antecipated_scenario_dataset_folder"])
        self.classifier = DecisionTreeClassifier(random_state=42, max_depth=3)

    def _load_dataset(self, folder: str) -> pd.DataFrame:
        folder_path = Path(folder)
        dfs = []
        for csv_path in sorted(folder_path.glob("*.csv")):
            df = pd.read_csv(csv_path)
            df["execution"] = csv_path.stem
            dfs.append(df)
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    def extract_rules(self, clf, feature_names, class_names=None):
        tree = clf.tree_
        if class_names is None:
            class_names = [str(c) for c in getattr(clf, "classes_", [])] or None
        rules = []

        def recurse(node, conditions):
            feat_id = tree.feature[node]
            if feat_id != _tree.TREE_UNDEFINED:
                feat = feature_names[feat_id]
                thr = round(float(tree.threshold[node]), 4)
                feat_clean = feat.replace(".", "_")
                recurse(tree.children_left[node],  conditions + [f"{feat_clean} <= {thr}"])
                recurse(tree.children_right[node], conditions + [f"{feat_clean} > {thr}"])
                return
            value = tree.value[node][0]
            total = float(value.sum())
            proba = (value / total) if total > 0 else np.zeros_like(value)
            pred_idx = int(np.argmax(value))
            pred = class_names[pred_idx] if class_names else str(pred_idx)
            rules.append({
                "if": conditions,
                "then": pred,
                "proba": {
                    (class_names[i] if class_names else str(i)): float(round(proba[i], 4))
                    for i in range(len(proba))
                },
                "samples": int(tree.n_node_samples[node]),
            })

        recurse(0, [])
        return rules

    def path_conditions(self, clf, X_row: pd.DataFrame) -> tuple[str, bool]:
        """Conditions on the tree path of one execution, simplified per feature, and the leaf prediction.

        Joining every positive leaf with AND gives contradictory conditions when the tree has more than
        one positive leaf (e.g. "x <= 0.1325 AND x > 0.1325"); the path of the current execution is a
        consistent conjunction that covers the situation being diagnosed.
        """
        tree = clf.tree_
        feature_names = list(X_row.columns)
        lower: dict[str, float] = {}   # feature > value  (keeps the largest)
        upper: dict[str, float] = {}   # feature <= value (keeps the smallest)
        order: list[str] = []
        for node in clf.decision_path(X_row).indices:
            feat_id = tree.feature[node]
            if feat_id == _tree.TREE_UNDEFINED:
                continue
            feat = feature_names[feat_id]
            thr = round(float(tree.threshold[node]), 4)
            if feat not in order:
                order.append(feat)
            if X_row.iloc[0, feat_id] <= tree.threshold[node]:
                upper[feat] = min(upper.get(feat, thr), thr)
            else:
                lower[feat] = max(lower.get(feat, thr), thr)
        conditions = []
        for feat in order:
            clean = feat.replace(".", "_")
            if feat in lower:
                conditions.append(f"{clean} > {lower[feat]}")
            if feat in upper:
                conditions.append(f"{clean} <= {upper[feat]}")
        predicted = str(clf.predict(X_row)[0]) in ("1", "1.0", "True", "true")
        return " AND ".join(conditions), predicted

    def diagnosis(self, identified_unanticipated_scenario: dict, current_execution: str | None = None) -> dict:
        """
        current_execution: stem of the current run's CSV. When given, the diagnostic conditions are the
        tree path of that execution; otherwise, the conditions of the positive leaves (only one is
        expected when the dataset holds the nominal runs and the current one).
        """
        scenario_name = identified_unanticipated_scenario["name"].replace("_unanticipated", "")

        df = self._load_dataset(self._dataset_folder)
        scenario_rows = df[df["active_scenario_name"] == scenario_name].copy()

        if scenario_rows.empty:
            raise ValueError(f"Nenhuma linha encontrada para o cenário '{scenario_name}' no dataset.")

        # ── 1. Label por execução ────────────────────────────────────────────
        label_name = f"{scenario_name}_unanticipated"
        exec_label = (
            scenario_rows.groupby("execution")["sat"]
            .apply(lambda s: s.eq(False).any())
            .rename(label_name)
        )

        # ── 2. Snapshot: primeira linha de cada execução ─────────────────────
        snapshot = scenario_rows.groupby("execution").first()
        exec_ds  = snapshot.join(exec_label)

        # ── 3. Montar X e y ──────────────────────────────────────────────────
        drop = _DROP_COLS | {label_name}
        X_raw  = exec_ds.drop(columns=[c for c in drop if c in exec_ds.columns])
        X_num  = X_raw.select_dtypes(include=[np.number, bool])
        X_all  = X_num.loc[:, X_num.nunique() > 1]
        y_exec = exec_ds[label_name]

        # ── 4. Features estáticas (std == 0 na execução inteira) ─────────────
        # Avaliar só as linhas do cenário faria um efeito dinâmico parecer causa:
        # finger_contacts é constante dentro de TRANSPORT_OBJECT, mas varia na execução.
        static_cols = [
            col for col in X_all.columns
            if col in df.columns
            and (df.groupby("execution")[col].std(ddof=0).fillna(0) == 0).all()
        ]

        if not static_cols:
            raise ValueError(
                f"Nenhuma feature estática encontrada para '{scenario_name}' — não é possível diagnosticar."
            )

        X_static = X_all[static_cols]

        # ── 5. Treina árvore e extrai regras ─────────────────────────────────
        self.classifier.fit(X_static, y_exec)
        rules = self.extract_rules(self.classifier, feature_names=list(X_static.columns))

        for r in rules:
            r["then"] = "True" if str(r["then"]) in ("1", "1.0", "True", "true") else "False"

        false_rules = [r for r in rules if r["then"] == "True"]

        if current_execution is not None:
            if current_execution not in X_static.index:
                raise ValueError(f"Execução atual '{current_execution}' sem linhas de '{scenario_name}' no dataset.")
            unanticipated_conditions_str, predicted = self.path_conditions(
                self.classifier, X_static.loc[[current_execution]])
            if not predicted:
                raise ValueError(
                    f"Diagnóstico não cobre a execução atual: a árvore classifica '{current_execution}' "
                    f"sem violação de '{scenario_name}' (condições do caminho: {unanticipated_conditions_str})."
                )
        elif len(false_rules) > 1:
            raise ValueError(
                f"A árvore tem {len(false_rules)} folhas com violação de '{scenario_name}'; "
                "informe a execução atual para diagnosticar pelo seu caminho."
            )
        else:
            unanticipated_conditions_str = " AND ".join(cond for r in false_rules for cond in r["if"])

        if not unanticipated_conditions_str:
            raise ValueError(
                f"Diagnóstico sem condições para '{scenario_name}': a árvore não separou execuções "
                f"com e sem violação (features: {list(X_static.columns)}; "
                f"violações: {int(y_exec.sum())} de {len(y_exec)} execuções)."
            )

        # ── 6. Enriquece o cenário identificado ──────────────────────────────
        diagnosed = identified_unanticipated_scenario.copy()
        diagnosed.update({
            "name": "diagnosed_" + diagnosed["name"],
            "given": diagnosed["given"] + " AND " + unanticipated_conditions_str,
            "diagnostic_conditions": unanticipated_conditions_str,
            "do": "TBD",
        })

        return diagnosed
