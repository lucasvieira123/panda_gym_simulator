"""Figura HIPOTÉTICA da RQ1.1: o 0,155 contado como violação no transporte recuperada pelo C6.

Não é resultado experimental. Na bateria (versão `37fda0d`), o 0,155 não teve violação: a
desaceleração final do transporte (F5) manteve o cubo preso. Sem ela, a bancada mostra o 0,155
violando no TRANSPORT_OBJECT (`bateria/bancada25/bench155_old.py`). Esta figura ilustra esse
cenário, para apresentação, e traz o aviso na própria imagem. Os `outcome.json` não são alterados:
as contagens reais são lidas e conferidas, e a troca é aplicada só aqui, em memória.

Uso, a partir da raiz do projeto:
    python 5-experiments/RQ1.1/figures/plot_rq1_1_outcomes_hypothetical.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plot_rq1_1_outcomes as real  # noqa: E402

OUT = HERE / "hypothetical"
GROUP = "G2 — Moisture"
NOTE = ("<b>Hypothetical — not an experimental result.</b><br>"
        "μ = 0.155 is counted as a transport violation recovered by C6;<br>"
        "in the experiment it had no violation.")
NOTE_PX = 3  # linhas do aviso


def main() -> None:
    counts, goals = real.load_counts()
    real.check(counts, goals)                      # os dados reais continuam conferidos
    counts[GROUP]["A"] -= 1                        # 0,155: sem violação -> ...
    counts[GROUP]["B"] += 1                        # ... violação no transporte resolvida pelo C6
    OUT.mkdir(exist_ok=True)
    for name, variant in real.VARIANTS.items():
        fig = real.build(counts, **variant)
        extra = int(NOTE_PX * (variant["font"] - 2) * 1.35) + 10
        height = variant["height"] + extra         # a área das barras fica igual
        top = fig.layout.margin.t + extra
        fig.update_layout(height=height, margin={"t": top})
        fig.add_annotation(text=NOTE, xref="paper", yref="paper", x=0, y=1, yshift=extra - 2,
                           xanchor="left", yanchor="top", align="left", showarrow=False,
                           font={"size": variant["font"] - 2, "color": "#a3360f"})
        stem = OUT / f"{name}_hypothetical_155"
        fig.write_html(f"{stem}.html", include_plotlyjs=True, full_html=True,
                       config={"displaylogo": False, "responsive": False})
        size = {"width": variant["width"], "height": height}
        for fmt in ("svg", "pdf"):
            fig.write_image(f"{stem}.{fmt}", format=fmt, **size)
        fig.write_image(f"{stem}.png", format="png", scale=4, **size)
        print(f"  {stem}.{{html,svg,pdf,png}}")
    print(f"Hipotética: {GROUP} = {counts[GROUP]}; objetivo global continua {goals}/25.")


if __name__ == "__main__":
    main()
