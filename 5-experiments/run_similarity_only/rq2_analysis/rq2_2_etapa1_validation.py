"""
RQ2.2 -- Etapa 1: inspecao e validacao read-only dos artefatos reais antes
de gerar qualquer figura. NAO recalcula similaridade, NAO modifica nenhum
CSV/JSON de resultado -- so le e reconcilia.
"""
import json
import pandas as pd
from pathlib import Path

ANALYSIS_DIR = Path(__file__).resolve().parent
CONFIGS_DIR = ANALYSIS_DIR.parent / "configs"

summary = pd.read_csv(ANALYSIS_DIR / "rq2_summary.csv")
full = pd.read_csv(ANALYSIS_DIR / "rq2_full_ranking.csv")
classif = pd.read_csv(ANALYSIS_DIR / "rq2_grid_perturbation_classification.csv")
desired = json.load(open(CONFIGS_DIR / "desired_scenario.json", encoding="utf-8"))

REF_DO = "apply_vacuum_assist()"  # C_ref = Lift Slip, confirmado em decompose_rq2_similarity.py

print("=== 1. Quantos registros por grupo (prefixo do experiment_id) ===")
summary["group"] = summary["experiment_id"].astype(str).str.extract(r"^([A-Za-z]+)")
print(summary.groupby("group").size())
print()

r_native = summary[summary["experiment_id"].astype(str).str.startswith("R_")].copy()
print(f"Total nativo R_* em rq2_summary.csv: {len(r_native)}")
print(f"Total nativo R_* em rq2_grid_perturbation_classification.csv: {len(classif)}")
assert len(r_native) == len(classif) == 897, "Contagem nativa R_* nao bate com o esperado (897)"

print()
print("=== 2. Reconciliacao dos 3 pontos reaproveitados (H03xC02xF02/F03/F04) ===")
RECONCILED = {
    "H03xC02xF02": "diagnosed_LIFT_OBJECT_unanticipated__RQ2_C11_friction_0p300",
    "H03xC02xF03": "diagnosed_LIFT_OBJECT_unanticipated__RQ2_A0_baseline_full_context",
    "H03xC02xF04": "diagnosed_LIFT_OBJECT_unanticipated__RQ2_C03_friction_0p330",
}
for hcf, name in RECONCILED.items():
    row = summary[summary["desired_scenario"] == name]
    assert len(row) == 1, f"Esperava 1 linha para {name}, achei {len(row)}"
    print(f"  {hcf} == {name} -> encontrado, rank_ref={row['reference_rank'].iloc[0]}, "
          f"score_ref={row['reference_similarity'].iloc[0]}")

# categoria de cada um dos 3 reaproveitados (mesma logica do classify_rq2_grid_perturbations.py)
REFERENCE_CLAUSES = {"object_lift_height_cm": ("<", 10.0), "finger_contacts": ("<", 2.0), "lateral_friction": ("<=", 0.315)}
import re
CLAUSE_RE = re.compile(r"(object_lift_height_cm|finger_contacts|lateral_friction)\s*(<=|>=|<|>|==|!=)\s*([\d.]+)")
def classify_given(given):
    clauses = {v: (op, float(val)) for v, op, val in CLAUSE_RE.findall(given)}
    op_changed = any(clauses[v][0] != REFERENCE_CLAUSES[v][0] for v in REFERENCE_CLAUSES)
    val_changed = any(clauses[v][1] != REFERENCE_CLAUSES[v][1] for v in REFERENCE_CLAUSES)
    if not op_changed and not val_changed:
        return "Baseline"
    if not op_changed:
        return "Threshold-only"
    if not val_changed:
        return "Operator-only"
    return "Combined"

desired_by_name = {d["name"]: d for d in desired}
reconciled_rows = []
for hcf, name in RECONCILED.items():
    given = desired_by_name[name]["given"]
    cat = classify_given(given)
    srow = summary[summary["desired_scenario"] == name].iloc[0]
    reconciled_rows.append({
        "hcf": hcf, "reused_from": name, "category": cat,
        "reference_similarity": srow["reference_similarity"],
        "best_competitor_similarity": srow["best_competitor_similarity"],
        "top1_is_reference": srow["top1_is_reference"],
        "is_exact_tie_at_top": srow["is_exact_tie_at_top"],
    })
    print(f"    given={given}  -> categoria={cat}")

print()
print("=== 3. Categorias na grade nativa (897) + reconciliada (900) ===")
classif["category"].value_counts().to_dict()
native_counts = classif["category"].value_counts().to_dict()
print("Nativo (897):", native_counts)

recon_counts = dict(native_counts)
for r in reconciled_rows:
    recon_counts[r["category"]] = recon_counts.get(r["category"], 0) + 1
print("Reconciliado (900):", recon_counts)

expected = {"Threshold-only": 209, "Operator-only": 7, "Combined": 683, "Baseline": 1}
print("Esperado pelo usuario:", expected)
print("BATE?", recon_counts == expected)

print()
print("=== 4. Flips (outro candidato > C_ref) e empates, nativo vs reconciliado ===")
flips_native = classif[(classif["top1_is_reference"] == False) & (classif["is_exact_tie_at_top"] == False)]
ties_native = classif[classif["is_exact_tie_at_top"] == True]
print(f"Flips nativos (897): {len(flips_native)}")
print(f"Empates nativos (897): {len(ties_native)}")

flips_recon = len(flips_native) + sum(1 for r in reconciled_rows if not r["top1_is_reference"] and not r["is_exact_tie_at_top"])
ties_recon = len(ties_native) + sum(1 for r in reconciled_rows if r["is_exact_tie_at_top"])
print(f"Flips reconciliados (900): {flips_recon}  (esperado 7)")
print(f"Empates reconciliados (900): {ties_recon}  (esperado 36)")

print()
print("=== 5. D_ref -- valores exatos ===")
a0 = summary[summary["desired_scenario"] == "diagnosed_LIFT_OBJECT_unanticipated__RQ2_A0_baseline_full_context"].iloc[0]
print(a0[["desired_scenario", "top1_candidate_name", "reference_rank", "reference_similarity",
          "best_competitor_name", "best_competitor_similarity", "margin_signed",
          "top1_is_reference", "is_exact_tie_at_top"]])

print()
print("=== 6. Grupo C -- 15 C0x (exceto C08) + D_ref = 16? ===")
c_rows = summary[summary["experiment_id"].astype(str).str.match(r"^C\d+$")]
print(f"IDs presentes: {sorted(c_rows['experiment_id'].tolist())}")
print(f"Total C0x: {len(c_rows)}  (esperado 15, sem C08)")
print(f"C0x + D_ref = {len(c_rows) + 1}  (esperado 16)")

print()
print("=== 7. R_H03_C02_F08 -- confirmar Given e candidatos exatos ===")
target = classif[classif["desired_scenario"].str.contains("R_H03_C02_F08")]
print(target[["desired_scenario", "given", "category", "height_op", "height_value",
              "contacts_op", "contacts_value", "friction_op", "friction_value",
              "top1_candidate_name", "top1_is_reference", "margin_signed"]].to_string())

full_target = full[full["desired_scenario"] == target["desired_scenario"].iloc[0]]
print()
print("Ranking completo para R_H03_C02_F08:")
print(full_target[["rank", "candidate_scenario", "adaptive_behavior", "final_similarity", "is_reference_candidate"]].to_string())

print()
print("=== 8. C_ref / C2 (Parallel Arm Lift) para D_ref, comparacao com R_H03_C02_F08 ===")
full_a0 = full[full["desired_scenario"] == "diagnosed_LIFT_OBJECT_unanticipated__RQ2_A0_baseline_full_context"]
print("D_ref ranking completo:")
print(full_a0[["rank", "candidate_scenario", "adaptive_behavior", "final_similarity", "is_reference_candidate"]].to_string())
