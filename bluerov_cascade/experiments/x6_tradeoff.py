"""X6: nominal training cost against robustness, for every tuning run (not only the best one).

For each run of X2 (3030 evaluations, DE and PSO) and X2b (10 030 evaluations, PSO) of the
four cascades with an inner derivative action, evaluates the severe-noise test T2 and 100
Monte Carlo draws of T4 (the same draws as X3). Shows whether pushing the nominal cost down
makes the controllers more fragile.

    python3 -I experiments/x6_tradeoff.py        # ~5 min, results/x6_tradeoff.json
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rovc import objective, scenarios, sim  # noqa: E402
from rovc.controllers import STRUCTURES  # noqa: E402
from rovc.sim import I_FAIL  # noqa: E402
from x3_evaluate import monte_carlo  # noqa: E402

RES = os.path.join(os.path.dirname(__file__), "..", "results")
CASCADES = ("FOPID-(1+TFOID)", "P-PID", "PI-(1+FOPID)", "FOPI-FOPD")


def main():
    tests = scenarios.tests()
    t2, t4 = tests[1], tests[3]
    mc = monte_carlo(t4)
    out = {}
    for src, budget in (("x2_controllers.json", 3030), ("x2b_budget.json", 10030)):
        for k, r in json.load(open(os.path.join(RES, src))).items():
            if r["structure"] not in CASCADES:
                continue
            s = STRUCTURES[r["structure"]]
            x = np.array(r["x"])
            m2 = sim.run(s, x, t2)[0]
            m4 = sim.run(s, x, t4)[0]
            mcm = np.array([sim.run(s, x, sc)[0] for sc in mc])
            mcJ = objective.cost(mcm) / objective.cost(m4[None])[0]
            out[f"{budget}|{k}"] = dict(structure=r["structure"], method=r["method"], budget=budget, train_J=r["f"],
                                        T2_J=float(objective.cost(m2[None])[0]), T4_J=float(objective.cost(m4[None])[0]),
                                        mc_fail=int(np.sum(mcm[:, I_FAIL] > 0)),
                                        mc_ratio_median=float(np.median(mcJ)), mc_ratio_p90=float(np.percentile(mcJ, 90)))
            e = out[f"{budget}|{k}"]
            print(f"{budget:6d} {k:28s} train {e['train_J']:7.2f} T2 {e['T2_J']:8.1f} T4 {e['T4_J']:7.1f} "
                  f"MC fail {e['mc_fail']:3d} p90 ratio {e['mc_ratio_p90']:6.2f}", flush=True)
    json.dump(out, open(os.path.join(RES, "x6_tradeoff.json"), "w"), indent=1)
    # summary: rank correlation between training cost and fragility, per structure
    from scipy.stats import spearmanr
    for s in CASCADES:
        rows = [e for e in out.values() if e["structure"] == s and e["train_J"] < 1e3]
        tj = [e["train_J"] for e in rows]
        print(f"{s:16s} n={len(rows):2d}  Spearman(train J, MC failures) = {spearmanr(tj, [e['mc_fail'] for e in rows])[0]:+.2f}"
              f"  Spearman(train J, T2) = {spearmanr(tj, [e['T2_J'] for e in rows])[0]:+.2f}"
              f"  runs with 0 failures: {sum(e['mc_fail'] == 0 for e in rows)}")


if __name__ == "__main__":
    main()
