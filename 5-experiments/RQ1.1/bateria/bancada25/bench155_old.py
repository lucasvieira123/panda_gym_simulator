"""Roda 0,155, 0,16 e 0,15 com o transporte antigo, sem a desaceleração da F5.

Mostra que 0,155 sem violação na bateria é efeito da F5. Uso, a partir da raiz do projeto:
    python 5-experiments/RQ1.1/bateria/bancada25/bench155_old.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "bancada"))
import bench


def use_old_transport():
    import tasks.object_delivery.transport_object_task as t
    t._SLOWDOWN_RANGE = 1e-12  # equivale ao controlador antigo (velocidade máxima até o fim)


if __name__ == "__main__":
    use_old_transport()
    plans = [{"mu": mu, "first": "vacuum", "strategy": "produção", "offset": None, "max_steps": 1000,
              "first_regrasp": {"finger_friction": 3.0}, "second": {"finger_friction": 7.0}}
             for mu in (0.155, 0.16, 0.15)]
    for p in plans:
        r = bench.simulate(p)  # no mesmo processo, para valer a troca do controlador
        print(p["mu"], bench.category(r), r["violation"], r["violation_step"], r["end_step"], r["dist_cm"],
              [(t["start"], t["ticks"], t["held_at_end"]) for t in r["transports"]])
