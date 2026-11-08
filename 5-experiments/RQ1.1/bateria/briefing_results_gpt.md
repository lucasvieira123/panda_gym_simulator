# RQ1.1 — Actual results, for writing the Results subsection

## Your task

Write the **Results** part of Section RQ1.1 (Goal Preservation Under Unanticipated Situations) in LaTeX, in the same style and structure as the provisional Results text the author will paste along with this brief: a summary table by surface-contamination group, then one paragraph per group, then the adaptation outcomes, then an overall paragraph.

The provisional text used assumed numbers. **Replace them entirely with the results below.** Do not invent any number, candidate behaviour or mechanism that is not in this brief. Remove "provisional", "assumed" and "pending experimental verification".

## What was run

- 25 executions, one per `lateral_friction` value (0.800 to 0.010), grouped as in the paper: G1 adhesive residues (0.800–0.600, n=3), Nominal (0.500, n=1), G2 moisture (0.400–0.145, n=10), G3 lubricants (0.140–0.010, n=11).
- Each execution was independent. The application, the simulator and DejaVú's knowledge were reset before each run. Up to two adaptation attempts were allowed per execution.
- Each run is classified by the **global goal**: object within 5 cm of the target, with the gripper open, at the end of the run.
- All 25 runs completed without execution errors or runner timeouts.

## Summary by group (use for the table)

| Surface condition | μ (n) | Initial ASM violation | Recovery (1st / 2nd) | Fail-safe | Goal achieved |
|---|---|---|---|---|---|
| G1 – Adhesive residues | 0.800–0.600 (3) | No violation | – | 0 | 3/3 |
| Nominal | 0.500 (1) | No violation | – | 0 | 1/1 |
| G2 – Moisture | 0.400–0.145 (10) | 6 without violation; 4 TRANSPORT_OBJECT | 4 / 0 | 0 | 10/10 |
| G3 – Lubricants | 0.140–0.010 (11) | 10 LIFT_OBJECT; 1 TRANSPORT_OBJECT | 8 / 1 | 2 | 9/11 |
| **Total** | **25** | **15 violations** | **12 / 1** | **2** | **23/25** |

Derived figures:
- 13 of the 15 unanticipated situations were recovered (86.7%).
- 23 of the 25 executions achieved the goal (92.0%).
- 12 of the 15 were recovered by the first candidate (80.0%).
- A second attempt was made in 2 situations and succeeded in 1.

## Per-configuration results

| μ | Group | Violation | Attempt 1 | Attempt 2 | Fail-safe | Goal | Final distance to target |
|---|---|---|---|---|---|---|---|
| 0.800 | G1 | none | – | – | – | yes | 1.9 cm |
| 0.700 | G1 | none | – | – | – | yes | 1.8 cm |
| 0.600 | G1 | none | – | – | – | yes | 1.8 cm |
| 0.500 | Nominal | none | – | – | – | yes | 1.5 cm |
| 0.400 | G2 | none | – | – | – | yes | 0.8 cm |
| 0.300 | G2 | none | – | – | – | yes | 0.7 cm |
| 0.250 | G2 | none | – | – | – | yes | 1.9 cm |
| 0.200 | G2 | none | – | – | – | yes | 3.4 cm |
| 0.180 | G2 | none | – | – | – | yes | 2.5 cm |
| 0.170 | G2 | TRANSPORT_OBJECT | C6 success | – | – | yes | 1.6 cm |
| 0.160 | G2 | TRANSPORT_OBJECT | C6 success | – | – | yes | 0.5 cm |
| 0.155 | G2 | none | – | – | – | yes | 3.5 cm |
| 0.150 | G2 | TRANSPORT_OBJECT | C6 success | – | – | yes | 1.8 cm |
| 0.145 | G2 | TRANSPORT_OBJECT | C6 success | – | – | yes | 1.9 cm |
| 0.140 | G3 | LIFT_OBJECT | C1 success | – | – | yes | 1.6 cm |
| 0.135 | G3 | TRANSPORT_OBJECT | C6 success | – | – | yes | 1.5 cm |
| 0.130 | G3 | LIFT_OBJECT | C1 success | – | – | yes | 1.5 cm |
| 0.120 | G3 | LIFT_OBJECT | C1 success | – | – | yes | 1.4 cm |
| 0.110 | G3 | LIFT_OBJECT | C1 success | – | – | yes | 1.7 cm |
| 0.100 | G3 | LIFT_OBJECT | C1 success | – | – | yes | 2.0 cm |
| 0.080 | G3 | LIFT_OBJECT | C1 success | – | – | yes | 1.6 cm |
| 0.060 | G3 | LIFT_OBJECT | C1 success | – | – | yes | 1.9 cm |
| 0.040 | G3 | LIFT_OBJECT | C1 failure | C2 success | – | yes | 1.5 cm |
| 0.020 | G3 | LIFT_OBJECT | C1 failure | C2 failure | yes (attempts exhausted) | no | 33.1 cm (object on the table) |
| 0.010 | G3 | LIFT_OBJECT | C1 not completed (object left the table) | not allowed | yes (object off the table) | no | object fell off the table |

C1 = Suction-Assisted Lift Recovery, C2 = Tactile Grip-Force Recovery, C6 = Transport Slip Recovery, C7 = Transport Grip Pressure Recovery.

## What happened, step by step

**Detection.** Every violation was detected by the ASM-SM monitor:
- lift violations at tick 22–23, when the object did not reach 10 cm with two finger contacts;
- transport violations at tick 41, when the object slipped out of the gripper and dropped during transport, so its height and finger contacts no longer met the Then of TRANSPORT_OBJECT.

No violation was raised in the 10 configurations without one.

**Diagnosis.**
- In all 15 situations, the Diagnoser added `lateral_friction` as the causal condition of the Desired Adaptation Scenario. The threshold ranged from `lateral_friction <= 0.335` (μ = 0.170) to `<= 0.255` (μ = 0.010).
- How the threshold arises: the training data are the nominal traces (μ = 0.500) plus the current execution's own trace. The decision tree therefore places the threshold midway between 0.500 and the current μ. Describe this honestly, and do not present it as evidence of generalisation.
- The violated Then clauses were negated into the Given. For lift: `object_lift_height_cm < 10 AND finger_contacts < 2`. For transport: `distance_object_goal_cm > 5 AND object_lift_height_cm < 10 AND finger_contacts < 2`.

**Retrieval.** The When filter restricted lift situations to C1–C5 and transport situations to C6–C8. The ranking was the same in every situation of the same phase:
- **Lift (10 situations):** C1 first (score 0.944–0.962), C2 second (0.897), then C3 (0.832), C4 (0.708) and C5 (0.590).
- **Transport (5 situations):** C6 first (0.900–0.905), C7 second (0.536), C8 third (0.333).

**Adaptation and retry.**
- **First candidate:** recovered 12 situations. C6 handled all 5 transport violations; C1 handled 7 of the 10 lift violations.
- **Transport:** never needed a second attempt, so **C7 was never executed**. State this plainly; do not suggest that C7 was exercised.
- **μ = 0.040:** C1 failed (object not secured after the re-grasp). The retry conditions held, so DejaVú selected the next untried candidate from the original ranking, C2, which recovered the situation and the goal was achieved.
- **μ = 0.020:** C1 and C2 both failed (object not secured). With two attempts used, the Fallback/Fail-Safe Behaviour was activated.
- **μ = 0.010:** during C1's re-grasp, the object was pushed off the table. The adaptive task did not finish within its time limit, and the retry conditions were no longer met because the object was no longer on the table. The fail-safe was activated without a second attempt.

So the two fail-safe activations have **different reasons**: the attempts were exhausted in one, and the retry conditions were violated in the other. Both match the configured retry conditions.

**Fail-safe.** In both cases, the fail-safe stopped all arm and gripper motion, kept the gripper as it was (it does not open it, unlike the anticipated SAFE_ABORT), recorded the reason, notified the operator console and ended the execution.

**No undetected failures.** In no execution did DejaVú report a successful adaptation while the goal was missed. Every execution that missed the goal ended in an explicit fail-safe.

**Evolution (connects to RQ1.2).** The validated adaptation was incorporated into the ASM in the 13 recovered executions. The ASM was not evolved in the 2 fail-safe executions, because evolution requires both a successful adaptation and the global goal. Since knowledge was reset between runs, reuse is not evaluated here.

## How to explain why some situations were recovered and others not

This is the core of the narrative. The explanation should be presented as consistent with the observations, not as a fitted model.

- **How the candidates are simulated.** As the Evaluation section says, they are simulated through controlled changes in the simulator. C1 and C6 (suction assistance) and C2 (grip-force adjustment) all re-grasp the object with the same routine and differ only in the effective finger–object friction they simulate: ×3 for C1 and C6, ×7 for C2 (and C7). The simulator combines finger and object friction multiplicatively.
- **Nominal grasp.** It holds the object through lift when μ ≥ about 0.145. The observed boundaries of each candidate follow from that:
  - C1 at μ = 0.060 gives an effective 0.18 and holds; at μ = 0.040 it gives 0.12 and does not.
  - C2 at μ = 0.040 gives 0.28 and holds; at μ = 0.020 it gives 0.14 and does not.
  - At μ = 0.010, closing the gripper pushes the object away before any grasp is formed.
- **The second candidate adds recovery capacity, but it is not unlimited.** It extended the range that could be handled from μ = 0.060 down to μ = 0.040, but not to 0.020 or 0.010. This matches the author's intended message: a second strategy *can* add recovery capacity, without resolving every situation.
- **The 0.135–0.170 region is a transition zone, and the boundary is not monotonic.**
  - μ = 0.155 produced no violation, although 0.170, 0.160, 0.150 and 0.145 violated during transport.
  - μ = 0.140 violated during lift, while μ = 0.135 violated during transport.
  - Near the slip threshold, whether the object slips, and in which phase, depends on fine contact details. The simulation is deterministic, so this is not run-to-run noise.
  - Present this as an observed property of the exemplar's physics. It is also why G3 contains one transport violation (μ = 0.135), unlike the provisional text, which assumed all G3 violations occur during lift.

## Differences from the provisional text that must not survive

- 15 violations, not 17.
- G2 has 6 configurations without violation (0.400–0.180 and 0.155), not 4. Its 4 violations are all recovered by the first candidate (C6), with no second attempt and no fail-safe; the goal was achieved 10/10, not 9/10.
- G3 has 10 lift violations and 1 transport violation, not 11 lift violations.
  - First candidate: 8 recoveries (0.140, 0.135, 0.130, 0.120, 0.110, 0.100, 0.080, 0.060), not 4.
  - Second candidate: 1 recovery (0.040), not 3.
  - Fail-safe: 2 activations (0.020, 0.010), not 4.
  - Goal: 9/11.
- Overall: 12 first-candidate recoveries, not 8; 1 second-candidate recovery, not 4; 2 fail-safe activations, not 5; 13/15 situations recovered (86.7%), not 70.6%; goal 23/25 (92.0%), not 80.0%.
- The provisional text said the 0.155 and 0.145 transport cases needed a second candidate. Neither did: 0.155 had no violation and 0.145 was recovered by C6.

## Framing rules

- **Claim:** all four paths occurred (no violation; recovery by the first candidate; recovery by the second candidate; fail-safe) and DejaVú handled each correctly. That covers detection, diagnosis, the When filter, ranking, retry only when allowed, fail-safe with the right reason, ASM evolution only after validated recovery, and no undetected failure.
- **Do not claim:** per-candidate success rates as evidence of the candidates' real-world effectiveness. The candidates are simulated, and which μ each one handles depends on the exemplar's physical parameters.
- **Keep the groups illustrative:** G1–G3 are illustrative interpretations of friction values, as the Evaluation section already states.
- **Limitations, for the threats-to-validity section:**
  - Each configuration was executed once, from a fixed initial object position. The simulation is deterministic, so repetitions would be identical, and the split between paths depends on the exemplar's physical parameters. No sensitivity analysis was performed.
  - C3, C4, C5 and C8 take part in the ranking but have no physical implementation. C7 is implemented but was never triggered.
  - Clauses such as `object_secured` and `grip_pressure` in the candidates' Then are not observed by the exemplar. Adaptation success is judged on the diagnosed Then; the goal is judged at the end of the run.
  - The nominal transport controller decelerates in the last 5 cm before the target. Without this, the arm could oscillate over the target. It is part of the managed system, not of DejaVú.
