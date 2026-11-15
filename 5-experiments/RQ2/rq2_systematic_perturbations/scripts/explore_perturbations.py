"""
Exploration of Battery B: every perturbation of D0's Given considered, its characterisation and the
selection of the battery.

Two stages, in this order:

1. design (no score): explored perturbations, their assessment (logical status, consistency with the
   observation, feasibility, measurability, origin and plausibility), intensity, direction, parameter class, and the
   selection declared in perturbations.SELECTION -> exploration/exploratory_diagnoses.csv;
2. scores: every satisfiable explored perturbation the Retriever can measure, to describe the behaviour
   of the metric -> exploration/exploratory_scores.csv. The selection is not revisited after this stage.

Usage, from the project root, with the project's venv:
    .venv/Scripts/python.exe 5-experiments/RQ2/rq2_systematic_perturbations/scripts/explore_perturbations.py [--design-only]
"""
import argparse
import csv

import perturbations as pt

DESIGN_COLUMNS = [
    "exploratory_id", "selected_as", "category", "kind", "key", "original", "modified",
    "parameters_added", "parameters_removed", "parameters_modified", "parameters_affected", "parameter_class",
    "source_component", "intensity", "intensity_measure", "target_distance", "direction", "given",
    "logical_status", "observation_consistency", "violation_relation", "domain_feasibility", "metric_applicability",
    "origin_plausibility", "assessment_notes", "scored", "coincides_with_candidate", "components", "rationale",
    "exclusion_reason",
]


def fmt(value) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, list):
        return " | ".join(map(str, value)) if value and not all(isinstance(v, str) and " " not in v
                                                                for v in value) else " ".join(map(str, value))
    return "" if value is None else str(value)


def design_rows(explored: list[dict]) -> list[dict]:
    rows = []
    for item in explored:
        row = {c: fmt(item.get(c, "")) for c in DESIGN_COLUMNS}
        row["given"] = " AND ".join(item["given"])
        row["assessment_notes"] = " | ".join(item["assessment_notes"])
        rows.append(row)
    return rows


def write_csv(path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def score_rows(explored: list[dict]) -> list[dict]:
    spec = pt.spec_b()
    reference = pt.rq2.retrieve(pt.ADAPTER, pt.rq2.diagnosed_scenario(spec, pt.diagnosis_dict("B0", None)))
    ref_scores = {pt.CANDIDATE_BY_NAME[r["candidate"]["name"]]: r["similarity_result"] for r in reference}
    ref_order = [pt.CANDIDATE_BY_NAME[r["candidate"]["name"]] for r in reference]
    rows = []
    for item in explored:
        if not item["scored"] or item.get("duplicate_of"):
            continue
        diagnosed = pt.rq2.diagnosed_scenario(spec, pt.diagnosis_dict(item["exploratory_id"], item))
        results = pt.rq2.retrieve(pt.ADAPTER, diagnosed)
        order = [pt.CANDIDATE_BY_NAME[r["candidate"]["name"]] for r in results]
        scores = {pt.CANDIDATE_BY_NAME[r["candidate"]["name"]]: r["similarity_result"] for r in results}
        row = {"exploratory_id": item["exploratory_id"], "selected_as": item["selected_as"],
               "category": item["category"], "kind": item["kind"], "key": item["key"],
               "intensity": fmt(item["intensity"]), "direction": item["direction"], "given": diagnosed["given"]}
        for cid in sorted(pt.CANDIDATE_IDS):
            row[f"score_{cid}"] = f"{scores[cid]:.6f}"
        for cid in sorted(pt.CANDIDATE_IDS):
            row[f"delta_{cid}"] = f"{scores[cid] - ref_scores[cid]:+.6f}"
        row.update({
            "ranking": " > ".join(order), "top1": order[0], "top2": " ".join(order[:2]),
            "top3": " ".join(order[:3]), "margin_top1_top2": f"{scores[order[0]] - scores[order[1]]:.6f}",
            "top1_changed": order[0] != ref_order[0], "top3_set_changed": set(order[:3]) != set(ref_order[:3]),
            "rank_C1": order.index("C1") + 1, "kendall_tau_vs_B0": f"{pt.rq2.kendall_tau(order, ref_order):.1f}",
            "observation_consistency": item["observation_consistency"],
            "origin_plausibility": item["origin_plausibility"],
            "assessment_notes": " | ".join(item["assessment_notes"]),
        })
        rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--design-only", action="store_true", help="stage 1 only: no score is computed")
    args = parser.parse_args()

    explored, battery = pt.exploration_set()   # stage 1: the selection is fixed here
    write_csv(pt.EXPLORATION / "exploratory_diagnoses.csv", design_rows(explored))
    scored = sum(bool(i["scored"]) and not i.get("duplicate_of") for i in explored)
    print(f"explored {len(explored)} perturbations ({scored} scored); selected {len(battery)} + B0")
    for bid, item, _ in battery:
        print(f"  {bid:<4} {item['exploratory_id']}  {item['key']}")
    if args.design_only:
        return

    rows = score_rows(explored)                # stage 2: scores of every measurable explored perturbation
    write_csv(pt.EXPLORATION / "exploratory_scores.csv", rows)
    print(f"scored {len(rows)} explored perturbations -> {pt.EXPLORATION / 'exploratory_scores.csv'}")


if __name__ == "__main__":
    main()
