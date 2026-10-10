"""X4: stability margins of the linearized per-DOF loops for the tuned controllers of X2.

Model and definitions: rovc/margins.py (hover linearization, command delay of
the simulator, thruster lag). Reported for the Oustaloup approximation that the
simulator implements and for the exact (j w)^alpha: phase margin, crossover
frequency and delay margin per DOF, and the extra delay each loop tolerates
at the nominal 10 ms.

    python3 -I experiments/x4_margins.py         # seconds, results/x4_margins.json
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rovc import margins, params, scenarios  # noqa: E402
from rovc.controllers import STRUCTURES  # noqa: E402

RES = os.path.join(os.path.dirname(__file__), "..", "results")


def main():
    picks = {}
    for r in json.load(open(os.path.join(RES, "x2_controllers.json"))).values():
        k = (r["structure"], r["method"])
        if k not in picks or r["f"] < picks[k]["f"]:
            picks[k] = r
    out = {}
    print(f"{'structure|tuner':26s} " + " ".join(f"{d:>16s}" for d in params.DOF) + "   (PM deg / DM ms)")
    for (sname, tuner), r in sorted(picks.items()):
        s = STRUCTURES[sname]
        half = len(s.names)
        x = np.array(r["x"])
        row = {}
        for d in range(6):
            xg = x[:half] if d < 3 else x[half:]
            row[params.DOF[d]] = {}
            for exact in (False, True):
                pm, wc, dm = margins.margins(margins.loop(s, xg, d, scenarios.DT, scenarios.DELAY, exact=exact))
                row[params.DOF[d]]["exact" if exact else "oustaloup"] = dict(pm_deg=pm, wc=wc, delay_margin=dm)
        out[f"{sname}|{tuner}"] = row
        print(f"{sname + '|' + tuner:26s} " + " ".join(
            f"{row[d]['oustaloup']['pm_deg']:7.1f}/{1e3 * row[d]['oustaloup']['delay_margin']:6.1f}"
            for d in params.DOF))
    json.dump(out, open(os.path.join(RES, "x4_margins.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
