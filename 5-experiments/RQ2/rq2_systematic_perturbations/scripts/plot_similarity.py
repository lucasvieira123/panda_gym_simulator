"""
Figure of Battery B: similarity of C1-C5 in each configuration, from output/similarity_scores.csv and
output/rankings.csv (written by run_selected_battery.py).

Same visual style as the RQ2 figure of Battery A (generate_rq2_plotly.py, whose palette, markers, fonts and
size are imported): x order B15..B1 | B0 | B16..B19, with B0 in a light band in the centre, the isolated
modifications mirrored on the left (B1 next to B0) and the combined ones on the right; only the three block
headers; one line per candidate through the 20 configurations as a reading guide only (every configuration is
derived from B0 alone); every marker filled, so the figure does not encode the Top-3 (rankings.csv holds it,
and the hover shows each rank); y axis from 0.4 to 1 (every score of the battery is above 0.4; the script
stops if one is not).

Labels: the figure shows configuration Bk of the CSVs as Dk (D0-D19), the notation of the paper. Only the
displayed text changes; the CSVs and this script keep the B identifiers.

Value labels: each score is written in light grey, without the leading zero (".913"), so that a reader can
tell which point it belongs to. A reader attaches a number to the nearest marker, so a label is clear when it is
close to its own marker and every other marker is clearly farther (Scene.clarity). No label touches a guide
line, a marker, a band edge or another label. Where no clear position next to the marker exists (two markers
that almost coincide inside a bundle of lines, the inside of a peak), the number stands in nearby open space
with a thin leader to its marker. In every column the labels read top to bottom in the order of the scores.
The placement is a global search (place_value_labels); it is checked independently before export, and each
label's position, distances and verdict are written to figures/rq2_similarity_value_labels.csv. The plot is
60 px taller than the Battery A figure, which removes four leaders and keeps the reading order in every
column. --no-values draws the figure without labels.

No value is computed here. Before exporting, the script checks that every plotted point is the CSV score
with the CSV rank, and stops on the first failed check.

Outputs, in figures/: rq2_similarity.html (interactive), .pdf, .svg and .png (scale 4: 3168 px wide, about
576 dpi at the 5.5 in of \\textwidth in acmsmall).

Usage, from the project root, with the project's venv:
    .venv/Scripts/python.exe 5-experiments/RQ2/rq2_systematic_perturbations/scripts/plot_similarity.py
"""
import csv
import math
import re
import sys
from pathlib import Path

import plotly.graph_objects as go

SCRIPTS = Path(__file__).resolve().parent
BATTERY = SCRIPTS.parent
sys.path.insert(0, str(BATTERY.parent))

from generate_rq2_plotly import (  # noqa: E402  (style of the Battery A figure)
    AXIS, BAND, BAND_EDGE, BLOCK_GAP, BLOCK_SHIFT, CANDIDATES, FONT, FONT_SIZE, GRID, GUIDE_ALPHA, GUIDE_WIDTH,
    HEIGHT, INK, INK_SECONDARY, MARGIN, MARKER_SIZE, SURFACE, WIDTH, Checks, hex_rgba,
)

OUTPUT, FIGURES = BATTERY / "output", BATTERY / "figures"
ISOLATED = [f"B{k}" for k in range(1, 16)]
COMBINED = [f"B{k}" for k in range(16, 20)]
BLOCKS = [("isolated", "Isolated modifications", list(reversed(ISOLATED))),
          ("reference", "Reference", ["B0"]),
          ("combined", "Combined modifications", COMBINED)]
Y_RANGE, Y_TICKS = (0.4, 1.02), [k / 10 for k in range(4, 11)]
# The combined block has 4 configurations (8 in Battery A): its header only fits on two lines, and the
# isolated one follows for symmetry. The extra line takes 18 px more at the top.
HEADER_TEXT = {"isolated": "Isolated<br>modifications", "reference": "Reference",
               "combined": "Combined<br>modifications"}
MARGIN_B = {**MARGIN, "t": MARGIN["t"] + 18}
HEIGHT_B = HEIGHT + 18 + 60   # +60 px of plot height: fewer leaders, value labels in reading order (see README)
LABEL_PREFIX = "D"   # displayed prefix: configuration Bk of the CSVs is shown as Dk

# Value labels: each score in light grey, touching its own marker. Similarity never exceeds 1, so the leading
# zero is dropped (".913"). Placement and the clarity criterion: see place_value_labels.
VALUE_FONT = 10                  # px; about 5 pt at \textwidth
VALUE_COLOR = "#8c8b85"
VALUE_BOX_H = 9.0                # height of a label's ink box: the 7.2 px digits plus 0.9 px above and below
VALUE_GAP_PX = 2.0               # between a label's box and the edge of its own marker
CLEARANCE_PX = 1.0               # kept free between a label's box and any line, marker, band edge or other label
CLEAR_RATIO = 2.5                # clear: every other marker is at least this many times as far from the label
CLEAR_MIN_EXTRA_PX = 3.0         # ... and at least this much farther than its own marker
MAX_OWN_PX = 10.0                # ... and the label is at most this far from its own marker (edge to edge)
LINE_HALF_PX = GUIDE_WIDTH / 2
OUTLINE_PX = 0.6                 # half the white outline drawn around every marker
PLOT_WIDTH_PX = WIDTH - MARGIN_B["l"] - MARGIN_B["r"]
PLOT_HEIGHT_PX = HEIGHT_B - MARGIN_B["t"] - MARGIN_B["b"]
LEFT_PAD = {True: 1.0, False: 0.6}   # x units beyond the first and last columns (room for their labels)
# Arial advance widths, in em, of the characters a value label uses
CHAR_EM = {**{str(k): 0.556 for k in range(10)}, ".": 0.278}
# Positions tried around each marker and the preference among equally clear ones (lower is preferred). Left
# comes first, so that most labels read the same way; above/below suit two markers that almost touch.
SIDE_PREFERENCE = {"left": 0.0, "above": 1.0, "below": 1.0, "right": 2.0,
                   "above-left": 3.0, "below-left": 3.0, "above-right": 4.0, "below-right": 4.0}


def shown(text: str) -> str:
    """Bk -> Dk in displayed text (tick labels, hover)."""
    return re.sub(r"\bB(\d+)\b", LABEL_PREFIX + r"\1", text)


def value_text(score: float) -> str:
    return f"{score:.3f}".removeprefix("0")


def text_width_px(text: str) -> float:
    return sum(CHAR_EM[c] for c in text) * VALUE_FONT


class Pixels:
    """Plot-area pixel coordinates (origin at the bottom-left corner of the plot area, y upwards)."""

    def __init__(self, x_range: tuple[float, float]):
        self.x0, self.kx = x_range[0], PLOT_WIDTH_PX / (x_range[1] - x_range[0])
        self.y0, self.ky = Y_RANGE[0], PLOT_HEIGHT_PX / (Y_RANGE[1] - Y_RANGE[0])

    def x(self, value: float) -> float:
        return (value - self.x0) * self.kx

    def y(self, value: float) -> float:
        return (value - self.y0) * self.ky

    def score(self, py: float) -> float:
        return self.y0 + py / self.ky

    def data_x(self, px_x: float) -> float:
        return self.x0 + px_x / self.kx


# Geometry in pixels: a box is (left, right, bottom, top)

def segment_hits_box(a: tuple, b: tuple, box: tuple, pad: float) -> bool:
    """Whether segment a-b passes through the box grown by pad (Liang-Barsky clipping)."""
    left, right, bottom, top = box[0] - pad, box[1] + pad, box[2] - pad, box[3] + pad
    (x0, y0), (x1, y1) = a, b
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0 - left), (dx, right - x0), (-dy, y0 - bottom), (dy, top - y0)):
        if p == 0:
            if q < 0:
                return False
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return False
    return True


def distance_to_box(point: tuple, box: tuple) -> float:
    dx = max(box[0] - point[0], 0.0, point[0] - box[1])
    dy = max(box[2] - point[1], 0.0, point[1] - box[3])
    return math.hypot(dx, dy)


def boxes_overlap(a: tuple, b: tuple, pad: float) -> bool:
    return a[0] < b[1] + pad and b[0] < a[1] + pad and a[2] < b[3] + pad and b[2] < a[3] + pad


def box_centre(box: tuple) -> tuple[float, float]:
    return (box[0] + box[1]) / 2, (box[2] + box[3]) / 2


GAPS_PX = (VALUE_GAP_PX, 4.0, 7.0, 10.0)   # distances tried between a label and its marker, nearest first


def candidate_boxes(x: float, y: float, r: float, w: float, h: float) -> list[tuple[str, float, float, tuple]]:
    """(side, nudge, gap, box) of every position tried around a marker of radius r at (x, y): eight sides,
    small nudges along the side, and the distances of GAPS_PX (touching first)."""
    out = []
    for g in GAPS_PX:
        k = 0.707 * (r + g)
        for dy in (0.0, 1.5, -1.5, 3.0, -3.0):
            out.append(("left", dy, g, (x - r - g - w, x - r - g, y - h / 2 + dy, y + h / 2 + dy)))
            out.append(("right", dy, g, (x + r + g, x + r + g + w, y - h / 2 + dy, y + h / 2 + dy)))
        for dx in (0.0, 2.0, -2.0, 4.0, -4.0, 6.0, -6.0):
            out.append(("above", dx, g, (x - w / 2 + dx, x + w / 2 + dx, y + r + g, y + r + g + h)))
            out.append(("below", dx, g, (x - w / 2 + dx, x + w / 2 + dx, y - r - g - h, y - r - g)))
        out += [("above-left", 0.0, g, (x - k - w, x - k, y + k, y + k + h)),
                ("below-left", 0.0, g, (x - k - w, x - k, y - k - h, y - k)),
                ("above-right", 0.0, g, (x + k, x + k + w, y + k, y + k + h)),
                ("below-right", 0.0, g, (x + k, x + k + w, y - k - h, y - k))]
    return out


class Scene:
    """Everything a value label must not touch, and the markers a reader could attach it to."""

    def __init__(self, data: dict, geo: dict):
        xs, cells = geo["xs"], data["cells"]
        self.px = px = Pixels(geo["x_range"])
        path = order_by_x(xs)
        self.markers = {(d, c): (px.x(xs[d]), px.y(float(cells[d, c]["score"])),
                                 MARKER_SIZE[CANDIDATES[c][2]] / 2 + OUTLINE_PX)
                        for d in path for c in CANDIDATES}
        self.segments = [(self.markers[a, c][:2], self.markers[b, c][:2])
                         for a, b in zip(path, path[1:]) for c in CANDIDATES]
        self.band_edges = [px.x(x) for x in geo["band"]]

    def static_conflict(self, box: tuple) -> str:
        """Why the box cannot be used, ignoring the other labels; '' if it can."""
        cx, cy = box_centre(box)
        if not (0 <= box[0] and box[1] <= PLOT_WIDTH_PX and 0 <= box[2] and 0 <= cy <= PLOT_HEIGHT_PX
                and box[3] <= PLOT_HEIGHT_PX + 4):
            return "outside the plot"
        if any(segment_hits_box(a, b, box, LINE_HALF_PX + CLEARANCE_PX) for a, b in self.segments):
            return "line"
        if any(distance_to_box((mx, my), box) < r + CLEARANCE_PX for mx, my, r in self.markers.values()):
            return "marker"
        if any(box[0] - CLEARANCE_PX < xe < box[1] + CLEARANCE_PX for xe in self.band_edges):
            return "band edge"
        return ""

    def clarity(self, key: tuple, box: tuple) -> dict:
        """Distance (edge to edge) from the label to its own marker and to the nearest other marker.

        Clear, by relative proximity (what the eye uses to attach a number to a point): the label is at most
        MAX_OWN_PX from its own marker, and the nearest other marker is at least CLEAR_RATIO times as far and
        CLEAR_MIN_EXTRA_PX farther. A label touching its marker (2 px) needs every other marker 5 px or more
        away; a label 10 px away needs them 25 px away.
        """
        mx, my, r = self.markers[key]
        own = distance_to_box((mx, my), box) - r
        nearest, who = min((distance_to_box((ox, oy), box) - orr, k)
                           for k, (ox, oy, orr) in self.markers.items() if k != key)
        needed = max(CLEAR_RATIO * own, own + CLEAR_MIN_EXTRA_PX)
        return {"own_px": own, "other_px": nearest, "nearest_other": who, "margin_px": nearest - own,
                "needed_px": needed - own, "clear": own <= MAX_OWN_PX + 0.01 and nearest >= needed - 0.01}


LEADER_SEARCH_PX = 46            # farthest a label with a leader may sit from its marker, in x and in y
LEADER_STEP_PX = 2.0             # grid step of the positions tried for a label with a leader
LEADER_WIDTH = 0.6               # px; thin and in the label colour, so it reads as part of the label
LEADER_CROSSING_COST = 15.0      # cost of a leader crossing a guide line, in px of leader length
LEADER_AMBIGUITY_PX = 8.0        # a label with a leader should be this much nearer its own marker than any other
LEADER_AMBIGUITY_COST = 4.0      # cost per px short of that, in px of leader length
LEADER_BASE_COST = 25.0          # a leader is used only where no clear position next to the marker is free
LEADER_WHEN_CLEAR_BELOW = 8      # labels with fewer clear positions than this also get leader candidates
LEADER_CANDIDATES = 200          # cheapest leader positions kept per label
LEADER_AMBIGUITY_CAP = 6.0       # beyond this, nearness to the own marker no longer pays: isolation does
LEADER_ISOLATION_PX = 9.0        # a label with a leader keeps at least this from every other marker ...
LEADER_CROWDING_COST = 6.0       # ... or pays this per px short
UNCLEAR_BASE_COST = 400.0        # a position next to the marker that is not clear: only if nothing else fits
ORDER_COST = 8.0                 # a label set below the label of a lower score of the same column
CONFLICT_COST = 1000.0           # two labels touching (must not remain in the result)
SEARCH_SEED, SEARCH_ITERATIONS, SEARCH_T0, SEARCH_T1 = 7, 400_000, 40.0, 0.05


def segments_cross(a: tuple, b: tuple, c: tuple, d: tuple) -> bool:
    """Whether segments a-b and c-d intersect (proper or touching)."""
    def orient(p, q, r):
        v = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        return (v > 1e-9) - (v < -1e-9)
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    return o1 != o2 and o3 != o4


def leader_for(marker: tuple, r: float, box: tuple) -> tuple[tuple, tuple]:
    """Leader from just outside the marker's edge to 1 px short of the nearest point of the label box."""
    mx, my = marker
    bx, by = min(max(mx, box[0]), box[1]), min(max(my, box[2]), box[3])
    dx, dy = bx - mx, by - my
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    return (mx + ux * (r + 0.5), my + uy * (r + 0.5)), (bx - ux * 1.0, by - uy * 1.0)


def place_value_labels(data: dict, geo: dict) -> tuple[dict, list[dict], list[dict]]:
    """Place every value label so that a reader can tell which point it belongs to.

    Clarity. A reader attaches a number to the marker nearest to it (Scene.clarity): a label next to its marker
    is clear when it is close to it and every other marker is clearly farther. Where no such position exists
    (two markers that almost coincide inside a bundle of lines, the inside of a peak), the label sits in the
    nearest free spot and a thin leader joins it to its marker; even then the number should be nearer to its
    own marker than to any other (LEADER_AMBIGUITY_PX), because readers look at the number first.

    Hard constraints, for every label: it touches no guide line, marker, band edge, other label or leader
    (CLEARANCE_PX kept free), stays in the plot, and its leader crosses no other label or leader.

    Candidates per label: the positions of candidate_boxes free of lines, markers and band edges, and, for
    labels with few clear positions, leader positions on a LEADER_STEP_PX grid within LEADER_SEARCH_PX.
    Each candidate has a cost: a clear position next to the marker is cheap (side preference, nudge, distance,
    margin); an unclear one is expensive; a leader costs LEADER_BASE_COST plus its length, its guide-line
    crossings and the ambiguity of the number's spot. A label set below the label of a lower score of the same
    column costs ORDER_COST (reading order).

    Search: simulated annealing over the choice of every label (fixed seed, so the result is reproducible),
    minimising the total cost plus a large penalty per conflict between two labels; then a greedy polish that
    moves each label to its best position compatible with the others until nothing improves. The result must be
    free of conflicts.

    Returns the placement ((configuration, candidate) -> (text, centre x px, centre y px, side, leader or
    None)), one report row per label, and a log with the search summary.
    """
    import random

    xs, cells = geo["xs"], data["cells"]
    scene = Scene(data, geo)
    path = order_by_x(xs)
    keys = sorted(scene.markers, key=lambda k: (path.index(k[0]), k[1]))
    index = {k: i for i, k in enumerate(keys)}
    texts = {k: value_text(float(cells[k]["score"])) for k in keys}
    widths = {k: text_width_px(texts[k]) for k in keys}
    scores = {k: float(cells[k]["score"]) for k in keys}

    def near_segments(box: tuple, reach: float) -> list:
        return [(a, b) for a, b in scene.segments
                if min(a[0], b[0]) - reach <= box[1] and max(a[0], b[0]) + reach >= box[0]]

    # Candidates
    cands: list[list[dict]] = []
    for k in keys:
        mx, my, r = scene.markers[k]
        opts = []
        for side, nudge, gap, box in candidate_boxes(mx, my, r, widths[k], VALUE_BOX_H):
            if scene.static_conflict(box):
                continue
            cl = scene.clarity(k, box)
            if cl["clear"]:
                cost = (SIDE_PREFERENCE[side] + 0.4 * abs(nudge) + cl["own_px"]
                        - 0.3 * min(cl["margin_px"] - cl["needed_px"], 10))
            else:
                cost = UNCLEAR_BASE_COST + 8.0 * (cl["needed_px"] + cl["own_px"] - cl["other_px"])
            opts.append({"side": side, "nudge": nudge, "gap": gap, "box": box, "leader": None, "crossings": 0,
                         "cost": cost, **cl})
        if sum(o["clear"] for o in opts) < LEADER_WHEN_CLEAR_BELOW:
            steps = int(LEADER_SEARCH_PX / LEADER_STEP_PX)
            leader_opts = []
            for i in range(-steps, steps + 1):
                for j in range(-steps, steps + 1):
                    cx, cy = mx + i * LEADER_STEP_PX, my + j * LEADER_STEP_PX
                    box = (cx - widths[k] / 2, cx + widths[k] / 2, cy - VALUE_BOX_H / 2, cy + VALUE_BOX_H / 2)
                    if scene.static_conflict(box):
                        continue
                    start, end = leader_for((mx, my), r, box)
                    length = math.hypot(end[0] - start[0], end[1] - start[1])
                    if length < 3:
                        continue
                    if any(segment_hits_box(start, end, (ox - orr, ox + orr, oy - orr, oy + orr), 0) and
                           math.hypot(*(lambda t: (start[0] + t * (end[0] - start[0]) - ox,
                                                   start[1] + t * (end[1] - start[1]) - oy))(
                               max(0.0, min(1.0, ((ox - start[0]) * (end[0] - start[0]) + (oy - start[1]) *
                                                  (end[1] - start[1])) / (length ** 2))))) < orr
                           for kk, (ox, oy, orr) in scene.markers.items() if kk != k):
                        continue
                    crossings = sum(segments_cross(start, end, a, b) for a, b in scene.segments)
                    cl = scene.clarity(k, box)
                    # the number should be nearer its own marker than any other; where that is impossible, it
                    # should at least stand in open space, away from every other marker, so that only the
                    # leader attaches it
                    ambiguity = max(0.0, cl["own_px"] + LEADER_AMBIGUITY_PX - cl["other_px"])
                    crowding = max(0.0, LEADER_ISOLATION_PX - cl["other_px"])
                    cost = (LEADER_BASE_COST + length + LEADER_CROSSING_COST * crossings
                            + LEADER_AMBIGUITY_COST * min(ambiguity, LEADER_AMBIGUITY_CAP)
                            + LEADER_CROWDING_COST * crowding)
                    leader_opts.append({"side": "leader", "nudge": 0.0, "gap": length, "box": box,
                                        "leader": (start, end), "crossings": crossings, "cost": cost, **cl})
            opts += sorted(leader_opts, key=lambda o: o["cost"])[:LEADER_CANDIDATES]
        if not opts:
            raise SystemExit(f"[FAIL] value label {shown(k[0])}/{k[1]} has no position free of lines and markers")
        cands.append(opts)

    # Conflicts between candidates of labels that could meet
    def conflict(o: dict, p: dict) -> bool:
        if boxes_overlap(o["box"], p["box"], CLEARANCE_PX):
            return True
        if o["leader"] and segment_hits_box(*o["leader"], p["box"], CLEARANCE_PX):
            return True
        if p["leader"] and segment_hits_box(*p["leader"], o["box"], CLEARANCE_PX):
            return True
        return bool(o["leader"] and p["leader"] and segments_cross(*o["leader"], *p["leader"]))

    def reach(o: dict) -> tuple:
        xs_ = [o["box"][0], o["box"][1]] + ([o["leader"][0][0], o["leader"][1][0]] if o["leader"] else [])
        ys_ = [o["box"][2], o["box"][3]] + ([o["leader"][0][1], o["leader"][1][1]] if o["leader"] else [])
        return min(xs_), max(xs_), min(ys_), max(ys_)

    extents = [reach_all for reach_all in
               ((min(reach(o)[0] for o in c), max(reach(o)[1] for o in c),
                 min(reach(o)[2] for o in c), max(reach(o)[3] for o in c)) for c in cands)]
    neighbours = [[j for j in range(len(keys)) if j != i and boxes_overlap(extents[i], extents[j], CLEARANCE_PX)]
                  for i in range(len(keys))]
    conflicts: dict = {}
    for i in range(len(keys)):
        for j in neighbours[i]:
            if j > i:
                table = [[conflict(o, p) for p in cands[j]] for o in cands[i]]
                conflicts[i, j] = table

    def clash(i: int, a: int, j: int, b: int) -> bool:
        return conflicts[i, j][a][b] if i < j else conflicts[j, i][b][a]

    column_mates = [[j for j in range(len(keys)) if j != i and keys[j][0] == keys[i][0]] for i in range(len(keys))]

    def inverted(i: int, a: int, j: int, b: int) -> bool:
        yi, yj = box_centre(cands[i][a]["box"])[1], box_centre(cands[j][b]["box"])[1]
        si, sj = scores[keys[i]], scores[keys[j]]
        return (si > sj and yi < yj) or (si < sj and yi > yj)

    def local_energy(i: int, a: int, choice: list) -> float:
        e = cands[i][a]["cost"]
        e += CONFLICT_COST * sum(clash(i, a, j, choice[j]) for j in neighbours[i])
        e += ORDER_COST * sum(inverted(i, a, j, choice[j]) for j in column_mates[i])
        return e

    # Start: every label at its cheapest candidate; then simulated annealing
    rng = random.Random(SEARCH_SEED)
    choice = [min(range(len(c)), key=lambda a: c[a]["cost"]) for c in cands]
    temperature, cooling = SEARCH_T0, (SEARCH_T1 / SEARCH_T0) ** (1 / SEARCH_ITERATIONS)
    for _ in range(SEARCH_ITERATIONS):
        i = rng.randrange(len(keys))
        a_new = rng.randrange(len(cands[i]))
        if a_new == choice[i]:
            temperature *= cooling
            continue
        delta = local_energy(i, a_new, choice) - local_energy(i, choice[i], choice)
        if delta <= 0 or rng.random() < math.exp(-delta / temperature):
            choice[i] = a_new
        temperature *= cooling

    # Greedy polish until no label can move to a better compatible position
    improved = True
    while improved:
        improved = False
        for i in range(len(keys)):
            best = min(range(len(cands[i])), key=lambda a: (local_energy(i, a, choice), a))
            if local_energy(i, best, choice) < local_energy(i, choice[i], choice) - 1e-9:
                choice[i] = best
                improved = True

    remaining = [(keys[i], keys[j]) for i in range(len(keys)) for j in neighbours[i]
                 if j > i and clash(i, choice[i], j, choice[j])]
    if remaining:
        raise SystemExit(f"[FAIL] value labels still in conflict: {remaining[:5]}")

    placed = {keys[i]: cands[i][choice[i]] for i in range(len(keys))}
    report = []
    for k in keys:
        o = placed[k]
        cy = box_centre(o["box"])[1]
        same = [(scores[kk], box_centre(p["box"])[1]) for kk, p in placed.items() if kk[0] == k[0] and kk != k]
        report.append({"configuration": k[0], "label": shown(k[0]), "candidate": k[1], "text": texts[k],
                       "placement": "leader" if o["leader"] else "next to the marker", "side": o["side"],
                       "gap_or_leader_px": round(o["gap"], 1), "own_marker_px": round(o["own_px"], 1),
                       "nearest_other_marker": f"{shown(o['nearest_other'][0])}/{o['nearest_other'][1]}",
                       "nearest_other_px": round(o["other_px"], 1),
                       "clear": "by leader" if o["leader"] else o["clear"],
                       "leader_crossings": o["crossings"] if o["leader"] else "",
                       "reading_order_ok": all((scores[k] > other) == (cy > oy) for other, oy in same)})
    log = [{"candidates": sum(len(c) for c in cands), "labels_with_leader_candidates":
            sum(any(o["leader"] for o in c) for c in cands), "iterations": SEARCH_ITERATIONS, "seed": SEARCH_SEED,
            "total_cost": round(sum(local_energy(i, choice[i], choice) for i in range(len(keys))), 1)}]
    placement = {k: (texts[k], *box_centre(o["box"]), o["side"], o["leader"]) for k, o in placed.items()}
    return placement, report, log


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load(check: Checks) -> dict:
    scores, rankings = read_csv(OUTPUT / "similarity_scores.csv"), read_csv(OUTPUT / "rankings.csv")
    design = {r["configuration"]: r for r in read_csv(OUTPUT / "selected_diagnoses.csv")}
    order = [d for _, _, ids in BLOCKS for d in ids]
    cells = {(r["configuration"], r["candidate"]): r for r in scores}
    check(len(cells) == len(scores) == 5 * len(order) and set(cells) == {(d, c) for d in order for c in CANDIDATES},
          f"similarity_scores.csv has one score for each of C1-C5 in every configuration ({len(scores)} scores)")
    check(all(math.isfinite(float(r["score"])) and 0 <= float(r["score"]) <= 1 for r in scores),
          "every score is a finite number in [0, 1]")
    lowest = min(float(r["score"]) for r in scores)
    check(Y_RANGE[0] <= lowest, f"every score is inside the y axis (lowest {lowest:.4f} >= {Y_RANGE[0]})")
    ranking = {r["configuration"]: r for r in rankings}
    check(all(ranking[d]["ranking"].split(" > ") ==
              sorted(CANDIDATES, key=lambda c: int(cells[d, c]["rank"])) for d in order),
          "the ranking in rankings.csv is the order of the ranks in similarity_scores.csv")
    return {"order": order, "cells": cells, "ranking": ranking, "design": design}


def geometry(values: bool) -> dict:
    xs, x = {}, 0.0
    for b, (_, _, ids) in enumerate(BLOCKS):
        x += BLOCK_GAP if b else 0
        for d in ids:
            xs[d] = x
            x += 1
    band = ((xs["B1"] + xs["B0"]) / 2, (xs["B0"] + xs["B16"]) / 2)
    return {"xs": xs, "band": band,
            "x_range": (min(xs.values()) - LEFT_PAD[values], max(xs.values()) + LEFT_PAD[values])}


def order_by_x(xs: dict) -> list[str]:
    return sorted(xs, key=xs.get)


def hover(data: dict, d: str, cid: str) -> list:
    row, design = data["cells"][d, cid], data["design"][d]
    what = "Reference" if d == "B0" else (
        f"{design['category']} · {design['perturbation']}"
        + (f" ({shown(design['composition'])})" if design["composition"] else ""))
    # customdata[0] keeps the CSV identifier (checked by validate); customdata[5] is the displayed label
    return [d, cid, what, int(row["rank"]), f"{float(row['delta_vs_B0']):+.4f}", shown(d)]


def build(data: dict, geo: dict, placement: dict | None) -> go.Figure:
    xs, cells = geo["xs"], data["cells"]
    path = order_by_x(xs)
    fig = go.Figure()
    fig.add_shape(type="rect", xref="x", yref="paper", x0=geo["band"][0], x1=geo["band"][1], y0=0, y1=1,
                  fillcolor=BAND, line_width=0, layer="below")
    for xb in geo["band"]:
        fig.add_shape(type="line", xref="x", yref="paper", x0=xb, x1=xb, y0=0, y1=1, layer="between",
                      line={"color": BAND_EDGE, "width": 1})

    for cid, (_, color, _) in CANDIDATES.items():   # reading guides, under the points
        fig.add_trace(go.Scatter(
            x=[xs[d] for d in path], y=[float(cells[d, cid]["score"]) for d in path], mode="lines",
            line={"color": hex_rgba(color, GUIDE_ALPHA), "width": GUIDE_WIDTH}, legendgroup=cid, showlegend=False,
            hoverinfo="skip", meta={"kind": "guide", "candidate": cid}))
    # Every marker filled. Drawn from C5 to C1, so that where two points meet the higher-ranked candidate
    # of the reference is on top; the white outline keeps overlapping markers apart.
    for cid, (name, color, symbol) in reversed(list(CANDIDATES.items())):
        fig.add_trace(go.Scatter(
            x=[xs[d] for d in path], y=[float(cells[d, cid]["score"]) for d in path], mode="markers",
            cliponaxis=False, legendgroup=cid, showlegend=False,
            marker={"symbol": symbol, "size": MARKER_SIZE[symbol], "color": color,
                    "line": {"color": SURFACE, "width": 1.2}},
            customdata=[hover(data, d, cid) for d in path],
            hovertemplate=(f"<b>%{{customdata[5]}}</b> · %{{customdata[2]}}<br>{cid} {name}<br>"
                           "Similarity: %{y:.4f}<br>Rank: %{customdata[3]} of 5<br>"
                           f"Δ vs {shown('B0')}: %{{customdata[4]}}<extra></extra>"),
            meta={"kind": "points", "candidate": cid}))

    for cid, (name, color, symbol) in CANDIDATES.items():
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="lines+markers", name=f"{cid} {name}", legendgroup=cid, legend="legend",
            line={"color": hex_rgba(color, GUIDE_ALPHA), "width": GUIDE_WIDTH},
            marker={"symbol": symbol, "size": MARKER_SIZE[symbol], "color": color,
                    "line": {"color": SURFACE, "width": 1.2}}, meta={"kind": "legend"}))

    for block, _, ids in BLOCKS:
        fig.add_annotation(x=(xs[ids[0]] + xs[ids[-1]]) / 2, y=1, xref="x", yref="paper", yanchor="bottom",
                           yshift=BLOCK_SHIFT, text=HEADER_TEXT[block], showarrow=False, name="block",
                           font={"size": FONT_SIZE["header"], "color": INK_SECONDARY})

    if placement:   # value labels, each touching its own marker (place_value_labels)
        px = Pixels(geo["x_range"])
        for (d, cid), (text, cx, cy, side, leader) in placement.items():
            fig.add_annotation(x=xs[d], y=px.score(cy), xref="x", yref="y", xanchor="center", yanchor="middle",
                               xshift=cx - px.x(xs[d]), showarrow=False, name=f"value:{d}:{cid}:{side}", text=text,
                               borderpad=0, font={"size": VALUE_FONT, "color": VALUE_COLOR})
            if leader:
                (x0, y0), (x1, y1) = leader
                fig.add_shape(type="line", xref="x", yref="y", x0=px.data_x(x0), y0=px.score(y0),
                              x1=px.data_x(x1), y1=px.score(y1), layer="above", name=f"leader:{d}:{cid}",
                              line={"color": VALUE_COLOR, "width": LEADER_WIDTH})

    legend_common = {"orientation": "h", "xref": "paper", "yref": "container", "y": 0.012, "yanchor": "bottom",
                     "bgcolor": "rgba(0,0,0,0)", "font": {"size": FONT_SIZE["legend"], "color": INK}}
    fig.update_layout(
        width=WIDTH, height=HEIGHT_B, margin=MARGIN_B, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font={"family": FONT, "size": FONT_SIZE["base"], "color": INK},
        legend={**legend_common, "x": 0, "xanchor": "left", "traceorder": "normal", "itemwidth": 30,
                "entrywidth": 0.5, "entrywidthmode": "fraction"},
        hovermode="closest",
        hoverlabel={"bgcolor": SURFACE, "bordercolor": AXIS,
                    "font": {"family": FONT, "size": FONT_SIZE["hover"], "color": INK}})
    fig.update_xaxes(
        tickmode="array", tickvals=[xs[d] for d in path],
        ticktext=[f"<b>{shown(d)}</b>" if d == "B0" else shown(d) for d in path], range=list(geo["x_range"]),
        showgrid=False,
        zeroline=False, showline=True, linecolor=AXIS, linewidth=1, ticks="outside", ticklen=4, tickcolor=AXIS,
        tickfont={"size": FONT_SIZE["tick"], "color": INK_SECONDARY},
        title={"text": "Diagnostic Configurations", "standoff": 10,
               "font": {"size": FONT_SIZE["axis_title"], "color": INK_SECONDARY}})
    fig.update_yaxes(
        range=list(Y_RANGE), tickvals=Y_TICKS, tickformat=".1f", showgrid=True, gridcolor=GRID, zeroline=False,
        showline=False, ticks="", tickfont={"size": FONT_SIZE["tick"], "color": INK_SECONDARY},
        title={"text": "Similarity Score", "standoff": 8,
               "font": {"size": FONT_SIZE["axis_title"], "color": INK_SECONDARY}})
    return fig


def validate(fig: go.Figure, data: dict, geo: dict, values: bool, check: Checks) -> None:
    xs, cells = geo["xs"], data["cells"]
    expected = list(reversed(ISOLATED)) + ["B0"] + COMBINED
    inside = [d for d in xs if geo["band"][0] < xs[d] < geo["band"][1]]
    check(order_by_x(xs) == expected and inside == ["B0"],
          "x order is B15..B1 | B0 | B16..B19 (B1 and B16 next to B0); only B0 inside the reference band")
    labels = [t.replace("<b>", "").replace("</b>", "") for t in fig.layout.xaxis.ticktext]
    check(labels == [LABEL_PREFIX + d[1:] for d in expected] and not any(l.startswith("B") for l in labels),
          f"tick labels show each Bk as {LABEL_PREFIX}k, in the same order (D15..D1 | D0 | D16..D19)")
    kinds = {k: [t for t in fig.data if (t.meta or {}).get("kind") == k] for k in ("points", "guide", "legend")}
    check(sum(map(len, kinds.values())) == len(fig.data), "every trace is tagged as points, guide or legend")
    seen = []
    for t in kinds["points"]:
        cid = t.meta["candidate"]
        for x, y, cd in zip(t.x, t.y, t.customdata):
            d = cd[0]
            seen.append((d, cid))
            if not (x == xs[d] and y == float(cells[d, cid]["score"]) and cd[3] == int(cells[d, cid]["rank"])):
                check(False, f"point {d}/{cid} does not match similarity_scores.csv")
    check(sorted(seen) == sorted(cells), f"{len(seen)} points, one per (configuration, candidate), each at the "
          "CSV score, with the CSV rank in the hover")
    check(all(t.marker.color == CANDIDATES[t.meta["candidate"]][1] for t in kinds["points"]),
          "every marker is filled with its candidate's colour")
    check(not any(t.legend == "legend2" for t in fig.data) and len(kinds["legend"]) == len(CANDIDATES),
          "the legend lists only the five candidates")
    path = order_by_x(xs)
    check(all(list(t.x) == [xs[d] for d in path] and list(t.y) == [float(cells[d, t.meta["candidate"]]["score"])
                                                                   for d in path] for t in kinds["guide"])
          and sorted(t.meta["candidate"] for t in kinds["guide"]) == sorted(CANDIDATES),
          "one guide line per candidate through the 20 configurations in x order, joining the CSV scores")
    check(all(all(v is None for v in t.x) for t in kinds["legend"]), "legend-only traces draw nothing")
    headers = [a for a in fig.layout.annotations if a.name == "block"]
    check([a.text.replace("<br>", " ") for a in headers] == [t for _, t, _ in BLOCKS],
          "the only text above the plot is the three block headers")

    value_labels = [a for a in fig.layout.annotations if (a.name or "").startswith("value:")]
    check(len(headers) + len(value_labels) == len(fig.layout.annotations), "every annotation is a header or a value")
    if not values:
        check(not value_labels, "no value labels (--no-values)")
        return
    # Independent check, from the annotations as drawn: content, contacts, clarity and reading order
    px = Pixels(geo["x_range"])
    scene = Scene(data, geo)
    boxes, sides = {}, {}
    for a in value_labels:
        _, d, cid, side = a.name.split(":")
        score = float(cells[d, cid]["score"])
        if not (a.text == value_text(score) and a.x == xs[d] and Y_RANGE[0] < a.y < Y_RANGE[1]):
            check(False, f"value label {d}/{cid} does not show the CSV score at its configuration, inside the y axis")
        cx, cy, w = px.x(a.x) + a.xshift, px.y(a.y), text_width_px(a.text)
        boxes[d, cid] = (cx - w / 2, cx + w / 2, cy - VALUE_BOX_H / 2, cy + VALUE_BOX_H / 2)
        sides[d, cid] = side
    check(sorted(boxes) == sorted(cells), f"{len(boxes)} value labels, one per point, each with its CSV score "
          f"({value_text(0.9126)} style)")

    contacts = []
    keys = sorted(boxes)
    for i, k in enumerate(keys):
        box = boxes[k]
        if any(segment_hits_box(p, q, box, LINE_HALF_PX) for p, q in scene.segments):
            contacts.append(f"{shown(k[0])}/{k[1]} on a line")
        if any(distance_to_box((mx, my), box) < r for mx, my, r in scene.markers.values()):
            contacts.append(f"{shown(k[0])}/{k[1]} on a marker")
        if any(box[0] < xe < box[1] for xe in scene.band_edges):
            contacts.append(f"{shown(k[0])}/{k[1]} on a band edge")
        contacts += [f"{shown(k[0])}/{k[1]} on {shown(o[0])}/{o[1]}" for o in keys[i + 1:]
                     if boxes_overlap(box, boxes[o], 0)]
    check(not contacts, f"no value label touches a guide line, a marker, a band edge or another label "
          f"({len(contacts)} contacts{': ' + ', '.join(contacts[:5]) if contacts else ''})")

    # Leaders: each joins its own marker to its own label, and touches no other marker, label or leader
    leader_shapes = {tuple(s.name.split(":")[1:]): s for s in fig.layout.shapes if (s.name or "").startswith("leader:")}
    segs = {}
    bad_leaders, crossings = [], 0
    for k, s in leader_shapes.items():
        a, b = (px.x(s.x0), px.y(s.y0)), (px.x(s.x1), px.y(s.y1))
        segs[k] = (a, b)
        mx, my, r = scene.markers[k]
        starts_at_marker = abs(math.hypot(a[0] - mx, a[1] - my) - (r + 0.5)) < 0.05
        ends_at_label = distance_to_box(b, boxes[k]) <= 1.05
        hits_marker = any(segment_hits_box(a, b, (ox - orr, ox + orr, oy - orr, oy + orr), 0) and
                          distance_to_box((ox, oy), (min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]),
                                                     max(a[1], b[1]))) < orr
                          for kk, (ox, oy, orr) in scene.markers.items() if kk != k)
        hits_label = any(segment_hits_box(a, b, box, 0) for kk, box in boxes.items() if kk != k)
        if not (starts_at_marker and ends_at_label) or hits_marker or hits_label:
            bad_leaders.append(f"{shown(k[0])}/{k[1]}")
        crossings += sum(segments_cross(a, b, p, q) for p, q in scene.segments)
    bad_leaders += [f"{shown(k[0])}/{k[1]} x {shown(o[0])}/{o[1]}" for i, k in enumerate(sorted(segs))
                    for o in sorted(segs)[i + 1:] if segments_cross(*segs[k], *segs[o])]
    check(not bad_leaders, f"{len(segs)} leaders, each from its own marker to its own label, touching no other "
          f"marker, label or leader; together they cross {crossings} guide line(s)"
          + (f"; faulty: {', '.join(bad_leaders)}" if bad_leaders else ""))

    unclear, margins = [], []
    for k, box in boxes.items():
        if k in segs:
            continue
        cl = scene.clarity(k, box)
        margins.append(cl["margin_px"])
        if not cl["clear"]:
            unclear.append(f"{shown(k[0])}/{k[1]} (own {cl['own_px']:.1f} px, "
                           f"{shown(cl['nearest_other'][0])}/{cl['nearest_other'][1]} at {cl['other_px']:.1f} px)")
    check(not unclear, f"clarity: all {len(boxes) - len(segs)} labels next to their marker are clear (own marker at "
          f"most {MAX_OWN_PX:g} px away; every other marker {CLEAR_RATIO:g}x as far and {CLEAR_MIN_EXTRA_PX:g} px "
          f"farther; smallest margin {min(margins):.1f} px); the other {len(segs)} are joined by a leader"
          + (f"; not clear: {', '.join(unclear)}" if unclear else ""))
    inverted = [d for d in {k[0] for k in boxes}
                if [c for c in sorted(CANDIDATES, key=lambda c: -float(cells[d, c]["score"]))] !=
                sorted(CANDIDATES, key=lambda c: -(boxes[d, c][2] + boxes[d, c][3]))]
    check(True, f"reading order: in {20 - len(inverted)} of 20 columns the labels read top to bottom in the order "
          f"of the scores" + (f"; not in {', '.join(sorted(shown(d) for d in inverted))}" if inverted else ""))
    counts = {s: list(sides.values()).count(s) for s in SIDE_PREFERENCE if s in sides.values()}
    check(True, "sides: " + ", ".join(f"{s} {n}" for s, n in counts.items()))


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--no-values", action="store_true", help="omit the value labels next to the markers")
    values = not parser.parse_args().no_values

    check = Checks()
    data = load(check)
    geo = geometry(values)
    placement = None
    if values:
        placement, report, log = place_value_labels(data, geo)
        FIGURES.mkdir(parents=True, exist_ok=True)
        for name, rows in (("rq2_similarity_value_labels.csv", report), ("rq2_similarity_value_labels_log.csv", log)):
            with open(FIGURES / name, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
    fig = build(data, geo, placement)
    validate(fig, data, geo, values, check)
    FIGURES.mkdir(parents=True, exist_ok=True)
    paths = [FIGURES / f"rq2_similarity.{ext}" for ext in ("html", "pdf", "svg", "png")]
    fig.write_html(paths[0], include_plotlyjs=True, full_html=True,
                   config={"displaylogo": False, "responsive": False})
    size = {"width": WIDTH, "height": HEIGHT_B}
    fig.write_image(paths[1], format="pdf", **size)
    fig.write_image(paths[2], format="svg", **size)
    fig.write_image(paths[3], format="png", scale=4, **size)
    check(all(p.exists() and p.stat().st_size > 0 for p in paths), "the four files were written")
    for message in check.passed:
        print(f"[ok] {message}")
    for p in paths:
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
