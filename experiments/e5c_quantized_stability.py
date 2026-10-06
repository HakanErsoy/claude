"""E5c: inverse stability of the quantized coefficient tables, in exact arithmetic.

For both E5 configurations, every positive-order row of the coefficient ROM
defines a derivative bank whose inverse (the D/E-type at the mirrored
order) is stable iff the quantized DC gain H_q(1) > 0 (and H_q(-1) > 0,
which is also checked). Coefficients and pole steps are dyadic rationals,
so both signs are evaluated exactly with fractions.Fraction.

Reported per configuration, without and with the quantization-aware DC
floor (the floating-point floor is active in both):
  rows with H_q(1) <= 0, rows with H_q(-1) <= 0, and for the worst row the
  dominant inverse pole z* > 1 (exact bisection on z H_q(z), which is
  increasing for z > theta_max) and its e-folding time 1/ln z*.

Outputs: results/e5c_quantized_stability.json
"""

import json
import math
import os
import sys
from fractions import Fraction

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.fixedpoint import FixedPointBank  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "results")
CONFIGS = {"WS36_WM16": ("AB", 36, 16), "WS48_WM25": ("ABDE", 48, 25)}


def frac(MS):
    M, S = MS
    return Fraction(M, 1 << S) if S >= 0 else Fraction(M * (1 << -S))


def zH(z, row, theta):
    """z H_q(z) = z + c_d + sum_k c_k z / (z - theta_k), sample units (g0 = 1)."""
    return z + frac(row[-1]) + sum(frac(c) * z / (z - t) for c, t in zip(row[:-1], theta))


def dominant_pole(row, theta, iters=80):
    lo, hi = Fraction(1), Fraction(2)
    if zH(lo, row, theta) > 0:
        return None
    while zH(hi, row, theta) <= 0:
        hi *= 2
    for _ in range(iters):
        mid = (lo + hi) / 2
        if zH(mid, row, theta) <= 0:
            lo = mid
        else:
            hi = mid
    return lo


def analyse(fp):
    theta = [1 - frac(u) for u in fp.U]
    rows = [(a, row) for a, row in zip(fp.grid, fp.C) if a > 0]
    bad1, badm1, worst = [], 0, None
    for a, row in rows:
        H1 = zH(Fraction(1), row, theta)
        Hm1 = -zH(Fraction(-1), row, theta)
        if Hm1 <= 0:
            badm1 += 1
        if H1 <= 0:
            bad1.append((float(a), H1, row))
            if worst is None or H1 < worst[1]:
                worst = (float(a), H1, row)
    out = {"positive_rows": len(rows), "rows_H1_nonpositive": len(bad1), "rows_Hm1_nonpositive": badm1}
    if worst is not None:
        z = dominant_pole(worst[2], theta)
        out.update(worst_alpha=worst[0], worst_H1=float(worst[1]), dominant_pole_minus_1=float(z - 1),
                   efolding_samples=float(1.0 / math.log(float(z))) if z > 1 else None)
    return out


def main():
    e5 = json.load(open(os.path.join(OUT, "e5_fixed_point.json")))
    d = e5["design"]
    bank = DiscreteFixedPoleBank(1.0, d["xi_lo"], d["xi_hi"], d["K"])
    res = {}
    for name, (env, WS, WM) in CONFIGS.items():
        V = e5["envelopes"][env]["V_max"]
        res[name] = {}
        for floor in (False, True):
            fp = FixedPointBank(bank, P=e5["P"], amax=0.95, WS=WS, WM=WM, n_max=4000, V_max=V, dc_floor=floor)
            r = analyse(fp)
            res[name]["quantized_floor" if floor else "float_floor_only"] = r
            print(name, "quantized floor" if floor else "float floor only", r, flush=True)
    with open(os.path.join(OUT, "e5c_quantized_stability.json"), "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
