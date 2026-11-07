"""
Testes da infraestrutura de medição (sem simulação).

Uso, a partir de 3-dejavu/:
    python -m unittest discover -s tests -v
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))

from adaptation_evaluator import AdaptationEvaluator
from similarity.dejavu_similarity import _calculate_jaccard_similarity, _get_relational_expression_region
from unanticipated_scenario_diagnoser import UnanticipatedScenarioDiagnoser

LIFT_THEN = "object_lift_height_cm >= 10 AND finger_contacts >= 2"
OK   = {"object_lift_height_cm": 12, "finger_contacts": 2}
BAD  = {"object_lift_height_cm": 1, "finger_contacts": 0}
ADAPTATION = {"do": "apply_vacuum_assist()", "candidate_name": "C1", "then": LIFT_THEN + " AND object_secured == 1"}


def tick(subtask: str, values: dict = BAD) -> dict:
    return {**values, "current_subtask": subtask}


class IntegerParameterRegion(unittest.TestCase):
    def region(self, operator, value):
        return _get_relational_expression_region("x", operator, value, 0, 5, "int")

    def test_integer_written_as_float(self):
        self.assertEqual(self.region("<=", "1.0"), (0, 1))
        self.assertEqual(self.region("<", "1.0"), (0, 0))
        self.assertEqual(self.region(">", "2e0"), (3, 5))

    def test_decision_tree_threshold_between_integers(self):
        self.assertEqual(self.region("<=", "1.5"), (0, 1))
        self.assertEqual(self.region("<", "1.5"), (0, 1))
        self.assertEqual(self.region(">=", "1.5"), (2, 5))
        self.assertEqual(self.region(">", "1.5"), (2, 5))
        self.assertEqual(self.region("!=", "1.5"), (0, 5))

    def test_invalid_value_and_type_raise(self):
        with self.assertRaises(ValueError):
            self.region("<=", "abc")
        with self.assertRaises(ValueError):
            _get_relational_expression_region("x", "<=", "1", 0, 5, "text")

    def test_jaccard_accepts_diagnosed_finger_contacts(self):
        params = {"finger_contacts": {"type": "int", "min_value": 0, "max_value": 5}}
        self.assertGreaterEqual(_calculate_jaccard_similarity("finger_contacts <= 1.0", "finger_contacts < 2", params), 0)


class Evaluator(unittest.TestCase):
    def started(self, **kwargs):
        evaluator = AdaptationEvaluator(**kwargs)
        evaluator.start({"then": LIFT_THEN}, ADAPTATION)
        return evaluator

    def test_idle(self):
        self.assertIsNone(AdaptationEvaluator().evaluate(tick("LIFT_OBJECT")))

    def test_success_reports_candidate_clause_without_sensor(self):
        evaluator = self.started()
        self.assertEqual(evaluator.evaluate(tick("APPLY_VACUUM_ASSIST"))["status"], "waiting")
        result = evaluator.evaluate(tick("TRANSPORT_OBJECT", OK))
        self.assertEqual((result["status"], result["reason"]), ("success", "then_satisfied"))
        states = {c["clause"]: c["state"] for c in result["candidate_then"]}
        self.assertEqual(states["object_secured == 1"], "not_observed")

    def test_postconditions_not_met_within_window(self):
        evaluator = self.started(max_eval_ticks=3)
        evaluator.evaluate(tick("APPLY_VACUUM_ASSIST"))
        for _ in range(2):
            self.assertEqual(evaluator.evaluate(tick("TRANSPORT_OBJECT"))["status"], "evaluating")
        result = evaluator.evaluate(tick("TRANSPORT_OBJECT"))
        self.assertEqual((result["status"], result["reason"]), ("failure", "postconditions_not_met"))
        self.assertEqual(result["then_clauses"][0]["state"], "unsatisfied")

    def test_sequence_ended_without_postconditions(self):
        evaluator = self.started()
        evaluator.evaluate(tick("APPLY_VACUUM_ASSIST"))
        result = evaluator.evaluate(tick("PLACE_OBJECT"), sequence_done=True)
        self.assertEqual((result["status"], result["reason"]), ("failure", "sequence_ended"))

    def test_safe_abort(self):
        evaluator = self.started()
        evaluator.evaluate(tick("APPLY_VACUUM_ASSIST"))
        self.assertEqual(evaluator.evaluate(tick("SAFE_ABORT"))["reason"], "safe_abort")

    def test_adaptive_task_that_never_finishes_times_out(self):
        evaluator = self.started(max_run_ticks=3)
        statuses = [evaluator.evaluate(tick("APPLY_VACUUM_ASSIST"))["status"] for _ in range(3)]
        self.assertEqual(statuses, ["waiting", "waiting", "timeout"])
        self.assertEqual(evaluator.result["reason"], "adaptive_task_not_finished")

    def test_adaptation_that_never_starts_is_an_execution_error(self):
        evaluator = self.started(max_start_ticks=2)
        evaluator.evaluate(tick("LIFT_OBJECT"))
        result = evaluator.evaluate(tick("LIFT_OBJECT"))
        self.assertEqual((result["status"], result["reason"]), ("execution_error", "adaptation_not_started"))

    def test_diagnosed_postcondition_without_observation(self):
        evaluator = AdaptationEvaluator()
        evaluator.start({"then": "object_secured == 1"}, ADAPTATION)
        evaluator.evaluate(tick("APPLY_VACUUM_ASSIST"))
        result = evaluator.evaluate(tick("TRANSPORT_OBJECT", OK))
        self.assertEqual((result["status"], result["reason"]), ("execution_error", "postcondition_not_observable"))

    def test_terminal_result_is_kept(self):
        evaluator = self.started(max_run_ticks=1)
        first = evaluator.evaluate(tick("APPLY_VACUUM_ASSIST"))
        self.assertIs(evaluator.evaluate(tick("TRANSPORT_OBJECT", OK)), first)


class DiagnoserFeatures(unittest.TestCase):
    def diagnose(self, nominal_contacts, run_contacts, friction=0.135):
        rows = lambda execution, mu, contacts, sat: pd.DataFrame({
            "lateral_friction": mu,
            "finger_contacts": contacts,
            "active_scenario_name": ["GRASP_OBJECT"] + ["TRANSPORT_OBJECT"] * (len(contacts) - 1),
            "sat": sat,
        })
        diagnoser = UnanticipatedScenarioDiagnoser()
        with tempfile.TemporaryDirectory() as folder:
            rows("nominal", 0.5, nominal_contacts, True).to_csv(f"{folder}/nominal.csv", index=False)
            rows("run", friction, run_contacts, [True] * (len(run_contacts) - 1) + [False]).to_csv(f"{folder}/run.csv", index=False)
            diagnoser._dataset_folder = folder
            return diagnoser.diagnosis({"name": "TRANSPORT_OBJECT_unanticipated", "given": "finger_contacts < 2"})

    def test_dynamic_parameter_is_not_a_cause(self):
        # finger_contacts é constante dentro de TRANSPORT_OBJECT, mas varia na execução.
        diagnosed = self.diagnose([0, 2, 2], [0, 1, 1])
        self.assertIn("lateral_friction", diagnosed["diagnostic_conditions"])
        self.assertNotIn("finger_contacts", diagnosed["diagnostic_conditions"])

    def test_no_static_difference_gives_a_clear_error(self):
        with self.assertRaisesRegex(ValueError, "feature estática"):
            self.diagnose([0, 2, 2], [0, 1, 1], friction=0.5)


if __name__ == "__main__":
    unittest.main()
