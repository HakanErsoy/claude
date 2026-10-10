"""X3: the best tuned controller of each structure on the test cases T1-T4, plant variations and Monte Carlo.

For each structure and tuner the run with the lowest training cost (X2) is
evaluated (the controller is never retuned). Outputs per-DOF ITAE/IAE/ISE,
energy, peak error, overshoot and settling time (T1), the phase margins at the
three actuator points of the tuning constraint, the cost of the robustness
variants of T3 and T4, and 100 random plant/actuator draws on T4 (mass, added
mass, damping, buoyancy, battery voltage, thruster lag 0.05-0.2 s, latency
10-60 ms).

    python3 -I experiments/x3_evaluate.py        # ~3 min, results/x3_evaluate.json + x3_traces.npz
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rovc import margins, objective, params, scenarios, sim, thruster  # noqa: E402
from rovc.controllers import STRUCTURES  # noqa: E402
from rovc.sim import I_E, I_FAIL, I_IAE, I_ISE, I_ITAE, I_PEAK, I_TV  # noqa: E402

RES = os.path.join(os.path.dirname(__file__), "..", "results")
MC = 100


def best_runs(x2):
    out = {}
    for r in x2.values():
        k = (r["structure"], r["method"])
        if k not in out or r["f"] < out[k]["f"]:
            out[k] = r
    return out


def summary(m):
    return dict(ITAE=m[I_ITAE:I_ITAE + 6].tolist(), IAE=m[I_IAE:I_IAE + 6].tolist(),
                ISE=m[I_ISE:I_ISE + 6].tolist(), peak=m[I_PEAK:I_PEAK + 6].tolist(),
                wITAE=float(m[I_ITAE:I_ITAE + 6] @ scenarios.W_DOF), energy=float(m[I_E]),
                activity=float(m[I_TV]), fail=float(m[I_FAIL]), J=float(objective.cost(m[None])[0]))


def step_info(sc, tr, dofs=(0, 1, 2, 5), band=0.02):
    """Overshoot [%] and 2 % settling time [s] after the step at t = 1 s, against the raw set point."""
    out = {}
    for d in dofs:
        target = sc.raw[-1, d]
        y = tr[:, d]
        os_ = max(0.0, (np.max(y) - target) / abs(target) * 100.0) if target > 0 else 0.0
        outside = np.abs(y - target) > band * abs(target)
        idx = np.nonzero(outside)[0]
        ts = sc.t[idx[-1] + 1] - 1.0 if idx.size and idx[-1] + 1 < sc.t.size else (np.nan if idx.size else 0.0)
        out[params.DOF[d]] = dict(overshoot=float(os_), settling=float(ts))
    return out


def monte_carlo(base, n=MC, seed=7):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        veh = params.pack(mass=rng.uniform(0.8, 1.2), added=rng.uniform(0.5, 1.5),
                          damping=rng.uniform(0.5, 1.5), buoyancy=rng.uniform(0.98, 1.03))
        out.append(base.variant("mc", veh=veh, ca_true=thruster.coef_array(int(rng.choice([12, 14, 16, 18, 20]))),
                                tau_m=float(rng.uniform(0.05, 0.2)), delay=int(rng.integers(1, 7))))
    return out


def main():
    x2 = json.load(open(os.path.join(RES, "x2_controllers.json")))
    picks = best_runs(x2)
    tests = scenarios.tests()
    rob = scenarios.robustness(tests[2]) + scenarios.robustness(tests[3])
    mc = monte_carlo(tests[3])
    res, traces = {}, {}
    for (sname, tuner), r in sorted(picks.items()):
        s = STRUCTURES[sname]
        x = np.array(r["x"])
        key = f"{sname}|{tuner}"
        e = dict(structure=sname, tuner=tuner, train_J=r["f"], x=dict(zip(s.labels(), r["x"])), tests={},
                 pm_deg={f"tau_m {tm}, {10 * nd} ms": margins.phase_margins(s, x, scenarios.DT, nd, tau_m=tm,
                                                                           w=margins.W)[0].tolist()
                         for tm, nd, _ in objective.MARGIN_POINTS})
        for sc in tests:
            m, tr = sim.run(s, x, sc, trace=True)
            e["tests"][sc.name] = summary(m)
            traces[f"{key}|{sc.name}"] = tr[:, :20].astype(np.float32)
            if sc.name == "T1-step":
                e["step"] = step_info(sc, tr)
        e["robustness"] = {sc.name: summary(sim.run(s, x, sc)[0]) for sc in rob}
        mcJ = np.array([summary(sim.run(s, x, sc)[0])["wITAE"] for sc in mc])
        mcF = np.array([sim.run(s, x, sc)[0][I_FAIL] > 0 for sc in mc])
        e["monte_carlo"] = dict(wITAE=mcJ.tolist(), failures=int(mcF.sum()))
        res[key] = e
        t = e["tests"]
        print(f"{key:28s} train {r['f']:8.3f} | " + " ".join(f"{n.split('-')[0]} {t[n]['wITAE']:7.3f}"
                                                            for n in t) +
              f" | MC median {np.median(mcJ):.3f} p90 {np.percentile(mcJ, 90):.3f} fail {mcF.sum()}", flush=True)
    json.dump(res, open(os.path.join(RES, "x3_evaluate.json"), "w"), indent=1)
    np.savez_compressed(os.path.join(RES, "x3_traces.npz"), **traces)


if __name__ == "__main__":
    main()
