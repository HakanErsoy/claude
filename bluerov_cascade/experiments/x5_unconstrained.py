"""X5: what ITAE-only tuning does without latency and without the margin constraint.

The proposed controller is tuned as in the load-frequency study (no command
delay in the model, no phase-margin constraint), then its linearized phase
margins are computed and the simulator is rerun with 0..4 samples of command
delay. Compared with the margin-constrained tuning of X2 at the same delays.

    python3 -I experiments/x5_unconstrained.py   # ~5 min, results/x5_unconstrained.json
"""

import json
import os
import sys
from dataclasses import replace

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rovc import margins, objective, optim, scenarios, sim  # noqa: E402
from rovc.controllers import STRUCTURES  # noqa: E402
from rovc.sim import I_FAIL  # noqa: E402

RES = os.path.join(os.path.dirname(__file__), "..", "results")
S = "FOPID-(1+TFOID)"
DELAYS = (0, 1, 2, 3, 4, 6)


def delay_sweep(s, x, base):
    out = []
    for nd in DELAYS:
        m = sim.run(s, x, replace(base, delay=nd))[0]
        out.append(dict(delay=nd, J=float(objective.cost(m[None])[0]), fail=float(m[I_FAIL]),
                        pm_min=float(np.min(margins.phase_margins(s, x, base.dt, nd, w=margins.W)))))
    return out


def main():
    s = STRUCTURES[S]
    train0 = [replace(c, delay=0) for c in scenarios.training()]
    base = scenarios.tests()[3]
    res = {}
    for m in ("DE", "PSO"):
        for seed in range(3):
            ob = objective.Objective(s, cases=train0, pm_req=0.0)
            r = optim.minimize(m, ob, s.lb, s.ub, 3030, seed=seed)
            x = ob.params(r["x"])[0]
            key = f"unconstrained|{m}|{seed}"
            res[key] = dict(train_J=r["f"], x=x.tolist(),
                            pm_delay0=margins.phase_margins(s, x, base.dt, 0, w=margins.W)[0].tolist(),
                            sweep=delay_sweep(s, x, base))
            print(key, f"J={r['f']:.3f}", "PM(delay 0)", np.round(res[key]["pm_delay0"], 1),
                  "T4 J by delay", [round(d["J"], 2) for d in res[key]["sweep"]], flush=True)
    x2 = os.path.join(RES, "x2r_robust.json")
    if not os.path.exists(x2):
        x2 = os.path.join(RES, "x2_controllers.json")
    if os.path.exists(x2):
        runs = [r for r in json.load(open(x2)).values() if r["structure"] == S]
        best = min(runs, key=lambda r: r["f"])
        x = np.array(best["x"])
        res["constrained|best"] = dict(train_J=best["f"], method=best["method"], x=best["x"],
                                       sweep=delay_sweep(s, x, base))
        print("constrained best", "T4 J by delay", [round(d["J"], 2) for d in res["constrained|best"]["sweep"]])
    json.dump(res, open(os.path.join(RES, "x5_unconstrained.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
