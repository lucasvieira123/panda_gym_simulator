# RQ1.2 — Actual results, for writing the RQ1.2 subsection

## Your task

Write Section RQ1.2 (Knowledge Incorporation and Behavioural-Space Evolution) in LaTeX: a short experimental design, then the results, in the same style as the RQ1.1 subsection. Use only the facts in this brief. Do not invent numbers, mechanisms or outcomes. Where the author's earlier draft says something different, this brief prevails.

The research question, as stated in the paper: *How does incorporating successfully managed unanticipated situations as anticipated knowledge affect the system's anticipated behavioural space and its handling of subsequent occurrences?*

**The message to convey:**
- Once DejaVú incorporates a validated adaptation into the ASM, later occurrences within the incorporated region are handled by the managing system as anticipated behaviour. There is no violation, and DejaVú's unanticipated-situation handling is not invoked.
- Incorporated knowledge is itself monitored. When an incorporated scenario is violated, DejaVú handles the violation like any other, and a new validated adaptation refines the incorporated knowledge.
- When no candidate recovers, the ASM is not changed and the system stops in the fail-safe.

## Experimental design (what was run)

- One sequence of 16 executions, in decreasing friction order. The values are the 16 RQ1.1 configurations from μ = 0.170 to μ = 0.010: 0.170, 0.160, 0.155, 0.150, 0.145, 0.140, 0.135, 0.130, 0.120, 0.110, 0.100, 0.080, 0.060, 0.040, 0.020, 0.010.
  - This range covers every RQ1.1 configuration in which the initial ASM was violated.
  - μ = 0.155 is the only configuration in this range without a violation in RQ1.1.
- **Knowledge preserved between executions**, unlike RQ1.1:
  - the ASM evolved by one execution is the ASM of the next;
  - the Diagnoser's historical runtime data accumulate across the sequence.
  - The sequence starts from the initial ASM, with the Diagnoser initialised with the nominal traces (μ = 0.500), as in RQ1.1.
- Everything else is as in RQ1.1:
  - simulator, candidates and retry conditions (up to two attempts, then the fail-safe);
  - the goal criterion (object within 5 cm of the target, gripper open);
  - one execution per configuration (the simulation is deterministic).

## How incorporated knowledge works at runtime (describe as the mechanism)

- **When the ASM evolves.** Only after a validated adaptation, i.e. a candidate succeeds and the global goal is achieved at the end of the execution. Present this as a design choice of the approach: unvalidated knowledge is never incorporated. Do not present it as a limitation.
- **What the ASM Evolver changes:**
  1. It **narrows the violated scenario's Given** with the negation of the diagnosed condition. As a result, the original and the new scenario never apply at the same time.
  2. It **adds a new evolutionary scenario**:
     - Given: the violated scenario's Given plus the diagnosed condition;
     - When and Then: inherited from the violated scenario;
     - Do: the adaptive behaviour of the successful candidate;
     - transitions: inherited from the violated scenario.
- **In later executions:**
  - the managing system's MAPE-K loop evaluates the evolved ASM, including the contextual parameter `lateral_friction` used by the incorporated conditions;
  - when an incorporated scenario's Given and When hold, the managing system executes its Do as an anticipated (internal) adaptation;
  - the ASM-SM monitored by DejaVú is derived from the evolved ASM, so incorporated scenarios are monitored like any other anticipated scenario;
  - DejaVú's unanticipated-situation handling is invoked only if a violation occurs.
- **Refinement.** An incorporated scenario can itself be the violated scenario. The same two changes then apply to it: its Given is narrowed, and a new scenario derived from it is added.

## Results

### Incorporations (exactly three)

| Execution | Violated scenario | Diagnosis (causal condition) | Candidate | Incorporated scenario |
|---|---|---|---|---|
| μ = 0.170 | TRANSPORT_OBJECT (initial) | `lateral_friction <= 0.335` | C6 Transport Slip Recovery (`apply_vacuum_assist()`), 1st attempt, success | E1 TRANSPORT_OBJECT_VACUUM_ASSIST |
| μ = 0.140 | LIFT_OBJECT (initial) | `lateral_friction <= 0.1425` | C1 Suction-Assisted Lift Recovery (`apply_vacuum_assist()`), 1st attempt, success | E2 LIFT_OBJECT_VACUUM_ASSIST |
| μ = 0.040 | E2 LIFT_OBJECT_VACUUM_ASSIST (incorporated) | `lateral_friction <= 0.05` | C2 Tactile Grip-Force Recovery (`adjust_grip_force()`), 1st attempt, success | E3 LIFT_OBJECT_VACUUM_ASSIST_ADJUST_GRIP_FORCE (refinement of E2) |

GWDT of the evolved ASM (for the text and for the figure `arm_asm_evoluida.pdf`):

```
TRANSPORT_OBJECT (narrowed):  Given = finger_contacts >= 2 AND lateral_friction > 0.335

E1 TRANSPORT_OBJECT_VACUUM_ASSIST   (incorporated at μ = 0.170, from TRANSPORT_OBJECT)
  Given: finger_contacts >= 2 AND lateral_friction <= 0.335
  When : object_lift_height_cm >= 10
  Do   : apply_vacuum_assist()
  Then : distance_object_goal_cm <= 5 AND object_lift_height_cm >= 10 AND finger_contacts >= 2

LIFT_OBJECT (narrowed):       Given = finger_contacts >= 2 AND lateral_friction > 0.1425

E2 LIFT_OBJECT_VACUUM_ASSIST        (incorporated at μ = 0.140, from LIFT_OBJECT; narrowed at μ = 0.040)
  Given: finger_contacts >= 2 AND lateral_friction <= 0.1425 AND lateral_friction > 0.05
  When : grasp_completed == 1
  Do   : apply_vacuum_assist()
  Then : object_lift_height_cm >= 10 AND finger_contacts >= 2

E3 LIFT_OBJECT_VACUUM_ASSIST_ADJUST_GRIP_FORCE   (incorporated at μ = 0.040, from E2)
  Given: finger_contacts >= 2 AND lateral_friction <= 0.1425 AND lateral_friction <= 0.05
  When : grasp_completed == 1
  Do   : adjust_grip_force()
  Then : object_lift_height_cm >= 10 AND finger_contacts >= 2
```

- E3's Given keeps the clause inherited from E2 (`<= 0.1425`). It is equivalent to `finger_contacts >= 2 AND lateral_friction <= 0.05`.
- The text may use the simplified form, stating that it is equivalent. The figure shows the ASM as stored.

New transitions (13; the ASM went from 13 to 26 transitions):
- E1: LIFT_OBJECT → E1; E1 → PLACE_OBJECT; E1 → END.
- E2: GRASP_OBJECT → E2; RETRY_GRASP → E2; E2 → TRANSPORT_OBJECT; E2 → SAFE_ABORT; E2 → E1.
- E3: GRASP_OBJECT → E3; RETRY_GRASP → E3; E3 → TRANSPORT_OBJECT; E3 → SAFE_ABORT; E3 → E1.

The initial ASM had 7 scenarios; the evolved ASM has 10.

**The thresholds.** Each threshold lies midway between the lowest friction at which the violated scenario was satisfied in the retained history and the friction of the violation.
- **0.335 (E1):** midway between the nominal traces (0.500) and μ = 0.170.
- **0.1425 (E2):** midway between μ = 0.145 and μ = 0.140. The retained history already contained executions (0.170–0.145) in which lifting succeeded. In RQ1.1, where history was reset, the diagnosis at μ = 0.140 gave `<= 0.32`.
- **0.05 (E3):** midway between μ = 0.060, the last execution in which E2 succeeded, and μ = 0.040.

Present the thresholds as an effect of the retained runtime data on the diagnosis (narrower regions). Do not present them as evidence of generalisation.

### Per-configuration comparison with RQ1.1

| μ | RQ1.1 (knowledge reset) | RQ1.2 (knowledge preserved) |
|---|---|---|
| 0.170 | TRANSPORT violation → DejaVú, C6, recovered | TRANSPORT violation → DejaVú, C6, recovered → **E1 incorporated** |
| 0.160 | TRANSPORT violation → DejaVú, C6 | E1 applied; no violation |
| 0.155 | no violation | E1 applied; no violation |
| 0.150 | TRANSPORT violation → DejaVú, C6 | E1 applied; no violation |
| 0.145 | TRANSPORT violation → DejaVú, C6 | E1 applied; no violation |
| 0.140 | LIFT violation → DejaVú, C1, recovered | LIFT violation → DejaVú, C1, recovered → **E2 incorporated** |
| 0.135 | TRANSPORT violation → DejaVú, C6 | E2 then E1 applied; no violation |
| 0.130 | LIFT violation → DejaVú, C1 | E2 then E1 applied; no violation |
| 0.120 | LIFT violation → DejaVú, C1 | E2 then E1 applied; no violation |
| 0.110 | LIFT violation → DejaVú, C1 | E2 then E1 applied; no violation |
| 0.100 | LIFT violation → DejaVú, C1 | E2 then E1 applied; no violation |
| 0.080 | LIFT violation → DejaVú, C1 | E2 then E1 applied; no violation |
| 0.060 | LIFT violation → DejaVú, C1 | E2 then E1 applied; no violation |
| 0.040 | LIFT violation → DejaVú, C1 failed, C2 recovered on retry | E2 applied, violated → DejaVú, C2 recovered (1st attempt) → **E3 incorporated, E2 narrowed** |
| 0.020 | LIFT violation → DejaVú, C1 and C2 failed → fail-safe | E3 applied, lift succeeded; E1 applied, violated in transport → DejaVú, C6 and C7 failed → fail-safe |
| 0.010 | LIFT violation → DejaVú, C1 did not finish, object fell off the table → fail-safe | E3 applied, violated in lift → DejaVú, C2 and C1 failed → fail-safe |

Summary numbers:
- **DejaVú's unanticipated-situation handling:** invoked in 15 of the 16 configurations in RQ1.1, and in 5 of 16 in RQ1.2 (three incorporations and two fail-safes).
- **Reuse:** 11 of 16 configurations (0.160–0.145 and 0.135–0.060) were handled by incorporated knowledge, with no violation.
  - Ten of them violated the initial ASM in RQ1.1.
  - The eleventh, μ = 0.155, had no violation in RQ1.1 and now receives the incorporated adaptation preventively (see limitations).
- **Goal:** achieved in 14/16 executions in both RQ1.1 and RQ1.2. In both, it was not achieved at 0.020 and 0.010, which ended in the fail-safe. Final distance to the target in the RQ1.2 executions that achieved the goal: 1.3–1.9 cm.
- **Task length** (simulation steps, a clean measure independent of wall-clock time):
  - all 11 reuse executions finished in 64 steps, essentially the nominal length (the no-violation execution at μ = 0.155 in RQ1.1 took 65);
  - in RQ1.1, the 10 corresponding executions with violations took 89–120 steps, because recovery happened after the object slipped.
- **Execution integrity:**
  - no runner timeouts;
  - no DejaVú pipeline errors;
  - no unevaluated conditions in the managing system.

### Refinement of incorporated knowledge (μ = 0.040)

- E2 (suction) was applied preventively, but did not hold the object: it rose to 7.1 cm and slipped.
- The ASM-SM detected the violation of E2, an incorporated scenario.
- DejaVú diagnosed `lateral_friction <= 0.05`. E2 had runtime history from 0.135 to 0.060.
- C2 ranked first (0.897, ahead of C1 at 0.887) and recovered the object on the first attempt. The goal was achieved at 1.8 cm.
- The ASM Evolver then did two things:
  - it narrowed E2 to `lateral_friction > 0.05`;
  - it added E3, derived from E2, with `adjust_grip_force()`.
- In RQ1.1, the same configuration needed a retry (C1 failed, then C2 recovered).
- **The ranking order is a metric effect, not learning.**
  - The narrower diagnosed region (`<= 0.05`) overlaps less with C1's Given (`lateral_friction <= 0.4`), so C1's similarity drops. In RQ1.1, where the diagnosis was `<= 0.27`, C1 ranked first.
  - The ranking does not take into account that `apply_vacuum_assist()` had just failed as E2's Do.

### Limit of the candidate catalogue (μ = 0.020 and μ = 0.010)

- **μ = 0.020.**
  - The lift phase now used E3, and it succeeded: the object reached 10.4 cm with both fingers in contact.
  - In the transport phase, E1 was applied. Its Do sets the simulated finger friction to 3.0, replacing the 7.0 set by E3. The fingers lost contact in that same step, and the object fell.
  - The violation of E1 was detected at the end of the transport phase. DejaVú diagnosed `lateral_friction <= 0.04`.
  - C6 and C7 both failed to secure the object, and the run ended in the fail-safe (attempts exhausted).
- **μ = 0.010.**
  - E3 was applied but did not hold the object.
  - DejaVú diagnosed `lateral_friction <= 0.015`. E3 had runtime history from 0.020, where it succeeded in the lift phase.
  - C2 and C1 both failed, and the run ended in the fail-safe (attempts exhausted).
- **No evolution in either execution.** No adaptation was validated, so the ASM was not changed. Report this as the system's expected, safe behaviour.
- In RQ1.1, these two configurations also ended in the fail-safe, so the goal outcome is the same.

### Evolution of the anticipated behavioural space

Scenario applied in each task phase, by friction region, after the three incorporations:

| Friction region | Lift phase | Transport phase |
|---|---|---|
| μ > 0.335 | LIFT_OBJECT (initial) | TRANSPORT_OBJECT (initial) |
| 0.1425 < μ ≤ 0.335 | LIFT_OBJECT (initial) | E1 (incorporated, C6) |
| 0.05 < μ ≤ 0.1425 | E2 (incorporated, C1) | E1 (incorporated, C6) |
| μ ≤ 0.05 | E3 (incorporated from E2, C2) | E1 (incorporated, C6) |

- This is the core of the behavioural-space evolution. Regions where the initial ASM was violated now have anticipated scenarios. The lift region below 0.1425 was refined once more when its incorporated scenario proved insufficient.
- In each phase, exactly one scenario applies, because the scenario each new one was derived from was narrowed.
- Validation of each region in the sequence:
  - E1: 0.160 to 0.060;
  - E2: 0.135 to 0.060;
  - E3: the lift phase at 0.020.
- In the region μ ≤ 0.05, the combination E3 + E1 did not achieve the goal in any execution.

## Framing rules

- **Claim:** knowledge incorporated after validated adaptations was reused in later executions within the incorporated regions. This avoided the violations and the unanticipated-situation handling that the same configurations required when knowledge was reset (RQ1.1).
- **Claim:** incorporated knowledge is monitored and can be refined. At 0.040, a violation of an incorporated scenario led to a new validated adaptation, which narrowed that scenario and added a derived one.
- **Claim:** the ASM grew from 7 to 9 and then 10 scenarios. The anticipated behavioural space now covers friction regions that previously led to violations.
- **Claim:** when no candidate recovers (0.020, 0.010), the ASM is not changed, and the system stops in the fail-safe, as in RQ1.1.
- **Do not claim:**
  - reuse outside the executed configurations. The incorporated regions are defined by the diagnosis and validated only where they were executed;
  - that the narrower thresholds demonstrate generalisation; they reflect the runtime data retained in the sequence;
  - that DejaVú learned to avoid C1 at 0.040; the ranking order is a metric effect.
- **Do not present** the sequential application of two incorporated scenarios as an error. It follows from the ASM organising knowledge per task phase. Its consequences go in the limitations.
- Keep G1–G3 as illustrative interpretations, as in RQ1.1. Here, the relevant configurations belong to G2 (0.170–0.145) and G3 (0.140–0.010).

## Limitations and threats to validity

**Where each point goes.** The rule that the ASM grows only with validated adaptations belongs in the description of the mechanism (see above), not here. The fail-safe at 0.020 and 0.010 belongs in the results.

Limitations of the approach (and future work):
- **No revision of incorporated knowledge that fails without a replacement.**
  - When an incorporated scenario is violated and no candidate recovers, the scenario is left unchanged and keeps being applied, so the same failure can recur.
  - Example: E1 at 0.020. The diagnosis there (`<= 0.04`) did not capture the observed cause (see next point). Restricting E1 on that basis would have recorded a wrong cause.
  - Future work: revising or restricting incorporated knowledge that failed without a replacement.
- **Interference between incorporated scenarios of different phases.**
  - The ASM organises knowledge per task phase and does not consider the effect of an adaptation applied in an earlier phase.
  - At 0.020, the transport scenario (E1) undid the stronger grip set by the lift scenario (E3).
  - Where both phases use suction (0.05 < μ ≤ 0.1425), the second application is only physically redundant.
  - Future work: composing adaptations across phases.

Threats to validity:
- **One deterministic sequence, in one order.** The incorporated conditions depend on the order and on the runtime data seen before (e.g. the lift thresholds). A different order could yield different thresholds and scenarios.
- **Few samples.** The incorporated regions are learned from few executions and are wider than what was validated.
  - The transport region `lateral_friction <= 0.335` covers values never executed in the sequence above 0.170.
  - μ = 0.155, which did not violate the initial ASM, now receives the incorporated adaptation preventively. This had no negative effect on the goal.
- **Simulated candidates.**
  - The physical effect of each candidate is simulated by setting the finger friction to an absolute value: 3.0 for C1/C6 and 7.0 for C2/C7.
  - This simplification determines how strongly one adaptation overrides another, as in the interference at 0.020.
  - It cannot be claimed that 0.020 would have succeeded without that override: the strongest setting (7.0) also failed as a transport recovery (C7).

## Note for the author (not for the text)

The sequence was executed in two batches: 0.170–0.060, then 0.040–0.010. The second batch started from the exact ASM and runtime data left by 0.060.
- The only code change between the batches was the fail-safe on a DejaVú pipeline error, which the paper's pipeline describes.
- No pipeline error occurred, so that change was not exercised.
- This detail need not appear in the text.
