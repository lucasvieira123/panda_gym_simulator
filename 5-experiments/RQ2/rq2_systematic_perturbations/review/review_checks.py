"""
Review checks of Battery B (supplementary; they do not change the battery, its scores or its figure).

1. Predicate pairs the Jaccard actually compared, in B0-B19 and in every scored explored perturbation: kinds
   of pair (interval/interval, equality/equality, equality/interval), pairs with Jaccard above 1, and pairs
   involving a zero-length region.
2. Integer-convention sensitivity. The Retriever measures an integer region by the length hi - lo of the
   interval between its extreme admissible values (x < 10 over 0-100 is [0, 9], length 9), counts an equality
   as length 1 against an interval, and takes the hull of two intervals as their union. The alternative here
   is discrete cardinality: |A n B| / |A u B| over the sets of admissible integers of the catalogue domain,
   rounded to 5 decimals like the Retriever. Real-valued parameters keep the Retriever's measure. Applied to
   Battery B (B0-B19) and Battery A (D0-D19, paper labels), with every other part of the metric unchanged.
3. Order-3 combinations: every combination of three individual perturbations of Battery B that touch three
   different parameters, under both conventions. This is an exploratory check of whether the Top-3 can
   change with three simultaneous modifications; it is exhaustive over these operators only, so its counts
   are not an estimate of how often that happens in general.

Outputs, in review/: metric_pairs.csv, integer_convention_scores.csv, integer_convention_rankings.csv,
order3_combinations.csv, review_summary.json.

Usage, from the project root, with the project's venv:
    .venv/Scripts/python.exe 5-experiments/RQ2/rq2_systematic_perturbations/review/review_checks.py
"""
import csv
import json
import sys
from contextlib import contextmanager
from itertools import combinations
from pathlib import Path

REVIEW = Path(__file__).resolve().parent
sys.path.insert(0, str(REVIEW.parent / "scripts"))

import perturbations as pt  # noqa: E402
import similarity.dejavu_similarity as ds  # noqa: E402

rq2 = pt.rq2
CIDS = sorted(pt.CANDIDATE_IDS)
IMPLEMENTATION, DISCRETE = "implementation", "discrete cardinality"


# ── Conventions ──────────────────────────────────────────────────────────────

_production_jaccard = ds._calculate_jaccard_similarity


def discrete_jaccard(expression_1: str, expression_2: str, monitored_parameters_dict: dict) -> float:
    v1, _, _ = ds._decompose_relational_expression(expression_1)
    v2, _, _ = ds._decompose_relational_expression(expression_2)
    info = monitored_parameters_dict.get(v1)
    if v1 != v2 or info is None or info["type"] != "int":
        return _production_jaccard(expression_1, expression_2, monitored_parameters_dict)
    a, b = pt.integer_set(expression_1), pt.integer_set(expression_2)
    return round(len(a & b) / len(a | b), 5) if a | b else 0.0


@contextmanager
def convention(name: str):
    """Swaps the Jaccard the production code calls (calculate_parameters_similarity looks it up by name)."""
    ds._calculate_jaccard_similarity = discrete_jaccard if name == DISCRETE else _production_jaccard
    try:
        yield
    finally:
        ds._calculate_jaccard_similarity = _production_jaccard


def ranked(given: list[str]) -> list[tuple[str, float]]:
    diagnosed = {"name": "review", "given": " AND ".join(given), "when": pt.REFERENCE_WHEN, "do": "TBD",
                 "then": pt.REFERENCE_THEN}
    return [(pt.CANDIDATE_BY_NAME[r["candidate"]["name"]], r["similarity_result"])
            for r in rq2.retrieve(pt.ADAPTER, diagnosed)]


def write_csv(name: str, rows: list[dict]) -> None:
    with open(REVIEW / name, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


# ── 1. Predicate pairs ───────────────────────────────────────────────────────

def pair_kind(a: str, b: str) -> str:
    oa, ob = ds._decompose_relational_expression(a)[1], ds._decompose_relational_expression(b)[1]
    return "equality/equality" if oa == ob == "==" else "equality/interval" if "==" in (oa, ob) else \
        "interval/interval"


def zero_length(predicate: str) -> bool:
    reg = pt.region(predicate)
    return ds._decompose_relational_expression(predicate)[1] != "==" and not isinstance(reg, list) \
        and reg[1] - reg[0] <= 0


def metric_pairs(battery, explored) -> tuple[list[dict], dict]:
    scopes = {"Battery B (B0-B19)": [pt.REFERENCE_GIVEN] + [it["given"] for _, it, _ in battery],
              "scored exploration": [it["given"] for it in explored if it["scored"] and not it.get("duplicate_of")]}
    rows, summary = [], {}
    for scope, givens in scopes.items():
        counts, flagged = {}, set()
        for given in givens:
            for cand in pt.APPLICABLE.values():
                for d_clause, c_clause in ((" AND ".join(given), cand["given"]), (pt.REFERENCE_WHEN, cand["when"]),
                                           (pt.REFERENCE_THEN, cand["then"])):
                    for pair in ds.calculate_parameters_similarity(d_clause, c_clause, pt.DOMAINS):
                        for (a, b), j in pair.items():
                            kind = pair_kind(a, b)
                            counts[kind] = counts.get(kind, 0) + 1
                            if j > 1 or kind == "equality/interval" or zero_length(a) or zero_length(b):
                                flagged.add((a, b, j, kind))
        summary[scope] = {"pairs": counts, "flagged": [list(f) for f in sorted(flagged)]}
        rows += [{"scope": scope, "pair_kind": k, "pairs": n, "flagged_pair": ""} for k, n in sorted(counts.items())]
        rows += [{"scope": scope, "pair_kind": f[3], "pairs": "",
                  "flagged_pair": f"{f[0]} | {f[1]} -> Jaccard {f[2]}"} for f in sorted(flagged)]
    return rows, summary


# ── 2. Integer convention ────────────────────────────────────────────────────

def battery_a_configurations() -> list[tuple[str, list[str]]]:
    spec_a = pt.SPEC_A
    with open(pt.RQ2 / "figures" / "rq2_similarity_plotly_labels.csv", encoding="utf-8", newline="") as f:
        paper = {r["battery_id"]: r["paper_label"] for r in csv.DictReader(f)}
    configs = [(f"A:{paper[d['id']]}", rq2.build_given(spec_a["reference"]["given"], d["changes"]))
               for d in spec_a["diagnoses"]]
    return sorted(configs, key=lambda c: int(c[0][3:]))


def integer_convention(battery) -> tuple[list[dict], list[dict], dict]:
    configs = [("B:B0", pt.REFERENCE_GIVEN)] + [(f"B:{bid}", it["given"]) for bid, it, _ in battery] \
        + battery_a_configurations()
    results = {}
    for name in (IMPLEMENTATION, DISCRETE):
        with convention(name):
            results[name] = {cfg: ranked(given) for cfg, given in configs}
    score_rows, ranking_rows = [], []
    for cfg, _ in configs:
        impl, disc = dict(results[IMPLEMENTATION][cfg]), dict(results[DISCRETE][cfg])
        o_impl = [c for c, _ in results[IMPLEMENTATION][cfg]]
        o_disc = [c for c, _ in results[DISCRETE][cfg]]
        for cid in CIDS:
            score_rows.append({"configuration": cfg, "candidate": cid,
                               "score_implementation": f"{impl[cid]:.10f}", "score_discrete": f"{disc[cid]:.10f}",
                               "difference": f"{disc[cid] - impl[cid]:+.10f}",
                               "rank_implementation": o_impl.index(cid) + 1, "rank_discrete": o_disc.index(cid) + 1})
        ranking_rows.append({
            "configuration": cfg, "ranking_implementation": " > ".join(o_impl),
            "ranking_discrete": " > ".join(o_disc), "same_ranking": o_impl == o_disc,
            "same_top1": o_impl[0] == o_disc[0], "same_top3_set": set(o_impl[:3]) == set(o_disc[:3]),
            "margin_implementation": f"{impl[o_impl[0]] - impl[o_impl[1]]:.6f}",
            "margin_discrete": f"{disc[o_disc[0]] - disc[o_disc[1]]:.6f}",
            "max_abs_score_difference": f"{max(abs(disc[c] - impl[c]) for c in CIDS):.6f}",
        })
    # Intensity of the height thresholds of Battery B under each convention
    intensities = {}
    for bid, it, _ in battery:
        if it["kind"] == "threshold" and it["parameters_modified"] == ["object_lift_height_cm"]:
            with convention(DISCRETE):
                d_disc = 1 - ds._calculate_jaccard_similarity(it["original"], it["modified"], pt.DOMAINS)
            intensities[bid] = {"predicate": it["modified"], "implementation": round(it["intensity"], 6),
                                "discrete": round(d_disc, 6)}
    summary = {
        "convention_alternative": "integers measured by cardinality of admissible values (|A n B| / |A u B|); "
                                  "real-valued parameters unchanged",
        "configurations_with_a_different_ranking": [r["configuration"] for r in ranking_rows if not r["same_ranking"]],
        "configurations_with_a_different_top1": [r["configuration"] for r in ranking_rows if not r["same_top1"]],
        "configurations_with_a_different_top3_set": [r["configuration"] for r in ranking_rows
                                                     if not r["same_top3_set"]],
        "max_abs_score_difference": {
            "Battery B": max(float(r["max_abs_score_difference"]) for r in ranking_rows if r["configuration"][0] == "B"),
            "Battery A": max(float(r["max_abs_score_difference"]) for r in ranking_rows if r["configuration"][0] == "A"),
        },
        "height_threshold_intensity_battery_b": intensities,
    }
    return score_rows, ranking_rows, summary


# ── 3. Order-3 combinations ──────────────────────────────────────────────────

def order3(battery) -> tuple[list[dict], dict]:
    individual = [(bid, it) for bid, it, _ in battery if not it.get("components")]

    def touched(it):
        return set(it["parameters_added"] + it["parameters_removed"] + it["parameters_modified"])

    reference = {name: None for name in (IMPLEMENTATION, DISCRETE)}
    for name in reference:
        with convention(name):
            reference[name] = {c for c, _ in ranked(pt.REFERENCE_GIVEN)[:3]}
    distinct = [t for t in combinations(individual, 3)
                if not (touched(t[0][1]) & touched(t[1][1]) or touched(t[0][1]) & touched(t[2][1])
                        or touched(t[1][1]) & touched(t[2][1]))]
    # B5 + B6 + B7 omits all three conditions of D0: an empty Given is not a scenario
    triples = [t for t in distinct if rq2.build_given(pt.REFERENCE_GIVEN, [c for _, it in t for c in it["changes"]])]
    empty = [" + ".join(bid for bid, _ in t) for t in distinct if t not in triples]
    rows = []
    results = {}
    for name in (IMPLEMENTATION, DISCRETE):
        with convention(name):
            results[name] = [ranked(rq2.build_given(pt.REFERENCE_GIVEN, [c for _, it in t for c in it["changes"]]))
                             for t in triples]
    for t, r_impl, r_disc in zip(triples, results[IMPLEMENTATION], results[DISCRETE]):
        given = rq2.build_given(pt.REFERENCE_GIVEN, [c for _, it in t for c in it["changes"]])
        row = {"components": " + ".join(bid for bid, _ in t), "given": " AND ".join(given)}
        for label, r, ref in (("implementation", r_impl, reference[IMPLEMENTATION]),
                              ("discrete", r_disc, reference[DISCRETE])):
            row[f"ranking_{label}"] = " > ".join(c for c, _ in r)
            row[f"top3_changed_{label}"] = {c for c, _ in r[:3]} != ref
            row[f"gap_2nd_3rd_{label}"] = f"{r[1][1] - r[2][1]:.6f}"
            row[f"gap_3rd_4th_{label}"] = f"{r[2][1] - r[3][1]:.6f}"   # the margin that decides the Top-3 set
            for cid, score in sorted(r):
                row[f"score_{cid}_{label}"] = f"{score:.6f}"
        rows.append(row)
    changed = [r for r in rows if r["top3_changed_implementation"] or r["top3_changed_discrete"]]
    summary = {
        "combinations": len(rows),
        "excluded_empty_given": empty,
        "scope": "every combination of three individual perturbations of Battery B touching three different "
                 "parameters; an existence check, not a frequency estimate",
        "top3_changed": [{k: v for k, v in r.items()} for r in changed],
    }
    return rows, summary


def main() -> None:
    explored, battery = pt.exploration_set()
    pairs, pairs_summary = metric_pairs(battery, explored)
    write_csv("metric_pairs.csv", pairs)
    scores, rankings, convention_summary = integer_convention(battery)
    write_csv("integer_convention_scores.csv", scores)
    write_csv("integer_convention_rankings.csv", rankings)
    triples, order3_summary = order3(battery)
    write_csv("order3_combinations.csv", triples)
    summary = {"metric_pairs": pairs_summary, "integer_convention": convention_summary, "order3": order3_summary}
    (REVIEW / "review_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                                                encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
