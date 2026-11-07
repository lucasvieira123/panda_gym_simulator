"""Roda a bancada nos 25 atritos da bateria, posição nominal, para comparar com os runs reais.

Uso, a partir da raiz do projeto: python 5-experiments/RQ1.1/bateria/bancada25/bench25.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "bancada"))
import bench

MU = [0.80, 0.70, 0.60, 0.50, 0.40, 0.30, 0.25, 0.20, 0.18, 0.17, 0.16, 0.155, 0.150, 0.145, 0.140,
      0.135, 0.130, 0.120, 0.110, 0.100, 0.080, 0.060, 0.040, 0.020, 0.010]

if __name__ == "__main__":
    plans = [{"mu": mu, "first": "vacuum", "strategy": "produção", "offset": None, "max_steps": 1000,
              "first_regrasp": {"finger_friction": 3.0}, "second": {"finger_friction": 7.0}} for mu in MU]
    rows = bench.run_all(plans)
    for r in rows:
        print(r["mu"], bench.category(r), r["violation"], r["violation_step"], r["end_step"], r["dist_cm"],
              r["status"], r.get("first_ok"), r.get("second_ok"))
