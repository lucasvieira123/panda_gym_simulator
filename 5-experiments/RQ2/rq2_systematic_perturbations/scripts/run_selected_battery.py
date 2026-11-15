"""
Battery B of RQ2: runs the selected configurations B0-B19 through DejaVu's production Retriever.

Each configuration goes through run_rq2.run_diagnosis, the same path as Battery A: When filter and
calculate_scenario_similarity in SimilarityBasedAdapter, the sort of dejavu.py, and the per-clause
decomposition with the production helpers, checked against the production score.

Before running, B0 must reproduce D0 of Battery A (5-experiments/RQ2/output/results.csv) exactly. After
running, the scores must equal the ones the exploration computed for the same perturbations.

Outputs, in output/:
    selected_diagnoses.csv  design of each configuration (category, intensity, direction, composition)
    similarity_scores.csv   one row per configuration and candidate: score, rank, delta vs B0, clauses
    rankings.csv            one row per configuration: ranking, Top-1/2/3, changes vs B0, C1's rank, margin
    interactions.csv        combined configurations: joint delta vs the sum of the individual deltas
    summary.json            counts and the controlled comparisons (direction, intensity, parameter class)

Usage, from the project root, with the project's venv:
    .venv/Scripts/python.exe 5-experiments/RQ2/rq2_systematic_perturbations/scripts/run_selected_battery.py
"""
import csv
import json

import perturbations as pt

rq2 = pt.rq2
CIDS = sorted(pt.CANDIDATE_IDS)
MARGIN_SMALL = 0.01
TOLERANCE = 1e-12


def write_csv(name: str, rows: list[dict]) -> None:
    pt.OUTPUT.mkdir(parents=True, exist_ok=True)
    with open(pt.OUTPUT / name, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def check_reference(entry: dict) -> None:
    """B0 must give exactly the scores and ranking recorded for D0 in Battery A."""
    with open(pt.RQ2 / "output" / "results.csv", encoding="utf-8", newline="") as f:
        recorded = {r["candidate"]: r for r in csv.DictReader(f) if r["diagnosis"] == "D0"}
    for c in entry["ranking"]:
        a = recorded[c["id"]]
        if abs(float(a["score"]) - c["score"]) > TOLERANCE or int(a["rank"]) != c["rank"]:
            raise SystemExit(f"B0 x {c['id']}: {c['score']} (rank {c['rank']}) differs from Battery A's D0 "
                             f"{a['score']} (rank {a['rank']})")
    print("[ok] B0 reproduces D0 of Battery A: same five scores (within 1e-12) and the same ranking")


def run() -> tuple[list[tuple[str, dict | None, str]], dict]:
    explored, battery = pt.exploration_set()
    spec = pt.spec_b()
    configs = [("B0", None, "Reference: D0 of Battery A")] + battery
    entries = {}
    for bid, item, _ in configs:
        entries[bid] = rq2.run_diagnosis(pt.ADAPTER, spec, pt.diagnosis_dict(bid, item))
    check_reference(entries["B0"])

    with open(pt.EXPLORATION / "exploratory_scores.csv", encoding="utf-8", newline="") as f:
        explored_scores = {r["exploratory_id"]: r for r in csv.DictReader(f)}
    for bid, item, _ in battery:
        row = explored_scores[item["exploratory_id"]]
        scores = {c["id"]: c["score"] for c in entries[bid]["ranking"]}
        if any(f"{scores[cid]:.6f}" != row[f"score_{cid}"] for cid in CIDS):
            raise SystemExit(f"{bid}: scores differ from the exploration ({item['exploratory_id']})")
    print("[ok] the 19 modified configurations have the scores the exploration computed")
    return configs, entries


def scores_of(entry: dict) -> dict:
    return {c["id"]: c["score"] for c in entry["ranking"]}


def order_of(entry: dict) -> list[str]:
    return [c["id"] for c in entry["ranking"]]


def design_rows(configs) -> list[dict]:
    rows = []
    for bid, item, why in configs:
        item = item or {"exploratory_id": "", "category": "reference", "kind": "reference", "key": "",
                        "components": [], "parameters_added": [], "parameters_removed": [],
                        "parameters_modified": [], "parameters_affected": 0, "parameter_class": "",
                        "source_component": "", "intensity": "", "intensity_measure": "", "direction": "",
                        "given": pt.REFERENCE_GIVEN, "assessment_notes": [], "observation_consistency": "",
                        "origin_plausibility": "", "original": "", "modified": ""}
        components = item.get("components") or []
        component_ids = [next(b for b, i, _ in configs if i and i["key"] == k) for k in components]
        rows.append({
            "configuration": bid,
            "exploratory_id": item["exploratory_id"],
            "category": item["category"],
            "kind": item["kind"],
            "perturbation": item["key"],
            "composition": " + ".join(component_ids),
            "original_predicate": item.get("original", ""),
            "modified_predicate": item.get("modified", ""),
            "parameters_added": " ".join(item["parameters_added"]),
            "parameters_removed": " ".join(item["parameters_removed"]),
            "parameters_modified": " ".join(item["parameters_modified"]),
            "parameters_affected": item["parameters_affected"],
            "parameter_class": item["parameter_class"],
            "source_component": item["source_component"],
            "intensity": f"{item['intensity']:.6g}" if isinstance(item["intensity"], (int, float)) else "",
            "intensity_measure": item["intensity_measure"],
            "direction": item["direction"],
            "given": " AND ".join(item["given"]),
            "observation_consistency": item["observation_consistency"],
            "origin_plausibility": item["origin_plausibility"],
            "assessment_notes": " | ".join(item["assessment_notes"]),
            "justification": why,
        })
    return rows


def score_rows(configs, entries) -> list[dict]:
    ref = scores_of(entries["B0"])
    rows = []
    for bid, _, _ in configs:
        for c in sorted(entries[bid]["ranking"], key=lambda c: c["id"]):
            g, w, t = (c["clauses"][k] for k in ("given", "when", "then"))
            rows.append({
                "configuration": bid, "candidate": c["id"], "candidate_name": c["name"], "do": c["do"],
                "rank": c["rank"], "score": f"{c['score']:.10f}", "delta_vs_B0": f"{c['score'] - ref[c['id']]:+.10f}",
                "given_similarity": f"{g['similarity']:.10f}", "given_param_avg": f"{g['param_avg']:.10f}",
                "given_penalty": f"{g['penalty']:.10f}", "given_shared": " ".join(g["shared"]),
                "given_diagnosis_only": " ".join(g["diagnosis_only"]),
                "given_candidate_only": " ".join(g["candidate_only"]),
                "when_similarity": f"{w['similarity']:.10f}", "then_similarity": f"{t['similarity']:.10f}",
            })
    return rows


def ranking_rows(configs, entries) -> list[dict]:
    ref = entries["B0"]
    ref_order = order_of(ref)
    rows = []
    for bid, _, _ in configs:
        m = rq2.ranking_metrics(entries[bid], ref)
        order = m["order"]
        rows.append({
            "configuration": bid, "ranking": " > ".join(order), "top1": order[0],
            "top2": " ".join(order[:2]), "top3": " ".join(order[:3]),
            "top1_score": f"{m['top1_score']:.10f}", "margin_top1_top2": f"{m['margin']:.10f}",
            "top1_changed": m["top1_changed"], "top2_set_changed": set(order[:2]) != set(ref_order[:2]),
            "top3_set_changed": m["top3_set_changed"], "rank_C1": order.index("C1") + 1,
            "kendall_tau_vs_B0": f"{m['kendall_tau']:.1f}", "exact_ties": " ".join(m["exact_ties"]),
            "margin_below_0.01": m["margin"] < MARGIN_SMALL,
        })
    return rows


def interaction_rows(configs, entries) -> list[dict]:
    ref = scores_of(entries["B0"])
    key_to_bid = {item["key"]: bid for bid, item, _ in configs if item}
    rows = []
    for bid, item, _ in configs:
        if not item or not item.get("components"):
            continue
        a, b = (key_to_bid[k] for k in item["components"])
        joint, sa, sb = scores_of(entries[bid]), scores_of(entries[a]), scores_of(entries[b])
        for cid in CIDS:
            d_joint, d_a, d_b = joint[cid] - ref[cid], sa[cid] - ref[cid], sb[cid] - ref[cid]
            rows.append({
                "configuration": bid, "components": f"{a} + {b}", "candidate": cid,
                "delta_joint": f"{d_joint:+.6f}", f"delta_first": f"{d_a:+.6f}", "delta_second": f"{d_b:+.6f}",
                "delta_sum": f"{d_a + d_b:+.6f}", "residual_joint_minus_sum": f"{d_joint - (d_a + d_b):+.6f}",
                "top1_joint": order_of(entries[bid])[0], "top1_first": order_of(entries[a])[0],
                "top1_second": order_of(entries[b])[0],
            })
    return rows


def summary(configs, entries, rankings, interactions) -> dict:
    modified = [r for r in rankings if r["configuration"] != "B0"]
    ref = scores_of(entries["B0"])

    def deltas(bid):
        s = scores_of(entries[bid])
        return {cid: round(s[cid] - ref[cid], 6) for cid in CIDS}

    def brief(bid):
        r = next(x for x in rankings if x["configuration"] == bid)
        return {"ranking": r["ranking"], "margin": round(float(r["margin_top1_top2"]), 6), "delta": deltas(bid)}

    pairs = {
        "friction threshold, d=0.25: restrictive B10 vs permissive B12": ("B10", "B12"),
        "friction threshold, d=0.75: restrictive B11 vs permissive B13": ("B11", "B13"),
        "height threshold, d~0.5: restrictive B14 vs permissive B15": ("B14", "B15"),
        "friction threshold restrictive: low B10 vs high B11": ("B10", "B11"),
        "friction threshold permissive: low B12 vs high B13": ("B12", "B13"),
        "friction operator: minimum B8 vs maximum B9": ("B8", "B9"),
        "omission: distinguishing B5 vs shared B6": ("B5", "B6"),
        "omission: shared B6 vs shared B7": ("B6", "B7"),
    }
    groups = {
        "A addition": ["B1", "B2", "B3", "B4"], "B omission": ["B5", "B6", "B7"], "C operator": ["B8", "B9"],
        "D threshold": ["B10", "B11", "B12", "B13", "B14", "B15"], "combined": ["B16", "B17", "B18", "B19"],
    }
    by_cfg = {r["configuration"]: r for r in rankings}
    return {
        "reference": {"configuration": "B0", "ranking": by_cfg["B0"]["ranking"],
                      "scores": {cid: round(ref[cid], 6) for cid in CIDS},
                      "margin": round(float(by_cfg["B0"]["margin_top1_top2"]), 6)},
        "modified_configurations": len(modified),
        "top1_changed": [r["configuration"] for r in modified if r["top1_changed"]],
        "top2_set_changed": [r["configuration"] for r in modified if r["top2_set_changed"]],
        "top3_set_changed": [r["configuration"] for r in modified if r["top3_set_changed"]],
        "C1_in_top2": [r["configuration"] for r in modified if r["rank_C1"] <= 2],
        "C1_in_top3": [r["configuration"] for r in modified if r["rank_C1"] <= 3],
        "margin_below_0.01": [r["configuration"] for r in modified if r["margin_below_0.01"]],
        "top1_changes_with_margin_below_0.01": [r["configuration"] for r in modified
                                                if r["margin_below_0.01"] and r["top1_changed"]],
        "exact_ties": {r["configuration"]: r["exact_ties"] for r in rankings if r["exact_ties"]},
        "top1_score_range": [round(min(float(r["top1_score"]) for r in modified), 6),
                             round(max(float(r["top1_score"]) for r in modified), 6)],
        "by_category": {g: {b: brief(b) for b in ids} for g, ids in groups.items()},
        "controlled_comparisons": {name: {a: brief(a), b: brief(b)} for name, (a, b) in pairs.items()},
        "interactions": {
            bid: {"components": rows[0]["components"],
                  "residual_joint_minus_sum": {r["candidate"]: float(r["residual_joint_minus_sum"]) for r in rows},
                  "top1": {"joint": rows[0]["top1_joint"], "first": rows[0]["top1_first"],
                           "second": rows[0]["top1_second"]}}
            for bid in sorted({r["configuration"] for r in interactions}, key=lambda b: int(b[1:]))
            for rows in [[r for r in interactions if r["configuration"] == bid]]
        },
    }


def main() -> None:
    configs, entries = run()
    rankings = ranking_rows(configs, entries)
    interactions = interaction_rows(configs, entries)
    write_csv("selected_diagnoses.csv", design_rows(configs))
    write_csv("similarity_scores.csv", score_rows(configs, entries))
    write_csv("rankings.csv", rankings)
    write_csv("interactions.csv", interactions)
    data = summary(configs, entries, rankings, interactions)
    (pt.OUTPUT / "summary.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"{'cfg':4} {'ranking':24} {'margin':>8}  C1  " + "  ".join(f"{c:>6}" for c in CIDS))
    for r in rankings:
        s = scores_of(entries[r["configuration"]])
        print(f"{r['configuration']:4} {r['ranking']:24} {float(r['margin_top1_top2']):8.4f}  {r['rank_C1']}   "
              + "  ".join(f"{s[c]:.4f}" for c in CIDS))
    print("Top-1 changed:", data["top1_changed"])
    print("Top-2 set changed:", data["top2_set_changed"])
    print("Top-3 set changed:", data["top3_set_changed"])
    print(f"wrote {pt.OUTPUT}")


if __name__ == "__main__":
    main()
