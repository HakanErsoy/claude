"""E8: accuracy against cost for four realizations of the A- and B-types.

Methods (all at Ts = 1e-3, memory R = n = 1000, orders on P = 39 levels
-0.95:0.05:0.95, which is how a ROM-addressed core sees the order):

  FP-rule   fixed poles, residues from the analytic rule (this paper)
  FP-LP     fixed geometric poles with the best (u_lo, u_hi) from a grid
            search, residues of each level fitted by a minimax LP
  FP-LPs    as FP-LP, with the residue-sign and DC constraints under which
            the inverse-stability proposition certifies the D/E inverses
  MP-rule   moving poles: each level has its own rule-designed grid on a
            common state count, state kept on an order change (hot swap)
  FIR       truncated GL convolution with exact weights up to lag L-1

Accuracy is the relative operator error ||W^ - W_T||_inf / ||W_T||_inf,
the worst-case relative output error over all bounded inputs: over the 39
constant orders, and over eight variable-order sequences (T = A for the
output-scheduled forms, T = B for the input-scheduled ones).

Cost per sample: multiplications (MACs), state words, and coefficient ROM
words for the P levels. For the fixed-pole designs the derivative levels are
also checked for residue signs and for a nonpositive DC gain (unstable D/E
inverse).

Outputs: results/e8_baselines.json
"""

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.baselines import (FittedFixedPole, best_fitted, kernel_from, ltv_matrix,  # noqa: E402
                              moving_pole_levels, rel_err_all)
from vofrac.design import design_dt  # noqa: E402
from vofrac.opnorm import gl_table, norm, operator_matrix  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "results")
TS = 1e-3
N = 1000
LEVELS = np.round(np.linspace(-0.95, 0.95, 39), 10)
P = len(LEVELS)
EPS_LIST = (1e-2, 3e-3, 1e-3, 3e-4, 1e-4, 3e-5, 1e-5, 1e-6, 1e-7)
K_LP = (6, 8, 10, 12, 14, 16, 20, 24, 28)
L_FIR = (2, 4, 8, 16, 32, 64, 128, 256, 512, 1000)
PROBE = (-0.95, -0.5, -0.1, 0.1, 0.5, 0.95)
U_LO = np.geomspace(1e-7, 1e-2, 11)
U_HI = (1.5, 2.0, 3.0, 6.0, 12.0, 24.0)


def level_index(values):
    return np.abs(np.asarray(values)[:, None] - LEVELS[None, :]).argmin(axis=1)


def sequences(rng):
    n = np.arange(N)
    q = lambda v: level_index(v)
    return {
        "switch +0.3->+0.8": q(np.where(n < N // 2, 0.3, 0.8)),
        "switch -0.3->-0.8": q(np.where(n < N // 2, -0.3, -0.8)),
        "switch -0.5->+0.5": q(np.where(n < N // 2, -0.5, 0.5)),
        "switch +0.8->-0.8": q(np.where(n < N // 2, 0.8, -0.8)),
        "alternating +-0.5 (period 50)": q(np.where((n // 25) % 2 == 0, 0.5, -0.5)),
        "random piecewise": np.repeat(rng.integers(0, P, 20), N // 20 + 1)[:N],
        "iid levels": rng.integers(0, P, N),
        "smooth crossing": q(0.6 * np.sin(2 * np.pi * n / N)),
    }


GL = gl_table(LEVELS, N, TS)
REF = {}


def reference(name, idx, T):
    key = (name, T)
    if key not in REF:
        W = operator_matrix(GL, idx, T)
        REF[key] = (W, norm(W, np.inf))
    return REF[key]


def const_error(table):
    """max over levels of ||E||_inf / ||W||_inf at constant order (last row is the largest)."""
    e = np.abs(table - GL)[:, 1:].sum(axis=1)
    return float(np.max(e / np.abs(GL).sum(axis=1)))


def vo_error(seqs, mats):
    """mats(idx, T) -> realized matrix; worst relative inf-norm error per type."""
    out = {}
    for T in "AB":
        worst = 0.0
        for name, idx in seqs.items():
            W, wn = reference(name, idx, T)
            worst = max(worst, norm(mats(idx, T) - W, np.inf) / wn)
        out[T] = worst
    return out


def inverse_stats(levels):
    """Derivative levels whose residues are not all <= 0 (sign test of the stability
    proposition not applicable) and whose DC gain H(1) <= 0 (then H has a real zero in
    [1, inf) because H -> g0 > 0, so the D/E inverse is certainly unstable)."""
    mixed = unstable = certified = 0
    for a, (g0, cd, c, th) in zip(LEVELS, levels):
        if a <= 0:
            continue
        H1 = g0 + cd + np.sum(c / (1.0 - th))
        Hm1 = g0 - cd - np.sum(c / (1.0 + th))
        mixed += bool(np.any(c > 0))
        unstable += bool(H1 <= 0)
        certified += bool(np.all(c <= 0) and H1 > 0 and (cd <= 0 or Hm1 > 0))
    return {"derivative_levels": int(np.sum(LEVELS > 0)), "mixed_sign": mixed, "dc_gain_nonpositive": unstable,
            "certified_stable": certified}


def cost(method, K=None, L=None):
    if method == "FIR":
        return {"mac": L, "state_A": L, "state_B": 2 * L, "rom": P * L}
    rom = P * (K + 2) + K if method.startswith("FP") else P * (2 * K + 2)
    return {"mac": 2 * K + 2, "state_A": K + 1, "state_B": K + 1, "rom": rom}


def main():
    rng = np.random.default_rng(8)
    seqs = sequences(rng)
    rows = []
    t0 = time.time()

    # sanity: the switched one-pole simulation with fixed poles equals the table operator (Prop. structure)
    d = design_dt(TS, N, -0.95, 0.95, 1e-4)
    bank = DiscreteFixedPoleBank(TS, d["xi_lo"], d["xi_hi"], d["K"])
    lv = [(*bank.coeffs(float(a)), bank.theta) for a in LEVELS]
    tab = np.array([kernel_from(*c, N) for c in lv])
    idx = seqs["random piecewise"]
    check = max(float(np.max(np.abs(ltv_matrix(lv, idx, T) - operator_matrix(tab, idx, T)))
                    / np.max(np.abs(operator_matrix(tab, idx, T)))) for T in "AB")
    print(f"structure check (simulated vs table operator): {check:.1e}", flush=True)

    for eps in EPS_LIST:
        d = design_dt(TS, N, -0.95, 0.95, eps)
        bank = DiscreteFixedPoleBank(TS, d["xi_lo"], d["xi_hi"], d["K"])
        lv = [(*bank.coeffs(float(a)), bank.theta) for a in LEVELS]
        tab = np.array([kernel_from(*c, N) for c in lv])
        rec = {"method": "FP-rule", "eps": eps, "K": d["K"], **cost("FP", K=d["K"]), "inverse": inverse_stats(lv),
               "eps_R": max(rel_err_all(t, g) for t, g in zip(tab, GL)), "const": const_error(tab),
               "vo": vo_error(seqs, lambda i, T: operator_matrix(tab, i, T))}
        rows.append(rec)
        print(f"FP-rule eps={eps:.0e} K={d['K']:2d} eps_R={rec['eps_R']:.1e} const={rec['const']:.1e} "
              f"vo A/B={rec['vo']['A']:.1e}/{rec['vo']['B']:.1e}", flush=True)

        K, lv = moving_pole_levels(TS, N, LEVELS, eps)
        tab = np.array([kernel_from(*c, N) for c in lv])
        rec = {"method": "MP-rule", "eps": eps, "K": K, **cost("MP", K=K),
               "eps_R": max(rel_err_all(t, g) for t, g in zip(tab, GL)), "const": const_error(tab),
               "vo": vo_error(seqs, lambda i, T: ltv_matrix(lv, i, T))}
        rows.append(rec)
        print(f"MP-rule eps={eps:.0e} K={K:2d} eps_R={rec['eps_R']:.1e} const={rec['const']:.1e} "
              f"vo A/B={rec['vo']['A']:.1e}/{rec['vo']['B']:.1e}", flush=True)

    for method, signed in (("FP-LP", False), ("FP-LPs", True)):
        for K in K_LP:
            worst, u_lo, u_hi = best_fitted(TS, N, K, PROBE, U_LO, U_HI, signed=signed)
            f = FittedFixedPole(TS, N, u_lo, u_hi, K, signed=signed)
            lv = [f.level(float(a)) for a in LEVELS]
            tab = np.array([kernel_from(*c, N) for c in lv])
            rec = {"method": method, "K": K, "u_lo": float(u_lo), "u_hi": float(u_hi), **cost("FP", K=K),
                   "inverse": inverse_stats(lv),
                   "eps_R": max(rel_err_all(t, g) for t, g in zip(tab, GL)), "const": const_error(tab),
                   "vo": vo_error(seqs, lambda i, T: operator_matrix(tab, i, T))}
            rows.append(rec)
            print(f"{method:7s} K={K:2d} u=[{u_lo:.1e},{u_hi:.0f}] eps_R={rec['eps_R']:.1e} const={rec['const']:.1e} "
                  f"vo A/B={rec['vo']['A']:.1e}/{rec['vo']['B']:.1e} | mixed-sign {rec['inverse']['mixed_sign']}, "
                  f"H(1)<=0 {rec['inverse']['dc_gain_nonpositive']}, certified {rec['inverse']['certified_stable']} "
                  f"of {rec['inverse']['derivative_levels']}", flush=True)

    lag = np.arange(N)
    for L in L_FIR:
        tab = np.where(lag[None, :] < L, GL, 0.0)
        rec = {"method": "FIR", "L": L, **cost("FIR", L=L), "const": const_error(tab),
               "vo": vo_error(seqs, lambda i, T: operator_matrix(tab, i, T))}
        rows.append(rec)
        print(f"FIR     L={L:4d} const={rec['const']:.1e} vo A/B={rec['vo']['A']:.1e}/{rec['vo']['B']:.1e}", flush=True)

    res = {"Ts": TS, "n": N, "levels": LEVELS.tolist(), "sequences": list(seqs), "structure_check": check,
           "rows": rows, "seconds": time.time() - t0}
    with open(os.path.join(OUT, "e8_baselines.json"), "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
