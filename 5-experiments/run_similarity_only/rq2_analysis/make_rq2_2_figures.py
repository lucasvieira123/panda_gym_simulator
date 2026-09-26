"""
RQ2.2 -- geracao das figuras finais (Painel A + Painel B + combinada) a
partir EXCLUSIVAMENTE dos resultados reais ja existentes em rq2_analysis/
e configs/desired_scenario.json.

NAO recalcula similaridade, NAO reimplementa o Retriever, NAO modifica
nenhum CSV/JSON de resultado -- so le, reconcilia (mesma logica de
classify_rq2_grid_perturbations.py) e plota.

Gera em rq2_analysis/figures/:
    rq2_2_panel_a.pdf / .svg / .png
    rq2_2_panel_b.pdf / .svg / .png            (versao completa, 2 sub-paineis)
    rq2_2_panel_b_alt.pdf / .svg / .png        (versao simplificada, so o topo)
    rq2_2_combined.pdf / .svg / .png           (A + B lado a lado)
"""
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import pandas as pd

ANALYSIS_DIR = Path(__file__).resolve().parent
CONFIGS_DIR = ANALYSIS_DIR.parent / "configs"
FIG_DIR = ANALYSIS_DIR / "figures"
FIG_DIR.mkdir(exist_ok=True)

REF_DO = "apply_vacuum_assist()"
C2_DO = "reposition_and_regrip()"

# ---------------------------------------------------------------------------
# Etapa 1 (reaproveitada) -- carregar e reconciliar os dados reais
# ---------------------------------------------------------------------------
summary = pd.read_csv(ANALYSIS_DIR / "rq2_summary.csv")
full = pd.read_csv(ANALYSIS_DIR / "rq2_full_ranking.csv")
classif = pd.read_csv(ANALYSIS_DIR / "rq2_grid_perturbation_classification.csv")
desired = {d["name"]: d for d in json.load(open(CONFIGS_DIR / "desired_scenario.json", encoding="utf-8"))}

REFERENCE_CLAUSES = {"object_lift_height_cm": ("<", 10.0), "finger_contacts": ("<", 2.0), "lateral_friction": ("<=", 0.315)}
CLAUSE_RE = re.compile(r"(object_lift_height_cm|finger_contacts|lateral_friction)\s*(<=|>=|<|>|==|!=)\s*([\d.]+)")

def classify_given(given: str) -> str:
    clauses = {v: (op, float(val)) for v, op, val in CLAUSE_RE.findall(given)}
    op_changed = any(clauses[v][0] != REFERENCE_CLAUSES[v][0] for v in REFERENCE_CLAUSES)
    val_changed = any(clauses[v][1] != REFERENCE_CLAUSES[v][1] for v in REFERENCE_CLAUSES)
    if not op_changed and not val_changed:
        return "Baseline"
    if not op_changed:
        return "Threshold-only"
    if not val_changed:
        return "Operator-only"
    return "Combined"

RECONCILED = {
    "H03xC02xF02": "diagnosed_LIFT_OBJECT_unanticipated__RQ2_C11_friction_0p300",
    "H03xC02xF03": "diagnosed_LIFT_OBJECT_unanticipated__RQ2_A0_baseline_full_context",
    "H03xC02xF04": "diagnosed_LIFT_OBJECT_unanticipated__RQ2_C03_friction_0p330",
}

# Painel A: 897 nativos R_* (ja tem categoria em classif) + 3 reaproveitados
panel_a_rows = classif[["desired_scenario", "category"]].merge(
    summary[["desired_scenario", "reference_similarity", "best_competitor_similarity",
             "top1_is_reference", "is_exact_tie_at_top"]],
    on="desired_scenario", how="left",
)
for hcf, name in RECONCILED.items():
    cat = classify_given(desired[name]["given"])
    srow = summary[summary["desired_scenario"] == name].iloc[0]
    panel_a_rows = pd.concat([panel_a_rows, pd.DataFrame([{
        "desired_scenario": f"{name} (reused as {hcf})",
        "category": cat,
        "reference_similarity": srow["reference_similarity"],
        "best_competitor_similarity": srow["best_competitor_similarity"],
        "top1_is_reference": srow["top1_is_reference"],
        "is_exact_tie_at_top": srow["is_exact_tie_at_top"],
    }])], ignore_index=True)

assert len(panel_a_rows) == 900, f"esperava 900 pontos reconciliados, achei {len(panel_a_rows)}"
counts = panel_a_rows["category"].value_counts().to_dict()
expected_counts = {"Threshold-only": 209, "Operator-only": 7, "Combined": 683, "Baseline": 1}
assert counts == expected_counts, f"contagem de categorias nao bate: {counts} != {expected_counts}"
n_flips = int(((~panel_a_rows["top1_is_reference"]) & (~panel_a_rows["is_exact_tie_at_top"])).sum())
n_ties = int(panel_a_rows["is_exact_tie_at_top"].sum())
assert n_flips == 7 and n_ties == 36, f"flips={n_flips} ties={n_ties}, esperado 7/36"

D_REF_X = float(panel_a_rows.loc[panel_a_rows["category"] == "Baseline", "reference_similarity"].iloc[0])
D_REF_Y = float(panel_a_rows.loc[panel_a_rows["category"] == "Baseline", "best_competitor_similarity"].iloc[0])

print(f"[validado] 900 pontos reconciliados; categorias={counts}; flips={n_flips}; ties={n_ties}")
print(f"[validado] D_ref: X(C_ref)={D_REF_X:.6f}  Y(melhor concorrente)={D_REF_Y:.6f}")

# Grupo C (Painel B, topo): 15 C0x + D_ref
c_ids = sorted(classif_c := full[full["desired_scenario"].str.contains("RQ2_C\\d")]["desired_scenario"].unique(),
               key=lambda n: n)
group_c_names = [n for n in summary["desired_scenario"] if re.search(r"RQ2_C\d+_", n)]
assert len(group_c_names) == 15, f"esperava 15 cenarios C0x, achei {len(group_c_names)}"

def friction_threshold(given: str) -> float:
    m = re.search(r"lateral_friction\s*(?:<=|>=)\s*([\d.]+)", given)
    return float(m.group(1))

rows_b_top = []
for name in group_c_names + ["diagnosed_LIFT_OBJECT_unanticipated__RQ2_A0_baseline_full_context"]:
    given = desired[name]["given"]
    fr = friction_threshold(given)
    fr_full = full[full["desired_scenario"] == name]
    cref_sim = float(fr_full[fr_full["adaptive_behavior"] == REF_DO]["final_similarity"].iloc[0])
    c2_sim = float(fr_full[fr_full["adaptive_behavior"] == C2_DO]["final_similarity"].iloc[0])
    rows_b_top.append({"name": name, "friction": fr, "cref": cref_sim, "c2": c2_sim,
                        "is_ref": name.endswith("RQ2_A0_baseline_full_context")})
df_b_top = pd.DataFrame(rows_b_top).sort_values("friction").reset_index(drop=True)
assert len(df_b_top) == 16, f"esperava 16 pontos no Grupo C + D_ref, achei {len(df_b_top)}"
print(f"[validado] Grupo C + D_ref: {len(df_b_top)} pontos, friction de {df_b_top['friction'].min()} a {df_b_top['friction'].max()}")

# Painel B, base: D_ref vs R_H03_C02_F08 (so o operador do atrito muda)
op_flip_name = "diagnosed_LIFT_OBJECT_unanticipated__RQ2_R_H03_C02_F08"
op_flip_given = desired[op_flip_name]["given"]
op_flip_cat = classify_given(op_flip_given)
assert op_flip_cat == "Operator-only", f"R_H03_C02_F08 deveria ser Operator-only, veio {op_flip_cat}"
assert "lateral_friction >= 0.315" in op_flip_given, f"Given inesperado: {op_flip_given}"
assert "object_lift_height_cm < 10" in op_flip_given and "finger_contacts < 2" in op_flip_given, \
    f"altura/contatos deveriam estar inalterados: {op_flip_given}"

fr_op = full[full["desired_scenario"] == op_flip_name]
op_cref = float(fr_op[fr_op["adaptive_behavior"] == REF_DO]["final_similarity"].iloc[0])
op_c2 = float(fr_op[fr_op["adaptive_behavior"] == C2_DO]["final_similarity"].iloc[0])
ref_cref = float(df_b_top.loc[df_b_top["is_ref"], "cref"].iloc[0])
ref_c2 = float(df_b_top.loc[df_b_top["is_ref"], "c2"].iloc[0])
print(f"[validado] D_ref (<=0.315): C_ref={ref_cref:.6f}  C2={ref_c2:.6f}")
print(f"[validado] R_H03_C02_F08 (>=0.315): C_ref={op_cref:.6f}  C2={op_c2:.6f}")
print(f"[validado] Given confirmado: {op_flip_given}")

# ---------------------------------------------------------------------------
# Estilo / paleta (consistente com a figura da RQ2.1: C_ref azul, C2 laranja)
# ---------------------------------------------------------------------------
COL_CREF = "#2a78d6"
COL_C2 = "#eb6834"
COL_THRESHOLD = "#1baf7a"
COL_OPERATOR = "#4a3aa7"
COL_COMBINED = "#c3c2b7"
COL_DREF = "#0b0b0b"
COL_FLIP = "#d03b3b"
COL_TIE_EDGE = "#0b0b0b"
COL_GRID = "#e1e0d9"
COL_AXIS = "#898781"
COL_TEXT = "#0b0b0b"
COL_TEXT_MUTED = "#52514e"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "axes.edgecolor": COL_AXIS,
    "axes.labelcolor": COL_TEXT,
    "xtick.color": COL_TEXT_MUTED,
    "ytick.color": COL_TEXT_MUTED,
    "svg.fonttype": "none",
    "pdf.fonttype": 42,  # texto editavel no PDF (nao rasterizado como path)
})


# ---------------------------------------------------------------------------
# Painel A
# ---------------------------------------------------------------------------
def draw_panel_a(ax, fontsize_base=7.2):
    ax.set_title("(A) Retrieval outcomes across predicate variations", fontsize=fontsize_base + 1.3, loc="left", pad=8)

    lo, hi = 0.62, 1.02
    ax.plot([lo, hi], [lo, hi], color=COL_AXIS, linewidth=1.0, linestyle="--", zorder=1, dashes=(4, 3))
    ax.text(hi - 0.01, hi - 0.035, "y = x", fontsize=fontsize_base - 1, color=COL_TEXT_MUTED,
             ha="right", va="top", style="italic")

    cat_style = {
        "Combined":       dict(color=COL_COMBINED, size=8,  alpha=0.45, zorder=2),
        "Threshold-only": dict(color=COL_THRESHOLD, size=10, alpha=0.60, zorder=3),
        "Operator-only":  dict(color=COL_OPERATOR,  size=26, alpha=0.95, zorder=4),
    }
    for cat, style in cat_style.items():
        sub = panel_a_rows[panel_a_rows["category"] == cat]
        ax.scatter(sub["reference_similarity"], sub["best_competitor_similarity"],
                    s=style["size"], c=style["color"], alpha=style["alpha"],
                    linewidths=0, zorder=style["zorder"], label=cat)

    # empates: anel preto em volta (nao muda a cor de categoria de baixo)
    ties = panel_a_rows[panel_a_rows["is_exact_tie_at_top"]]
    ax.scatter(ties["reference_similarity"], ties["best_competitor_similarity"],
                s=34, facecolors="none", edgecolors=COL_TIE_EDGE, linewidths=0.8,
                zorder=5, label="Exact tie at top")

    # flips: X vermelho por cima (outro candidato supera C_ref)
    flips = panel_a_rows[(~panel_a_rows["top1_is_reference"]) & (~panel_a_rows["is_exact_tie_at_top"])]
    ax.scatter(flips["reference_similarity"], flips["best_competitor_similarity"],
                s=46, c=COL_FLIP, marker="x", linewidths=1.6,
                zorder=6, label="Other candidate wins")

    # D_ref: estrela preta, anotada
    ax.scatter([D_REF_X], [D_REF_Y], s=90, c=COL_DREF, marker="*", zorder=7,
                edgecolors="white", linewidths=0.5, label=r"$D_{\mathrm{ref}}$")
    ax.annotate(r"$D_{\mathrm{ref}}$", xy=(D_REF_X, D_REF_Y), xytext=(D_REF_X - 0.16, D_REF_Y - 0.10),
                 fontsize=fontsize_base, color=COL_TEXT, fontweight="bold",
                 arrowprops=dict(arrowstyle="-", color=COL_AXIS, linewidth=0.8))

    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel("Similarity to $C_{\\mathrm{ref}}$", fontsize=fontsize_base + 0.5)
    ax.set_ylabel("Highest similarity among other candidates", fontsize=fontsize_base + 0.5)
    ax.set_xticks([0.6, 0.7, 0.8, 0.9, 1.0])
    ax.set_yticks([0.6, 0.7, 0.8, 0.9, 1.0])
    ax.tick_params(labelsize=fontsize_base - 0.5)
    ax.grid(color=COL_GRID, linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.set_aspect("equal", adjustable="box")

    ax.text(lo + 0.015, hi - 0.02, "other candidate\nsuperior", fontsize=fontsize_base - 1.3,
             color=COL_TEXT_MUTED, ha="left", va="top", style="italic")
    ax.text(hi - 0.015, lo + 0.015, "$C_{\\mathrm{ref}}$ superior", fontsize=fontsize_base - 1.3,
             color=COL_TEXT_MUTED, ha="right", va="bottom", style="italic")

    legend_elems = [
        mpatches.Patch(facecolor=COL_COMBINED, label=f"Combined (n={counts['Combined']})", alpha=0.6),
        mpatches.Patch(facecolor=COL_THRESHOLD, label=f"Threshold-only (n={counts['Threshold-only']})", alpha=0.7),
        mpatches.Patch(facecolor=COL_OPERATOR, label=f"Operator-only (n={counts['Operator-only']})"),
        Line2D([0], [0], marker="*", color="none", markerfacecolor=COL_DREF, markersize=9, label="$D_{\\mathrm{ref}}$ (n=1)"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor="none", markeredgecolor=COL_TIE_EDGE,
               markersize=6, label=f"Exact tie at top (n={n_ties})"),
        Line2D([0], [0], marker="x", color="none", markeredgecolor=COL_FLIP, markersize=6.5,
               markeredgewidth=1.6, label=f"Other candidate wins (n={n_flips})"),
    ]
    ax.legend(handles=legend_elems, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2,
               fontsize=fontsize_base - 1.6, frameon=False, handletextpad=0.5,
               borderaxespad=0.2, labelspacing=0.4, columnspacing=1.0)


# ---------------------------------------------------------------------------
# Painel B (versao completa: topo threshold sweep, base operator flip)
# ---------------------------------------------------------------------------
def draw_panel_b_top(ax, fontsize_base=7.2, with_title=True):
    if with_title:
        ax.set_title("(B) Effect of friction-predicate variations", fontsize=fontsize_base + 1.3, loc="left", pad=8)

    ax.axvline(0.315, color=COL_AXIS, linewidth=0.9, linestyle="--", dashes=(4, 3), zorder=1)
    ax.text(0.315, ax.get_ylim()[1] if ax.get_ylim()[1] > 0 else 1.0, "", alpha=0)  # noop, ylim set later

    ax.plot(df_b_top["friction"], df_b_top["cref"], color=COL_CREF, linewidth=1.6,
             marker="o", markersize=4.2, zorder=3, label="$C_{\\mathrm{ref}}$ — Lift Slip ($C_1$)")
    ax.plot(df_b_top["friction"], df_b_top["c2"], color=COL_C2, linewidth=1.6,
             marker="s", markersize=4.0, zorder=3, label="$C_2$ — Parallel Arm Lift")

    ref_row = df_b_top[df_b_top["is_ref"]].iloc[0]
    ax.scatter([ref_row["friction"]], [ref_row["cref"]], s=60, facecolors="none",
                edgecolors=COL_DREF, linewidths=1.1, zorder=4)
    ax.annotate(r"$D_{\mathrm{ref}}$", xy=(ref_row["friction"], ref_row["cref"]),
                 xytext=(ref_row["friction"] + 0.006, ref_row["cref"] + 0.028),
                 fontsize=fontsize_base - 0.8, color=COL_TEXT, fontweight="bold")

    ax.set_xlabel("Friction threshold in Given ($\\leq$ value)", fontsize=fontsize_base)
    ax.set_ylabel("Similarity score", fontsize=fontsize_base)
    xmin, xmax = df_b_top["friction"].min(), df_b_top["friction"].max()
    pad = (xmax - xmin) * 0.06
    ax.set_xlim(xmax + pad, xmin - pad)  # invertido: threshold decrescente da esquerda p/ direita, como o Grupo C original
    ax.set_ylim(0.85, 1.0)
    ax.tick_params(labelsize=fontsize_base - 0.8)
    ax.grid(color=COL_GRID, linewidth=0.5, zorder=0, axis="y")
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.legend(loc="lower left", fontsize=fontsize_base - 1.4, frameon=False, handlelength=1.6,
               borderaxespad=0.2, labelspacing=0.3)


def draw_panel_b_bottom(ax, fontsize_base=7.2):
    labels = ["$D_{\\mathrm{ref}}$\n($\\leq$ 0.315)", "Operator flip\n($\\geq$ 0.315)"]
    cref_vals = [ref_cref, op_cref]
    c2_vals = [ref_c2, op_c2]

    x = [0, 1]
    width = 0.32
    bars1 = ax.bar([xi - width / 2 for xi in x], cref_vals, width=width, color=COL_CREF,
                    zorder=3, label="$C_{\\mathrm{ref}}$ — Lift Slip ($C_1$)")
    bars2 = ax.bar([xi + width / 2 for xi in x], c2_vals, width=width, color=COL_C2,
                    zorder=3, label="$C_2$ — Parallel Arm Lift")

    for bars, vals in ((bars1, cref_vals), (bars2, c2_vals)):
        for rect, v in zip(bars, vals):
            ax.text(rect.get_x() + rect.get_width() / 2, v + 0.012, f"{v:.3f}",
                     ha="center", va="bottom", fontsize=fontsize_base - 1.6, color=COL_TEXT)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=fontsize_base - 0.6)
    ax.set_ylabel("Similarity score", fontsize=fontsize_base)
    ax.set_ylim(0, 1.18)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.tick_params(labelsize=fontsize_base - 0.8)
    ax.grid(color=COL_GRID, linewidth=0.5, zorder=0, axis="y")
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2, fontsize=fontsize_base - 1.4,
               frameon=False, borderaxespad=0.2, labelspacing=0.3, columnspacing=1.2)
    ax.set_title("Relational-operator flip on the friction predicate\n(height and contacts unchanged)",
                  fontsize=fontsize_base - 0.3, loc="left", pad=6, color=COL_TEXT_MUTED)


# ---------------------------------------------------------------------------
# Montagem das figuras
# ---------------------------------------------------------------------------
def save_all(fig, stem):
    fig.savefig(FIG_DIR / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{stem}.svg", bbox_inches="tight")
    fig.savefig(FIG_DIR / f"{stem}.png", bbox_inches="tight", dpi=300)
    print(f"  saved {stem}.pdf / .svg / .png")


# Painel A isolado
fig_a, ax_a = plt.subplots(figsize=(3.4, 3.4), dpi=300)
draw_panel_a(ax_a)
fig_a.tight_layout()
save_all(fig_a, "rq2_2_panel_a")
plt.close(fig_a)

# Painel B isolado (completo, 2 sub-paineis empilhados)
fig_b, (ax_b1, ax_b2) = plt.subplots(2, 1, figsize=(3.4, 4.6), dpi=300,
                                       gridspec_kw={"height_ratios": [1.15, 1]})
draw_panel_b_top(ax_b1)
draw_panel_b_bottom(ax_b2)
fig_b.tight_layout(h_pad=2.0)
save_all(fig_b, "rq2_2_panel_b")
plt.close(fig_b)

# Painel B alternativo (simplificado -- so o sweep de threshold, sem o painel de barras)
fig_b_alt, ax_b_alt = plt.subplots(figsize=(3.4, 2.5), dpi=300)
draw_panel_b_top(ax_b_alt, with_title=True)
fig_b_alt.tight_layout()
save_all(fig_b_alt, "rq2_2_panel_b_alt")
plt.close(fig_b_alt)

# Combinada: A (esq.) + B completo (dir.), layout horizontal para largura de duas colunas
fig_c = plt.figure(figsize=(7.0, 4.6), dpi=300)
gs = fig_c.add_gridspec(2, 2, width_ratios=[1.05, 1], height_ratios=[1.15, 1], wspace=0.38, hspace=0.55)
ax_ca = fig_c.add_subplot(gs[:, 0])
ax_cb1 = fig_c.add_subplot(gs[0, 1])
ax_cb2 = fig_c.add_subplot(gs[1, 1])
draw_panel_a(ax_ca, fontsize_base=6.6)
draw_panel_b_top(ax_cb1, fontsize_base=6.6)
draw_panel_b_bottom(ax_cb2, fontsize_base=6.6)
save_all(fig_c, "rq2_2_combined")
plt.close(fig_c)

print()
print("Todas as figuras geradas em:", FIG_DIR)
