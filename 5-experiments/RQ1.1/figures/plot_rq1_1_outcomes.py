"""Figura dos resultados agregados da RQ1.1: caminho de cada execução por grupo de superfície.

Lê os `outcome.json` da bateria final (`5-experiments/RQ1.1/bateria/results/`, versão
`37fda0d`), confere os totais contra os números relatados no artigo e gera duas variantes:

- `rq1_1_outcomes.*`      compacta, para cerca de 3,5 in de largura impressa
- `rq1_1_outcomes_wide.*` mais larga, para a largura do texto do acmsmall (~5,5 in)

Cada variante sai em HTML (interativo), SVG, PDF (para pdflatex, que não lê SVG) e PNG.
As fontes são dimensionadas para cerca de 8,5–9 pt na largura impressa indicada.

Requer `pip install plotly kaleido` (o Kaleido usa o Chrome instalado na máquina).
Uso, a partir da raiz do projeto:
    python 5-experiments/RQ1.1/figures/plot_rq1_1_outcomes.py
"""
import json
from pathlib import Path

import plotly.graph_objects as go

HERE    = Path(__file__).resolve().parent
RESULTS = HERE.parent / "bateria" / "results"

# Grupos como na tabela de configurações do artigo, de cima para baixo
GROUPS = [
    ("G1 — Adhesive residues", (0.800, 0.700, 0.600)),
    ("Nominal",                (0.500,)),
    ("G2 — Moisture",          (0.400, 0.300, 0.250, 0.200, 0.180, 0.170, 0.160, 0.155, 0.150, 0.145)),
    ("G3 — Lubricants",        (0.140, 0.135, 0.130, 0.120, 0.110, 0.100, 0.080, 0.060, 0.040, 0.020, 0.010)),
]

# Caminho do outcome.json -> categoria da figura. A rampa azul (claro -> escuro) ordena o esforço
# de adaptação; o fail-safe é outro tipo de resultado: outra cor e hachura, legível em cinza.
CATEGORIES = [
    # scenario, rótulo, cor, cor do número, hachura
    ("A", "No ASM violation",       "#86b6ef", "#0b0b0b", ""),
    ("B", "1st candidate recovery", "#2a78d6", "#ffffff", ""),
    ("C", "2nd candidate recovery", "#104281", "#ffffff", ""),
    ("D", "Fail-safe activation",   "#eb6834", "#0b0b0b", "/"),
]

# Números relatados no texto; a figura não é gerada se os arquivos divergirem
EXPECTED = {
    "G1 — Adhesive residues": {"A": 3, "B": 0, "C": 0, "D": 0},
    "Nominal":                {"A": 1, "B": 0, "C": 0, "D": 0},
    "G2 — Moisture":          {"A": 6, "B": 4, "C": 0, "D": 0},
    "G3 — Lubricants":        {"A": 0, "B": 8, "C": 1, "D": 2},
}
EXPECTED_GOALS = 23

INK, INK_SECONDARY, SURFACE = "#0b0b0b", "#52514e", "#ffffff"
FONT = "Arial, Helvetica, sans-serif"

VARIANTS = {
    # nome: largura e altura em px, fonte base, margem inferior e onde ficam os nomes dos grupos.
    # Na compacta, o nome fica acima de cada barra, para as barras e a legenda (2 colunas) usarem a
    # largura toda; na larga, fica à esquerda, e a legenda ocupa 2 linhas sob as barras.
    "rq1_1_outcomes":      {"width": 504, "height": 380, "font": 17, "bottom": 112, "labels_above": True},
    "rq1_1_outcomes_wide": {"width": 792, "height": 270, "font": 18, "bottom": 92,  "labels_above": False},
}


def load_counts() -> tuple[dict, int]:
    group_of = {mu: name for name, mus in GROUPS for mu in mus}
    counts = {name: {scenario: 0 for scenario, *_ in CATEGORIES} for name, _ in GROUPS}
    goals, seen = 0, set()
    for path in sorted(RESULTS.glob("*/outcome.json")):
        outcome = json.loads(path.read_text(encoding="utf-8"))
        mu = round(outcome["lateral_friction"], 3)
        scenario = outcome["scenario"]
        if mu not in group_of or mu in seen:
            raise SystemExit(f"{path}: atrito {mu} fora da bateria ou repetido")
        if scenario not in counts[group_of[mu]]:
            raise SystemExit(f"{path}: caminho {scenario} não previsto na figura")
        seen.add(mu)
        counts[group_of[mu]][scenario] += 1
        goals += bool(outcome["physical"]["global_goal_achieved"])
    if len(seen) != 25:
        raise SystemExit(f"esperadas 25 execuções em {RESULTS}, encontradas {len(seen)}")
    return counts, goals


def check(counts: dict, goals: int) -> None:
    for name, mus in GROUPS:
        if sum(counts[name].values()) != len(mus):
            raise SystemExit(f"{name}: {sum(counts[name].values())} execuções, esperadas {len(mus)}")
    if counts != EXPECTED:
        raise SystemExit(f"contagens divergem do texto:\n{json.dumps(counts, indent=1)}")
    if sum(sum(c.values()) for c in counts.values()) != 25:
        raise SystemExit("o total das categorias não soma 25")
    if goals != EXPECTED_GOALS:
        raise SystemExit(f"objetivo global em {goals} execuções, esperadas {EXPECTED_GOALS}")


def build(counts: dict, width: int, height: int, font: int, bottom: int, labels_above: bool) -> go.Figure:
    totals = {name: len(mus) for name, mus in GROUPS}
    labels = [f"{name} (n = {totals[name]})" for name, _ in GROUPS]
    bargap = 0.48 if labels_above else 0.32
    fig = go.Figure()
    for scenario, label, color, text_color, hatch in CATEGORIES:
        values = [counts[name][scenario] for name, _ in GROUPS]
        fig.add_trace(go.Bar(
            name=label, orientation="h", y=labels,
            x=[v or None for v in values],                     # zero: sem segmento, rótulo nem tooltip
            text=[str(v) if v else "" for v in values],
            textposition="inside", insidetextanchor="middle", textangle=0,
            textfont={"color": text_color, "size": font},
            marker={"color": color, "line": {"color": SURFACE, "width": 1.5},
                    "pattern": {"shape": hatch, "fgcolor": "#ffffff", "fgopacity": 0.45,
                                "size": 7, "solidity": 0.3}},
            customdata=[[name, totals[name]] for name, _ in GROUPS],
            hovertemplate=("<b>%{customdata[0]}</b><br>" + label +
                           "<br>%{x} of %{customdata[1]} configurations<extra></extra>"),
        ))
    top = 4 if labels_above else 6
    fig.update_layout(
        barmode="stack", bargap=bargap, barcornerradius=3,
        width=width, height=height,
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font={"family": FONT, "size": font, "color": INK},
        margin={"l": 12 if labels_above else 8, "r": 12, "t": top, "b": bottom},
        uniformtext={"minsize": font - 4, "mode": "hide"},  # número só onde cabe
        # Legenda no pé da figura, sob o título do eixo X, alinhada com o início das barras
        legend={"orientation": "h", "x": 0, "xanchor": "left", "xref": "paper",
                "y": 0, "yanchor": "bottom", "yref": "container",
                "traceorder": "normal", "font": {"size": font - 1}, "itemwidth": 30,
                "entrywidth": 0.5, "entrywidthmode": "fraction"},
        hoverlabel={"font": {"family": FONT, "size": font - 2}},
    )
    fig.update_yaxes(categoryorder="array", categoryarray=labels[::-1], automargin=True,
                     showgrid=False, showline=False, ticks="", ticklabelstandoff=6,
                     showticklabels=not labels_above, tickfont={"color": INK})
    if labels_above:
        # Altura de cada barra em px, para pôr o nome do grupo logo acima dela
        bar_px = (height - top - bottom) / len(GROUPS) * (1 - bargap)
        for text in labels:
            fig.add_annotation(x=0, y=text, xref="x", yref="y", text=text, showarrow=False,
                               xanchor="left", yanchor="bottom", yshift=bar_px / 2 + 1, xshift=-2,
                               font={"size": font - 1, "color": INK})
    fig.update_xaxes(title={"text": "Number of configurations", "standoff": 6,
                            "font": {"size": font - 1, "color": INK_SECONDARY}},
                     range=[0, 11.2], dtick=1, showgrid=False, zeroline=False,
                     showline=True, linecolor="#b8b7b0", linewidth=1, ticks="outside",
                     ticklen=4, tickcolor="#b8b7b0", tickfont={"color": INK_SECONDARY, "size": font - 2})
    return fig


def main() -> None:
    counts, goals = load_counts()
    check(counts, goals)
    for name, variant in VARIANTS.items():
        fig = build(counts, **variant)
        fig.write_html(HERE / f"{name}.html", include_plotlyjs=True, full_html=True,
                       config={"displaylogo": False, "responsive": False})
        size = {"width": variant["width"], "height": variant["height"]}  # o Kaleido não lê do layout
        for fmt in ("svg", "pdf"):
            fig.write_image(HERE / f"{name}.{fmt}", format=fmt, **size)
        fig.write_image(HERE / f"{name}.png", format="png", scale=4, **size)
    print("Totais conferidos: 25 execuções; 10 sem violação, 12 pelo 1º candidato, 1 pelo 2º, "
          f"2 fail-safe; objetivo global em {goals}/25.")
    for name in VARIANTS:
        print(f"  {HERE / name}.{{html,svg,pdf,png}}")


if __name__ == "__main__":
    main()
