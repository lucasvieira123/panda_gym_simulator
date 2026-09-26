"""
RQ2.2 -- figura simplificada para publicacao (ACM TAAS), 2 paineis:
  (A) Numerical Threshold Variation -- Grupo C (sweep 1D de lateral_friction) + D_ref
  (B) Relational Operator Variation -- D_ref (<=0.315) vs R_H03_C02_F08 (>=0.315)

Os ~900 pontos da grade fatorial (R_*) NAO entram nesta figura -- ficam
reservados para tabela/narrativa separada, conforme pedido.

NAO recalcula similaridade, NAO reimplementa o Retriever, NAO modifica
nenhum CSV/JSON de resultado -- so le rq2_summary.csv/rq2_full_ranking.csv/
desired_scenario.json e plota. Todos os valores usados sao reconferidos
aqui, de forma independente da figura anterior (rq2_2_combined).

Gera em rq2_analysis/figures/:
    rq2_2_simplified.pdf / .svg / .png
"""
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import pandas as pd

ANALYSIS_DIR = Path(__file__).resolve().parent
CONFIGS_DIR = ANALYSIS_DIR.parent / "configs"
FIG_DIR = ANALYSIS_DIR / "figures"
FIG_DIR.mkdir(exist_ok=True)

REF_DO = "apply_vacuum_assist()"   # C_ref = Lift Slip (C1)
C2_DO = "reposition_and_regrip()"  # C2 = Parallel Arm Lift

# ---------------------------------------------------------------------------
# Etapa de revisao cientifica -- recarrega e reconfere tudo do zero
# ---------------------------------------------------------------------------
summary = pd.read_csv(ANALYSIS_DIR / "rq2_summary.csv")
full = pd.read_csv(ANALYSIS_DIR / "rq2_full_ranking.csv")
desired = {d["name"]: d for d in json.load(open(CONFIGS_DIR / "desired_scenario.json", encoding="utf-8"))}


def friction_threshold(given: str) -> float:
    m = re.search(r"lateral_friction\s*(?:<=|>=)\s*([\d.]+)", given)
    return float(m.group(1))


# --- Painel A: Grupo C (15 pontos C01-C16, sem C08) + D_ref = 16 pontos ---
group_c_names = [n for n in summary["desired_scenario"] if re.search(r"RQ2_C\d+_", n)]
assert len(group_c_names) == 15, f"[revisao 1] esperava 15 cenarios C0x, achei {len(group_c_names)}"

rows_a = []
for name in group_c_names + ["diagnosed_LIFT_OBJECT_unanticipated__RQ2_A0_baseline_full_context"]:
    given = desired[name]["given"]
    assert "object_lift_height_cm < 10" in given and "finger_contacts < 2" in given and "<=" in given.split("lateral_friction")[1], \
        f"[revisao 1] altura/contatos/operador deveriam estar fixos em {name}: {given}"
    fr = friction_threshold(given)
    fr_full = full[full["desired_scenario"] == name]
    cref = float(fr_full[fr_full["adaptive_behavior"] == REF_DO]["final_similarity"].iloc[0])
    c2 = float(fr_full[fr_full["adaptive_behavior"] == C2_DO]["final_similarity"].iloc[0])
    rows_a.append({"name": name, "friction": fr, "cref": cref, "c2": c2,
                    "is_ref": name.endswith("RQ2_A0_baseline_full_context")})
df_a = pd.DataFrame(rows_a).sort_values("friction", ascending=True).reset_index(drop=True)
assert len(df_a) == 16, f"[revisao 1] esperava 16 pontos (Grupo C + D_ref), achei {len(df_a)}"
assert df_a["is_ref"].sum() == 1, "[revisao 1] D_ref deveria aparecer exatamente 1 vez"
print(f"[revisao 1] OK -- Grupo C = {len(group_c_names)} + D_ref = {len(df_a)} pontos totais, "
      f"friction de {df_a['friction'].min()} a {df_a['friction'].max()}, ordenados ascendente")
print(f"[revisao 1] C_ref sempre >= C2 no Grupo C? {(df_a['cref'] >= df_a['c2']).all()} "
      f"(C_ref min={df_a['cref'].min():.6f}, C2 max={df_a['c2'].max():.6f})")

# --- Painel B: D_ref (<=0.315) vs R_H03_C02_F08 (>=0.315) ---
D_REF_NAME = "diagnosed_LIFT_OBJECT_unanticipated__RQ2_A0_baseline_full_context"
OP_FLIP_NAME = "diagnosed_LIFT_OBJECT_unanticipated__RQ2_R_H03_C02_F08"

d_ref_given = desired[D_REF_NAME]["given"]
op_given = desired[OP_FLIP_NAME]["given"]
print(f"[revisao 2] D_ref given: {d_ref_given}")
print(f"[revisao 3] Cenario modificado given: {op_given}")
assert d_ref_given == "object_lift_height_cm < 10 AND finger_contacts < 2 AND lateral_friction <= 0.315"
assert op_given == "object_lift_height_cm < 10 AND finger_contacts < 2 AND lateral_friction >= 0.315", \
    "[revisao 3] o cenario modificado deveria trocar SO o operador do atrito, mantendo os demais predicados"
print("[revisao 3] OK -- confirmado: unica diferenca entre os dois Givens e '<=' -> '>=' em lateral_friction; "
      "altura e contatos identicos e no mesmo valor numerico (10 / 2), atrito no mesmo valor numerico (0.315).")

d_ref_full = full[full["desired_scenario"] == D_REF_NAME]
op_full = full[full["desired_scenario"] == OP_FLIP_NAME]
d_ref_cref = float(d_ref_full[d_ref_full["adaptive_behavior"] == REF_DO]["final_similarity"].iloc[0])
d_ref_c2 = float(d_ref_full[d_ref_full["adaptive_behavior"] == C2_DO]["final_similarity"].iloc[0])
op_cref = float(op_full[op_full["adaptive_behavior"] == REF_DO]["final_similarity"].iloc[0])
op_c2 = float(op_full[op_full["adaptive_behavior"] == C2_DO]["final_similarity"].iloc[0])

print(f"[revisao 2] D_ref (<=0.315):    C_ref={d_ref_cref:.6f}  C2={d_ref_c2:.6f}")
print(f"[revisao 4] Modificado (>=0.315): C_ref={op_cref:.6f}  C2={op_c2:.6f}")
flip_happens = op_c2 > op_cref
diff = op_c2 - op_cref
print(f"[revisao 4] C2 ultrapassa C_ref no cenario modificado? {flip_happens}  |  diferenca exata = {diff:.6f}")
assert flip_happens, "[revisao 4] esperava que C2 ultrapassasse C_ref no cenario com operador invertido"

# cross-check com rq2_summary.csv (rank/top1) para o mesmo cenario, evita depender so do full_ranking
op_summary = summary[summary["desired_scenario"] == OP_FLIP_NAME].iloc[0]
assert op_summary["top1_is_reference"] == False
assert "Parallel Arm" in op_summary["top1_candidate_name"]
print(f"[revisao 4] Confirmado via rq2_summary.csv: top1_candidate_name='{op_summary['top1_candidate_name']}', "
      f"top1_is_reference={op_summary['top1_is_reference']}")

# ---------------------------------------------------------------------------
# Estilo (cores consistentes com as figuras anteriores da RQ2.1/RQ2.2)
# ---------------------------------------------------------------------------
COL_CREF = "#2a78d6"
COL_C2 = "#eb6834"
COL_DREF_MARK = "#0b0b0b"
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
    "pdf.fonttype": 42,
    "font.size": 8,
})

fig, (axA, axB) = plt.subplots(1, 2, figsize=(7.0, 2.85), dpi=300, gridspec_kw={"width_ratios": [1.15, 1]})

# --- Painel A ---
axA.set_title("(A) Numerical Threshold Variation", fontsize=9, loc="left", pad=6)
axA.plot(df_a["friction"], df_a["cref"], color=COL_CREF, linewidth=1.6, marker="o",
          markersize=4.0, zorder=3, label="$C_{\\mathrm{ref}}$ (Lift Slip)")
axA.plot(df_a["friction"], df_a["c2"], color=COL_C2, linewidth=1.6, marker="s",
          markersize=3.6, zorder=3, label="$C_2$ (Parallel Arm Lift)")

ref_row = df_a[df_a["is_ref"]].iloc[0]
axA.scatter([ref_row["friction"]], [ref_row["cref"]], s=64, facecolors="none",
             edgecolors=COL_DREF_MARK, linewidths=1.2, zorder=4)
axA.annotate("$D_{\\mathrm{ref}}$", xy=(ref_row["friction"], ref_row["cref"]),
              xytext=(ref_row["friction"] - 0.006, ref_row["cref"] - 0.026),
              fontsize=7.6, color=COL_TEXT, fontweight="bold", ha="center", va="top")

axA.set_xlabel("Friction threshold ($\\leq$ value)", fontsize=8.3)
axA.set_ylabel("Similarity score", fontsize=8.3)
axA.set_xlim(df_a["friction"].min() - 0.006, df_a["friction"].max() + 0.006)
axA.set_ylim(0.85, 1.0)
axA.tick_params(labelsize=7.4)
axA.grid(color=COL_GRID, linewidth=0.5, zorder=0)
axA.set_axisbelow(True)
for s in ("top", "right"):
    axA.spines[s].set_visible(False)

# --- Painel B (slope chart, escala nao-zero) ---
axB.set_title("(B) Relational Operator Variation", fontsize=9, loc="left", pad=6)

x_pos = [0, 1]
x_labels = ["Original\n($\\leq$ 0.315)", "Modified\n($\\geq$ 0.315)"]

axB.plot(x_pos, [d_ref_cref, op_cref], color=COL_CREF, linewidth=1.8, marker="o",
          markersize=5.2, zorder=3)
axB.plot(x_pos, [d_ref_c2, op_c2], color=COL_C2, linewidth=1.8, marker="s",
          markersize=5.0, zorder=3)

for xi, (v_cref, v_c2) in zip(x_pos, [(d_ref_cref, d_ref_c2), (op_cref, op_c2)]):
    # Deslocamento vertical adaptativo: o ponto mais alto NESTA posicao recebe
    # o rotulo empurrado pra cima, o mais baixo pra baixo -- nao uma regra
    # fixa por serie, porque em "Modified" a ordem local se inverte (C2 fica
    # acima de C_ref) e um offset fixo faria os dois textos se cruzarem.
    cref_above = v_cref >= v_c2
    dy_cref = 9 if cref_above else -12
    dy_c2 = -12 if cref_above else 9
    ha = "left" if xi == 0 else "right"
    dx = 6 if xi == 0 else -6
    axB.annotate(f"{v_cref:.3f}", xy=(xi, v_cref), xytext=(dx, dy_cref),
                  textcoords="offset points", fontsize=7.2, color=COL_CREF,
                  ha=ha, fontweight="bold")
    axB.annotate(f"{v_c2:.3f}", xy=(xi, v_c2), xytext=(dx, dy_c2),
                  textcoords="offset points", fontsize=7.2, color=COL_C2,
                  ha=ha, fontweight="bold")

# destaque discreto da troca de lideranca (sem caixa) -- anel + seta curta
# vindo de uma area vazia do grafico (canto superior direito), pra nao
# cruzar nenhuma das duas linhas nem os rotulos numericos.
axB.scatter([1], [op_c2], s=80, facecolors="none", edgecolors=COL_DREF_MARK,
             linewidths=1.3, zorder=4)
axB.annotate("Top-1 changes", xy=(1, op_c2), xytext=(0.80, 0.975),
              fontsize=7.0, color=COL_TEXT_MUTED, style="italic", ha="center",
              arrowprops=dict(arrowstyle="-", color=COL_TEXT_MUTED, linewidth=0.7,
                               connectionstyle="arc3,rad=0.15"))

axB.set_xlim(-0.35, 1.35)
y_center = (d_ref_cref + op_cref + d_ref_c2 + op_c2) / 4
axB.set_ylim(0.865, 0.995)  # zoom deliberado: intervalo real dos 4 valores, sem iniciar em 0
axB.set_xticks(x_pos)
axB.set_xticklabels(x_labels, fontsize=7.6)
axB.set_ylabel("Similarity score", fontsize=8.3)
axB.tick_params(labelsize=7.4)
axB.grid(color=COL_GRID, linewidth=0.5, zorder=0, axis="y")
axB.set_axisbelow(True)
for s in ("top", "right"):
    axB.spines[s].set_visible(False)

# --- legenda unica e compacta, abaixo dos dois paineis ---
legend_elems = [
    Line2D([0], [0], color=COL_CREF, marker="o", markersize=4.5, linewidth=1.6, label="$C_{\\mathrm{ref}}$ — Lift Slip ($C_1$)"),
    Line2D([0], [0], color=COL_C2, marker="s", markersize=4.2, linewidth=1.6, label="$C_2$ — Parallel Arm Lift"),
    Line2D([0], [0], marker="o", color="none", markerfacecolor="none", markeredgecolor=COL_DREF_MARK,
           markersize=6.5, label="$D_{\\mathrm{ref}}$ / Top-1 change"),
]
fig.legend(handles=legend_elems, loc="lower center", bbox_to_anchor=(0.5, -0.06), ncol=3,
            fontsize=7.6, frameon=False, handletextpad=0.5, columnspacing=1.3, borderaxespad=0.0)

fig.tight_layout(rect=[0, 0.05, 1, 1])

for ext in ("pdf", "svg", "png"):
    kwargs = {"bbox_inches": "tight"}
    if ext == "png":
        kwargs["dpi"] = 300
    fig.savefig(FIG_DIR / f"rq2_2_simplified.{ext}", **kwargs)
    print(f"  saved rq2_2_simplified.{ext}")

plt.close(fig)
print()
print("Figura simplificada gerada em:", FIG_DIR)
