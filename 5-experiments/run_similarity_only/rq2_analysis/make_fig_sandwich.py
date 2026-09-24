"""
Paper figure: DejaVu similarity across structural variants of the diagnosed
Given (Grupo B additions -> A0 baseline -> Grupo A omissions), Option 1
("sandwich") from the RQ2 chart-options exploration.

Grupo B was redesigned from 3 isolated single-clause additions (old B1/B2/B3,
each testing one parameter in parallel) to a CUMULATIVE sequence B1->B2->B3
(each step keeps every clause from the previous step and adds one more):
  B1 (+1 extra): ... AND objects_object_1_mass > 0.5
  B2 (+2 extra): ... AND objects_object_1_mass > 0.5 AND gripper_width_cm >= 6
  B3 (+3 extra): ... AND objects_object_1_mass > 0.5 AND gripper_width_cm >= 6
                     AND grasp_attempts >= 1
The old B4 (discriminative mass>3, matching Cobot Industrial's own threshold)
was dropped entirely -- out of scope for this "how much does accumulating
generic extra parameters cost" question. See
5-experiments/run_similarity_only/configs/desired_scenario.json for the
authoritative Given strings.

Values come from 5-experiments/run_similarity_only/rq2_analysis/rq2_full_ranking.csv
for A0-A6; B1/B2/B3 (new cumulative definitions) were computed live against
the real calculate_scenario_similarity() in
3-dejavu/src/similarity/dejavu_similarity.py -- the official pipeline
(decompose_rq2_similarity.py) has not been re-run against the edited
desired_scenario.json yet, so these B-group numbers are not yet reflected in
rq2_full_ranking.csv / rq2_analysis.md. No values are invented here -- this
script only lays out numbers produced by the real similarity engine.

Point labels show 3 decimals, TRUNCATED (not rounded) -- e.g. a true value of
0.89947 is printed as "0.899", never rounded up to "0.900".
"""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.lines import Line2D

def trunc3(v):
    """Truncate (never round) to 3 decimals, e.g. 0.89947 -> 0.899."""
    return math.floor(v * 1000) / 1000

DATA = {
    "B3": {"LiftSlip": 0.81849, "ParallelArm": 0.78571, "CobotIndustrial": 0.80896, "LightweightArm": 0.62041, "CobotGrip": 0.55952},
    "B2": {"LiftSlip": 0.85139, "ParallelArm": 0.80851, "CobotIndustrial": 0.84063, "LightweightArm": 0.64321, "CobotGrip": 0.57092},
    "B1": {"LiftSlip": 0.89947, "ParallelArm": 0.84211, "CobotIndustrial": 0.88655, "LightweightArm": 0.67680, "CobotGrip": 0.58772},
    "A0": {"LiftSlip": 0.97639, "ParallelArm": 0.89655, "CobotIndustrial": 0.86585, "LightweightArm": 0.73125, "CobotGrip": 0.61494},
    "A1": {"LiftSlip": 0.98413, "ParallelArm": 1.00000, "CobotIndustrial": 0.95382, "LightweightArm": 0.83470, "CobotGrip": 0.66667},
    "A2": {"LiftSlip": 0.94871, "ParallelArm": 0.83333, "CobotIndustrial": 0.80231, "LightweightArm": 0.66803, "CobotGrip": 0.66667},
    "A3": {"LiftSlip": 0.94871, "ParallelArm": 0.83333, "CobotIndustrial": 0.80231, "LightweightArm": 0.66803, "CobotGrip": 0.50000},
    "A4": {"LiftSlip": 0.94444, "ParallelArm": 0.96970, "CobotIndustrial": 0.90720, "LightweightArm": 0.80440, "CobotGrip": 0.80303},
    "A5": {"LiftSlip": 0.94444, "ParallelArm": 0.96970, "CobotIndustrial": 0.90720, "LightweightArm": 0.80440, "CobotGrip": 0.50000},
    "A6": {"LiftSlip": 0.87361, "ParallelArm": 0.66667, "CobotIndustrial": 0.65079, "LightweightArm": 0.50137, "CobotGrip": 0.50000},
}

ORDER = ["B3", "B2", "B1", "A0", "A1", "A2", "A3", "A4", "A5", "A6"]
XLABELS = {
    "B3": "$D_1$ (+mass+grip\n+attempts $\\geq$1)",
    "B2": "$D_2$ (+mass+grip $\\geq$6)",
    "B1": "$D_3$ (+mass >0.5)",
    "A0": "$D_{\\mathrm{ref}}$",
    "A1": "$D_4$ ($-$friction)",
    "A2": "$D_5$ ($-$contacts)",
    "A3": "$D_6$ ($-$height)",
    "A4": "$D_7$ (height only)",
    "A5": "$D_8$ (contacts only)",
    "A6": "$D_9$ (friction only)",
}

SERIES = [
    ("LiftSlip",        "Lift Slip ($C_1$)",        "#2a78d6", "o"),
    ("ParallelArm",     "Parallel Arm ($C_2$)",     "#eb6834", "s"),
    ("CobotIndustrial", "Cobot Industrial ($C_3$)", "#1baf7a", "^"),
    ("LightweightArm",  "Lightweight Arm ($C_6$)",  "#c98500", "D"),
    ("CobotGrip",       "Cobot Lift Failure ($C_4$)", "#e87ba4", "v"),
]

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8.2,
    "axes.linewidth": 0.7,
    "xtick.major.width": 0.7,
    "ytick.major.width": 0.7,
})

fig, ax = plt.subplots(figsize=(7.0, 3.95), dpi=300)

x = list(range(len(ORDER)))
baseline_idx = ORDER.index("A0")

for key, name, color, marker in SERIES:
    ys = [DATA[pid][key] for pid in ORDER]
    ax.plot(x, ys, color=color, linewidth=1.4, marker=marker, markersize=4.6,
             markerfacecolor=color, markeredgecolor="white", markeredgewidth=0.6,
             zorder=3, label=name)

# Every point on every series is labeled (5 series x 10 columns = 50 labels).
# Per column: start every label AT its true value, nudged just enough to
# clear its OWN line (a small V_GAP push away from wherever that line is
# headed next -- see line_y_at/push_direction), then only move it further
# when it would collide with a neighbor, by the minimum amount that
# restores MIN_GAP. This keeps every label reading next to where its
# value actually sits on the y-axis (never snapped into a generic
# evenly-spaced stack) while still guaranteeing rank order, since the
# up/down-pass average below is isotonic (order-preserving).
LABEL_DX = 0.13
# Own-line push: the tightest constraint is at the text's LEFT edge
# (LABEL_DX) -- a rising line is at its lowest there (only climbs further
# away to the right); a falling line is at its highest there (only drops
# further away to the right).
V_GAP = 0.016
MIN_GAP = 0.034

def line_y_at(ys, i, dx):
    if i == len(ys) - 1:
        return ys[i]
    return ys[i] + (ys[i + 1] - ys[i]) * dx

def push_direction(ys, i):
    if i == len(ys) - 1:
        return 0
    return -1 if ys[i + 1] > ys[i] else 1

series_ys = {key: [DATA[pid][key] for pid in ORDER] for key, *_ in SERIES}

label_y = {}  # (i, key) -> final label y
for i in range(len(ORDER)):
    entries = []
    for key, *_ in SERIES:
        ys = series_ys[key]
        nudged = line_y_at(ys, i, LABEL_DX) + V_GAP * push_direction(ys, i)
        entries.append((key, nudged))
    entries.sort(key=lambda e: e[1])  # ascending, for the isotonic passes below
    targets = [v for _, v in entries]
    n = len(targets)
    # Push-up-only pass and push-down-only pass, each the smallest possible
    # move that enforces MIN_GAP; averaging the two centers each label
    # between them, which is the minimal-total-displacement compromise
    # that still keeps every gap >= MIN_GAP.
    up = [targets[0]] + [0.0] * (n - 1)
    for k in range(1, n):
        up[k] = max(targets[k], up[k - 1] + MIN_GAP)
    down = [0.0] * (n - 1) + [targets[-1]]
    for k in range(n - 2, -1, -1):
        down[k] = min(targets[k], down[k + 1] - MIN_GAP)
    for (key, val), u, d in zip(entries, up, down):
        label_y[(i, key)] = (u + d) / 2

# Pointwise manual nudges, in on-page pixels at this exact figsize/dpi/
# tight_layout rect (calibrated below -- see PX_PER_DATA_UNIT). dy: positive
# = up. dx: positive = right (added on top of LABEL_DX, so negative brings
# a label back toward its marker or past it to the left). Use this for
# one-off touch-ups the general spacing rules don't cover, rather than
# re-tuning the global constants for a single label.
PX_PER_DATA_UNIT = 1399.40  # ax height (px) / (ylim upper - lower), this layout
PX_PER_DATA_UNIT_X = 184.91  # ax width (px) / (xlim upper - lower), this layout
MANUAL_NUDGE_PX = {
    ("LiftSlip", "B3"): (26, 0),
    ("CobotIndustrial", "B3"): (19, 0),
    ("LiftSlip", "B2"): (40, 0),
    ("CobotIndustrial", "B2"): (26, 0),
    # At B1 ("+mass >0.5"): same order-inversion issue as A1 above --
    # Lift Slip's true value (0.899) is higher than Cobot Industrial's
    # (0.887), but Cobot Industrial's own-line push ended up larger,
    # rendering it above Lift Slip. Swap them and push Lift Slip further
    # clear of its own (steeply rising) line toward the baseline.
    ("LiftSlip", "B1"): (90, 0),
    ("CobotIndustrial", "B1"): (-25, 0),
    ("ParallelArm", "A0"): (55, -40),
    # At A1 ("-friction"): Parallel Arm's true value (1.000) is above
    # Lift Slip's (0.984), but Parallel Arm's line falls away much more
    # steeply right after this point, so its own-line push (which only
    # looks at slope, not the neighbor's value) ended up smaller than
    # Lift Slip's and the two rendered in the wrong vertical order. Swap
    # them back so rank order matches value order at this column too.
    ("LiftSlip", "A1"): (-30, 15),
    ("ParallelArm", "A1"): (48, 0),
    ("CobotIndustrial", "A1"): (-30, -70),
    # A5 ("contacts only"): same order-inversion pattern -- Parallel Arm's
    # true value (0.969) is above Lift Slip's (0.944), but rendered below
    # it. Swap, then nudge Lift Slip right per request.
    ("LiftSlip", "A5"): (-33, 15),
    ("ParallelArm", "A5"): (48, 0),
    ("CobotIndustrial", "A5"): (-15, -80),
    ("LightweightArm", "A5"): (0, -4),
    ("CobotGrip", "A2"): (-8, 0),
    ("ParallelArm", "A3"): (18, -90),
}
label_dx_extra = {}  # (i, key) -> extra dx in data units, on top of LABEL_DX
for (key, pid), (dy_px, dx_px) in MANUAL_NUDGE_PX.items():
    i = ORDER.index(pid)
    label_y[(i, key)] += dy_px / PX_PER_DATA_UNIT
    label_dx_extra[(i, key)] = dx_px / PX_PER_DATA_UNIT_X

def label(i, pid, key, color):
    val = DATA[pid][key]
    y = label_y[(i, key)]
    dx = LABEL_DX + label_dx_extra.get((i, key), 0.0)
    ax.annotate(f"{trunc3(val):.3f}", xy=(i, val), xytext=(i + dx, y),
                 fontsize=6.2, color=color, va="center", ha="left",
                 fontweight="bold",
                 annotation_clip=False, zorder=4)

for key, name, color, marker in SERIES:
    for i, pid in enumerate(ORDER):
        label(i, pid, key, color)

# baseline bracket (two dashed vertical lines) + label above the plot
ax.axvline(baseline_idx - 0.5, color="#9a9890", linestyle="--", linewidth=0.9, zorder=1)
ax.axvline(baseline_idx + 0.5, color="#9a9890", linestyle="--", linewidth=0.9, zorder=1)
ax.text(baseline_idx, 1.045, "Reference", ha="center", va="bottom", fontsize=7.3,
         fontweight="bold", color="#52514e", clip_on=False)

ax.set_xticks(x)
ax.set_xticklabels([XLABELS[p] for p in ORDER], fontsize=6.6,
                     rotation=28, ha="right", rotation_mode="anchor")
ax.set_xlim(-0.5, len(ORDER) - 0.15)
ax.set_ylim(0.45, 1.08)
ax.set_yticks([0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
ax.set_ylabel("Similarity", fontsize=8.5)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", color="#e1e0d9", linewidth=0.6, zorder=0)
ax.set_axisbelow(True)

legend = ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.01), ncol=5,
                     frameon=False, fontsize=6.9, handlelength=1.6,
                     columnspacing=1.0, handletextpad=0.5)

fig.tight_layout(rect=[0, 0.02, 1, 0.90])

out_png = "fig_rq2_a1_sandwich_similarity.png"
out_pdf = "fig_rq2_a1_sandwich_similarity.pdf"
fig.savefig(out_png, dpi=300, bbox_inches="tight")
fig.savefig(out_pdf, bbox_inches="tight")
print("saved:", out_png, out_pdf)
