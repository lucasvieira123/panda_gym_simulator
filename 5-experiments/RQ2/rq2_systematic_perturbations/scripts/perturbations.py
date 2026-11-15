"""
Battery B of RQ2: systematic perturbations of D0's Given clause.

Shared definitions for the exploration, the selected battery and the figure:

- the reference (D0 of Battery A, read from ../../diagnoses.json) and the production Retriever (run_rq2.py);
- the perturbation operators of the four categories (A addition, B omission, C relational operator,
  D threshold) and their characterisation: parameter class in the catalogue, DejaVu component the Given
  predicate comes from, intensity, direction, validity and plausibility;
- the selection of Battery B, declared in SELECTION.

Nothing in this module reads a similarity score. The selection is a function of the design attributes
only, and the exploration script fixes it before it computes any score.

Intensity of a change to an existing predicate is the Jaccard distance between the original and the
modified admissible region, 1 - Jaccard, computed with the Retriever's own `_calculate_jaccard_similarity`
over the catalogue domains, so that it measures the change exactly as the metric sees it. Intensity of an
addition or omission is the number of parameters added or removed.
"""
from __future__ import annotations

import json
import math
import sys
from itertools import combinations
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
BATTERY = SCRIPTS.parent
RQ2 = BATTERY.parent
sys.path.insert(0, str(RQ2))

import run_rq2 as rq2  # noqa: E402  (puts 3-dejavu/src on sys.path: the production Retriever)
from similarity.dejavu_similarity import (  # noqa: E402
    _calculate_jaccard_similarity,
    _decompose_relational_expression,
    _extract_parameters,
    _get_relational_expression_region,
)
from similarity.when_filter import filter_candidates_by_when  # noqa: E402

EXPLORATION = BATTERY / "exploration"
OUTPUT = BATTERY / "output"
FIGURES = BATTERY / "figures"

# D0 as the prompt states it; checked against Battery A's diagnoses.json
REFERENCE_GIVEN = ["object_lift_height_cm < 10", "finger_contacts < 2", "lateral_friction <= 0.1425"]
REFERENCE_WHEN = "grasp_completed == 1"
REFERENCE_THEN = "object_lift_height_cm >= 10 AND finger_contacts >= 2"

THRESHOLD_TARGETS = (0.25, 0.50, 0.75)   # Jaccard distances explored for the threshold modifications
OPERATORS = ("<", "<=", ">", ">=", "==", "!=")

# Category A: conditions absent from D0. For a parameter some candidate represents, the predicate is that
# candidate's predicate, so the addition isolates the structural effect (presence of the parameter) from
# region overlap, which Categories C and D study. For parameters no applicable candidate represents, the
# predicate only needs to be plausible: it is never paired, so its value cannot change any score.
ADDITIONS = [
    ("object_shape_irregular == 1",          "the object has an irregular shape"),
    ("grasp_alignment_error_cm > 1",         "the gripper is misaligned with the object by more than 1 cm"),
    ("underwater_current_speed_cm_s > 15",   "a water current faster than 15 cm/s acts on the object"),
    ("planned_lift_acceleration_m_s2 > 2",   "the planned lift acceleration exceeds 2 m/s2"),
    ("payload_swing_risk == 1",              "the payload is at risk of swinging"),
    ("objects_object_1_mass > 0.5",          "the object is heavier than 0.5 kg"),
    ("grasp_attempts > 1",                   "the grasp needed more than one attempt"),
    ("grip_pressure < 40",                   "the grip pressure is below 40"),
]
IMPLAUSIBLE = {  # parameter -> reason, for the robotic-arm exemplar (tabletop pick-and-place, in air)
    "underwater_current_speed_cm_s": "implausible in the exemplar: the arm does not operate under water",
}
# Multiple additions of one parameter class (intensity = number of conditions added)
MULTIPLE_ADDITIONS = [
    ["planned_lift_acceleration_m_s2 > 2", "payload_swing_risk == 1"],
    ["objects_object_1_mass > 0.5", "grasp_attempts > 1"],
    ["objects_object_1_mass > 0.5", "grasp_attempts > 1", "grip_pressure < 40"],
]


# ── Reference and catalogue ──────────────────────────────────────────────────

def load_spec_a() -> dict:
    return json.loads((RQ2 / "diagnoses.json").read_text(encoding="utf-8"))


SPEC_A = load_spec_a()
ADAPTER = rq2.make_adapter()
DOMAINS = ADAPTER.monitored_parameters_dict
CANDIDATE_IDS = dict(SPEC_A["candidates"])               # C1 -> name
CANDIDATE_BY_NAME = {name: cid for cid, name in CANDIDATE_IDS.items()}


def spec_b() -> dict:
    """The spec run_rq2.run_diagnosis expects: D0 of Battery A as B0, and the five lift candidates."""
    reference = dict(SPEC_A["reference"], id="B0")
    if (reference["given"] != REFERENCE_GIVEN or reference["when"] != REFERENCE_WHEN
            or reference["then"] != REFERENCE_THEN):
        raise SystemExit("D0 in ../../diagnoses.json differs from the reference of Battery B")
    return {"reference": reference, "candidates": CANDIDATE_IDS}


def applicable_candidates() -> dict:
    """Candidates that pass the When filter for D0's When, by id: cid -> catalogue entry."""
    applicable, _ = filter_candidates_by_when(REFERENCE_WHEN, ADAPTER.candidates)
    found = {CANDIDATE_BY_NAME[c["name"]]: c for c in applicable}
    if sorted(found) != sorted(CANDIDATE_IDS):
        raise SystemExit(f"When filter kept {sorted(found)}, expected C1-C5")
    return found


APPLICABLE = applicable_candidates()
CANDIDATE_PARAMS = {cid: set(_extract_parameters(c["given"])) for cid, c in APPLICABLE.items()}
CATALOGUE_PARAMS = set().union(*(_extract_parameters(c["given"]) for c in ADAPTER.candidates))
CANDIDATE_PREDICATES = {cid: [p.strip() for p in c["given"].split(" AND ")] for cid, c in APPLICABLE.items()}


def parameter_class(parameter: str) -> str:
    holders = [cid for cid in sorted(CANDIDATE_PARAMS) if parameter in CANDIDATE_PARAMS[cid]]
    if len(holders) == len(CANDIDATE_PARAMS):
        return "shared by all candidates"
    if len(holders) == 1:
        return f"specific to {holders[0]}"
    if holders:
        return "shared by " + ", ".join(holders)
    if parameter in CATALOGUE_PARAMS:
        return "absent from the applicable candidates (only in candidates the When filter excludes)"
    return "absent from the catalogue"


def source_component(parameter: str) -> str:
    """Which DejaVu component writes this parameter into the Given."""
    then_params = set(_extract_parameters(REFERENCE_THEN))
    if parameter in then_params:
        return "Identifier (negated violated Then)"
    return "Diagnoser (decision-tree path)"


# ── Regions, intensity, direction and validity ───────────────────────────────

def region(predicate: str):
    variable, operator, value = _decompose_relational_expression(predicate)
    info = DOMAINS[variable]
    return _get_relational_expression_region(
        variable, operator, value, info["min_value"], info["max_value"], info["type"])


def jaccard(p1: str, p2: str) -> float:
    return _calculate_jaccard_similarity(p1, p2, DOMAINS)


def integer_set(predicate: str) -> set[int]:
    variable, _, _ = _decompose_relational_expression(predicate)
    info = DOMAINS[variable]
    parts = region(predicate)
    parts = parts if isinstance(parts, list) else [parts]
    values = set()
    for lo, hi in parts:
        values |= set(range(max(math.ceil(lo), info["min_value"]), min(math.floor(hi), info["max_value"]) + 1))
    return values


def direction(original: str, modified: str) -> str:
    j = jaccard(original, modified)
    r_o, r_m = region(original), region(modified)
    if isinstance(r_o, list) or isinstance(r_m, list):
        return "split region"
    if j == 1.0:
        return "equivalent under the metric"
    if j == 0.0:
        return "disjoint"
    if r_o[0] <= r_m[0] and r_m[1] <= r_o[1]:
        return "restrictive"
    if r_m[0] <= r_o[0] and r_o[1] <= r_m[1]:
        return "permissive"
    return "shifted"


# Then clause that each Identifier-written predicate negates (the violation it represents)
THEN_PREDICATES = {p.split()[0]: p for p in (q.strip() for q in REFERENCE_THEN.split(" AND "))}


def _observed_state() -> dict:
    """State observed when D0's violation was detected (run 15_0_140 of RQ1.2, copied in ../inputs/d0_source)."""
    for path in sorted((RQ2 / "inputs" / "d0_source").glob("events_*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if record["event"] == "violation":
                return record["observed"]
    raise SystemExit("no violation event in ../inputs/d0_source")


OBSERVED = _observed_state()
# Values the managed system can produce, where narrower than the catalogue domain
APPLICATION_RANGES = {
    "finger_contacts": ({0, 1, 2}, "the two-finger gripper sensor reports 0, 1 or 2 contacts "
                                   "(2-managing/src/sensors/finger_contact_sensor.py); the catalogue declares 0-5"),
}


def admits(predicate: str, value: float) -> bool:
    parts = region(predicate)
    return any(lo <= value <= hi for lo, hi in (parts if isinstance(parts, list) else [parts]))


def assess_predicate(predicate: str) -> dict:
    """One predicate of a perturbed Given, judged against the violation it represents and the observation.

    - logical: is the predicate satisfiable in the catalogue domain?
    - observation: does it admit the value observed at the violation (when one was recorded)?
    - violation relation (Identifier predicates only): compared with the violation of the Then clause it
      negates, does it admit the same states, fewer, also non-violating ones, or no violating state at all?
    - feasibility: does it admit any value the managed system can produce?
    - metric: can the Retriever's Jaccard measure it as the specification intends?
    - origin: could the component that writes this predicate produce it as an inaccuracy?
    """
    variable, operator, _ = _decompose_relational_expression(predicate)
    info = DOMAINS[variable]
    reg = region(predicate)
    parts = reg if isinstance(reg, list) else [reg]
    satisfiable = (bool(integer_set(predicate)) if info["type"] == "int"
                   else operator == "==" or any(hi > lo for lo, hi in parts))
    observed = OBSERVED.get(variable)
    admits_observed = None if observed is None else admits(predicate, observed)
    origin = source_component(variable)

    relation = ""
    if variable in THEN_PREDICATES:
        holds = integer_set(THEN_PREDICATES[variable])
        violating = set(range(info["min_value"], info["max_value"] + 1)) - holds
        admitted = integer_set(predicate)
        relation = ("denies the violation it represents (admits no state violating "
                    f"'{THEN_PREDICATES[variable]}')" if not admitted & violating else
                    f"over-general (also admits states where '{THEN_PREDICATES[variable]}' holds)"
                    if admitted & holds else
                    "same states as the violation" if admitted == violating else "narrower than the violation")

    feasible = True
    if variable in APPLICATION_RANGES and info["type"] == "int":
        feasible = bool(integer_set(predicate) & APPLICATION_RANGES[variable][0])

    if info["type"] == "float" and operator == "==":
        metric = "not measurable: an equality on a continuous parameter is counted as length 1, Jaccard above 1"
    elif operator != "==" and not isinstance(reg, list) and reg[1] - reg[0] <= 0:
        metric = "not measurable: zero-length region in the Retriever's interval model (Jaccard 0 even with itself)"
    elif isinstance(reg, list):
        metric = "approximate: the Retriever measures the union of a split region by its hull"
    else:
        metric = "ok"

    if origin.startswith("Identifier") and admits_observed is False:
        plausibility = (f"implausible origin: the Identifier writes this predicate by negating "
                        f"'{THEN_PREDICATES[variable]}', a clause the observation violated "
                        f"({variable} = {observed:g}); the negation of a violated clause always admits the observed "
                        "value, so no Then clause, however imprecise, yields a predicate that excludes it")
    elif variable in IMPLAUSIBLE:
        plausibility = IMPLAUSIBLE[variable]
    else:
        plausibility = "plausible"

    notes = []
    if admits_observed is False:
        notes.append(f"excludes the observed value {variable} = {observed:g}"
                     + ("; possible as a Diagnoser inaccuracy if the value of the feature it used was wrong"
                        if origin.startswith("Diagnoser") else ""))
    if relation and not relation.startswith(("same", "narrower")):
        notes.append(relation)
    if not feasible:
        notes.append(f"infeasible in the application: {APPLICATION_RANGES[variable][1]}")
    if metric != "ok":
        notes.append(metric)
    if operator == "!=":
        notes.append("uninformative: '!=' admits every value but one")
    return {"predicate": predicate, "satisfiable": satisfiable, "admits_observed": admits_observed,
            "violation_relation": relation, "feasible": feasible, "metric": metric,
            "plausibility": plausibility, "uninformative": operator == "!=", "notes": notes}


def assess(given: list[str], changes: list[dict]) -> dict:
    """Assessment of a perturbed Given; only the predicates the perturbation writes are judged (the others are
    D0's own)."""
    if not given:
        return {"logical_status": "empty Given: no condition left to describe the failure",
                "observation_consistency": "", "violation_relation": "", "domain_feasibility": "",
                "metric_applicability": "", "origin_plausibility": "", "assessment_notes": [],
                "uninformative": False, "scored": False, "eligible": False}
    written = [c.get("with") or c.get("add") for c in changes if "with" in c or "add" in c]
    judged = [assess_predicate(p) for p in written]
    unsatisfiable = [j["predicate"] for j in judged if not j["satisfiable"]]
    inconsistent = [j for j in judged if j["admits_observed"] is False]
    metric = [j["metric"] for j in judged if j["metric"] != "ok"]
    implausible = [j["plausibility"] for j in judged if j["plausibility"] != "plausible"]
    infeasible = [j for j in judged if not j["feasible"]]
    removed = [c["remove"] for c in changes if "remove" in c]
    notes = [f"'{j['predicate']}': {n}" for j in judged for n in j["notes"]]
    notes += [f"omits '{p}' (" + (f"the violation of '{THEN_PREDICATES[p.split()[0]]}'" if p.split()[0] in
              THEN_PREDICATES else "a diagnosed condition") + ")" for p in removed]
    return {
        "logical_status": "satisfiable" if not unsatisfiable else "unsatisfiable: " + ", ".join(unsatisfiable),
        "observation_consistency": ("consistent" if not inconsistent else
                                    "inconsistent: " + "; ".join(f"excludes {j['predicate'].split()[0]} = "
                                                                 f"{OBSERVED[j['predicate'].split()[0]]:g}"
                                                                 for j in inconsistent)),
        "violation_relation": "; ".join(f"'{j['predicate']}': {j['violation_relation']}" for j in judged
                                        if j["violation_relation"]),
        "domain_feasibility": "feasible" if not infeasible else "infeasible in the application",
        "metric_applicability": "ok" if not metric else "; ".join(metric),
        "origin_plausibility": "plausible" if not implausible else "; ".join(implausible),
        "assessment_notes": notes,
        "uninformative": any(j["uninformative"] for j in judged),
        "scored": not unsatisfiable and not any(m.startswith("not measurable: an equality") for m in metric),
        "eligible": (not unsatisfiable and not infeasible and not implausible and not metric
                     and not any(j["uninformative"] for j in judged)),
    }


def coincides_with_candidate(predicate: str) -> str:
    norm = " ".join(predicate.split())
    return " ".join(cid for cid in sorted(CANDIDATE_PREDICATES)
                    if norm in (" ".join(p.split()) for p in CANDIDATE_PREDICATES[cid]))


# ── Perturbations ────────────────────────────────────────────────────────────

def _threshold_value(original: str, target: float, side: str) -> tuple[str, float] | None:
    """Threshold whose Jaccard distance to the original region is closest to target.

    Float parameters: the exact value for the target, rounded to 4 decimals. Integer parameters: every
    integer threshold is tried; ties go to the less extreme change (the threshold closer to the original).
    """
    variable, operator, value = _decompose_relational_expression(original)
    info = DOMAINS[variable]
    if info["type"] == "float":
        v = float(value)
        lo = info["min_value"]
        length = v - lo
        new = lo + (length * (1 - target) if side == "restrictive" else length / (1 - target))
        if not (info["min_value"] < new < info["max_value"]):
            return None
        new = round(new, 4)
        candidates = [f"{variable} {operator} {new:g}"]
    else:
        v = int(value)
        rng = range(info["min_value"] + 1, v) if side == "restrictive" else range(v + 1, info["max_value"] + 2)
        candidates = [f"{variable} {operator} {t}" for t in rng]
    best = None
    for predicate in candidates:
        d = 1 - jaccard(original, predicate)
        t = float(_decompose_relational_expression(predicate)[2])
        key = (abs(d - target), abs(t - float(value)))
        if best is None or key < best[0]:
            best = (key, predicate, d)
    return best[1], best[2]


def individual_perturbations() -> list[dict]:
    """Every individual perturbation explored, in category order, before any score is known."""
    items: list[dict] = []

    for predicate, meaning in ADDITIONS:
        items.append({"key": f"add:{predicate}", "category": "A", "kind": "addition",
                      "changes": [{"add": predicate}], "intensity": 1, "intensity_measure": "parameters added",
                      "direction": "adds a condition", "modified": predicate, "original": "",
                      "rationale": f"adds '{predicate}' ({meaning})"})
    for predicates in MULTIPLE_ADDITIONS:
        items.append({"key": "add:" + " + ".join(predicates), "category": "A", "kind": "multiple addition",
                      "changes": [{"add": p} for p in predicates], "intensity": len(predicates),
                      "intensity_measure": "parameters added", "direction": "adds conditions",
                      "modified": " AND ".join(predicates), "original": "",
                      "rationale": f"adds {len(predicates)} conditions of the same parameter class"})

    for predicate in REFERENCE_GIVEN:
        items.append({"key": f"omit:{predicate.split()[0]}", "category": "B", "kind": "omission",
                      "changes": [{"remove": predicate}], "intensity": 1, "intensity_measure": "parameters removed",
                      "direction": "removes a condition", "original": predicate, "modified": "",
                      "rationale": f"omits '{predicate}'"})
    items.append({"key": "omit:all", "category": "B", "kind": "multiple omission",
                  "changes": [{"remove": p} for p in REFERENCE_GIVEN], "intensity": 3,
                  "intensity_measure": "parameters removed", "direction": "removes conditions",
                  "original": " AND ".join(REFERENCE_GIVEN), "modified": "", "rationale": "omits every condition"})

    for predicate in REFERENCE_GIVEN:
        variable, operator, value = _decompose_relational_expression(predicate)
        for op in OPERATORS:
            if op == operator:
                continue
            modified = f"{variable} {op} {value}"
            items.append({"key": f"op:{predicate} -> {modified}", "category": "C", "kind": "operator",
                          "changes": [{"replace": predicate, "with": modified}],
                          "intensity": 1 - jaccard(predicate, modified), "intensity_measure": "Jaccard distance",
                          "direction": direction(predicate, modified), "original": predicate, "modified": modified,
                          "rationale": f"changes the operator '{operator}' to '{op}'"})
        if DOMAINS[variable]["type"] == "int" and operator == "<":
            modified = f"{variable} <= {int(value) - 1}"   # same integer set, written differently
            items.append({"key": f"op:{predicate} -> {modified}", "category": "C", "kind": "equivalent rewrite",
                          "changes": [{"replace": predicate, "with": modified}],
                          "intensity": 1 - jaccard(predicate, modified), "intensity_measure": "Jaccard distance",
                          "direction": direction(predicate, modified), "original": predicate, "modified": modified,
                          "rationale": "control: other operator and constant, same admissible integers"})

    for predicate in REFERENCE_GIVEN:
        variable = predicate.split()[0]
        if variable == "finger_contacts":
            # Domain 0-5 with a region of length 1: every integer threshold is explored instead of targets
            for t in (1, 3, 4, 5, 6):
                modified = f"{variable} < {t}"
                items.append({"key": f"thr:{modified}", "category": "D", "kind": "threshold",
                              "changes": [{"replace": predicate, "with": modified}],
                              "intensity": 1 - jaccard(predicate, modified), "intensity_measure": "Jaccard distance",
                              "direction": direction(predicate, modified), "original": predicate,
                              "modified": modified, "target_distance": "",
                              "rationale": "integer threshold of finger_contacts"})
            continue
        for side in ("restrictive", "permissive"):
            for target in THRESHOLD_TARGETS:
                found = _threshold_value(predicate, target, side)
                if found is None:
                    continue
                modified, d = found
                items.append({"key": f"thr:{variable}:{side}:{target}", "category": "D", "kind": "threshold",
                              "changes": [{"replace": predicate, "with": modified}], "intensity": d,
                              "intensity_measure": "Jaccard distance", "direction": direction(predicate, modified),
                              "original": predicate, "modified": modified, "target_distance": target,
                              "rationale": f"{side} threshold, target Jaccard distance {target}"})
    return items


# ── Selection of Battery B (design attributes only) ──────────────────────────

# (B id, keys of the individual perturbations it applies to D0, justification)
SELECTION = [
    ("B1",  ["add:object_shape_irregular == 1"],
     "Addition of a parameter shared by two candidates (C3, C4)."),
    ("B2",  ["add:grasp_alignment_error_cm > 1"],
     "Addition of a parameter specific to one candidate (C3), whose Then is close to D0's."),
    ("B3",  ["add:planned_lift_acceleration_m_s2 > 2"],
     "Addition of a parameter specific to one candidate (C5), whose Then differs from D0's."),
    ("B4",  ["add:objects_object_1_mass > 0.5"],
     "Addition of a plausible parameter absent from every candidate: structural penalty without correspondence."),
    ("B5",  ["omit:lateral_friction"],
     "Omission of the only parameter that distinguishes a candidate (C1); written by the Diagnoser."),
    ("B6",  ["omit:finger_contacts"],
     "Omission of a parameter shared by all candidates; written by the Identifier."),
    ("B7",  ["omit:object_lift_height_cm"],
     "Omission of the other parameter shared by all candidates, to compare two shared omissions."),
    ("B8",  ["op:lateral_friction <= 0.1425 -> lateral_friction < 0.1425"],
     "Operator change of minimum intensity (boundary inclusion only)."),
    ("B9",  ["op:lateral_friction <= 0.1425 -> lateral_friction > 0.1425"],
     "Operator change of maximum intensity (complementary region). It excludes the observed friction (0.14), "
     "which a Diagnoser inaccuracy can produce; inversions of the Identifier's predicates cannot (addendum)."),
    ("B10", ["thr:lateral_friction:restrictive:0.25"], "Friction threshold, restrictive, low intensity."),
    ("B11", ["thr:lateral_friction:restrictive:0.75"], "Friction threshold, restrictive, high intensity."),
    ("B12", ["thr:lateral_friction:permissive:0.25"],  "Friction threshold, permissive, low intensity."),
    ("B13", ["thr:lateral_friction:permissive:0.75"],  "Friction threshold, permissive, high intensity."),
    ("B14", ["thr:object_lift_height_cm:restrictive:0.5"],
     "Height threshold, restrictive, intermediate intensity: a shared parameter, one intensity per direction."),
    ("B15", ["thr:object_lift_height_cm:permissive:0.5"],
     "Height threshold, permissive, intermediate intensity (opposite direction of B14, same target)."),
    ("B16", ["add:grasp_alignment_error_cm > 1", "add:planned_lift_acceleration_m_s2 > 2"],
     "Multiple additions related to different candidates (B2 + B3: C3 and C5)."),
    ("B17", ["omit:lateral_friction", "omit:finger_contacts"],
     "Multiple omissions, one distinguishing and one shared (B5 + B6)."),
    ("B18", ["omit:lateral_friction", "add:objects_object_1_mass > 0.5"],
     "Omission combined with addition: the distinguishing condition is replaced by an uninformative one "
     "(B5 + B4)."),
    ("B19", ["thr:lateral_friction:permissive:0.25", "add:object_shape_irregular == 1"],
     "Threshold change combined with addition: a region change on C1's parameter and a structural change "
     "towards C3 and C4 (B12 + B1)."),
]

# Why each explored perturbation not in SELECTION was left out, checked in order: whether it is a scenario at
# all, the origin and plausibility of the inaccuracy, feasibility, measurability, then design reasons
def exclusion_reason(item: dict, selected_keys: set[str]) -> str:
    key, kind = item["key"], item["kind"]
    if item["logical_status"] != "satisfiable":
        return "not a scenario: " + item["logical_status"]
    if item["origin_plausibility"] != "plausible":
        extra = "; also infeasible in the application" if item["domain_feasibility"] != "feasible" else ""
        return item["origin_plausibility"] + extra
    if item["domain_feasibility"] != "feasible":
        return "infeasible in the application"
    if item["metric_applicability"].startswith("not measurable"):
        return item["metric_applicability"]
    if item["uninformative"]:
        return ("uninformative: '!=' admits every value but one; "
                "the Retriever also measures its split region by the hull")
    if kind == "equivalent rewrite":
        return "control only: same admissible region as D0 (reported in the exploration)"
    if kind == "operator":
        if key.endswith(">= 0.1425"):
            return "redundant with B9: regions differ by one point, the same under the metric"
        return ("on an integer parameter, '<=' with the same constant is a threshold change by one unit; "
                "threshold changes are covered by Category D")
    if kind == "threshold" and key.startswith("thr:lateral_friction"):
        return "intermediate friction intensity: the battery keeps the low and high intensities in each direction"
    if kind == "threshold" and key.startswith("thr:object_lift_height_cm"):
        return "height keeps one intensity per direction (0.5); the others stay in the exploration"
    if kind == "threshold" and key.startswith("thr:finger_contacts"):
        return ("finger_contacts plays the same role as object_lift_height_cm (shared, from the Identifier) and "
                "its integer domain only allows permissive thresholds; height represents the shared thresholds")
    if kind == "addition":
        cls = parameter_class(item["parameters_added"][0])
        if cls.startswith("absent"):
            return (f"{cls}: no applicable candidate represents it, the same role as B4 "
                    "(one representative per class)")
        return f"{cls}, like a selected addition: one representative per class"
    if kind == "multiple addition":
        return "multiple additions of one class: the battery combines additions related to different candidates"
    if kind == "combined":
        return "pairwise combination not among the four pre-declared combinations"
    return "not selected"


def characterise(item: dict) -> dict:
    given = rq2.build_given(REFERENCE_GIVEN, item["changes"])
    added = [c["add"].split()[0] for c in item["changes"] if "add" in c]
    removed = [c["remove"].split()[0] for c in item["changes"] if "remove" in c]
    replaced = [c["replace"].split()[0] for c in item["changes"] if "replace" in c]
    assessment = assess(given, item["changes"])
    affected = added + removed + replaced
    return {
        **item,
        "given": given,
        "parameters_added": added,
        "parameters_removed": removed,
        "parameters_modified": replaced,
        "parameters_affected": len(affected),
        "parameter_class": "; ".join(f"{p}: {parameter_class(p)}" for p in affected),
        "source_component": "; ".join(sorted({source_component(p) for p in affected})),
        "coincides_with_candidate": " | ".join(
            f"{p}: {c}" for p in (q.strip() for q in item.get("modified", "").split(" AND ") if q.strip())
            for c in [coincides_with_candidate(p)] if c),
        **assessment,
    }


def exploration_set() -> tuple[list[dict], list[tuple[str, dict, str]]]:
    """(all explored perturbations, the selected battery as (B id, perturbation, justification)).

    Order: individual perturbations, the selection of the individual configurations, the pairwise
    combinations of the selected individual configurations, the selection of the combined ones. No score
    is read at any step.
    """
    individuals = [characterise(i) for i in individual_perturbations()]
    by_key = {i["key"]: i for i in individuals}
    selected_individual_keys = [keys[0] for _, keys, _ in SELECTION if len(keys) == 1]
    missing = [k for _, keys, _ in SELECTION for k in keys if k not in by_key]
    if missing:
        raise SystemExit(f"SELECTION refers to unknown perturbations: {missing}")

    combined = []
    for a, b in combinations(selected_individual_keys, 2):
        pa, pb = by_key[a], by_key[b]
        touched_a = set(pa["parameters_added"] + pa["parameters_removed"] + pa["parameters_modified"])
        touched_b = set(pb["parameters_added"] + pb["parameters_removed"] + pb["parameters_modified"])
        if touched_a & touched_b:
            continue  # two changes to the same parameter are not a combination of independent errors
        combined.append(characterise({
            "key": f"{a} & {b}", "category": f"{pa['category']}+{pb['category']}", "kind": "combined",
            "changes": pa["changes"] + pb["changes"], "components": [a, b], "intensity": 2,
            "intensity_measure": "individual changes combined", "direction": "combined",
            "original": "", "modified": "", "rationale": f"{a} combined with {b}"}))

    # Drop explored configurations whose Given repeats an earlier one (e.g. a combination of two additions
    # that is also a multiple addition)
    explored, seen = [], {}
    for item in individuals + combined:
        signature = frozenset(item["given"])
        if signature in seen and item["scored"]:
            item = {**item, "duplicate_of": seen[signature]}
        seen.setdefault(signature, item["key"])
        explored.append(item)

    category_prefix = {"A": "EA", "B": "EB", "C": "EC", "D": "ED"}
    counters: dict[str, int] = {}
    for item in explored:
        prefix = category_prefix.get(item["category"], "EK")
        counters[prefix] = counters.get(prefix, 0) + 1
        item["exploratory_id"] = f"{prefix}{counters[prefix]:02d}"

    by_components = {frozenset(i.get("components") or [i["key"]]): i for i in explored}
    battery = []
    for bid, keys, why in SELECTION:
        item = by_components.get(frozenset(keys))
        if item is None:
            raise SystemExit(f"{bid}: {' & '.join(keys)} is not an explored perturbation")
        if not item["eligible"]:
            raise SystemExit(f"{bid}: {item['key']} is not a satisfiable, plausible, feasible and measurable "
                             "perturbation")
        battery.append((bid, item, why))
    selected = {item["key"]: bid for bid, item, _ in battery}
    for item in explored:
        item["selected_as"] = selected.get(item["key"], "")
        item["exclusion_reason"] = ("" if item["selected_as"] else
                                    f"duplicate of {item['duplicate_of']}" if item.get("duplicate_of") else
                                    exclusion_reason(item, set(selected)))
    return explored, battery


def diagnosis_dict(bid: str, item: dict | None) -> dict:
    """A diagnosis in the format of run_rq2 (id, changes)."""
    return {"id": bid, "changes": [] if item is None else item["changes"]}
