"""
End-to-end check of the Battery B figure against the data, from the exported SVG (what the paper will show),
not from the Plotly figure object the plot script builds.

1. Diagnosis: the Given of every configuration in output/selected_diagnoses.csv is the Given of its
   perturbation applied to D0 (scripts/perturbations.py), and B0 is D0 of Battery A.
2. Similarity: the five scores of every configuration, recomputed now with the production Retriever from that
   Given, equal output/similarity_scores.csv.
3. Points: every marker drawn in figures/rq2_similarity.svg is read back. Its configuration comes from the
   tick under it (Dk = Bk), its candidate from its fill colour, its score from its height (the y axis fitted
   on the tick labels). Each must equal the CSV, and there must be exactly one marker per (configuration,
   candidate).
4. Guide lines: every vertex of each candidate's line is that candidate's marker.
5. Value labels: for every number drawn, the point a reader attaches it to: the marker at the other end of its
   leader, if it has one, otherwise the marker nearest to the digits. The number must be the CSV score of that
   point, and every point must get exactly one number. The digits must not touch a guide line, a marker or
   other digits.

Output: review/figure_verification.csv (one row per configuration and candidate) and a summary on stdout.

Usage, from the project root, with the project's venv (after plot_similarity.py):
    .venv/Scripts/python.exe 5-experiments/RQ2/rq2_systematic_perturbations/review/verify_figure.py
"""
import csv
import math
import re
import sys
from pathlib import Path

REVIEW = Path(__file__).resolve().parent
BATTERY = REVIEW.parent
sys.path.insert(0, str(BATTERY / "scripts"))

import perturbations as pt  # noqa: E402  (production Retriever, D0 and the battery design)

SVG = BATTERY / "figures" / "rq2_similarity.svg"
CANDIDATE_COLOURS = {  # fill colours of the markers, as in generate_rq2_plotly.CANDIDATES
    "C1": "#2a78d6", "C2": "#eb6834", "C3": "#1baf7a", "C4": "#eda100", "C5": "#e87ba4"}
LABEL_GREY = (140, 139, 133)
FONT_PX, CAP_HEIGHT_EM = 10, 0.716
CHAR_EM = {**{str(k): 0.556 for k in range(10)}, ".": 0.278}
LINE_HALF_PX = 0.55
problems: list[str] = []


def rgb(hex_colour: str) -> tuple:
    return tuple(int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))


def as_text(score: float) -> str:
    return f"{score:.3f}".removeprefix("0")


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def problem(message: str) -> None:
    problems.append(message)


# ── 1-2. Diagnosis and similarity ────────────────────────────────────────────

design = {r["configuration"]: r for r in read_csv(BATTERY / "output" / "selected_diagnoses.csv")}
scores = {(r["configuration"], r["candidate"]): r for r in read_csv(BATTERY / "output" / "similarity_scores.csv")}
explored, battery = pt.exploration_set()
expected_given = {"B0": pt.REFERENCE_GIVEN, **{bid: item["given"] for bid, item, _ in battery}}
configs = ["B0"] + [bid for bid, _, _ in battery]
recomputed = {}
for b in configs:
    given_csv = design[b]["given"].split(" AND ")
    if given_csv != expected_given[b]:
        problem(f"{b}: Given in selected_diagnoses.csv differs from its perturbation applied to D0")
    diagnosed = {"name": b, "given": " AND ".join(given_csv), "when": pt.REFERENCE_WHEN, "do": "TBD",
                 "then": pt.REFERENCE_THEN}
    ranked = pt.rq2.retrieve(pt.ADAPTER, diagnosed)
    for rank, r in enumerate(ranked, start=1):
        c = pt.CANDIDATE_BY_NAME[r["candidate"]["name"]]
        recomputed[b, c] = (r["similarity_result"], rank)
        row = scores[b, c]
        if abs(float(row["score"]) - r["similarity_result"]) > 1e-9 or int(row["rank"]) != rank:
            problem(f"{b}/{c}: CSV score {row['score']} rank {row['rank']} vs recomputed "
                    f"{r['similarity_result']:.10f} rank {rank}")
with open(pt.RQ2 / "output" / "results.csv", encoding="utf-8", newline="") as f:
    battery_a_d0 = {r["candidate"]: float(r["score"]) for r in csv.DictReader(f) if r["diagnosis"] == "D0"}
if any(abs(battery_a_d0[c] - recomputed["B0", c][0]) > 1e-12 for c in CANDIDATE_COLOURS):
    problem("B0 differs from D0 of Battery A")

# ── 3-5. The exported figure ────────────────────────────────────────────────

svg = SVG.read_text(encoding="utf-8")
ox, oy = map(float, re.search(r'class="xy" transform="translate\(([\d.]+),([\d.]+)\)"', svg).groups())

ticks_x = {m.group(2): float(m.group(1)) for m in
           re.finditer(r'class="xtick"><text[^>]*transform="translate\(([\d.]+),0\)"[^>]*>(?:<tspan[^>]*>)?([^<]+)<', svg)}
ticks_y = [(float(m.group(2)), float(m.group(1))) for m in
           re.finditer(r'class="ytick"><text[^>]*transform="translate\(0,([\d.]+)\)"[^>]*>([\d.]+)<', svg)]
# score = a + b * y_svg, least squares on the tick labels
n = len(ticks_y)
my_, ms_ = sum(y for _, y in ticks_y) / n, sum(s for s, _ in ticks_y) / n
slope = sum((y - my_) * (s - ms_) for s, y in ticks_y) / sum((y - my_) ** 2 for _, y in ticks_y)
intercept = ms_ - slope * my_
px_per_score = -1 / slope
tick_residual = max(abs(intercept + slope * y - s) for s, y in ticks_y)

colour_to_candidate = {rgb(h): c for c, h in CANDIDATE_COLOURS.items()}
tick_to_config = {d: "B" + d[1:] for d in ticks_x}
markers = {}   # (config, candidate) -> (x, y, radius) in SVG coordinates
for m in re.finditer(r'<path class="point plotly-customdata" transform="translate\(([\d.]+),([\d.]+)\)" '
                     r'd="([^"]+)" style="[^"]*fill: rgb\((\d+), (\d+), (\d+)\)', svg):
    x, y = float(m.group(1)) + ox, float(m.group(2)) + oy
    numbers = [abs(float(v)) for v in re.findall(r"-?[\d.]+", m.group(3))]
    radius = max(v for v in numbers if v < 10)
    candidate = colour_to_candidate.get(tuple(int(m.group(i)) for i in (4, 5, 6)))
    tick, dx = min(((t, abs(tx - x)) for t, tx in ticks_x.items()), key=lambda t: t[1])
    if candidate is None or dx > 0.5:
        problem(f"marker at ({x:.1f}, {y:.1f}) has no candidate colour or no tick under it")
        continue
    key = (tick_to_config[tick], candidate)
    if key in markers:
        problem(f"two markers for {tick}/{candidate}")
    markers[key] = (x, y, radius)
if sorted(markers) != sorted(scores):
    problem(f"markers drawn for {len(markers)} (configuration, candidate) pairs, expected {len(scores)}")

point_rows = {}
for key, (x, y, _) in markers.items():
    read_score = intercept + slope * y
    expected_y = (float(scores[key]["score"]) - intercept) / slope
    point_rows[key] = (read_score, y - expected_y)
    if abs(y - expected_y) > 0.05:      # the SVG rounds coordinates to 0.01 px
        problem(f"{key}: marker at score {read_score:.4f}, CSV {float(scores[key]['score']):.4f}")

lines = {}
for m in re.finditer(r'<path class="js-line" d="(M[^"]+)"[^>]*stroke: rgb\((\d+), (\d+), (\d+)\)', svg):
    vertices = [(float(a) + ox, float(b) + oy) for a, b in re.findall(r"([\d.]+),([\d.]+)", m.group(1))]
    candidate = colour_to_candidate.get(tuple(int(m.group(i)) for i in (2, 3, 4)))
    if candidate and len(vertices) > 2:
        lines[candidate] = vertices
def distance_to_segment(p: tuple, a: tuple, b: tuple) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
    return math.hypot(a[0] + t * dx - p[0], a[1] + t * dy - p[1])


# Plotly drops the middle vertex of three collinear points when it writes a line (e.g. C1 at D3, D2, D1, all
# .836), so the check is geometric: every vertex is one of the candidate's markers, in x order, and every marker
# of the candidate lies on the line
simplified = {}
for c, vertices in lines.items():
    own = [(x, y) for (b, cc), (x, y, _) in markers.items() if cc == c]
    vertices_are_markers = all(min(math.hypot(v[0] - x, v[1] - y) for x, y in own) <= 0.05 for v in vertices)
    in_order = all(a[0] < b[0] for a, b in zip(vertices, vertices[1:]))
    on_line = all(min(distance_to_segment(p, a, b) for a, b in zip(vertices, vertices[1:])) <= 0.05 for p in own)
    simplified[c] = len(own) - len(vertices)
    if not (vertices_are_markers and in_order and on_line and len(lines) == len(CANDIDATE_COLOURS)):
        problem(f"the guide line of {c} does not pass through its markers")
segments = [(a, b) for v in lines.values() for a, b in zip(v, v[1:])]

leaders = [tuple(map(float, m.groups())) for m in
           re.finditer(r'd="M([\d.]+),([\d.]+)L([\d.]+),([\d.]+)" style="[^"]*stroke: rgb\(140, 139, 133\)', svg)]

labels = []    # (text, ink box, full box) in SVG coordinates
for m in re.finditer(r'<g class="cursor-pointer" transform="translate\(([\d.]+),([\d.]+)\)"><rect class="bg" '
                     r'x="0.5" y="0.5" width="([\d.]+)" height="([\d.]+)"[^>]*/><text class="annotation-text"'
                     r'[^>]*y="([\d.]+)"[^>]*fill: rgb\(140, 139, 133\)[^>]*>([^<]+)<', svg):
    tx, ty, w, h, baseline, text = (*map(float, m.groups()[:5]), m.group(6))
    tw = sum(CHAR_EM[ch] for ch in text) * FONT_PX
    left = tx + 0.5 + (w - tw) / 2
    ink = (left, left + tw, ty + baseline - CAP_HEIGHT_EM * FONT_PX, ty + baseline)   # x0, x1, y_top, y_bottom
    labels.append((text, ink, (tx + 0.5, tx + 0.5 + w, ty + 0.5, ty + 0.5 + h)))


def distance_to_box(p: tuple, box: tuple) -> float:
    dx = max(box[0] - p[0], 0.0, p[0] - box[1])
    dy = max(box[2] - p[1], 0.0, p[1] - box[3])
    return math.hypot(dx, dy)


def segment_hits_box(a: tuple, b: tuple, box: tuple, pad: float) -> bool:
    left, right, top, bottom = box[0] - pad, box[1] + pad, box[2] - pad, box[3] + pad
    steps = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) * 4))
    return any(left <= a[0] + (b[0] - a[0]) * t / steps <= right and top <= a[1] + (b[1] - a[1]) * t / steps <= bottom
               for t in range(steps + 1))


attached = {}
label_rows = {}
for text, ink, full in labels:
    method, key = None, None
    for x0, y0, x1, y1 in leaders:
        ends = [(x0, y0), (x1, y1)]
        near_label = [e for e in ends if distance_to_box(e, full) <= 2.0]
        if near_label:
            other = ends[1] if near_label[0] == ends[0] else ends[0]
            key = min(markers, key=lambda k: math.hypot(markers[k][0] - other[0], markers[k][1] - other[1]))
            mx, my, r = markers[key]
            if math.hypot(mx - other[0], my - other[1]) > r + 1.5:
                problem(f"label {text}: its leader does not end at a marker")
            method = "leader"
            break
    ranked = sorted((distance_to_box((mx, my), ink) - r, k) for k, (mx, my, r) in markers.items())
    if method is None:
        key, method = ranked[0][1], "nearest marker"
    own = next(d for d, k in ranked if k == key)
    other = next(d for d, k in ranked if k != key)
    if key in attached:
        problem(f"two numbers attach to {key}: {attached[key]} and {text}")
    attached[key] = text
    label_rows[key] = (text, method, own, other)
    if text != as_text(float(scores[key]["score"])):
        problem(f"number {text} attaches to {key}, whose CSV score is {float(scores[key]['score']):.4f}")
    if any(segment_hits_box(a, b, ink, LINE_HALF_PX) for a, b in segments):
        problem(f"number {text} of {key} touches a guide line")
    if any(distance_to_box((mx, my), ink) < r for (mx, my, r) in markers.values()):
        problem(f"number {text} of {key} touches a marker")
if len(attached) != len(markers):
    problem(f"{len(attached)} points have a number, expected {len(markers)}")
inks = [ink for _, ink, _ in labels]
overlaps = sum(1 for i, a in enumerate(inks) for b in inks[i + 1:]
               if a[0] < b[1] and b[0] < a[1] and a[2] < b[3] and b[2] < a[3])
if overlaps:
    problem(f"{overlaps} pairs of numbers overlap")

rows = []
for (b, c) in sorted(scores, key=lambda k: (int(k[0][1:]), k[1])):
    csv_score = float(scores[b, c]["score"])
    text, method, own, other = label_rows.get((b, c), ("", "", math.nan, math.nan))
    rows.append({
        "figure_label": "D" + b[1:], "configuration": b, "candidate": c,
        "given": design[b]["given"], "csv_score": f"{csv_score:.10f}",
        "recomputed_score": f"{recomputed[b, c][0]:.10f}", "csv_rank": scores[b, c]["rank"],
        "recomputed_rank": recomputed[b, c][1],
        "score_read_from_marker": f"{point_rows[b, c][0]:.4f}", "marker_offset_px": f"{point_rows[b, c][1]:+.3f}",
        "number_drawn": text, "number_expected": as_text(csv_score), "number_attached_by": method,
        "digits_to_own_marker_px": f"{own:.1f}", "digits_to_nearest_other_marker_px": f"{other:.1f}",
        "ok": text == as_text(csv_score) and abs(point_rows[b, c][1]) <= 0.05
              and abs(recomputed[b, c][0] - csv_score) <= 1e-9,
    })
with open(REVIEW / "figure_verification.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

nearest = [r for r in rows if r["number_attached_by"] == "nearest marker"]
print(f"configurations: {len(configs)}; Given of each = its perturbation applied to D0; B0 = Battery A D0")
print(f"scores recomputed with the production Retriever: {len(recomputed)}, largest difference from the CSV "
      f"{max(abs(recomputed[k][0] - float(scores[k]['score'])) for k in scores):.1e}")
print(f"markers read from the SVG: {len(markers)}; y axis fitted on {n} ticks (residual {tick_residual:.1e}), "
      f"{px_per_score:.1f} px per unit; largest marker offset from its CSV score "
      f"{max(abs(v[1]) for v in point_rows.values()):.3f} px")
print(f"guide lines: {len(lines)}; every vertex is a marker of its candidate and every marker lies on its line "
      f"(collinear vertices dropped by Plotly: {simplified})")
print(f"numbers read from the SVG: {len(labels)}; attached by leader {len(rows) - len(nearest)}, by nearest marker "
      f"{len(nearest)}; smallest ratio nearest-other / own among the latter "
      f"{min(float(r['digits_to_nearest_other_marker_px']) / max(float(r['digits_to_own_marker_px']), 0.5) for r in nearest):.2f}")
print(f"rows ok: {sum(r['ok'] for r in rows)} of {len(rows)}")
print("PROBLEMS:" if problems else "no problem found", *problems, sep="\n  ")
sys.exit(1 if problems else 0)
