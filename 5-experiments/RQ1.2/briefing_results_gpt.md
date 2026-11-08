# RQ1.2 — Actual results, for writing the RQ1.2 subsection

## Your task

Write Section RQ1.2 (Knowledge Incorporation and Behavioural-Space Evolution) in LaTeX: a short experimental design, then the results, in the same style as the RQ1.1 subsection. Use only the facts in this brief. Do not invent numbers, mechanisms or outcomes. Where the author's earlier draft says something different, this brief prevails.

The research question, as stated in the paper: *How does incorporating successfully managed unanticipated situations as anticipated knowledge affect the system's anticipated behavioural space and its handling of subsequent occurrences?*

**The message to convey:** once DejaVú incorporates a validated adaptation into the ASM, subsequent occurrences within the incorporated region are handled by the managing system as anticipated behaviour, with no violation and without invoking DejaVú's unanticipated-situation handling.

## Experimental design (what was run)

- One sequence of 13 executions, in decreasing friction order. The values are the RQ1.1 configurations from μ = 0.170 to μ = 0.060: 0.170, 0.160, 0.155, 0.150, 0.145, 0.140, 0.135, 0.130, 0.120, 0.110, 0.100, 0.080, 0.060.
- **Knowledge preserved between executions**, unlike RQ1.1:
  - the ASM evolved by one execution is the ASM of the next;
  - the Diagnoser's historical runtime data accumulate across the sequence.
  - The sequence starts from the initial ASM, with the Diagnoser initialised with the nominal traces (μ = 0.500), as in RQ1.1.
- Everything else is as in RQ1.1:
  - simulator, candidates and retry conditions (up to two attempts);
  - the goal criterion (object within 5 cm of the target, gripper open);
  - one execution per configuration (the simulation is deterministic).
- **Why the sequence ends at μ = 0.060.** RQ1.2 asks whether incorporated knowledge is reused, which can only be tested where the incorporated adaptation is effective.
  - RQ1.1 showed that the lift candidate (C1, suction-assisted) recovers the situation down to μ = 0.060, but not at 0.040, 0.020 and 0.010.
  - The range was therefore fixed from the RQ1.1 results, before running RQ1.2. State this explicitly.
  - Handling cases where incorporated knowledge is itself insufficient (knowledge refinement) is outside this RQ.

## How incorporated knowledge works at runtime (describe as the mechanism)

- After a validated adaptation, with the goal achieved at the end of the execution, the ASM Evolver changes the ASM in two ways:
  1. It **narrows the violated scenario's Given** with the negation of the diagnosed condition, so the original and the new scenario never apply at the same time.
  2. It **adds a new evolutionary scenario**. Its Given is the original Given plus the diagnosed condition; its When and Then are inherited from the violated scenario; its Do is the adaptive behaviour of the successful candidate. It also inherits the violated scenario's transitions.
- In later executions:
  - the managing system's MAPE-K loop evaluates the evolved ASM, including the contextual parameter `lateral_friction` used by the incorporated conditions;
  - when the incorporated scenario's Given and When hold, the managing system executes its Do as an anticipated (internal) adaptation;
  - the ASM-SM monitored by DejaVú is derived from the evolved ASM, so the incorporated scenarios are monitored like any other anticipated scenario;
  - DejaVú's unanticipated-situation handling is invoked only if a violation occurs.

## Results

### Incorporations (exactly two)

| Execution | Violation | Diagnosis (causal condition) | Candidate | Incorporated scenario |
|---|---|---|---|---|
| μ = 0.170 | TRANSPORT_OBJECT | `lateral_friction <= 0.335` | C6 Transport Slip Recovery (`apply_vacuum_assist()`), success | TRANSPORT_OBJECT_VACUUM_ASSIST |
| μ = 0.140 | LIFT_OBJECT | `lateral_friction <= 0.1425` | C1 Suction-Assisted Lift Recovery (`apply_vacuum_assist()`), success | LIFT_OBJECT_VACUUM_ASSIST |

GWDT of the evolved ASM (for the text and for the figure `arm_asm_evoluida.pdf`):

```
TRANSPORT_OBJECT_VACUUM_ASSIST   (incorporated at μ = 0.170)
  Given: finger_contacts >= 2 AND lateral_friction <= 0.335
  When : object_lift_height_cm >= 10
  Do   : apply_vacuum_assist()
  Then : distance_object_goal_cm <= 5 AND object_lift_height_cm >= 10 AND finger_contacts >= 2
TRANSPORT_OBJECT (narrowed):  Given = finger_contacts >= 2 AND lateral_friction > 0.335

LIFT_OBJECT_VACUUM_ASSIST        (incorporated at μ = 0.140)
  Given: finger_contacts >= 2 AND lateral_friction <= 0.1425
  When : grasp_completed == 1
  Do   : apply_vacuum_assist()
  Then : object_lift_height_cm >= 10 AND finger_contacts >= 2
LIFT_OBJECT (narrowed):       Given = finger_contacts >= 2 AND lateral_friction > 0.1425
```

New transitions:
- LIFT_OBJECT → TRANSPORT_OBJECT_VACUUM_ASSIST;
- TRANSPORT_OBJECT_VACUUM_ASSIST → PLACE_OBJECT;
- GRASP_OBJECT → LIFT_OBJECT_VACUUM_ASSIST;
- RETRY_GRASP → LIFT_OBJECT_VACUUM_ASSIST;
- LIFT_OBJECT_VACUUM_ASSIST → TRANSPORT_OBJECT;
- LIFT_OBJECT_VACUUM_ASSIST → SAFE_ABORT;
- LIFT_OBJECT_VACUUM_ASSIST → TRANSPORT_OBJECT_VACUUM_ASSIST.

The initial ASM had 7 scenarios; the evolved ASM has 9.

**The thresholds.**
- The transport threshold (0.335) lies midway between the nominal traces (0.500) and μ = 0.170.
- The lift threshold (0.1425) lies midway between μ = 0.145 and μ = 0.140, because the retained history already contained executions (0.170–0.145) in which lifting succeeded. In RQ1.1, where history was reset, the diagnosis at μ = 0.140 gave `<= 0.32`.
- Present this as an effect of the retained runtime data on the diagnosis (a narrower region). Do not present it as evidence of generalisation.

### Per-configuration comparison with RQ1.1

| μ | RQ1.1 (knowledge reset) | RQ1.2 (knowledge preserved) |
|---|---|---|
| 0.170 | TRANSPORT violation → DejaVú, C6, recovered | TRANSPORT violation → DejaVú, C6, recovered → **incorporated** |
| 0.160 | TRANSPORT violation → DejaVú, C6 | TRANSPORT_OBJECT_VACUUM_ASSIST applied; no violation |
| 0.155 | no violation | TRANSPORT_OBJECT_VACUUM_ASSIST applied; no violation |
| 0.150 | TRANSPORT violation → DejaVú, C6 | TRANSPORT_OBJECT_VACUUM_ASSIST applied; no violation |
| 0.145 | TRANSPORT violation → DejaVú, C6 | TRANSPORT_OBJECT_VACUUM_ASSIST applied; no violation |
| 0.140 | LIFT violation → DejaVú, C1, recovered | LIFT violation → DejaVú, C1, recovered → **incorporated** |
| 0.135 | TRANSPORT violation → DejaVú, C6 | both incorporated scenarios applied (lift, then transport); no violation |
| 0.130 | LIFT violation → DejaVú, C1 | both applied; no violation |
| 0.120 | LIFT violation → DejaVú, C1 | both applied; no violation |
| 0.110 | LIFT violation → DejaVú, C1 | both applied; no violation |
| 0.100 | LIFT violation → DejaVú, C1 | both applied; no violation |
| 0.080 | LIFT violation → DejaVú, C1 | both applied; no violation |
| 0.060 | LIFT violation → DejaVú, C1 | both applied; no violation |

Summary numbers:
- **DejaVú's unanticipated-situation handling:** invoked in 12 of the 13 configurations in RQ1.1, and in 2 of 13 in RQ1.2 (the two incorporations).
- **Reuse:** 11 of 13 configurations were handled by incorporated knowledge, with no violation. Ten of them violated the initial ASM in RQ1.1. The eleventh, μ = 0.155, had no violation in RQ1.1 and now receives the incorporated adaptation preventively (see limitations).
- **Goal:** achieved in 13/13 executions in both RQ1.1 and RQ1.2. Final distance to the target in RQ1.2: 1.3–1.9 cm.
- **Task length** (simulation steps, a clean measure independent of wall-clock time):
  - all 11 reuse executions finished in 64 steps, essentially the nominal length (the no-violation execution at μ = 0.155 in RQ1.1 took 65);
  - in RQ1.1, the 10 corresponding executions with violations took 89–120 steps, because recovery happened after the object slipped.
- **Execution integrity:** no runner timeouts, no execution errors and no unevaluated conditions.

### Evolution of the anticipated behavioural space

Scenario applied in each task phase, by friction region, after the two incorporations:

| Friction region | Lift phase | Transport phase |
|---|---|---|
| μ > 0.335 | LIFT_OBJECT (initial) | TRANSPORT_OBJECT (initial) |
| 0.1425 < μ ≤ 0.335 | LIFT_OBJECT (initial) | TRANSPORT_OBJECT_VACUUM_ASSIST (incorporated) |
| μ ≤ 0.1425 | LIFT_OBJECT_VACUUM_ASSIST (incorporated) | TRANSPORT_OBJECT_VACUUM_ASSIST (incorporated) |

- This is the core of the behavioural-space evolution: regions that were outside the initial anticipated behaviour, where the initial ASM was violated, now have anticipated scenarios.
- In each phase, exactly one scenario applies, because the original scenario was narrowed.
- In the lowest region, both phases use incorporated knowledge, so one execution applies both incorporated scenarios in sequence (observed: lift at step 15, transport at steps 19–20).

## Framing rules

- **Claim:** knowledge incorporated after validated adaptations was reused in later executions within the incorporated regions. This avoided the violations and the unanticipated-situation handling that the same configurations required when knowledge was reset (RQ1.1).
- **Claim:** the ASM grew from 7 to 9 scenarios, and the anticipated behavioural space now covers friction regions that previously led to violations.
- **Do not claim** reuse outside the tested range (μ < 0.060 or values not executed). The incorporated regions are defined by the diagnosis; they are validated only at the executed configurations.
- **Do not claim** that the narrower lift threshold demonstrates generalisation; it reflects the runtime data retained in the sequence.
- **Do not present** the sequential application of both incorporated scenarios as an error. It follows from the ASM organising knowledge per task phase. Mention in the limitations that the second application is physically redundant once the grip has been reinforced.
- Keep G1–G3 as illustrative interpretations, as in RQ1.1. Here, the relevant configurations belong to G2 and G3.

## Limitations (for threats to validity)

- **One deterministic sequence, in one order.** The incorporated conditions depend on the order and on the runtime data seen before, e.g. the lift threshold. A different order could yield different thresholds.
- **Few samples.** The incorporated regions are learned from few executions and are wider than what was validated.
  - The transport region `lateral_friction <= 0.335` covers values never executed in the sequence above 0.170.
  - μ = 0.155, which did not violate the initial ASM, now receives the incorporated adaptation preventively. This had no negative effect on the goal.
- **Redundancy in the lowest region.** Both incorporated scenarios are applied, one per phase. The second application is redundant once the grip has been reinforced, because the ASM does not observe the grip state.
- **Insufficient incorporated knowledge is out of scope.** When incorporated knowledge is insufficient (μ < 0.060, where the incorporated lift adaptation does not hold the object), refining the incorporated knowledge is left for future work.
- **Simulated candidates.** The physical effect of the candidates is simulated by changes in effective finger friction, as in RQ1.1.
