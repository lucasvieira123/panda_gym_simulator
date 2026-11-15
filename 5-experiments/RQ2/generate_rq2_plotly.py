"""
Final RQ2 figure for the paper: similarity of C1-C5 in each diagnostic configuration (Desired Adaptation
Scenario), read from output/results.csv and output/rankings.csv (written by run_rq2.py).

Every configuration is derived from D0 alone, none from its neighbour, so the horizontal arrangement is
analytical, not sequential. D0, the shared reference, sits in a light band in the centre and the reading starts
from it: x order D11..D1 | D0 | D12..D19, with the isolated modifications mirrored on the left (D1 next to D0)
and the combined ones on the right (groups with a title in PAPER_LAYOUT would get a name and thin dotted
separators; the current layout has none). Filled marker
= candidate in the Top-3, open marker = rank 4 or 5. Thin straight lines join a candidate's points as a reading
guide only: with --lines through-reference (default) one line per candidate runs through the 20 configurations
in x order, D0 included; with --lines within-blocks they stay inside the isolated and the combined block and never
reach D0; with --lines none the figure is a plain categorical scatter.

Paper labels. The figure numbers the configurations by the modifications M1-M11 below (PAPER_LAYOUT), which
differs from the IDs of the battery (diagnoses.json and the CSVs). The mapping paper label -> battery ID is not
typed by hand: each paper label is matched to the one battery configuration whose changes to D0 are exactly its
modifications, and the Given recorded in results.csv is checked against D0's Given with those modifications
applied. The mapping is printed and written to <name>_labels.csv.

No value is computed here: scores, ranks, Top-1 and Top-3 come from the CSVs. Before exporting, the script
validates the data, the mapping and the built figure, and stops on the first failed check.

Outputs, in figures/ by default: <name>.html (interactive, with hover), .pdf, .svg, .png (scale 4) and
<name>_labels.csv. The figure is 792 px wide, sized for \\textwidth of the acmsmall format (about 5.5 in):
1 px prints at about 0.5 pt, so the 13-17 px fonts print at 6.5-8.5 pt.

Requires plotly and kaleido (both in the project's venv). Usage, from the project root:
    .venv/Scripts/python.exe 5-experiments/RQ2/generate_rq2_plotly.py [--out-dir DIR] [--name NAME]
"""
import argparse
import csv
import json
import math
from pathlib import Path

import plotly.graph_objects as go

HERE = Path(__file__).resolve().parent

# ------------------------------------------------------------------------------- paper organisation

FRICTION, HEIGHT = "lateral_friction <= 0.1425", "object_lift_height_cm < 10"
MODIFICATIONS = {  # each one is a change to D0's Given, in the format of diagnoses.json
    "M1":  ("Set lateral_friction <= 0.25",            {"replace": FRICTION, "with": "lateral_friction <= 0.25"}),
    "M2":  ("Set lateral_friction >= 0.1425",          {"replace": FRICTION, "with": "lateral_friction >= 0.1425"}),
    "M3":  ("Omit lateral_friction",                   {"remove": FRICTION}),
    "M4":  ("Omit finger_contacts",                    {"remove": "finger_contacts < 2"}),
    "M5":  ("Add object_shape_irregular == 1",         {"add": "object_shape_irregular == 1"}),
    "M6":  ("Add grasp_alignment_error_cm > 1",        {"add": "grasp_alignment_error_cm > 1"}),
    "M7":  ("Add planned_lift_acceleration_m_s2 > 2",  {"add": "planned_lift_acceleration_m_s2 > 2"}),
    "M8":  ("Add payload_swing_risk == 1",             {"add": "payload_swing_risk == 1"}),
    "M9":  ("Set object_lift_height_cm < 12",          {"replace": HEIGHT, "with": "object_lift_height_cm < 12"}),
    "M10": ("Set object_lift_height_cm < 20",          {"replace": HEIGHT, "with": "object_lift_height_cm < 20"}),
    "M11": ("Add object_mass > 0.5",                   {"add": "object_mass > 0.5"}),
}
# (block, block title, [(group title, [(paper label, modifications)])]), left to right
PAPER_LAYOUT = [
    # Mirrored, so that the reading starts at D0: D1 is next to it and D11 at the left edge. No group titles:
    # a group with title None draws no name, separator or extra gap
    ("isolated", "Isolated modifications", [
        (None, [("D11", ["M11"]), ("D10", ["M10"]), ("D9", ["M9"]), ("D8", ["M8"]), ("D7", ["M7"]),
                ("D6", ["M6"]), ("D5", ["M5"]), ("D4", ["M4"]), ("D3", ["M3"]), ("D2", ["M2"]), ("D1", ["M1"])]),
    ]),
    ("reference", "Reference", [(None, [("D0", [])])]),
    ("combined", "Combined modifications", [
        (None, [("D12", ["M5", "M6"]), ("D13", ["M3", "M5", "M6"]),
                ("D14", ["M9", "M5", "M6"]), ("D15", ["M3", "M9", "M5", "M6"]),
                ("D16", ["M7", "M8"]), ("D17", ["M3", "M7", "M8"]),
                ("D18", ["M10", "M7", "M8"]), ("D19", ["M3", "M10", "M7", "M8"])]),
    ]),
]

# Results of the current battery, in paper labels, checked against the CSVs (never used to draw)
EXPECTED_DIAGNOSES = 20
EXPECTED_TOP1_CHANGED = 15
EXPECTED_TOP3_SET_CHANGED = {"D18", "D19"}

# ------------------------------------------------------------------------------------------- style

# Same palette and markers as plot_rq2.py: fixed categorical order validated on white, with the marker
# shape as the secondary encoding
CANDIDATES = {
    "C1": ("Suction-Assisted Lift Recovery",  "#2a78d6", "circle"),
    "C2": ("Tactile Grip-Force Recovery",     "#eb6834", "square"),
    "C3": ("Shape-Adaptive Grasp Recovery",   "#1baf7a", "diamond"),
    "C4": ("Conformal Grasp Stabilisation",   "#eda100", "triangle-up"),
    "C5": ("Dynamic-Load Lift Stabilisation", "#e87ba4", "triangle-down"),
}
MARKER_SIZE = {"circle": 9, "square": 9, "diamond": 10, "triangle-up": 11, "triangle-down": 11}
INK, INK_SECONDARY, SURFACE = "#0b0b0b", "#52514e", "#ffffff"
GRID, AXIS = "#e9e8e4", "#b8b7b0"
BAND, BAND_EDGE = "#f3f3f1", "#c4c3bd"
FONT = "Arial, Helvetica, sans-serif"
FONT_SIZE = {"base": 17, "axis_title": 16, "tick": 14, "header": 15, "group": 13, "legend": 15, "hover": 14}

GUIDE_ALPHA, GUIDE_WIDTH = 0.55, 1.1
GROUP_GAP = 0.5       # extra x space between two groups of the same block
BLOCK_GAP = 0.75      # extra x space on each side of D0
Y_RANGE, Y_TICKS = (0.30, 1.02), [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
WIDTH, HEIGHT = 792, 516
MARGIN = {"l": 64, "r": 16, "t": 40, "b": 138}
GROUP_SHIFT = 5                                       # px between the plot area and the group names
BLOCK_SHIFT = 27 if any(g for _, _, gs in PAPER_LAYOUT for g, _ in gs) else 8   # ... and the block names


class Checks:
    """Stops at the first failed check; keeps the passed ones for the report."""

    def __init__(self) -> None:
        self.passed: list[str] = []

    def __call__(self, condition: bool, message: str) -> None:
        if not condition:
            raise SystemExit(f"[FAIL] {message}")
        self.passed.append(message)


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def hex_rgba(color: str, alpha: float) -> str:
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alpha})"


def paper_entries() -> list[tuple[str, str, str | None, list[str]]]:
    """(block, group, paper label, modifications) in x order."""
    return [(block, group, label, mods)
            for block, _, groups in PAPER_LAYOUT for group, entries in groups for label, mods in entries]


def change_key(changes: list[dict]) -> frozenset:
    return frozenset(json.dumps(c, sort_keys=True) for c in changes)


def apply_changes(given: list[str], changes: list[dict]) -> set[str]:
    predicates = set(given)
    for c in changes:
        if "replace" in c:
            predicates.remove(c["replace"])
            predicates.add(c["with"])
        elif "remove" in c:
            predicates.remove(c["remove"])
        else:
            predicates.add(c["add"])
    return predicates


# --------------------------------------------------------------------------------------------- data

def map_labels(spec: dict, results: list[dict], check: Checks) -> dict:
    """Paper label -> battery ID, matched by the changes to D0 (see the module docstring)."""
    battery = {d["id"]: d for d in spec["diagnoses"]}
    by_changes = {}
    for d in spec["diagnoses"]:
        by_changes.setdefault(change_key(d["changes"]), []).append(d["id"])
    check(all(len(ids) == 1 for ids in by_changes.values()),
          "diagnoses.json: no two battery configurations make the same changes to D0")

    mapping = {}
    for _, _, label, mods in paper_entries():
        ids = by_changes.get(change_key([MODIFICATIONS[m][1] for m in mods]), [])
        if len(ids) != 1:
            check(False, f"{label} ({' + '.join(mods) or 'no change'}) matches no battery configuration")
        mapping[label] = ids[0]
    check(len(mapping) == EXPECTED_DIAGNOSES and sorted(mapping.values()) == sorted(battery),
          f"the {EXPECTED_DIAGNOSES} paper labels map one-to-one onto the battery configurations, D0 onto D0")

    recorded = {r["diagnosis"]: r["given"] for r in results}
    expected = {label: apply_changes(spec["reference"]["given"], [MODIFICATIONS[m][1] for m in mods])
                for _, _, label, mods in paper_entries()}
    check(all(set(recorded[mapping[label]].split(" AND ")) == expected[label] for label in mapping),
          "the Given recorded in results.csv for each mapped configuration is D0's Given with exactly its "
          "modifications M1-M11 applied")
    return mapping


def load_data(results_path: Path, rankings_path: Path, spec_path: Path, check: Checks) -> dict:
    results, rankings = read_csv(results_path), read_csv(rankings_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    mapping = map_labels(spec, results, check)
    order = [label for _, _, label, _ in paper_entries()]
    battery_ids = set(mapping.values())

    ranking = {r["diagnosis"]: r for r in rankings}
    check(len(rankings) == len(ranking) == EXPECTED_DIAGNOSES and set(ranking) == battery_ids,
          f"rankings.csv has the {EXPECTED_DIAGNOSES} battery configurations, once each")
    keys = [(r["diagnosis"], r["candidate"]) for r in results]
    by_battery = dict(zip(keys, results))
    check(len(keys) == len(by_battery) == 5 * EXPECTED_DIAGNOSES
          and set(by_battery) == {(d, c) for d in battery_ids for c in CANDIDATES},
          f"results.csv has one score for each of C1-C5 in every configuration ({len(keys)} scores)")
    check(all(math.isfinite(float(r["score"])) for r in results), "every score is a finite number")

    # From here on everything is keyed by the paper label
    cells = {(label, c): by_battery[mapping[label], c] for label in order for c in CANDIDATES}
    ranking = {label: ranking[mapping[label]] for label in order}

    def by_rank(d: str) -> list[str]:
        return sorted(CANDIDATES, key=lambda c: int(cells[d, c]["rank"]))

    check(all(sorted(int(cells[d, c]["rank"]) for c in CANDIDATES) == [1, 2, 3, 4, 5] for d in order),
          "ranks are a permutation of 1-5 in every configuration")
    check(all(float(cells[d, a]["score"]) >= float(cells[d, b]["score"])
              for d in order for a, b in zip(by_rank(d), by_rank(d)[1:])),
          "a better rank never has a lower score")
    top1 = {d: by_rank(d)[0] for d in order}
    top3 = {d: set(by_rank(d)[:3]) for d in order}
    check(all(ranking[d]["top1"] == top1[d] for d in order), "Top-1 in rankings.csv = rank 1 in results.csv")
    check(all(set(ranking[d]["top3"].split()) == top3[d] for d in order),
          "Top-3 in rankings.csv = ranks 1-3 in results.csv")
    return {"order": order, "mapping": mapping, "cells": cells, "ranking": ranking, "top1": top1, "top3": top3}


def check_ranking_changes(data: dict, check: Checks) -> None:
    modified = [d for d in data["order"] if d != "D0"]
    top1, top3, ranking = data["top1"], data["top3"], data["ranking"]
    changed = [d for d in modified if top1[d] != top1["D0"]]
    same = [d for d in modified if d not in changed]
    check(len(changed) == EXPECTED_TOP1_CHANGED,
          f"Top-1 differs from D0's ({top1['D0']}) in {len(changed)} of {len(modified)} modified configurations "
          f"(expected {EXPECTED_TOP1_CHANGED}); same Top-1 in {', '.join(same)}")
    check({d for d in modified if ranking[d]["top1_changed"] == "True"} == set(changed),
          "column top1_changed of rankings.csv agrees")
    set_changed = {d for d in modified if top3[d] != top3["D0"]}
    check(set_changed == EXPECTED_TOP3_SET_CHANGED,
          f"Top-3 set differs from D0's ({' '.join(sorted(top3['D0']))}) only in "
          f"{', '.join(sorted(set_changed, key=lambda d: int(d[1:])))} "
          f"(expected {', '.join(sorted(EXPECTED_TOP3_SET_CHANGED))})")
    check({d for d in modified if ranking[d]["top3_set_changed"] == "True"} == set_changed,
          "column top3_set_changed of rankings.csv agrees")


# ------------------------------------------------------------------------------------------- figure

def geometry() -> dict:
    """x of each label; spans of the groups and blocks; the separators between groups."""
    xs, x = {}, 0.0
    groups, blocks = [], {}
    for b, (block, _, block_groups) in enumerate(PAPER_LAYOUT):
        x += BLOCK_GAP if b else 0
        for g, (group, entries) in enumerate(block_groups):
            x += GROUP_GAP if g else 0
            for label, _ in entries:
                xs[label] = x
                x += 1
            groups.append((block, group, [label for label, _ in entries]))
        labels = [label for _, entries in block_groups for label, _ in entries]
        blocks[block] = labels
    first, last = min(xs.values()), max(xs.values())
    d0 = xs["D0"]
    left = max(v for v in xs.values() if v < d0)
    right = min(v for v in xs.values() if v > d0)
    band = ((left + d0) / 2, (d0 + right) / 2)
    separators = [(xs[a[2][-1]] + xs[b[2][0]]) / 2
                  for a, b in zip(groups, groups[1:]) if a[0] == b[0]]
    return {"xs": xs, "band": band, "groups": groups, "blocks": blocks, "separators": separators,
            "x_range": (first - 0.6, last + 0.6)}


def order_by_x(xs: dict) -> list[str]:
    return sorted(xs, key=xs.get)


def hover_rows(data: dict, d: str, cid: str) -> list:
    row, d0 = data["cells"][d, cid], data["cells"]["D0", cid]
    mods = next(m for _, _, label, m in paper_entries() if label == d)
    if d == "D0":
        what, vs_d0 = "Reference diagnosis", ""
    else:
        what = " + ".join(mods) + ": " + "; ".join(MODIFICATIONS[m][0] for m in mods)
        vs_d0 = f"<br>Δ similarity vs D0: {float(row['score_delta_vs_D0']):+.4f} (rank in D0: {d0['rank']})"
    return [d, cid, what, int(row["rank"]), vs_d0, data["mapping"][d]]


def guide_segments(data: dict, geo: dict, lines: str) -> list[list[str]]:
    """Labels joined by each candidate's guide line(s), in x order."""
    if lines == "through-reference":
        return [data["order"]]
    if lines == "within-blocks":
        return [geo["blocks"][block] for block in ("isolated", "combined")]
    return []


def build_figure(data: dict, geo: dict, lines: str) -> go.Figure:
    xs, cells, order = geo["xs"], data["cells"], data["order"]
    fig = go.Figure()

    # D0 band, under the grid, delimited by two thin lines; dotted separators between groups
    fig.add_shape(type="rect", xref="x", yref="paper", x0=geo["band"][0], x1=geo["band"][1], y0=0, y1=1,
                  fillcolor=BAND, line_width=0, layer="below")
    for xb in geo["band"]:
        fig.add_shape(type="line", xref="x", yref="paper", x0=xb, x1=xb, y0=0, y1=1, layer="between",
                      line={"color": BAND_EDGE, "width": 1})
    for xb in geo["separators"]:
        fig.add_shape(type="line", xref="x", yref="paper", x0=xb, x1=xb, y0=0, y1=1, layer="between",
                      name="separator", line={"color": BAND_EDGE, "width": 1, "dash": "dot"})

    # Reading guides, under the points
    for cid, (_, color, _) in CANDIDATES.items():
        for ids in guide_segments(data, geo, lines):
            fig.add_trace(go.Scatter(
                x=[xs[d] for d in ids], y=[float(cells[d, cid]["score"]) for d in ids],
                mode="lines", line={"color": hex_rgba(color, GUIDE_ALPHA), "width": GUIDE_WIDTH, "shape": "linear"},
                legendgroup=cid, showlegend=False, hoverinfo="skip", meta={"kind": "guide", "candidate": cid}))

    # Points: open markers (ranks 4-5) first so that they never cover a Top-3 marker
    for filled in (False, True):
        for cid, (name, color, symbol) in CANDIDATES.items():
            ids = [d for d in order if (int(cells[d, cid]["rank"]) <= 3) == filled]
            fig.add_trace(go.Scatter(
                x=[xs[d] for d in ids], y=[float(cells[d, cid]["score"]) for d in ids],
                mode="markers", cliponaxis=False, legendgroup=cid, showlegend=False,
                marker={"symbol": symbol, "size": MARKER_SIZE[symbol], "color": color if filled else SURFACE,
                        "line": {"color": SURFACE if filled else color, "width": 1.2 if filled else 1.8}},
                customdata=[hover_rows(data, d, cid) for d in ids],
                hovertemplate=(f"<b>%{{customdata[0]}}</b> · %{{customdata[2]}}<br>{cid} {name}<br>"
                               "Similarity: %{y:.4f}<br>Rank: %{customdata[3]} of 5%{customdata[4]}"
                               "<br>Battery ID: %{customdata[5]}<extra></extra>"),
                meta={"kind": "points", "candidate": cid, "filled": filled}))

    # Legends: candidates (as drawn: guide line, if any, and filled marker) and the marker key
    for cid, (name, color, symbol) in CANDIDATES.items():
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers" if lines == "none" else "lines+markers", name=f"{cid} {name}",
            legendgroup=cid, legend="legend", line={"color": hex_rgba(color, GUIDE_ALPHA), "width": GUIDE_WIDTH},
            marker={"symbol": symbol, "size": MARKER_SIZE[symbol], "color": color,
                    "line": {"color": SURFACE, "width": 1.2}},
            meta={"kind": "legend"}))
    for label, filled in (("In the Top-3", True), ("Rank 4 or 5", False)):
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers", name=label, legend="legend2",
            marker={"symbol": "circle", "size": 9, "color": INK_SECONDARY if filled else SURFACE,
                    "line": {"color": SURFACE if filled else INK_SECONDARY, "width": 1.2 if filled else 1.8}},
            meta={"kind": "legend"}))

    # Two header rows above the plot: block names, then group names
    for block, title, _ in PAPER_LAYOUT:
        ids = geo["blocks"][block]
        fig.add_annotation(x=(xs[ids[0]] + xs[ids[-1]]) / 2, y=1, xref="x", yref="paper", yanchor="bottom",
                           yshift=BLOCK_SHIFT, text=title, showarrow=False, name="block",
                           font={"size": FONT_SIZE["header"], "color": INK_SECONDARY})
    for _, group, ids in geo["groups"]:
        if group:
            fig.add_annotation(x=(xs[ids[0]] + xs[ids[-1]]) / 2, y=1, xref="x", yref="paper", yanchor="bottom",
                               yshift=GROUP_SHIFT, text=group, showarrow=False, name="group",
                               font={"size": FONT_SIZE["group"], "color": INK_SECONDARY})

    legend_common = {"orientation": "h", "xref": "paper", "yref": "container", "y": 0.012, "yanchor": "bottom",
                     "bgcolor": "rgba(0,0,0,0)", "font": {"size": FONT_SIZE["legend"], "color": INK},
                     "itemclick": "toggle", "itemdoubleclick": "toggleothers"}
    fig.update_layout(
        width=WIDTH, height=HEIGHT, margin=MARGIN, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font={"family": FONT, "size": FONT_SIZE["base"], "color": INK},
        legend={**legend_common, "x": 0, "xanchor": "left", "traceorder": "normal", "itemwidth": 30,
                "entrywidth": 0.5, "entrywidthmode": "fraction"},
        legend2={**legend_common, "x": 0.5, "xanchor": "left", "itemwidth": 30},
        hovermode="closest",
        hoverlabel={"bgcolor": SURFACE, "bordercolor": AXIS,
                    "font": {"family": FONT, "size": FONT_SIZE["hover"], "color": INK}},
    )
    fig.update_xaxes(
        tickmode="array", tickvals=[xs[d] for d in order_by_x(xs)],
        ticktext=[f"<b>{d}</b>" if d == "D0" else d for d in order_by_x(xs)],
        range=list(geo["x_range"]), showgrid=False, zeroline=False, showline=True, linecolor=AXIS, linewidth=1,
        ticks="outside", ticklen=4, tickcolor=AXIS, tickfont={"size": FONT_SIZE["tick"], "color": INK_SECONDARY},
        title={"text": "Diagnostic Configuration", "standoff": 10,
               "font": {"size": FONT_SIZE["axis_title"], "color": INK_SECONDARY}})
    fig.update_yaxes(
        range=list(Y_RANGE), tickvals=Y_TICKS, tickformat=".1f", showgrid=True, gridcolor=GRID, gridwidth=1,
        zeroline=False, showline=False, ticks="", tickfont={"size": FONT_SIZE["tick"], "color": INK_SECONDARY},
        title={"text": "Similarity", "standoff": 8, "font": {"size": FONT_SIZE["axis_title"], "color": INK_SECONDARY}})
    return fig


# ----------------------------------------------------------------------------------- figure checks

def validate_figure(fig: go.Figure, data: dict, geo: dict, lines: str, check: Checks) -> None:
    xs, cells = geo["xs"], data["cells"]

    expected_x_order = ([f"D{k}" for k in range(11, 0, -1)] + ["D0"] + [f"D{k}" for k in range(12, 20)])
    lo, hi = geo["band"]
    inside = [d for d in xs if lo < xs[d] < hi]
    check(order_by_x(xs) == expected_x_order and set(inside) == {"D0"}
          and list(fig.layout.xaxis.ticktext).index("<b>D0</b>") == 11,
          "x order is D11..D1 | D0 | D12..D19 (D1 and D12 next to D0), and only D0's markers fall inside the "
          "reference band")
    check(all(not (min(xs[i] for i in ids) < s < max(xs[i] for i in ids))
              for s in geo["separators"] for _, _, ids in geo["groups"])
          and len(geo["separators"]) == sum(len(g) - 1 for _, _, g in PAPER_LAYOUT),
          f"{len(geo['separators'])} dotted separators, each between two groups, none inside a group")

    traces = {kind: [t for t in fig.data if (t.meta or {}).get("kind") == kind]
              for kind in ("points", "guide", "legend")}
    check(sum(map(len, traces.values())) == len(fig.data), "every trace is tagged as points, guide or legend")
    check(all(t.mode == "markers" for t in traces["points"]), "point traces draw markers only, without lines")

    # Guides: straight segments in x order through the CSV scores of the expected labels
    expected_segments = guide_segments(data, geo, lines)
    by_candidate = {}
    for t in traces["guide"]:
        cid = t.meta["candidate"]
        labels = [min(xs, key=lambda d: abs(xs[d] - x)) for x in t.x]
        if not all(x == xs[d] and y == float(cells[d, cid]["score"]) for d, x, y in zip(labels, t.x, t.y)):
            check(False, f"a {cid} guide line differs from the CSV")
        by_candidate.setdefault(cid, []).append(labels)
    check(all(by_candidate.get(cid, []) == expected_segments for cid in CANDIDATES)
          and set(by_candidate) <= set(CANDIDATES),
          {"through-reference": "guide lines: one per candidate through the 20 configurations in x order, "
                                "D0 included, joining the CSV scores",
           "within-blocks": "guide lines: one per candidate in the isolated block and one in the combined block, "
                            "joining the CSV scores; none reaches D0",
           "none": "no guide line: plain categorical scatter"}[lines])

    # Points: each (configuration, candidate) exactly once, at its place, with the CSV score, filled iff Top-3
    seen = []
    for t in traces["points"]:
        cid = t.meta["candidate"]
        for x, y, cd in zip(t.x, t.y, t.customdata):
            d = cd[0]
            seen.append((d, cid))
            rank = int(cells[d, cid]["rank"])
            if not (cd[1] == cid and y == float(cells[d, cid]["score"]) and x == xs[d]
                    and (rank <= 3) == t.meta["filled"] and cd[3] == rank and cd[5] == data["mapping"][d]):
                check(False, f"point {d}/{cid} does not match results.csv")
    check(len(seen) == len(set(seen)) == len(cells) and set(seen) == set(cells),
          f"the figure shows {len(seen)} points, one per (configuration, candidate), each with exactly the CSV "
          "score, rank and fill of its battery configuration")
    check(all(all(v is None for v in t.x) for t in traces["legend"]), "legend-only traces draw nothing")

    expected_text = ([title for _, title, _ in PAPER_LAYOUT]
                     + [group for _, group, _ in geo["groups"] if group])
    check([a.text for a in fig.layout.annotations] == expected_text,
          "the only text above the plot is the block names and the group names")


# ------------------------------------------------------------------------------------------- export

def write_labels(data: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["paper_label", "battery_id", "block", "group", "modifications", "description",
                    "top1", "top3"])
        for block, group, label, mods in paper_entries():
            w.writerow([label, data["mapping"][label], block, group or "", " + ".join(mods),
                        "; ".join(MODIFICATIONS[m][0] for m in mods) or "Reference",
                        data["top1"][label], " ".join(sorted(data["top3"][label]))])


def export(fig: go.Figure, data: dict, out_dir: Path, name: str, check: Checks) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / f"{name}.{ext}" for ext in ("html", "pdf", "svg", "png")] + [out_dir / f"{name}_labels.csv"]
    fig.write_html(paths[0], include_plotlyjs=True, full_html=True,
                   config={"displaylogo": False, "responsive": False,
                           "toImageButtonOptions": {"format": "svg", "filename": name}})
    size = {"width": WIDTH, "height": HEIGHT}  # Kaleido does not take the size from the layout
    fig.write_image(paths[1], format="pdf", **size)
    fig.write_image(paths[2], format="svg", **size)
    fig.write_image(paths[3], format="png", scale=4, **size)
    write_labels(data, paths[4])
    check(all(p.exists() and p.stat().st_size > 0 for p in paths), "the five files were written")
    return paths


def print_mapping(data: dict) -> None:
    print("paper  battery  modifications        Top-1  Top-3")
    for _, _, label, mods in paper_entries():
        print(f"{label:<6} {data['mapping'][label]:<8} {' + '.join(mods) or '-':<20} "
              f"{data['top1'][label]:<6} {' '.join(sorted(data['top3'][label]))}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--results", type=Path, default=HERE / "output" / "results.csv")
    parser.add_argument("--rankings", type=Path, default=HERE / "output" / "rankings.csv")
    parser.add_argument("--spec", type=Path, default=HERE / "diagnoses.json")
    parser.add_argument("--out-dir", type=Path, default=HERE / "figures")
    parser.add_argument("--name", default="rq2_similarity_plotly")
    parser.add_argument("--lines", choices=("through-reference", "within-blocks", "none"),
                        default="through-reference",
                        help="guide lines through D0 (default), only inside the isolated and combined blocks, or none")
    args = parser.parse_args()

    check = Checks()
    data = load_data(args.results, args.rankings, args.spec, check)
    check_ranking_changes(data, check)
    geo = geometry()
    fig = build_figure(data, geo, args.lines)
    validate_figure(fig, data, geo, args.lines, check)
    paths = export(fig, data, args.out_dir, args.name, check)

    print_mapping(data)
    for message in check.passed:
        print(f"[ok] {message}")
    for p in paths:
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
