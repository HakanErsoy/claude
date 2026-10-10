"""X4: stability margins of the linearized per-DOF loops for the tuned controllers of X2.

Model and definitions: rovc/margins.py (hover linearization, command delay,
thruster lag). Reported at the three actuator points of the tuning constraint
(rovc.objective.MARGIN_POINTS), for the Oustaloup approximation that the
simulator implements and for the exact (j w)^alpha: phase margin, crossover
frequency and delay margin (extra latency tolerated) per DOF.

    python3 -I experiments/x4_margins.py         # seconds, results/x4_margins.json
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rovc import margins, objective, params, scenarios  # noqa: E402
from rovc.controllers import STRUCTURES  # noqa: E402

RES = os.path.join(os.path.dirname(__file__), "..", "results")


def main():
    picks = {}
    for r in json.load(open(os.path.join(RES, "x2_controllers.json"))).values():
        k = (r["structure"], r["method"])
        if k not in picks or r["f"] < picks[k]["f"]:
            picks[k] = r
    out = {}
    for (sname, tuner), r in sorted(picks.items()):
        s = STRUCTURES[sname]
        half = len(s.names)
        x = np.array(r["x"])
        row = {}
        for tm, nd, req in objective.MARGIN_POINTS:
            pt = f"tau_m {tm}, {10 * nd} ms"
            row[pt] = {}
            for d in range(6):
                xg = x[:half] if d < 3 else x[half:]
                row[pt][params.DOF[d]] = {}
                for exact in (False, True):
                    pm, wc, dm = margins.margins(margins.loop(s, xg, d, scenarios.DT, nd, tau_m=tm, exact=exact))
                    row[pt][params.DOF[d]]["exact" if exact else "oustaloup"] = dict(pm_deg=pm, wc=wc,
                                                                                     delay_margin=dm)
        out[f"{sname}|{tuner}"] = row
        nom = row[f"tau_m {objective.MARGIN_POINTS[0][0]}, {10 * objective.MARGIN_POINTS[0][1]} ms"]
        print(f"{sname + '|' + tuner:26s} nominal PM/DM: " + " ".join(
            f"{nom[d]['oustaloup']['pm_deg']:5.1f}/{1e3 * nom[d]['oustaloup']['delay_margin']:5.1f}"
            for d in params.DOF) + " | min PM per point: " + " ".join(
            f"{min(row[p][d]['oustaloup']['pm_deg'] for d in params.DOF):5.1f}" for p in row))
    json.dump(out, open(os.path.join(RES, "x4_margins.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
