"""
Figures of RQ2, read from output/results.csv and output/rankings.csv (written by run_rq2.py):

- figures/similarity_scores.*   similarity of each candidate per diagnosis (main figure)
- figures/candidate_rankings.*  ranking position of each candidate per diagnosis
- figures/similarity_rankings.* the ranking figure with similarity on Y (filled marker = Top-3)

Each figure is written as HTML (interactive), SVG, PDF and PNG, sized like the wide RQ1.1 figure
(792 px for the acmsmall text width of about 5.5 in, fonts of about 9 pt when printed).
No value is typed in here: every point comes from the CSVs.

Requires plotly and kaleido (the project's venv has both). Usage, from the project root:
    .venv/Scripts/python.exe 5-experiments/RQ2/plot_rq2.py
"""
import csv
from pathlib import Path

import plotly.graph_objects as go

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "output"
FIGURES = HERE / "figures"

INK, INK_SECONDARY, INK_MUTED, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#ffffff"
GRID, AXIS = "#e6e5e0", "#b8b7b0"
FONT = "Arial, Helvetica, sans-serif"

# Fixed categorical order (validated for adjacent pairs on white); markers are the secondary encoding
CANDIDATES = {
    "C1": ("Suction-Assisted Lift Recovery",  "#2a78d6", "circle"),
    "C2": ("Tactile Grip-Force Recovery",     "#eb6834", "square"),
    "C3": ("Shape-Adaptive Grasp Recovery",   "#1baf7a", "diamond"),
    "C4": ("Conformal Grasp Stabilisation",   "#eda100", "triangle-up"),
    "C5": ("Dynamic-Load Lift Stabilisation", "#e87ba4", "triangle-down"),
}
GROUPS = {"reference": "Ref.", "isolated": "Isolated modifications", "combined": "Combined modifications"}
GROUP_FILL = {"reference": "#ecebe6", "isolated": None, "combined": "#f5f4f1"}
WIDTH, FONT_SIZE = 792, 17
# After the When filter S_When = 1 for every candidate, so no score falls below 1/3; the axis starts
# just under that bound to give the crossings room. (0, 1) restores the full scale.
Y_RANGE = (0.3, 1.0)


def read_csv(name: str) -> list[dict]:
    with open(OUTPUT / name, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load() -> tuple[list[dict], dict]:
    rankings = read_csv("rankings.csv")
    results = read_csv("results.csv")
    diagnoses = [r["diagnosis"] for r in rankings]
    data = {cid: {"score": [], "rank": []} for cid in CANDIDATES}
    for d in diagnoses:
        rows = {r["candidate"]: r for r in results if r["diagnosis"] == d}
        if set(rows) != set(CANDIDATES):
            raise SystemExit(f"{d}: candidates {sorted(rows)} in results.csv, expected {sorted(CANDIDATES)}")
        if sorted(int(r["rank"]) for r in rows.values()) != [1, 2, 3, 4, 5]:
            raise SystemExit(f"{d}: ranks are not a permutation of 1..5")
        for cid in CANDIDATES:
            data[cid]["score"].append(float(rows[cid]["score"]))
            data[cid]["rank"].append(int(rows[cid]["rank"]))
    if len(diagnoses) != 20:
        raise SystemExit(f"{len(diagnoses)} diagnoses in rankings.csv, expected 20")
    return rankings, data


def group_spans(rankings: list[dict]) -> list[tuple[str, int, int]]:
    spans = []
    for i, r in enumerate(rankings):
        if spans and spans[-1][0] == r["group"]:
            spans[-1] = (r["group"], spans[-1][1], i)
        else:
            spans.append((r["group"], i, i))
    return spans


def base_layout(fig: go.Figure, rankings: list[dict], height: int, top: int, bottom: int,
                left: int = 78, fills: bool = True) -> None:
    """Shared layout; groups are shaded bands (fills) or dotted separators."""
    fig.update_layout(
        width=WIDTH, height=height, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font={"family": FONT, "size": FONT_SIZE, "color": INK},
        margin={"l": left, "r": 14, "t": top, "b": bottom},
        legend={"orientation": "h", "x": 0, "xanchor": "left", "xref": "paper",
                "y": 0, "yanchor": "bottom", "yref": "container", "traceorder": "normal",
                "font": {"size": FONT_SIZE - 2}, "entrywidth": 0.5, "entrywidthmode": "fraction",
                "itemwidth": 36},
        hoverlabel={"font": {"family": FONT, "size": FONT_SIZE - 3}},
        hovermode="closest",
    )
    fig.update_xaxes(
        tickmode="array", tickvals=list(range(len(rankings))), ticktext=[r["diagnosis"] for r in rankings],
        range=[-0.6, len(rankings) - 0.4], showgrid=False, zeroline=False, showline=True,
        linecolor=AXIS, linewidth=1, ticks="outside", ticklen=4, tickcolor=AXIS,
        tickfont={"color": INK_SECONDARY, "size": FONT_SIZE - 3},
        title={"text": "Desired Adaptation Scenario (independent configurations)", "standoff": 8,
               "font": {"size": FONT_SIZE - 2, "color": INK_SECONDARY}},
    )
    for group, first, last in group_spans(rankings):
        if fills and GROUP_FILL[group]:
            fig.add_vrect(x0=first - 0.5, x1=last + 0.5, fillcolor=GROUP_FILL[group], line_width=0, layer="below")
        if not fills and first > 0:
            fig.add_vline(x=first - 0.5, line={"color": AXIS, "width": 1, "dash": "dot"}, layer="below")
        fig.add_annotation(x=(first + last) / 2, y=1, xref="x", yref="paper", yanchor="bottom", yshift=30,
                           text=GROUPS[group], showarrow=False,
                           font={"size": FONT_SIZE - 3, "color": INK_SECONDARY})


def add_row(fig: go.Figure, label: str, texts: list[str], yshift: int) -> None:
    """A row of ink labels above the plot, one per diagnosis."""
    fig.add_annotation(x=-0.6, y=1, xref="x", yref="paper", xanchor="right", yanchor="bottom", yshift=yshift,
                       text=label, showarrow=False, font={"size": FONT_SIZE - 4, "color": INK_SECONDARY})
    for i, text in enumerate(texts):
        if text:
            fig.add_annotation(x=i, y=1, xref="x", yref="paper", yanchor="bottom", yshift=yshift, text=text,
                               showarrow=False, font={"size": FONT_SIZE - 4, "color": INK})


def candidate_traces(fig: go.Figure, rankings: list[dict], data: dict, key: str) -> None:
    labels = [r["label"] for r in rankings]
    for cid, (name, color, symbol) in CANDIDATES.items():
        values = data[cid][key]
        other = data[cid]["rank" if key == "score" else "score"]
        fig.add_trace(go.Scatter(
            x=list(range(len(rankings))), y=values, name=f"{cid} {name}", mode="lines+markers",
            line={"color": color, "width": 2},
            marker={"color": color, "symbol": symbol, "size": 9, "line": {"color": SURFACE, "width": 1.5}},
            customdata=[[r["diagnosis"], lab, o] for r, lab, o in zip(rankings, labels, other)],
            hovertemplate=(f"<b>{cid} {name}</b><br>%{{customdata[0]}}: %{{customdata[1]}}<br>"
                           + ("similarity %{y:.4f}<br>rank %{customdata[2]}" if key == "score"
                              else "rank %{y}<br>similarity %{customdata[2]:.4f}")
                           + "<extra></extra>"),
        ))


def build_similarity(rankings: list[dict], data: dict) -> go.Figure:
    fig = go.Figure()
    base_layout(fig, rankings, height=470, top=62, bottom=128)
    candidate_traces(fig, rankings, data, "score")
    add_row(fig, "Top-1", [r["top1"] for r in rankings], yshift=6)
    # After the When filter S_When = 1, so no score can fall below 1/3
    fig.add_hline(y=1 / 3, line={"color": INK_MUTED, "width": 1, "dash": "dot"}, layer="below")
    fig.add_annotation(x=len(rankings) - 0.45, y=1 / 3, xref="x", yref="y", xanchor="right", yanchor="bottom",
                       text="minimum possible score (1/3)", showarrow=False,
                       font={"size": FONT_SIZE - 5, "color": INK_SECONDARY})
    fig.update_yaxes(title={"text": "Similarity", "standoff": 6, "font": {"size": FONT_SIZE - 2,
                                                                          "color": INK_SECONDARY}},
                     range=list(Y_RANGE), dtick=0.1, tickformat=".1f", showgrid=True, gridcolor=GRID,
                     gridwidth=1, zeroline=False, showline=False, ticks="",
                     tickfont={"color": INK_SECONDARY, "size": FONT_SIZE - 3})
    return fig


def build_ranking(rankings: list[dict], data: dict) -> go.Figure:
    fig = go.Figure()
    fig.add_hrect(y0=0.5, y1=3.5, fillcolor="#f0f6fd", line_width=0, layer="below")  # before the separators
    base_layout(fig, rankings, height=430, top=80, bottom=128, left=118, fills=False)
    fig.add_annotation(x=len(rankings) - 0.45, y=3.5, xref="x", yref="y", xanchor="right", yanchor="bottom",
                       text="Top-3", showarrow=False, font={"size": FONT_SIZE - 5, "color": INK_SECONDARY})
    candidate_traces(fig, rankings, data, "rank")
    add_row(fig, "Top-1 ≠ D0", ["●" if r["top1_changed"] == "True" else "" for r in rankings], yshift=24)
    add_row(fig, "Top-3 set ≠ D0", ["◆" if r["top3_set_changed"] == "True" else "" for r in rankings],
            yshift=4)
    for cid in CANDIDATES:  # direct labels at the right end, where the ranks are distinct
        fig.add_annotation(x=len(rankings) - 1, y=data[cid]["rank"][-1], xref="x", yref="y", xanchor="left",
                           xshift=10, text=cid, showarrow=False, font={"size": FONT_SIZE - 4, "color": INK})
    fig.update_xaxes(range=[-0.6, len(rankings) + 0.3])
    fig.update_yaxes(title={"text": "Ranking position", "standoff": 6,
                            "font": {"size": FONT_SIZE - 2, "color": INK_SECONDARY}},
                     range=[5.5, 0.5], tickvals=[1, 2, 3, 4, 5], showgrid=True, gridcolor=GRID,
                     zeroline=False, showline=False, ticks="",
                     tickfont={"color": INK_SECONDARY, "size": FONT_SIZE - 3})
    # Group annotations sit above the two marker rows
    for a in fig.layout.annotations:
        if a.text in GROUPS.values():
            a.yshift = 50
    return fig


def dodge(values: dict[str, float], min_gap: float) -> dict[str, float]:
    """Label positions at least min_gap apart, pushed down from the highest value."""
    placed, previous = {}, None
    for cid, value in sorted(values.items(), key=lambda kv: -kv[1]):
        y = value if previous is None else min(value, previous - min_gap)
        placed[cid], previous = y, y
    return placed


def build_similarity_ranking(rankings: list[dict], data: dict) -> go.Figure:
    """The ranking figure with similarity on Y: filled markers are the Top-3, open markers ranks 4 and 5."""
    height, top, bottom = 510, 80, 150
    fig = go.Figure()
    base_layout(fig, rankings, height=height, top=top, bottom=bottom, left=118, fills=False)
    labels = [r["label"] for r in rankings]
    for cid, (name, color, symbol) in CANDIDATES.items():
        in_top3 = [rank <= 3 for rank in data[cid]["rank"]]
        fig.add_trace(go.Scatter(
            x=list(range(len(rankings))), y=data[cid]["score"], name=f"{cid} {name}", mode="lines+markers",
            line={"color": color, "width": 2},
            marker={"symbol": symbol, "size": 10,
                    "color": [color if t else SURFACE for t in in_top3],
                    "line": {"color": [SURFACE if t else color for t in in_top3],
                             "width": [1.5 if t else 2 for t in in_top3]}},
            customdata=[[r["diagnosis"], lab, rank] for r, lab, rank in zip(rankings, labels, data[cid]["rank"])],
            hovertemplate=(f"<b>{cid} {name}</b><br>%{{customdata[0]}}: %{{customdata[1]}}<br>"
                           "similarity %{y:.4f}<br>rank %{customdata[2]}<extra></extra>"),
        ))
    add_row(fig, "Top-1", [r["top1"] for r in rankings], yshift=32)
    add_row(fig, "Top-3 set ≠ D0", ["◆" if r["top3_set_changed"] == "True" else "" for r in rankings], yshift=12)
    for a in fig.layout.annotations:  # group names above the two rows
        if a.text in GROUPS.values():
            a.yshift = 56

    fig.add_hline(y=1 / 3, line={"color": INK_MUTED, "width": 1, "dash": "dot"}, layer="below")
    fig.add_annotation(x=len(rankings) - 0.45, y=1 / 3, xref="x", yref="y", xanchor="right", yanchor="bottom",
                       text="minimum possible score (1/3)", showarrow=False,
                       font={"size": FONT_SIZE - 5, "color": INK_SECONDARY})

    # Direct labels at the right end, spread apart where the last values are close
    plot_px = height - top - bottom
    min_gap = 15 * (Y_RANGE[1] - Y_RANGE[0]) / plot_px
    last = {cid: data[cid]["score"][-1] for cid in CANDIDATES}
    for cid, y in dodge(last, min_gap).items():
        fig.add_annotation(x=len(rankings) - 1, y=y, xref="x", yref="y", xanchor="left", xshift=10,
                           text=cid, showarrow=False, font={"size": FONT_SIZE - 4, "color": INK})
    fig.update_layout(legend_title={"text": "Filled marker: in the Top-3 · open marker: rank 4 or 5",
                                    "side": "top", "font": {"size": FONT_SIZE - 4, "color": INK_SECONDARY}})
    fig.update_xaxes(range=[-0.6, len(rankings) + 0.3])
    fig.update_yaxes(title={"text": "Similarity", "standoff": 6,
                            "font": {"size": FONT_SIZE - 2, "color": INK_SECONDARY}},
                     range=list(Y_RANGE), dtick=0.1, tickformat=".1f", showgrid=True, gridcolor=GRID,
                     zeroline=False, showline=False, ticks="",
                     tickfont={"color": INK_SECONDARY, "size": FONT_SIZE - 3})
    return fig


def export(fig: go.Figure, name: str) -> None:
    FIGURES.mkdir(exist_ok=True)
    fig.write_html(FIGURES / f"{name}.html", include_plotlyjs=True, full_html=True,
                   config={"displaylogo": False, "responsive": False})
    size = {"width": fig.layout.width, "height": fig.layout.height}  # Kaleido does not read them from the layout
    for fmt in ("svg", "pdf"):
        fig.write_image(FIGURES / f"{name}.{fmt}", format=fmt, **size)
    fig.write_image(FIGURES / f"{name}.png", format="png", scale=4, **size)
    print(f"  {FIGURES / name}.{{html,svg,pdf,png}}")


def main() -> None:
    rankings, data = load()
    export(build_similarity(rankings, data), "similarity_scores")
    export(build_ranking(rankings, data), "candidate_rankings")
    export(build_similarity_ranking(rankings, data), "similarity_rankings")


if __name__ == "__main__":
    main()
