"""
Testes do ASM-SM gerado do ASM e dos eventos de cenários evoluídos (P4 em 5-experiments/RQ1.2/decisions.md).
Os ticks imitam as subtarefas do Managing; não há simulação.

Uso, a partir de 3-dejavu/:
    python -m unittest discover -s tests -v
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))

from antecipated_scenario_monitor import StateMachineEngine
from asm_evolver import AsmEvolver
from dejavu import _SM_INITIAL, _sm_params
from has_model_to_assm import assm_yaml_from_asm_file
from subtask_events import DOMAIN_EVENTS, SubtaskEventMapper

BASE_ASM = ROOT.parent / "1-manager" / "configs" / "arm" / "asm.json"
VACUUM = {"do": "apply_vacuum_assist()"}


def ticks(mu, *phases):
    """phases: (subtask, overrides) em ordem; cada um vira um tick."""
    base = {"task_started": 1, "object_available": 1, "gripper_width_cm": 7, "distance_ee_object_cm": 20,
            "grasp_completed": 0, "finger_contacts": 0, "grasp_attempts": 0, "object_lift_height_cm": 0,
            "distance_object_goal_cm": 40, "task_aborted": 0, "lateral_friction": mu, "is_success": False}
    return [{**base, **values, "current_subtask": subtask} for subtask, values in phases]


HELD = {"grasp_completed": 1, "finger_contacts": 2, "gripper_width_cm": 3, "grasp_attempts": 1,
        "distance_ee_object_cm": 1}
APPROACH_GRASP = [("APPROACH_OBJECT", {}), ("APPROACH_OBJECT", {"distance_ee_object_cm": 1}),
                  ("GRASP_OBJECT", {"distance_ee_object_cm": 1}), ("GRASP_OBJECT", HELD)]
TRANSPORT_PLACE = [("TRANSPORT_OBJECT", {**HELD, "object_lift_height_cm": 14, "distance_object_goal_cm": 30}),
                   ("TRANSPORT_OBJECT", {**HELD, "object_lift_height_cm": 12, "distance_object_goal_cm": 3}),
                   ("PLACE_OBJECT", {**HELD, "object_lift_height_cm": 5, "distance_object_goal_cm": 3}),
                   ("PLACE_OBJECT", {"grasp_completed": 1, "gripper_width_cm": 7, "distance_object_goal_cm": 3,
                                     "is_success": True})]
NOMINAL_LIFT = [("LIFT_OBJECT", {**HELD, "object_lift_height_cm": 5}),
                ("LIFT_OBJECT", {**HELD, "object_lift_height_cm": 14})]


def run(asm_path, perceptions):
    """Repete o laço do DejaVu para o monitor; devolve os sat de cada tick, os cenários visitados e se chegou a FINAL."""
    with contextlib.redirect_stdout(io.StringIO()):
        engine = StateMachineEngine(dict(_SM_INITIAL), asm_path=asm_path)
        mapper = SubtaskEventMapper(json.loads(Path(asm_path).read_text(encoding="utf-8")))
        prev, sats, visited = None, [], []
        for perception in perceptions:
            sm_tick, prev, skip = _sm_params(perception, prev, mapper, engine.awaited_events())
            sats.append(engine.check_state_machine(sm_tick, skip_rewind=skip))
            name = engine.itp.context["active_scenario"]["name"]
            if not visited or visited[-1] != name:
                visited.append(name)
    return sats, visited, engine.itp.final  # o Sismic encerra o statechart ao entrar em FINAL


class GeneratedStateMachine(unittest.TestCase):
    def test_initial_asm_gives_the_committed_yaml(self):
        generated = yaml.safe_load(assm_yaml_from_asm_file(BASE_ASM))
        committed = yaml.safe_load((ROOT / "configs" / "arm" / "scenario_state_machine.yaml").read_text(encoding="utf-8"))
        self.assertEqual(generated["statechart"]["root state"], committed["statechart"]["root state"])

    def test_initial_asm_keeps_the_domain_events(self):
        mapper = SubtaskEventMapper(json.loads(BASE_ASM.read_text(encoding="utf-8")))
        self.assertEqual(mapper.evolved_phases, {})
        for subtask, event in DOMAIN_EVENTS.items():
            self.assertEqual(mapper.action(subtask, "NEXT", False, {event}), event)
        self.assertIsNone(mapper.action("LIFT_OBJECT", "LIFT_OBJECT", False, set()))


class InitialAsm(unittest.TestCase):
    def test_nominal_run_has_no_violation(self):
        sats, _, final = run(BASE_ASM, ticks(0.5, *APPROACH_GRASP, *NOMINAL_LIFT, *TRANSPORT_PLACE))
        self.assertNotIn(False, sats)
        self.assertTrue(final)

    def test_lift_slip_is_still_detected(self):
        slip = [("LIFT_OBJECT", {**HELD, "object_lift_height_cm": 2}),
                ("LIFT_OBJECT", {"grasp_completed": 1, "gripper_width_cm": 0}),
                ("TRANSPORT_OBJECT", {"grasp_completed": 1, "gripper_width_cm": 0})]
        sats, visited, _ = run(BASE_ASM, ticks(0.13, *APPROACH_GRASP, *slip))
        self.assertIs(sats[-1], False)
        self.assertEqual(visited[-1], "LIFT_OBJECT")


class EvolvedAsm(unittest.TestCase):
    """ASM com as duas incorporações da RQ1.2: transporte em 0,170 e lift em 0,140."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.asm = Path(self.folder.name) / "asm.json"
        self.asm.write_text(BASE_ASM.read_text(encoding="utf-8"), encoding="utf-8")
        evolver = AsmEvolver(str(self.asm))
        evolver.evolve({"anticipated_id": "transport_object"}, {"diagnostic_conditions": "lateral_friction <= 0.335"},
                       VACUUM, context={"lateral_friction": 0.17})
        evolver.evolve({"anticipated_id": "lift_object"}, {"diagnostic_conditions": "lateral_friction <= 0.1425"},
                       VACUUM, context={"lateral_friction": 0.14})

    def tearDown(self):
        self.folder.cleanup()

    def test_nominal_friction_follows_the_domain_scenarios(self):
        sats, visited, final = run(self.asm, ticks(0.5, *APPROACH_GRASP, *NOMINAL_LIFT, *TRANSPORT_PLACE))
        self.assertNotIn(False, sats)
        self.assertTrue(final)
        self.assertIn("TRANSPORT_OBJECT", visited)
        self.assertNotIn("TRANSPORT_OBJECT_VACUUM_ASSIST", visited)

    def test_transport_assist_is_checked_after_the_transport(self):
        # 0,16: lift nominal; o Manager aplica a sucção ao atingir 10 cm, e o transporte retoma
        lift_then_assist = [("LIFT_OBJECT", {**HELD, "object_lift_height_cm": 5}),
                            ("LIFT_OBJECT", {**HELD, "object_lift_height_cm": 10}),
                            ("APPLY_VACUUM_ASSIST", {**HELD, "object_lift_height_cm": 14})]
        sats, visited, final = run(self.asm, ticks(0.16, *APPROACH_GRASP, *lift_then_assist, *TRANSPORT_PLACE))
        self.assertNotIn(False, sats)
        self.assertTrue(final)
        self.assertIn("TRANSPORT_OBJECT_VACUUM_ASSIST", visited)
        self.assertNotIn("TRANSPORT_OBJECT", visited)

    def test_lift_and_transport_assists_in_sequence(self):
        # 0,13: sucção ao completar a pegada (lift) e de novo no transporte
        assists = [("APPLY_VACUUM_ASSIST", {**HELD, "object_lift_height_cm": 5}),
                   ("APPLY_VACUUM_ASSIST", {**HELD, "object_lift_height_cm": 15}),
                   ("TRANSPORT_OBJECT", {**HELD, "object_lift_height_cm": 15, "distance_object_goal_cm": 35}),
                   ("APPLY_VACUUM_ASSIST", {**HELD, "object_lift_height_cm": 15, "distance_object_goal_cm": 35})]
        sats, visited, final = run(self.asm, ticks(0.13, *APPROACH_GRASP, *assists, *TRANSPORT_PLACE))
        self.assertNotIn(False, sats)
        self.assertTrue(final)
        self.assertIn("LIFT_OBJECT_VACUUM_ASSIST", visited)
        self.assertIn("TRANSPORT_OBJECT_VACUUM_ASSIST", visited)

    def test_failed_lift_assist_is_a_violation_of_the_evolved_scenario(self):
        # 0,04: a sucção não segura o objeto; a violação é do cenário evoluído, de onde parte a nova incorporação
        failed = [("APPLY_VACUUM_ASSIST", {"grasp_completed": 1, "gripper_width_cm": 0}),
                  ("TRANSPORT_OBJECT", {"grasp_completed": 1, "gripper_width_cm": 0})]
        sats, visited, _ = run(self.asm, ticks(0.04, *APPROACH_GRASP, *failed))
        self.assertIs(sats[-1], False)
        self.assertEqual(visited[-1], "LIFT_OBJECT_VACUUM_ASSIST")


if __name__ == "__main__":
    unittest.main()
