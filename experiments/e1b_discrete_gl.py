"""E1b: discrete-time fixed-pole bank against the GL definitions.

References are Sierociuk's Def. 2 (A-type) and Def. 3 (B-type) at h = Ts,
so any input can be used. Two error notions are reported:

* total error: realization output vs GL-A / GL-B
* definitional error: realization output vs the *same realization* run as
  a frozen-order LTI system. For a piecewise-constant order with value set
  V and masks M_v = [alpha == v]:
      own A-type:  y[n] = (R_{alpha[n]} u)[n]
      own B-type:  y    = sum_v R_v (u * M_v)            (linearity)
  This isolates what the switching does from how well each LTI member
  approximates s^alpha, so CT/DT band mismatch of the Oustaloup baselines
  does not enter.

Outputs: results/e1b_discrete.json
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.oustaloup import SwitchedOustaloup  # noqa: E402
from vofrac.reference import gl_A, gl_B  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "results")
TS = 1e-3
NSAMP = 4001
DFP = dict(xi_lo=1e-4, xi_hi=4e5, K=32)
OU = dict(w_b=1e-3, w_h=1e5, N=15)      # 31 states, comparable to 32 + delay


def rel_rms(y, r, skip=100):
    return float(np.sqrt(np.mean((y - r)[skip:] ** 2) / np.mean(r[skip:] ** 2)))


def make_inputs(t, rng):
    return {
        "step": np.ones_like(t),
        "noise": rng.standard_normal(len(t)),
        "multisine": sum(np.sin(2 * np.pi * f * t + p) for f, p in [(0.5, 0.1), (3, 1.0), (17, 2.0), (60, 0.5)]),
    }


def make_profiles(t, rng):
    n = len(t)
    return {
        "switch +0.3->+0.7": (np.where(t < 2.0, 0.3, 0.7), True),
        "switch -0.3->-0.7": (np.where(t < 2.0, -0.3, -0.7), True),
        "switch -0.5->+0.5": (np.where(t < 2.0, -0.5, 0.5), True),
        "random piecewise": (np.repeat(rng.uniform(-0.8, 0.8, 20), n // 20 + 1)[:n], True),
        "smooth derivative": (0.5 + 0.3 * np.sin(np.pi * t / 2), False),
        "smooth integral": (-0.5 + 0.3 * np.sin(np.pi * t / 2), False),
        "smooth crossing": (0.6 * np.sin(np.pi * t / 2), False),
    }


def realizations():
    bank = DiscreteFixedPoleBank(TS, **DFP)
    ou_p = SwitchedOustaloup(OU["w_b"], OU["w_h"], OU["N"], "parallel")
    ou_c = SwitchedOustaloup(OU["w_b"], OU["w_h"], OU["N"], "cascade")
    return {
        "DFP-out": lambda u, a: bank.simulate(u, a, "output"),
        "DFP-in": lambda u, a: bank.simulate(u, a, "input"),
        "Ou-par": lambda u, a: ou_p.simulate(u, a, TS),
        "Ou-cas": lambda u, a: ou_c.simulate(u, a, TS),
    }


def own_references(sim, u, alpha):
    vals = np.unique(alpha)
    ownA = np.empty_like(u)
    ownB = np.zeros_like(u)
    for v in vals:
        mask = alpha == v
        const = np.full_like(u, v)
        ownA[mask] = sim(u, const)[mask]
        ownB += sim(u * mask, const)
    return ownA, ownB


def main():
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(1)
    t = np.arange(NSAMP) * TS
    inputs = make_inputs(t, rng)
    profiles = make_profiles(t, rng)
    reals = realizations()
    out = {"Ts": TS, "N": NSAMP, "DFP": DFP, "Oustaloup": OU, "rows": []}
    for pname, (alpha, piecewise) in profiles.items():
        for iname, u in inputs.items():
            rA, rB = gl_A(u, alpha, TS), gl_B(u, alpha, TS)
            row = {"profile": pname, "input": iname, "gap_AB": rel_rms(rA, rB)}
            for name, sim in reals.items():
                y = sim(u, alpha)
                rec = {"A": rel_rms(y, rA), "B": rel_rms(y, rB)}
                if piecewise:
                    ownA, ownB = own_references(sim, u, alpha)
                    rec["def_A"] = rel_rms(y, ownA)
                    rec["def_B"] = rel_rms(y, ownB)
                row[name] = rec
            out["rows"].append(row)
            msg = f"{pname:18s} {iname:9s} gap {row['gap_AB']:.1e}"
            for name in reals:
                r = row[name]
                msg += f" | {name} A {r['A']:.1e} B {r['B']:.1e}"
                if piecewise:
                    msg += f" dA {r['def_A']:.1e} dB {r['def_B']:.1e}"
            print(msg, flush=True)
    with open(os.path.join(OUT, "e1b_discrete.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
