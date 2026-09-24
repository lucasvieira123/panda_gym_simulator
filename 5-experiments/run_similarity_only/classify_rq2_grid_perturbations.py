"""
RQ2.2 -- classificacao complementar da grade fatorial (Height x Contacts x
Friction) em Baseline / Threshold-only / Operator-only / Combined.

NAO recalcula nenhuma similaridade e NAO reimplementa o Retriever: le o
Given de cada cenario R_* diretamente de configs/desired_scenario.json (so
para classificar a PERTURBACAO em si, comparando operador e valor de cada
clausula contra a referencia) e junta com os resultados JA existentes em
rq2_analysis/rq2_summary.csv (top1_is_reference, is_exact_tie_at_top,
margin_signed) -- nenhum desses valores e recalculado.

So considera cenarios cujo nome contem 'RQ2_R_' (grade combinatoria da
RQ2.2). Cenarios de omissao/adicao/sweep local (grupos A/B/C) sao
explicitamente excluidos.

Gera:
    rq2_analysis/rq2_grid_perturbation_classification.csv  -- 1 linha por cenario R_*
    rq2_analysis/rq2_grid_direction_summary.json            -- tabela agregada por categoria
"""
import csv
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

THIS_DIR = Path(__file__).resolve().parent
CONFIGS_DIR = THIS_DIR / "configs"
OUTPUT_DIR = THIS_DIR / "rq2_analysis"

# Given de referencia (RQ2_A0 / RQ1 episodio 17_0_130), nao alterado
REFERENCE_CLAUSES = {
    "object_lift_height_cm": ("<", 10.0),
    "finger_contacts": ("<", 2.0),
    "lateral_friction": ("<=", 0.315),
}

CLAUSE_RE = re.compile(r"(object_lift_height_cm|finger_contacts|lateral_friction)\s*(<=|>=|<|>|==|!=)\s*([\d.]+)")


def parse_given(given: str) -> dict:
    clauses = {}
    for var, op, val in CLAUSE_RE.findall(given):
        clauses[var] = (op, float(val))
    return clauses


def classify(clauses: dict) -> str:
    op_changed = False
    threshold_changed = False
    for var, (ref_op, ref_val) in REFERENCE_CLAUSES.items():
        op, val = clauses[var]
        if op != ref_op:
            op_changed = True
        if val != ref_val:
            threshold_changed = True

    if not op_changed and not threshold_changed:
        return "Baseline"
    if not op_changed and threshold_changed:
        return "Threshold-only"
    if op_changed and not threshold_changed:
        return "Operator-only"
    return "Combined"


def main() -> None:
    desired_list = json.load(open(CONFIGS_DIR / "desired_scenario.json", encoding="utf-8"))
    r_items = [d for d in desired_list if "RQ2_R_" in d["name"]]

    with open(OUTPUT_DIR / "rq2_summary.csv", encoding="utf-8") as f:
        summary_by_name = {row["desired_scenario"]: row for row in csv.DictReader(f)}

    rows = []
    missing_from_summary = []
    for d in r_items:
        name = d["name"]
        clauses = parse_given(d["given"])
        if len(clauses) != 3:
            raise ValueError(f"Given inesperado (nao tem as 3 clausulas conhecidas): {name} -> {d['given']}")
        category = classify(clauses)

        summary = summary_by_name.get(name)
        if summary is None:
            missing_from_summary.append(name)
            continue

        top1_is_reference = summary["top1_is_reference"] == "True"
        is_tie = summary["is_exact_tie_at_top"] == "True"
        margin = float(summary["margin_signed"])

        rows.append({
            "desired_scenario": name,
            "given": d["given"],
            "category": category,
            "height_op": clauses["object_lift_height_cm"][0],
            "height_value": clauses["object_lift_height_cm"][1],
            "contacts_op": clauses["finger_contacts"][0],
            "contacts_value": clauses["finger_contacts"][1],
            "friction_op": clauses["lateral_friction"][0],
            "friction_value": clauses["lateral_friction"][1],
            "top1_candidate_name": summary["top1_candidate_name"],
            "top1_is_reference": top1_is_reference,
            "is_exact_tie_at_top": is_tie,
            "margin_signed": margin,
        })

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_DIR / "rq2_grid_perturbation_classification.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # --- agregacao por categoria ---
    categories = ["Baseline", "Threshold-only", "Operator-only", "Combined"]
    summary_table = {}
    for cat in categories:
        cat_rows = [r for r in rows if r["category"] == cat]
        n = len(cat_rows)
        if n == 0:
            summary_table[cat] = {
                "total": 0,
                "cstar_unique_top1": 0,
                "other_unique_top1": 0,
                "tie_at_top": 0,
                "margin_min": None,
                "margin_max": None,
                "note": "Nenhuma configuracao desta categoria existe na grade -- nao foi gerada artificialmente.",
            }
            continue

        cstar_unique = sum(1 for r in cat_rows if r["top1_is_reference"] and not r["is_exact_tie_at_top"])
        other_unique = sum(1 for r in cat_rows if not r["top1_is_reference"] and not r["is_exact_tie_at_top"])
        ties = sum(1 for r in cat_rows if r["is_exact_tie_at_top"])
        margins = [r["margin_signed"] for r in cat_rows]

        summary_table[cat] = {
            "total": n,
            "cstar_unique_top1": cstar_unique,
            "other_unique_top1": other_unique,
            "tie_at_top": ties,
            "margin_min": min(margins),
            "margin_max": max(margins),
        }

    total_classified = sum(v["total"] for v in summary_table.values())

    # --- reconciliacao com a distincao anterior direction-preserving / direction-changing ---
    # direction-preserving == nenhum operador mudou (Baseline + Threshold-only)
    # direction-changing   == pelo menos um operador mudou (Operator-only + Combined)
    direction_preserving = summary_table["Baseline"]["total"] + summary_table["Threshold-only"]["total"]
    direction_changing = summary_table["Operator-only"]["total"] + summary_table["Combined"]["total"]
    direction_changing_flips = sum(
        1 for r in rows if not r["top1_is_reference"] and not r["is_exact_tie_at_top"]
        and r["category"] in ("Operator-only", "Combined")
    )
    direction_changing_ties = sum(
        1 for r in rows if r["is_exact_tie_at_top"] and r["category"] in ("Operator-only", "Combined")
    )

    result = {
        "reference_given": "object_lift_height_cm < 10 AND finger_contacts < 2 AND lateral_friction <= 0.315",
        "total_R_configs_in_desired_scenario_json": len(r_items),
        "total_classified": total_classified,
        "missing_from_rq2_summary_csv": missing_from_summary,
        "expected_full_factorial_size": 900,
        "actual_grid_size": len(r_items),
        "grid_size_gap": 900 - len(r_items),
        "grid_size_gap_note": (
            "A grade fatorial completa (9 H x 10 C x 10 F) teria 900 pontos; "
            f"apenas {len(r_items)} existem em configs/desired_scenario.json. "
            "Nenhuma configuracao foi gerada artificialmente para completar os 900."
        ),
        "categories": summary_table,
        "direction_reconciliation": {
            "direction_preserving_total": direction_preserving,
            "direction_changing_total": direction_changing,
            "direction_changing_strict_flips": direction_changing_flips,
            "direction_changing_ties": direction_changing_ties,
            "matches_previously_reported_210_690": (direction_preserving == 210 and direction_changing == 690),
            "note": (
                "Nenhum arquivo no repositorio contem os numeros '210 direction-preserving' / "
                "'690 direction-changing' citados no pedido -- nao ha registro anterior para "
                "confirmar contra. Os valores acima sao calculados agora, pela primeira vez "
                "nesta base de codigo, a partir dos 897 pontos reais da grade."
            ),
        },
    }

    # ------------------------------------------------------------------
    # Reconciliacao com a grade teorica de 900 (9 H x 10 C x 10 F).
    # As 3 combinacoes ausentes de R_* (H03xC02xF02/F03/F04) NAO sao
    # experimentos nao executados -- sao semanticamente identicas (mesmo
    # Given, char a char) a configuracoes ja existentes em outros grupos:
    #   H03xC02xF02 == RQ2_C11_friction_0p300
    #   H03xC02xF03 == RQ2_A0_baseline_full_context
    #   H03xC02xF04 == RQ2_C03_friction_0p330
    # Reaproveitamos os resultados JA calculados para essas 3 (nenhum
    # recalculo, nenhuma configuracao nova) para reconstruir a grade de 900.
    # ------------------------------------------------------------------
    RECONCILED_POINTS = [
        {
            "hcf": "H03xC02xF02",
            "equivalent_name": "diagnosed_LIFT_OBJECT_unanticipated__RQ2_C11_friction_0p300",
            "equivalent_id": "C11",
        },
        {
            "hcf": "H03xC02xF03",
            "equivalent_name": "diagnosed_LIFT_OBJECT_unanticipated__RQ2_A0_baseline_full_context",
            "equivalent_id": "A0",
        },
        {
            "hcf": "H03xC02xF04",
            "equivalent_name": "diagnosed_LIFT_OBJECT_unanticipated__RQ2_C03_friction_0p330",
            "equivalent_id": "C03",
        },
    ]

    reconciled_rows = []
    for point in RECONCILED_POINTS:
        summary = summary_by_name.get(point["equivalent_name"])
        if summary is None:
            raise ValueError(f"Configuracao equivalente '{point['equivalent_name']}' nao encontrada "
                              f"em rq2_summary.csv -- nao posso reconciliar sem resultado real.")
        given = next(d["given"] for d in desired_list if d["name"] == point["equivalent_name"])
        clauses = parse_given(given)
        category = classify(clauses)
        reconciled_rows.append({
            "hcf": point["hcf"],
            "reused_from_id": point["equivalent_id"],
            "reused_from_name": point["equivalent_name"],
            "given": given,
            "category": category,
            "top1_candidate_name": summary["top1_candidate_name"],
            "top1_is_reference": summary["top1_is_reference"] == "True",
            "is_exact_tie_at_top": summary["is_exact_tie_at_top"] == "True",
            "margin_signed": float(summary["margin_signed"]),
        })

    # tabela agregada de 900 = 897 (R_*) + 3 (reaproveitadas, nao duplicadas)
    summary_table_900 = {}
    for cat in categories:
        native = [r for r in rows if r["category"] == cat]
        reused = [r for r in reconciled_rows if r["category"] == cat]
        all_rows = native + reused
        n = len(all_rows)
        if n == 0:
            summary_table_900[cat] = {
                "total": 0, "cstar_unique_top1": 0, "other_unique_top1": 0, "tie_at_top": 0,
                "margin_min": None, "margin_max": None,
                "note": "Nenhuma configuracao desta categoria existe na grade de 900 -- nao foi gerada artificialmente.",
            }
            continue
        cstar_unique = sum(1 for r in all_rows if r["top1_is_reference"] and not r["is_exact_tie_at_top"])
        other_unique = sum(1 for r in all_rows if not r["top1_is_reference"] and not r["is_exact_tie_at_top"])
        ties = sum(1 for r in all_rows if r["is_exact_tie_at_top"])
        margins = [r["margin_signed"] for r in all_rows]
        summary_table_900[cat] = {
            "total": n, "cstar_unique_top1": cstar_unique, "other_unique_top1": other_unique,
            "tie_at_top": ties, "margin_min": min(margins), "margin_max": max(margins),
            "reused_from_other_groups": len(reused),
        }

    total_900 = sum(v["total"] for v in summary_table_900.values())
    preserving_900 = summary_table_900["Baseline"]["total"] + summary_table_900["Threshold-only"]["total"]
    changing_900 = summary_table_900["Operator-only"]["total"] + summary_table_900["Combined"]["total"]
    all_900_rows = rows + reconciled_rows
    flips_900 = sum(1 for r in all_900_rows if not r["top1_is_reference"] and not r["is_exact_tie_at_top"])
    ties_900 = sum(1 for r in all_900_rows if r["is_exact_tie_at_top"])

    result["reconciliation_900"] = {
        "method": "As 3 combinacoes ausentes de R_* sao semanticamente identicas (mesmo Given) a "
                  "configuracoes ja existentes em outros grupos -- reaproveitadas aqui SEM duplicar "
                  "objetos no desired_scenario.json e SEM recalcular similaridade.",
        "reconciled_points": reconciled_rows,
        "categories_900": summary_table_900,
        "total_900": total_900,
        "direction_preserving_900": preserving_900,
        "direction_changing_900": changing_900,
        "strict_top1_flips_900": flips_900,
        "ties_900": ties_900,
        "matches_article_210_690_7_36": (
            preserving_900 == 210 and changing_900 == 690 and flips_900 == 7 and ties_900 == 36
        ),
    }

    print()
    print("=== Reconciliacao com a grade teorica de 900 ===")
    for p in reconciled_rows:
        print(f"  {p['hcf']} == {p['reused_from_id']} (reaproveitado, nao duplicado) -> "
              f"categoria={p['category']}  top1={p['top1_candidate_name']}  margem={p['margin_signed']:.5f}")
    print()
    print(f"{'Categoria':<16} {'Total':>6} {'C* unico':>9} {'Outro unico':>12} {'Empate':>7} {'Margem min':>11} {'Margem max':>11}")
    for cat in categories:
        s = summary_table_900[cat]
        if s["total"] == 0:
            print(f"{cat:<16} {'0':>6}  -- categoria vazia --")
        else:
            print(f"{cat:<16} {s['total']:>6} {s['cstar_unique_top1']:>9} {s['other_unique_top1']:>12} "
                  f"{s['tie_at_top']:>7} {s['margin_min']:>11.5f} {s['margin_max']:>11.5f}")
    print()
    print(f"Total reconciliado: {total_900} (esperado 900)")
    print(f"direction-preserving = {preserving_900} | direction-changing = {changing_900} | "
          f"flips estritos = {flips_900} | empates = {ties_900}")
    print(f"Bate com o artigo (210/690/7/36)? {result['reconciliation_900']['matches_article_210_690_7_36']}")

    json_path = OUTPUT_DIR / "rq2_grid_direction_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # --- console ---
    print(f"Total de configuracoes R_* em desired_scenario.json: {len(r_items)}")
    print(f"Total classificadas (com correspondencia em rq2_summary.csv): {total_classified}")
    if missing_from_summary:
        print(f"AVISO -- sem correspondencia em rq2_summary.csv: {len(missing_from_summary)} -> {missing_from_summary}")
    print(f"Gap vs grade fatorial completa (900): {900 - len(r_items)} configuracoes ausentes")
    print()
    print(f"{'Categoria':<16} {'Total':>6} {'C* unico':>9} {'Outro unico':>12} {'Empate':>7} {'Margem min':>11} {'Margem max':>11}")
    for cat in categories:
        s = summary_table[cat]
        if s["total"] == 0:
            print(f"{cat:<16} {'0':>6}  -- categoria vazia na grade, nao preenchida artificialmente --")
        else:
            print(f"{cat:<16} {s['total']:>6} {s['cstar_unique_top1']:>9} {s['other_unique_top1']:>12} "
                  f"{s['tie_at_top']:>7} {s['margin_min']:>11.5f} {s['margin_max']:>11.5f}")
    print()
    print(f"direction-preserving (Baseline+Threshold-only) = {direction_preserving}")
    print(f"direction-changing   (Operator-only+Combined)  = {direction_changing}")
    print(f"  dos quais mudanca estrita de Top-1: {direction_changing_flips}  |  empates: {direction_changing_ties}")
    print(f"Bate com '210 preserving / 690 changing' citado no pedido? "
          f"{result['direction_reconciliation']['matches_previously_reported_210_690']}")
    print()
    print(f"Saidas em: {OUTPUT_DIR}")
    print(f"  - {csv_path.name}")
    print(f"  - {json_path.name}")


if __name__ == "__main__":
    main()
