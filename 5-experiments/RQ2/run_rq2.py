"""
RQ2 — Retrieval robustness to inaccuracies in the Desired Adaptation Scenario.

Runs the 20 diagnoses of `diagnoses.json` through DejaVu's production Retriever and writes the
results to `output/`. Nothing here computes similarity on its own:

- scores and ranking: `SimilarityBasedAdapter.calculate_similarity` (When filter, then
  `calculate_scenario_similarity` per candidate) followed by the sort of `dejavu.py`
  (stable, by score, descending) and `SimilarityBasedAdapter.recommend` for the Top-1;
- per-clause decomposition: the production helpers of `similarity/dejavu_similarity.py`
  (`calculate_parameters_similarity`, `_parameter_similarity_weighted_avg`, `_extract_parameters`,
  `_penalty`), checked against the production score of every candidate.

Complementary runs use the same production code with other inputs:

- domain sensitivity: the domains of the independent reproduction (`exploratory_reference.json`)
  in place of the catalogue's, to explain the differences from that reproduction;
- friction domain: D0 and D2 with other upper bounds of `lateral_friction`;
- integration replay: every diagnosis recorded in the final RQ1.1 and RQ1.2 runs, with the
  catalogue and weights of that run, compared with the ranking DejaVu recorded during the run.

Usage, from the project root, with the project's venv:
    .venv/Scripts/python.exe 5-experiments/RQ2/run_rq2.py
"""
import csv
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "3-dejavu" / "src"))

from retry_policy import MAX_ATTEMPTS  # noqa: E402
from similarity.dejavu_similarity import (  # noqa: E402
    _decompose_relational_expression,
    _extract_parameters,
    _get_relational_expression_region,
    _parameter_similarity_weighted_avg,
    _penalty,
    calculate_conditional_similarity,
    calculate_parameters_similarity,
)
from similarity_based_adapter import SimilarityBasedAdapter  # noqa: E402

OUTPUT = HERE / "output"
CLAUSES = ("given", "when", "then")
NEAR_TIE = 1e-9      # adjacent scores closer than this are reported as near ties
TOLERANCE = 1e-12    # decomposition must recompose the production score within this

# Final batteries whose recorded rankings are replayed (results/ folders are not versioned)
REPLAY_GLOBS = (
    "5-experiments/RQ1.1/bateria/results/*/outputs/dejavu_traces/events_*.jsonl",
    "5-experiments/RQ1.2/sequencia/results/principal/*/outputs/dejavu_traces/events_*.jsonl",
    "5-experiments/RQ1.2/sequencia/results/extensao/*/outputs/dejavu_traces/events_*.jsonl",
)


# ── Battery specification ────────────────────────────────────────────────────

def load_json(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def build_given(reference_given: list[str], changes: list[dict]) -> list[str]:
    """Applies the changes to a fresh copy of D0's predicates: no change carries over to another D."""
    given = list(reference_given)
    for change in changes:
        if "replace" in change:
            given[given.index(change["replace"])] = change["with"]
        elif "remove" in change:
            given.remove(change["remove"])
        elif "add" in change:
            if change["add"] in given:
                raise ValueError(f"predicate already in the Given: {change['add']}")
            given.append(change["add"])
        else:
            raise ValueError(f"unknown change: {change}")
    return given


def diagnosed_scenario(spec: dict, diagnosis: dict, given: list[str] | None = None) -> dict:
    """The dict the Diagnoser hands to the Retriever, with D0's When, Do and Then."""
    reference = spec["reference"]
    given = given if given is not None else build_given(reference["given"], diagnosis["changes"])
    return {
        "name":  diagnosis["id"],
        "given": " AND ".join(given),
        "when":  reference["when"],
        "do":    reference["do"],
        "then":  reference["then"],
    }


# ── Production Retriever ─────────────────────────────────────────────────────

def make_adapter(domains: dict | None = None) -> SimilarityBasedAdapter:
    """Production adapter, reading the production catalogue and weights; `domains` replaces only the domains."""
    adapter = SimilarityBasedAdapter()
    if domains is not None:
        adapter.monitored_parameters_dict = domains
    return adapter


def retrieve(adapter: SimilarityBasedAdapter, diagnosed: dict) -> list:
    """Scores of the production adapter, ranked as in the RETRIEVE stage of dejavu.py."""
    results = adapter.calculate_similarity(diagnosed)
    results.sort(key=lambda s: s["similarity_result"], reverse=True)  # same statement as dejavu.py
    return results


def similarity_kwargs(adapter: SimilarityBasedAdapter) -> dict:
    """The keyword arguments SimilarityBasedAdapter passes to calculate_scenario_similarity."""
    return {**adapter.weight_configs_dict, "monitored_parameters": adapter.monitored_parameters_dict}


def region(leaf: str, domains: dict) -> str:
    """Admissible region of a predicate, as the production Jaccard computes it."""
    variable, operator, value = _decompose_relational_expression(leaf)
    info = domains.get(variable)
    if info is None:
        return "no domain"
    reg = _get_relational_expression_region(
        variable, operator, value, info["min_value"], info["max_value"], info["type"])
    parts = reg if isinstance(reg, list) else [reg]
    return " U ".join(f"[{lo:g}, {hi:g}]" for lo, hi in parts)


def decompose_clause(diagnosis_expr: str, candidate_expr: str, kwargs: dict) -> dict:
    """S_param, the Tversky penalty and S_cond of one clause, from the production helpers."""
    domains = kwargs["monitored_parameters"]
    weights = kwargs["parameter_weights"]
    alpha, beta = kwargs["tversky_weights"]["alpha"], kwargs["tversky_weights"]["beta"]

    pairs = calculate_parameters_similarity(diagnosis_expr, candidate_expr, domains)
    param_avg = _parameter_similarity_weighted_avg(pairs, parameter_weights=weights)
    d_params = _extract_parameters(diagnosis_expr)
    c_params = _extract_parameters(candidate_expr)
    penalty = _penalty(d_params, c_params, alpha=alpha, beta=beta)
    similarity = calculate_conditional_similarity(
        diagnosis_expr, candidate_expr, domains, weights, alpha=alpha, beta=beta)
    if abs(max(param_avg - penalty, 0) - similarity) > TOLERANCE:
        raise AssertionError(f"S_cond is not max(0, S_param - P): {diagnosis_expr!r} vs {candidate_expr!r}")

    jaccard = [
        {"parameter": d_leaf.split()[0], "diagnosis_predicate": d_leaf, "candidate_predicate": c_leaf,
         "region_diagnosis": region(d_leaf, domains), "region_candidate": region(c_leaf, domains),
         "jaccard": value}
        for pair in pairs for (d_leaf, c_leaf), value in pair.items()
    ]
    d_set, c_set = set(d_params), set(c_params)
    return {
        "param_avg":      param_avg,
        "penalty":        penalty,
        "similarity":     similarity,
        "shared":         sorted(d_set & c_set),
        "diagnosis_only": sorted(d_set - c_set),
        "candidate_only": sorted(c_set - d_set),
        "jaccard":        jaccard,
    }


def run_diagnosis(adapter: SimilarityBasedAdapter, spec: dict, diagnosis: dict,
                  given: list[str] | None = None) -> dict:
    diagnosed = diagnosed_scenario(spec, diagnosis, given)
    results = retrieve(adapter, diagnosed)
    expected = list(spec["candidates"].values())
    if adapter.last_when_filter["applicable"] != expected:
        raise SystemExit(f"{diagnosis['id']}: When filter kept {adapter.last_when_filter['applicable']}, "
                         f"expected {expected}")

    ids = {name: cid for cid, name in spec["candidates"].items()}
    kwargs = similarity_kwargs(adapter)
    weights = kwargs["conditional_weights"]
    ranking = []
    for rank, result in enumerate(results, start=1):
        candidate = result["candidate"]
        clauses = {k: decompose_clause(diagnosed[k], candidate[k], kwargs) for k in CLAUSES}
        recomposed = sum(weights[k] * clauses[k]["similarity"] for k in CLAUSES) / sum(weights[k] for k in CLAUSES)
        if abs(recomposed - result["similarity_result"]) > TOLERANCE:
            raise AssertionError(f"{diagnosis['id']} x {candidate['name']}: decomposition {recomposed} "
                                 f"!= production {result['similarity_result']}")
        ranking.append({
            "id": ids[candidate["name"]], "name": candidate["name"], "do": candidate["do"],
            "rank": rank, "score": result["similarity_result"], "clauses": clauses,
        })
    return {
        "diagnosis":   diagnosis,
        "diagnosed":   diagnosed,
        "when_filter": adapter.last_when_filter,
        "recommended": adapter.recommend(results),
        "ranking":     ranking,
    }


def run_battery(spec: dict, adapter: SimilarityBasedAdapter | None = None) -> list[dict]:
    adapter = adapter or make_adapter()
    return [run_diagnosis(adapter, spec, diagnosis) for diagnosis in spec["diagnoses"]]


# ── Ranking analysis ─────────────────────────────────────────────────────────

def kendall_tau(order: list[str], reference: list[str]) -> float:
    position = {c: i for i, c in enumerate(order)}
    pairs = [(a, b) for i, a in enumerate(reference) for b in reference[i + 1:]]
    concordant = sum(position[a] < position[b] for a, b in pairs)
    return (2 * concordant - len(pairs)) / len(pairs)


def ranking_metrics(entry: dict, reference: dict) -> dict:
    order = [c["id"] for c in entry["ranking"]]
    ref_order = [c["id"] for c in reference["ranking"]]
    scores = [c["score"] for c in entry["ranking"]]
    gaps = [a - b for a, b in zip(scores, scores[1:])]
    return {
        "order":              order,
        "top1":               order[0],
        "top3":               order[:3],
        "top1_score":         scores[0],
        "top2_score":         scores[1],
        "margin":             gaps[0],
        "min_gap":            min(gaps),
        "exact_ties":         [f"{order[i]}={order[i + 1]}" for i, g in enumerate(gaps) if g == 0],
        "near_ties":          [f"{order[i]}~{order[i + 1]}" for i, g in enumerate(gaps) if g < NEAR_TIE],
        "top1_changed":       order[0] != ref_order[0],
        "top3_order_changed": order[:3] != ref_order[:3],
        "top3_set_changed":   set(order[:3]) != set(ref_order[:3]),
        "order_changed":      order != ref_order,
        "kendall_tau":        kendall_tau(order, ref_order),
        "retry_set":          order[:MAX_ATTEMPTS],
    }


def scores_by_id(entry: dict) -> dict:
    return {c["id"]: c["score"] for c in entry["ranking"]}


def friction_domain_check(spec: dict, repo_domains: dict, maxima=(2.0, 1.0, 0.6)) -> list[dict]:
    """
    D0 and D2 with other upper bounds of the friction domain. The region of the inverted predicate of
    D2 reaches the upper bound, so its Jaccard with C1 (<= 0.4) depends on that bound.
    """
    rows = []
    for maximum in maxima:
        domains = {**repo_domains, "lateral_friction": {**repo_domains["lateral_friction"], "max_value": maximum}}
        adapter = make_adapter(domains)
        for diagnosis in spec["diagnoses"]:
            if diagnosis["id"] not in ("D0", "D2"):
                continue
            entry = run_diagnosis(adapter, spec, diagnosis)
            c1 = next(c for c in entry["ranking"] if c["id"] == "C1")
            friction = next(j for j in c1["clauses"]["given"]["jaccard"] if j["parameter"] == "lateral_friction")
            scores = scores_by_id(entry)
            rows.append({"friction_max": maximum, "diagnosis": diagnosis["id"],
                         "jaccard_friction_C1": friction["jaccard"], "C1": scores["C1"], "C2": scores["C2"],
                         "top1": entry["ranking"][0]["id"]})
    return rows


# ── Integration replay ───────────────────────────────────────────────────────

def adapter_for_run(run_dir: Path) -> SimilarityBasedAdapter:
    """Production adapter with the catalogue and weights the run copied into its inputs."""
    inputs = run_dir / "inputs" / "dejavu"
    catalogue = json.loads((inputs / "arm" / "scenario_catalogue.json").read_text(encoding="utf-8"))
    adapter = SimilarityBasedAdapter()
    adapter.monitored_parameters_dict = catalogue.get("monitored_parameters", {})
    adapter.candidates = list(catalogue.get("scenarios", {}).values())
    adapter.weight_configs_dict = yaml.safe_load((inputs / "weights_config.yaml").read_text(encoding="utf-8"))
    return adapter


def replay_recorded_rankings() -> list[dict]:
    rows = []
    for pattern in REPLAY_GLOBS:
        for events_path in sorted(ROOT.glob(pattern)):
            run_dir = events_path.parents[2]
            adapter = adapter_for_run(run_dir)
            diagnosis = None
            for line in events_path.read_text(encoding="utf-8").splitlines():
                event = json.loads(line)
                if event["event"] == "diagnosis":
                    diagnosis = event
                elif event["event"] == "ranking" and diagnosis is not None:
                    replayed = retrieve(adapter, {"name": "replay", "given": diagnosis["given"],
                                                  "when": diagnosis["when"], "do": "TBD",
                                                  "then": diagnosis["then"]})
                    recorded = event["ranking"]
                    recorded_names = [r["candidate"] for r in recorded]
                    replayed_names = [r["candidate"]["name"] for r in replayed]
                    same = recorded_names == replayed_names
                    rows.append({
                        "run":              str(run_dir.relative_to(ROOT)).replace("\\", "/"),
                        "episode":          event["episode"],
                        "step":             event["step"],
                        "active_scenario":  event["active_scenario"],
                        "given":            diagnosis["given"],
                        "recorded_ranking": " > ".join(recorded_names),
                        "same_order":       same,
                        "max_abs_score_diff": (max(abs(r["score"] - s["similarity_result"])
                                                   for r, s in zip(recorded, replayed)) if same else None),
                    })
                    diagnosis = None
    return rows


# ── Output ───────────────────────────────────────────────────────────────────

def write_csv(name: str, rows: list[dict]) -> None:
    OUTPUT.mkdir(exist_ok=True)
    with open(OUTPUT / name, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def results_rows(battery: list[dict]) -> list[dict]:
    reference = {c["id"]: c for c in battery[0]["ranking"]}
    rows = []
    for entry in battery:
        d = entry["diagnosis"]
        for c in sorted(entry["ranking"], key=lambda c: c["id"]):
            g, w, t = (c["clauses"][k] for k in CLAUSES)
            rows.append({
                "diagnosis": d["id"], "group": d["group"], "label": d["label"],
                "given": entry["diagnosed"]["given"],
                "candidate": c["id"], "candidate_name": c["name"], "do": c["do"],
                "rank": c["rank"], "score": c["score"],
                "score_delta_vs_D0": c["score"] - reference[c["id"]]["score"],
                "rank_delta_vs_D0": c["rank"] - reference[c["id"]]["rank"],
                "given_similarity": g["similarity"], "given_param_avg": g["param_avg"],
                "given_penalty": g["penalty"], "given_shared": " ".join(g["shared"]),
                "given_diagnosis_only": " ".join(g["diagnosis_only"]),
                "given_candidate_only": " ".join(g["candidate_only"]),
                "when_similarity": w["similarity"],
                "then_similarity": t["similarity"], "then_param_avg": t["param_avg"],
                "then_penalty": t["penalty"], "then_shared": " ".join(t["shared"]),
                "then_diagnosis_only": " ".join(t["diagnosis_only"]),
                "then_candidate_only": " ".join(t["candidate_only"]),
            })
    return rows


def jaccard_rows(battery: list[dict]) -> list[dict]:
    rows = []
    for entry in battery:
        for c in sorted(entry["ranking"], key=lambda c: c["id"]):
            for clause in CLAUSES:
                for j in c["clauses"][clause]["jaccard"]:
                    rows.append({"diagnosis": entry["diagnosis"]["id"], "candidate": c["id"],
                                 "clause": clause, **j})
    return rows


def ranking_rows(battery: list[dict], sensitivity: list[dict], exploratory: dict) -> list[dict]:
    rows = []
    for entry, alt in zip(battery, sensitivity):
        d = entry["diagnosis"]
        m = ranking_metrics(entry, battery[0])
        alt_top3 = [c["id"] for c in alt["ranking"]][:3]
        rows.append({
            "diagnosis": d["id"], "group": d["group"], "label": d["label"],
            "given": entry["diagnosed"]["given"],
            "ranking": " > ".join(m["order"]), "top1": m["top1"], "top3": " ".join(m["top3"]),
            "recommended_do": entry["recommended"]["do"],
            "top1_score": m["top1_score"], "top2_score": m["top2_score"],
            "margin_top1_top2": m["margin"], "min_adjacent_gap": m["min_gap"],
            "exact_ties": " ".join(m["exact_ties"]), "near_ties": " ".join(m["near_ties"]),
            "top1_changed": m["top1_changed"], "top3_order_changed": m["top3_order_changed"],
            "top3_set_changed": m["top3_set_changed"], "order_changed": m["order_changed"],
            "kendall_tau_vs_D0": m["kendall_tau"], "retry_set": " ".join(m["retry_set"]),
            "top3_exploratory": " ".join(exploratory["top3"][d["id"]]),
            "top3_matches_exploratory": m["top3"] == exploratory["top3"][d["id"]],
            "top3_spec_domains": " ".join(alt_top3),
        })
    return rows


def comparison_rows(battery: list[dict], sensitivity: list[dict], exploratory: dict) -> list[dict]:
    rows = []
    for entry, alt in zip(battery, sensitivity):
        real, alt_scores = scores_by_id(entry), scores_by_id(alt)
        for cid in sorted(real):
            ref = exploratory["scores"][entry["diagnosis"]["id"]][cid]
            rows.append({
                "diagnosis": entry["diagnosis"]["id"], "candidate": cid,
                "real": real[cid], "exploratory": ref, "diff": real[cid] - ref,
                "matches_4dp": round(real[cid], 4) == ref,
                "spec_domains": alt_scores[cid], "spec_domains_diff": alt_scores[cid] - ref,
                "spec_domains_matches_4dp": round(alt_scores[cid], 4) == ref,
            })
    return rows


def domain_rows(spec: dict, battery: list[dict], repo_domains: dict, exploratory: dict) -> list[dict]:
    used_by_diagnoses, used_by_candidates = set(), set()
    for entry in battery:
        for k in CLAUSES:
            used_by_diagnoses |= set(_extract_parameters(entry["diagnosed"][k]))
        for c in entry["ranking"]:
            for k in CLAUSES:
                used_by_candidates |= set(c["clauses"][k]["shared"]) | set(c["clauses"][k]["candidate_only"])
    rows = []
    for name in sorted(used_by_diagnoses | used_by_candidates):
        repo, expl = repo_domains.get(name), exploratory["domains"].get(name)
        fmt = (lambda d: f"{d['type']} [{d['min_value']:g}, {d['max_value']:g}]" if d else "absent")
        rows.append({
            "parameter": name,
            "in_diagnoses": name in used_by_diagnoses,
            "in_candidates": name in used_by_candidates,
            "repository": fmt(repo),
            "exploratory": fmt(expl),
            "differs": fmt(repo) != fmt(expl),
        })
    return rows


def fmt4(x: float) -> str:
    return f"{x:.4f}"


def summary_markdown(spec, battery, rankings, comparison, domains, replay, friction) -> str:
    ids = list(spec["candidates"])
    lines = ["# RQ2 — summary generated by run_rq2.py", "",
             "Generated from the production Retriever; do not edit by hand. Interpretation: `../analysis.md`.", ""]

    lines += ["## Similarity per diagnosis", "",
              "| D | Group | Change | " + " | ".join(ids) + " | Top-3 | Margin Top-1/Top-2 |",
              "|---|---|---|" + "---:|" * len(ids) + "---|---:|"]
    for entry, r in zip(battery, rankings):
        s = scores_by_id(entry)
        cells = [f"**{fmt4(s[c])}**" if c == r["top1"] else fmt4(s[c]) for c in ids]
        lines.append(f"| {r['diagnosis']} | {r['group']} | {r['label']} | " + " | ".join(cells)
                     + f" | {r['top3']} | {r['margin_top1_top2']:.4f} |")

    lines += ["", "## Given similarity (S_Given) per diagnosis", "",
              "When and Then do not change in the battery, so every score is (S_Given + S_When + S_Then) / 3 "
              "with S_When and S_Then fixed per candidate (next table).", "",
              "| D | " + " | ".join(ids) + " |", "|---|" + "---:|" * len(ids)]
    for entry in battery:
        g = {c["id"]: c["clauses"]["given"] for c in entry["ranking"]}
        lines.append(f"| {entry['diagnosis']['id']} | "
                     + " | ".join(f"{g[c]['similarity']:.4f} ({g[c]['param_avg']:.4f} − {g[c]['penalty']:.4f})"
                                  for c in ids) + " |")
    lines += ["", "Cell: S_Given (S_param − P_Given).", ""]

    lines += ["## When and Then per candidate (fixed in the battery)", "",
              "| Candidate | S_When | S_Then | S_param(Then) | P_Then | Then: shared / D only / C only |",
              "|---|---:|---:|---:|---:|---|"]
    fixed = {}
    for c in sorted(battery[0]["ranking"], key=lambda c: c["id"]):
        w, t = c["clauses"]["when"], c["clauses"]["then"]
        for entry in battery:  # same value in every diagnosis
            other = next(x for x in entry["ranking"] if x["id"] == c["id"])["clauses"]
            if other["when"]["similarity"] != w["similarity"] or other["then"]["similarity"] != t["similarity"]:
                raise AssertionError(f"When/Then similarity of {c['id']} varies in the battery")
        fixed[c["id"]] = w["similarity"] + t["similarity"]
        lines.append(f"| {c['id']} | {w['similarity']:.4f} | {t['similarity']:.6f} | {t['param_avg']:.6f} | "
                     f"{t['penalty']:.6f} | {' '.join(t['shared'])} / {' '.join(t['diagnosis_only']) or '—'} / "
                     f"{' '.join(t['candidate_only']) or '—'} |")
    lines += ["", "Ci ranks above Cj when S_Given(Ci) − S_Given(Cj) > [S_When + S_Then](Cj) − [S_When + S_Then](Ci). "
              "Required Given advantage of the row over the column:", "",
              "| | " + " | ".join(ids) + " |", "|---|" + "---:|" * len(ids)]
    for a in ids:
        lines.append(f"| {a} | " + " | ".join("—" if a == b else f"{fixed[b] - fixed[a]:+.4f}" for b in ids) + " |")

    n = len(rankings) - 1
    count = lambda key: sum(bool(r[key]) for r in rankings[1:])  # noqa: E731
    lines += ["", "## Ranking changes relative to D0", "",
              f"- Top-1 changed: {count('top1_changed')} of {n}",
              f"- Top-3 order changed: {count('top3_order_changed')} of {n}",
              f"- Top-3 composition changed: {count('top3_set_changed')} of {n}",
              f"- Full order changed: {count('order_changed')} of {n}",
              f"- Exact ties between adjacent candidates: {sum(bool(r['exact_ties']) for r in rankings)}",
              f"- Near ties (< {NEAR_TIE:g}): {sum(bool(r['near_ties']) for r in rankings)}",
              f"- Smallest Top-1/Top-2 margin: {min(r['margin_top1_top2'] for r in rankings):.6f} "
              f"({min(rankings, key=lambda r: r['margin_top1_top2'])['diagnosis']})",
              f"- Smallest gap between any adjacent pair: {min(r['min_adjacent_gap'] for r in rankings):.6f} "
              f"({min(rankings, key=lambda r: r['min_adjacent_gap'])['diagnosis']})", ""]

    matches = sum(r["matches_4dp"] for r in comparison)
    alt_matches = sum(r["spec_domains_matches_4dp"] for r in comparison)
    top3 = sum(r["top3_matches_exploratory"] for r in rankings)
    lines += ["## Comparison with the independent reproduction", "",
              f"- Scores equal at 4 decimals: {matches} of {len(comparison)}",
              f"- Top-3 equal: {top3} of {len(rankings)}",
              f"- With the reproduction's domains (sensitivity run): {alt_matches} of {len(comparison)} scores equal "
              f"at 4 decimals; Top-3 equal in "
              f"{sum(r['top3_spec_domains'] == r['top3_exploratory'] for r in rankings)} of {len(rankings)}", "",
              "| D | C | Production | Reproduction | Difference | With the reproduction's domains |",
              "|---|---|---:|---:|---:|---:|"]
    for r in comparison:
        if not r["matches_4dp"]:
            lines.append(f"| {r['diagnosis']} | {r['candidate']} | {r['real']:.6f} | {r['exploratory']:.4f} | "
                         f"{r['diff']:+.6f} | {r['spec_domains']:.6f} |")

    lines += ["", "## Domains of the parameters in the battery", "",
              "| Parameter | In diagnoses | In candidates | Repository (used) | Reproduction | Differs |",
              "|---|---|---|---|---|---|"]
    for r in domains:
        lines.append(f"| {r['parameter']} | {'yes' if r['in_diagnoses'] else 'no'} | "
                     f"{'yes' if r['in_candidates'] else 'no'} | {r['repository']} | {r['exploratory']} | "
                     f"{'**yes**' if r['differs'] else 'no'} |")

    lines += ["", "## Friction domain and the inverted operator (D2)", "",
              "Same production code with other upper bounds of `lateral_friction` (the catalogue uses 2.0).", "",
              "| Friction domain | D | J(friction) with C1 | C1 | C2 | Top-1 |", "|---|---|---:|---:|---:|---|"]
    for r in friction:
        lines.append(f"| [0, {r['friction_max']:g}] | {r['diagnosis']} | {r['jaccard_friction_C1']:.5f} | "
                     f"{r['C1']:.4f} | {r['C2']:.4f} | {r['top1']} |")

    lines += ["", "## Integration replay", ""]
    if replay:
        same = sum(r["same_order"] for r in replay)
        diff = max((r["max_abs_score_diff"] for r in replay if r["same_order"]), default=0.0)
        runs = len({r["run"] for r in replay})
        lines += [f"Rankings recorded by DejaVu during the RQ1.1 and RQ1.2 runs, recomputed with the catalogue and "
                  f"weights of each run: {same} of {len(replay)} rankings ({runs} runs) in the same order; largest "
                  f"score difference {diff:.3g}."]
    else:
        lines += ["No recorded run found (the results/ folders are not versioned)."]
    return "\n".join(lines) + "\n"


def main() -> None:
    spec = load_json("diagnoses.json")
    exploratory = load_json("exploratory_reference.json")

    adapter = make_adapter()
    battery = run_battery(spec, adapter)

    # Domain sensitivity: same production code, domains of the independent reproduction
    spec_domains = {**adapter.monitored_parameters_dict, **exploratory["domains"]}
    sensitivity = run_battery(spec, make_adapter(spec_domains))

    friction = friction_domain_check(spec, adapter.monitored_parameters_dict)
    replay = replay_recorded_rankings()

    rankings = ranking_rows(battery, sensitivity, exploratory)
    comparison = comparison_rows(battery, sensitivity, exploratory)
    domains = domain_rows(spec, battery, adapter.monitored_parameters_dict, exploratory)

    write_csv("results.csv", results_rows(battery))
    write_csv("rankings.csv", rankings)
    write_csv("jaccard.csv", jaccard_rows(battery))
    write_csv("comparison.csv", comparison)
    write_csv("domains.csv", domains)
    write_csv("friction_domain_check.csv", friction)
    if replay:
        write_csv("integration_replay.csv", replay)
    summary = summary_markdown(spec, battery, rankings, comparison, domains, replay, friction)
    (OUTPUT / "summary.md").write_text(summary, encoding="utf-8")

    reference_ok = [{"candidate": c["name"], "score": c["score"]} for c in battery[0]["ranking"]] \
        == spec["reference"]["recorded_ranking"]
    print(f"D0 reproduces the ranking recorded in RQ1.2 (mu = 0.140): {reference_ok}")
    print(f"Top-1 changed in {sum(r['top1_changed'] for r in rankings)} of {len(rankings) - 1}; "
          f"Top-3 order in {sum(r['top3_order_changed'] for r in rankings)}; "
          f"Top-3 composition in {sum(r['top3_set_changed'] for r in rankings)}; "
          f"exact ties: {sum(bool(r['exact_ties']) for r in rankings)}")
    print(f"Scores equal to the reproduction at 4 decimals: {sum(r['matches_4dp'] for r in comparison)} of "
          f"{len(comparison)} (with its domains: {sum(r['spec_domains_matches_4dp'] for r in comparison)})")
    if replay:
        print(f"Replay: {sum(r['same_order'] for r in replay)} of {len(replay)} recorded rankings in the same order")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()
