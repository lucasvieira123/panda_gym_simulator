"""
Testes do Manager com cenários evoluídos pelo DejaVu (P1 e P6 em 5-experiments/RQ1.2/decisions.md).
Sem simulação.

Uso, a partir de 1-manager/:
    python -m unittest discover -s tests -v
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from asm_evaluator import AsmEvaluator, _eval
from asm_loader import load_asm
from knowledge import SystemState
from plan import Planner

BASE_ASM = ROOT / "configs" / "arm" / "asm.json"
TRANSPORT_THEN = "distance_object_goal_cm <= 5 AND object_lift_height_cm >= 10 AND finger_contacts >= 2"
LIFT_THEN = "object_lift_height_cm >= 10 AND finger_contacts >= 2"

# Resultado do AsmEvolver para as duas incorporações da RQ1.2 (0,170 no transporte; 0,140 no lift)
EVOLVED = {
    "transport_object_vacuum_assist": {
        "name": "TRANSPORT_OBJECT_VACUUM_ASSIST", "type": "evolutionary",
        "given": "finger_contacts >= 2 AND lateral_friction <= 0.335", "when": "object_lift_height_cm >= 10",
        "do": "apply_vacuum_assist()", "then": TRANSPORT_THEN, "evolved_from": "transport_object"},
    "lift_object_vacuum_assist": {
        "name": "LIFT_OBJECT_VACUUM_ASSIST", "type": "evolutionary",
        "given": "finger_contacts >= 2 AND lateral_friction <= 0.1425", "when": "grasp_completed == 1",
        "do": "apply_vacuum_assist()", "then": LIFT_THEN, "evolved_from": "lift_object"},
}
NARROWED = {"transport_object": "finger_contacts >= 2 AND lateral_friction > 0.335",
            "lift_object": "finger_contacts >= 2 AND lateral_friction > 0.1425"}
NEW_TRANSITIONS = [
    ("lift_object", "transport_object_vacuum_assist"), ("transport_object_vacuum_assist", "place_object"),
    ("transport_object_vacuum_assist", "__end__"), ("grasp_object", "lift_object_vacuum_assist"),
    ("retry_grasp", "lift_object_vacuum_assist"), ("lift_object_vacuum_assist", "transport_object"),
    ("lift_object_vacuum_assist", "safe_abort"), ("lift_object_vacuum_assist", "transport_object_vacuum_assist"),
]


def context(mu, subtask, **values):
    state = SystemState(lateral_friction=mu, current_subtask=subtask, task_started=1, object_available=1,
                        gripper_width_cm=3, grasp_completed=1, finger_contacts=2, grasp_attempts=1, **values)
    return state.to_eval_dict()


class ManagerWithEvolvedAsm(unittest.TestCase):
    def setUp(self):
        raw = json.loads(BASE_ASM.read_text(encoding="utf-8"))
        raw["scenarios"].update(EVOLVED)
        for key, given in NARROWED.items():
            raw["scenarios"][key]["given"] = given
        raw["transitions"] += [{"from": a, "to": b} for a, b in NEW_TRANSITIONS]
        self.folder = tempfile.TemporaryDirectory()
        path = Path(self.folder.name) / "asm.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        self.asm = load_asm(path)

    def tearDown(self):
        self.folder.cleanup()

    def evaluate(self, node, ctx):
        evaluator = AsmEvaluator(self.asm)
        evaluator._current_node = node
        with contextlib.redirect_stdout(io.StringIO()):
            return evaluator.evaluate(ctx)

    def test_eval_context_has_lateral_friction(self):
        self.assertEqual(SystemState(lateral_friction=0.16).to_eval_dict()["lateral_friction"], 0.16)

    def test_transport_assist_matches_below_the_threshold(self):
        matched = self.evaluate("lift_object", context(0.16, "LIFT_OBJECT", object_lift_height_cm=11))
        self.assertEqual(matched.key, "transport_object_vacuum_assist")

    def test_nominal_friction_keeps_the_domain_transport(self):
        self.assertIsNone(self.evaluate("lift_object", context(0.5, "LIFT_OBJECT", object_lift_height_cm=11)))
        matched = self.evaluate("lift_object", context(0.5, "TRANSPORT_OBJECT", object_lift_height_cm=12))
        self.assertEqual(matched.key, "transport_object")

    def test_lift_assist_matches_when_the_grasp_completes(self):
        matched = self.evaluate("grasp_object", context(0.13, "GRASP_OBJECT"))
        self.assertEqual(matched.key, "lift_object_vacuum_assist")
        self.assertIsNone(self.evaluate("grasp_object", context(0.16, "GRASP_OBJECT")))

    def test_planner_sends_the_action_of_an_evolved_scenario(self):
        planner = Planner(self.asm)
        state = SystemState()
        with contextlib.redirect_stdout(io.StringIO()):
            state.matched_scenario = self.asm.scenarios["transport_object_vacuum_assist"]
            self.assertEqual(planner.plan(state), "APPLY_VACUUM_ASSIST")
            state.matched_scenario = self.asm.scenarios["retry_grasp"]
            self.assertEqual(planner.plan(state), "RETRY_GRASP")
            state.matched_scenario = self.asm.scenarios["safe_abort"]
            self.assertEqual(planner.plan(state), "SAFE_ABORT")

    def test_missing_variable_is_reported(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertFalse(_eval("unknown_parameter_xyz <= 1", {}))
        self.assertIn("unknown_parameter_xyz", output.getvalue())


if __name__ == "__main__":
    unittest.main()
