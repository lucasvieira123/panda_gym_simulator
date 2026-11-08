"""
Testes do diagnóstico pelo caminho da execução atual e das salvaguardas do AsmEvolver
(P2, P3, Q2 e Q3 em 5-experiments/RQ1.2/decisions.md). Sem simulação.

Uso, a partir de 3-dejavu/:
    python -m unittest discover -s tests -v
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))

from asm_evolver import AsmEvolver, EvolutionRejected, _negate_conditions
from unanticipated_scenario_diagnoser import UnanticipatedScenarioDiagnoser

LIFT_THEN = "object_lift_height_cm >= 10 AND finger_contacts >= 2"
TRANSPORT_THEN = "distance_object_goal_cm <= 5 AND " + LIFT_THEN
ASM = {
    "scenarios": {
        "grasp_object": {"name": "GRASP_OBJECT", "type": "domain", "given": "gripper_width_cm >= 6",
                         "when": "distance_ee_object_cm <= 2", "do": "close_gripper()", "then": "grasp_completed == 1"},
        "lift_object": {"name": "LIFT_OBJECT", "type": "domain", "given": "finger_contacts >= 2",
                        "when": "grasp_completed == 1", "do": "lift_object()", "then": LIFT_THEN},
        "transport_object": {"name": "TRANSPORT_OBJECT", "type": "domain", "given": "finger_contacts >= 2",
                             "when": "object_lift_height_cm >= 10", "do": "transport_to_goal()",
                             "then": TRANSPORT_THEN},
    },
    "transitions": [
        {"from": "grasp_object", "to": "lift_object"},
        {"from": "lift_object", "to": "transport_object"},
        {"from": "transport_object", "to": "__end__"},
    ],
}
VACUUM = {"do": "apply_vacuum_assist()"}


class DiagnoserPath(unittest.TestCase):
    """Uma execução por atrito; o rótulo é a violação de LIFT_OBJECT."""

    def diagnose(self, executions: dict, current: str):
        diagnoser = UnanticipatedScenarioDiagnoser()
        with tempfile.TemporaryDirectory() as folder:
            for name, (mu, violated) in executions.items():
                pd.DataFrame({
                    "lateral_friction": [mu, mu],
                    "active_scenario_name": ["GRASP_OBJECT", "LIFT_OBJECT"],
                    "sat": [True, not violated],
                }).to_csv(f"{folder}/{name}.csv", index=False)
            diagnoser._dataset_folder = folder
            return diagnoser.diagnosis({"name": "LIFT_OBJECT_unanticipated", "given": "G"}, current_execution=current)

    def test_isolated_run_keeps_the_rq1_1_threshold(self):
        diagnosed = self.diagnose({"nominal": (0.5, False), "run": (0.14, True)}, "run")
        self.assertEqual(diagnosed["diagnostic_conditions"], "lateral_friction <= 0.32")

    def test_preserved_dataset_separates_the_neighbours(self):
        runs = {"nominal": (0.5, False), "r170": (0.17, False), "r145": (0.145, False), "r140": (0.14, True)}
        self.assertEqual(self.diagnose(runs, "r140")["diagnostic_conditions"], "lateral_friction <= 0.1425")

    def test_non_monotonic_data_gives_a_consistent_interval(self):
        # 0,135 sem violação entre 0,140 e 0,130 com violação (como na sequência da RQ1.2)
        runs = {"nominal": (0.5, False), "r145": (0.145, False), "r140": (0.14, True),
                "r135": (0.135, False), "r130": (0.13, True)}
        self.assertEqual(self.diagnose(runs, "r130")["diagnostic_conditions"], "lateral_friction <= 0.1325")
        self.assertEqual(self.diagnose(runs, "r140")["diagnostic_conditions"],
                         "lateral_friction > 0.1375 AND lateral_friction <= 0.1425")

    def test_unknown_current_execution_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "Execução atual"):
            self.diagnose({"nominal": (0.5, False), "run": (0.14, True)}, "other")


class Evolution(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "asm.json"
        self.path.write_text(json.dumps(ASM), encoding="utf-8")
        self.evolver = AsmEvolver(str(self.path))

    def tearDown(self):
        self.folder.cleanup()

    def evolve(self, key, conditions, mu, do=VACUUM):
        return self.evolver.evolve({"anticipated_id": key}, {"diagnostic_conditions": conditions}, do,
                                   context={"lateral_friction": mu, "finger_contacts": 0})

    def asm(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def test_transport_incorporation_at_0_170(self):
        result = self.evolve("transport_object", "lateral_friction <= 0.335", 0.17)
        self.assertEqual(result["new_scenario"]["given"], "finger_contacts >= 2 AND lateral_friction <= 0.335")
        self.assertEqual(result["updated_given"], "finger_contacts >= 2 AND lateral_friction > 0.335")
        self.assertEqual(result["new_scenario"]["then"], TRANSPORT_THEN)
        transitions = {(t["from"], t["to"]) for t in self.asm()["transitions"]}
        self.assertTrue({("lift_object", "transport_object_vacuum_assist"),
                         ("transport_object_vacuum_assist", "__end__")} <= transitions)

    def test_interval_is_negated_with_de_morgan(self):
        self.assertEqual(_negate_conditions("lateral_friction > 0.1375 AND lateral_friction <= 0.1425"),
                         "(lateral_friction <= 0.1375 OR lateral_friction > 0.1425)")
        result = self.evolve("lift_object", "lateral_friction > 0.1375 AND lateral_friction <= 0.1425", 0.14)
        self.assertEqual(result["updated_given"],
                         "finger_contacts >= 2 AND (lateral_friction <= 0.1375 OR lateral_friction > 0.1425)")

    def test_existing_key_is_rejected_and_asm_is_unchanged(self):
        self.evolve("transport_object", "lateral_friction <= 0.335", 0.17)
        before = self.asm()
        with self.assertRaises(EvolutionRejected) as ctx:
            self.evolve("transport_object", "lateral_friction <= 0.335", 0.16)
        self.assertEqual(ctx.exception.reason, "scenario_key_exists")
        self.assertEqual(self.asm(), before)

    def test_given_that_misses_the_situation_is_rejected(self):
        # Caso reproduzido da sequência antiga: violação em 0,16 atribuída ao TRANSPORT_OBJECT já restringido
        self.evolve("transport_object", "lateral_friction <= 0.335", 0.17)
        before = self.asm()
        with self.assertRaises(EvolutionRejected) as ctx:
            self.evolve("transport_object", "lateral_friction <= 0.335", 0.16, do={"do": "increase_grip_pressure()"})
        self.assertEqual(ctx.exception.reason, "given_does_not_cover_situation")
        self.assertEqual(self.asm(), before)

    def test_transitions_are_not_duplicated(self):
        self.evolve("transport_object", "lateral_friction <= 0.335", 0.17)
        self.evolve("lift_object", "lateral_friction <= 0.1425", 0.14)
        pairs = [(t["from"], t["to"]) for t in self.asm()["transitions"]]
        self.assertEqual(len(pairs), len(set(pairs)))
        self.assertIn(("lift_object_vacuum_assist", "transport_object_vacuum_assist"), pairs)


if __name__ == "__main__":
    unittest.main()
