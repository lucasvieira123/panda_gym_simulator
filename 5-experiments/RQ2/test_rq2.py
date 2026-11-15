"""
Properties of the RQ2 battery, checked against the production Retriever.

Usage, from the project root:
    .venv/Scripts/python.exe -m unittest discover -s 5-experiments/RQ2 -p "test_*.py"
"""
import csv
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_rq2 as rq2  # noqa: E402

LIFT = ["Suction-Assisted Lift Recovery", "Tactile Grip-Force Recovery", "Shape-Adaptive Grasp Recovery",
        "Conformal Grasp Stabilisation", "Dynamic-Load Lift Stabilisation"]
TRANSPORT = ["Transport Slip Recovery", "Transport Grip Pressure Recovery", "Motor Overload Transport Recovery"]
ALPHA, BETA = 0.9, 0.1


def split_given(expression: str) -> list[str]:
    return [p.strip().strip("()").strip() for p in expression.split(" AND ")]


class BatteryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = rq2.load_json("diagnoses.json")
        cls.exploratory = rq2.load_json("exploratory_reference.json")
        cls.adapter = rq2.make_adapter()
        cls.battery = rq2.run_battery(cls.spec, cls.adapter)
        cls.by_id = {e["diagnosis"]["id"]: e for e in cls.battery}

    def candidate(self, d: str, cid: str) -> dict:
        return next(c for c in self.by_id[d]["ranking"] if c["id"] == cid)

    def scores(self, d: str) -> dict:
        return rq2.scores_by_id(self.by_id[d])

    # ── Specification ────────────────────────────────────────────────────────

    def test_twenty_configurations(self):
        groups = [d["group"] for d in self.spec["diagnoses"]]
        self.assertEqual((groups.count("reference"), groups.count("isolated"), groups.count("combined")),
                         (1, 11, 8))
        self.assertEqual([d["id"] for d in self.spec["diagnoses"]], [f"D{i}" for i in range(20)])

    def test_each_diagnosis_changes_only_the_declared_given_predicates(self):
        reference = self.spec["reference"]
        for entry in self.battery:
            d, diagnosed = entry["diagnosis"], entry["diagnosed"]
            with self.subTest(d["id"]):
                self.assertEqual((diagnosed["when"], diagnosed["do"], diagnosed["then"]),
                                 (reference["when"], reference["do"], reference["then"]))
                removed = {c.get("replace") or c.get("remove") for c in d["changes"]} - {None}
                added = {c.get("with") or c.get("add") for c in d["changes"]} - {None}
                given = set(split_given(diagnosed["given"]))
                self.assertEqual(set(reference["given"]) - given, removed)   # nothing else removed,
                self.assertEqual(given - set(reference["given"]), added)     # nothing carried over

    def test_reference_is_the_diagnosis_recorded_in_rq1_2(self):
        """D0 comes from the copy of the run's events in inputs/d0_source (RQ1.2 results are not versioned)."""
        reference = self.spec["reference"]
        self.assertEqual(split_given(reference["recorded_given"]), reference["given"])
        events_name = Path(reference["source"]["events"]).name
        snapshot = HERE / "inputs" / "d0_source" / events_name
        original = rq2.ROOT / reference["source"]["run"] / reference["source"]["events"]
        if original.exists():
            self.assertEqual(snapshot.read_bytes(), original.read_bytes())
        diagnosis = next(json.loads(line) for line in snapshot.read_text(encoding="utf-8").splitlines()
                         if json.loads(line)["event"] == "diagnosis")
        self.assertEqual((diagnosis["active_scenario"], diagnosis["given"], diagnosis["when"], diagnosis["then"]),
                         ("LIFT_OBJECT", reference["recorded_given"], reference["when"], reference["then"]))

    def test_input_snapshot_is_what_the_production_retriever_reads(self):
        """inputs/dejavu_configs holds the catalogue and weights the battery ran with."""
        configs = HERE / "inputs" / "dejavu_configs"
        catalogue = json.loads((configs / "scenario_catalogue.json").read_text(encoding="utf-8"))
        weights = rq2.yaml.safe_load((configs / "weights_config.yaml").read_text(encoding="utf-8"))
        self.assertEqual(catalogue["monitored_parameters"], self.adapter.monitored_parameters_dict)
        self.assertEqual(list(catalogue["scenarios"].values()), self.adapter.candidates)
        self.assertEqual(weights, self.adapter.weight_configs_dict)

    # ── Production Retriever ─────────────────────────────────────────────────

    def test_reference_reproduces_the_ranking_recorded_in_rq1_2(self):
        produced = [{"candidate": c["name"], "score": c["score"]} for c in self.by_id["D0"]["ranking"]]
        self.assertEqual(produced, self.spec["reference"]["recorded_ranking"])

    def test_parentheses_of_the_recorded_given_do_not_change_the_scores(self):
        recorded = split_given(self.spec["reference"]["recorded_given"])
        diagnosed = rq2.diagnosed_scenario(self.spec, self.spec["diagnoses"][0])
        diagnosed["given"] = self.spec["reference"]["recorded_given"]
        replayed = rq2.retrieve(self.adapter, diagnosed)
        self.assertEqual(recorded, self.spec["reference"]["given"])
        self.assertEqual([r["similarity_result"] for r in replayed],
                         [c["score"] for c in self.by_id["D0"]["ranking"]])

    def test_when_filter_keeps_only_the_lift_candidates(self):
        for entry in self.battery:
            self.assertEqual(entry["when_filter"]["applicable"], LIFT)
            self.assertEqual(entry["when_filter"]["excluded"], TRANSPORT)

    def test_ranking_rule_is_the_one_in_dejavu(self):
        source = (rq2.ROOT / "3-dejavu" / "src" / "dejavu.py").read_text(encoding="utf-8")
        self.assertRegex(source, re.compile(
            r'similarities\.sort\(\s*key=lambda s: s\["similarity_result"\],\s*reverse=True,?\s*\)'))
        for entry in self.battery:
            self.assertEqual(entry["recommended"]["candidate_name"], entry["ranking"][0]["name"])

    def test_ties_keep_the_catalogue_order(self):
        twin = dict(self.adapter.candidates[1], name="Twin of C2")
        adapter = rq2.make_adapter()
        reference = rq2.diagnosed_scenario(self.spec, self.spec["diagnoses"][0])
        for order in ([twin, self.adapter.candidates[1]], [self.adapter.candidates[1], twin]):
            adapter.candidates = order
            ranked = rq2.retrieve(adapter, reference)
            self.assertEqual(ranked[0]["similarity_result"], ranked[1]["similarity_result"])
            self.assertEqual([r["candidate"]["name"] for r in ranked], [c["name"] for c in order])

    # ── Equations (values derived by hand from the formulas) ─────────────────

    def test_d0_c1(self):
        c1 = self.candidate("D0", "C1")["clauses"]
        given = (1 + 1 + 0.1425 / 0.4) / 3                     # height, contacts, friction; no penalty
        then = 1 - (1 - 2 / (2 + BETA * 1))                     # object_secured only in C1
        self.assertAlmostEqual(c1["given"]["similarity"], given, places=12)
        self.assertEqual(c1["when"]["similarity"], 1.0)
        self.assertAlmostEqual(c1["then"]["similarity"], then, places=12)
        self.assertAlmostEqual(self.scores("D0")["C1"], (given + 1 + then) / 3, places=12)

    def test_d0_c2(self):
        given = 1 - (1 - 2 / (2 + ALPHA * 1))                   # friction only in D0
        self.assertAlmostEqual(self.scores("D0")["C2"], (given + 1 + 1) / 3, places=12)

    def test_d3_c2_is_a_perfect_match(self):
        self.assertEqual(self.scores("D3")["C2"], 1.0)

    def test_d16_c5_ranks_above_c1(self):
        c5 = (4 / (4 + ALPHA) + 1 + (round(80 / 90, 5) - 0.5)) / 3   # production rounds each Jaccard to 5 places
        self.assertAlmostEqual(self.scores("D16")["C5"], c5, places=12)
        self.assertEqual(self.by_id["D16"]["ranking"][0]["id"], "C5")
        self.assertEqual(self.by_id["D16"]["ranking"][1]["id"], "C1")

    def test_height_is_an_integer_domain(self):
        """`< 10` is [0, 9] and `< 12` is [0, 11], so J = 9/11, not 10/12 as in a continuous domain."""
        jaccard = self.candidate("D0", "C3")["clauses"]["given"]["jaccard"]
        height = next(j for j in jaccard if j["parameter"] == "object_lift_height_cm")
        self.assertEqual(height["jaccard"], round(9 / 11, 5))

    # ── Properties ───────────────────────────────────────────────────────────

    def test_every_score_recomposes_from_its_clauses(self):
        for entry in self.battery:
            for c in entry["ranking"]:
                clauses = c["clauses"]
                for k in rq2.CLAUSES:
                    self.assertAlmostEqual(clauses[k]["similarity"],
                                           max(0, clauses[k]["param_avg"] - clauses[k]["penalty"]), places=12)
                self.assertAlmostEqual(c["score"], sum(clauses[k]["similarity"] for k in rq2.CLAUSES) / 3,
                                       places=12)

    def test_when_and_then_similarities_are_fixed_per_candidate(self):
        for cid in self.spec["candidates"]:
            values = {(self.candidate(d, cid)["clauses"]["when"]["similarity"],
                       self.candidate(d, cid)["clauses"]["then"]["similarity"]) for d in self.by_id}
            self.assertEqual(len(values), 1, cid)

    def test_d6_and_d7_give_the_same_vector(self):
        self.assertEqual(self.scores("D6"), self.scores("D7"))
        self.assertEqual([c["id"] for c in self.by_id["D6"]["ranking"]],
                         [c["id"] for c in self.by_id["D7"]["ranking"]])

    def test_d8_only_adds_structural_penalty(self):
        for cid in self.spec["candidates"]:
            d0 = self.candidate("D0", cid)["clauses"]["given"]
            d8 = self.candidate("D8", cid)["clauses"]["given"]
            self.assertEqual(d8["param_avg"], d0["param_avg"], cid)          # no new pair
            self.assertEqual(d8["diagnosis_only"], sorted(d0["diagnosis_only"] + ["object_mass"]), cid)
            self.assertGreater(d8["penalty"], d0["penalty"], cid)

    def test_predicate_order_does_not_change_the_scores(self):
        for d in self.spec["diagnoses"]:
            given = rq2.build_given(self.spec["reference"]["given"], d["changes"])
            reversed_entry = rq2.run_diagnosis(self.adapter, self.spec, d, given=given[::-1])
            self.assertEqual(rq2.scores_by_id(reversed_entry), self.scores(d["id"]), d["id"])

    # ── Reported results ─────────────────────────────────────────────────────

    def test_reported_counts(self):
        metrics = [rq2.ranking_metrics(e, self.battery[0]) for e in self.battery[1:]]
        self.assertEqual(sum(m["top1_changed"] for m in metrics), 15)
        self.assertEqual(sum(m["top3_order_changed"] for m in metrics), 15)
        self.assertEqual(sum(m["top3_set_changed"] for m in metrics), 2)
        self.assertEqual(sum(bool(m["exact_ties"]) or bool(m["near_ties"]) for m in metrics), 0)

    def test_saved_results_match_a_fresh_run(self):
        path = rq2.OUTPUT / "results.csv"
        if not path.exists():
            self.skipTest("run run_rq2.py first")
        with open(path, encoding="utf-8", newline="") as f:
            saved = {(r["diagnosis"], r["candidate"]): (float(r["score"]), int(r["rank"])) for r in csv.DictReader(f)}
        fresh = {(e["diagnosis"]["id"], c["id"]): (c["score"], c["rank"]) for e in self.battery for c in e["ranking"]}
        self.assertEqual(saved, fresh)

    def test_reproduction_domains_explain_every_difference(self):
        domains = {**self.adapter.monitored_parameters_dict, **self.exploratory["domains"]}
        alternative = rq2.run_battery(self.spec, rq2.make_adapter(domains))
        for entry in alternative:
            d = entry["diagnosis"]["id"]
            for cid, score in rq2.scores_by_id(entry).items():
                self.assertEqual(round(score, 4), self.exploratory["scores"][d][cid], f"{d} {cid}")
            self.assertEqual([c["id"] for c in entry["ranking"]][:3], self.exploratory["top3"][d])


if __name__ == "__main__":
    unittest.main()
