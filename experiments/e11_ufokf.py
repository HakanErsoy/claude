"""E11: order tracking against unscented filters on the direct GL sum (UFOKF-type).

Same data as E10 (same seed and draw order: input, then the A- and B-type
noise per run; the same draws are used at every SNR), so the numbers can be
read next to the E10 table.

Unscented baselines, in the spirit of the unscented fractional-order Kalman
filter of Sierociuk et al. (our implementation for the direct-operator
problem): the order is a filter state, the output is evaluated by the GL
sum itself, and the unscented transform replaces linearization.

  UKF-GL-A(L)   scalar UKF, A-type GL sum over the last L samples
                (L = 100, 500 and n); about 6 L multiplications per sample
  UKF-bank-A    the same UKF on the output-scheduled bank; about 6 (K+2)
  UKF-GL-B(W)   B-type: the current order is not seen in y_n (Ts = 1), so the
                state holds the last W orders (fixed lag, W = 5 and 20); older
                orders are frozen at their estimates and their contributions
                to later outputs are accumulated (literal B-type sum, O(n));
                about (2W+1) W^2 + n multiplications per sample

Each A-type filter runs on A-type data and the B-type filters on B-type data.
Reported: RMSE of the order over 0.2 <= t < 4 (median and 90th percentile
over the runs), and the largest difference between UKF-GL-A(n) and
UKF-bank-A.

Outputs: results/e11_ufokf.json
"""

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.design import design_dt  # noqa: E402
from vofrac.reference import gl_A, gl_B  # noqa: E402
from vofrac.tracking import CoeffSpline, ukf_bank_A, ukf_gl_A, ukf_gl_B  # noqa: E402

sys.path.insert(0, os.path.dirname(__file__))
from e10_order_tracking import ALPHA, EKF_A_OPTS, M, N, Q, SNRS, TS, WIN_ALL, rmse  # noqa: E402


def main():
    d = design_dt(TS, N, -0.95, 0.95, 1e-5)
    bank = DiscreteFixedPoleBank(TS, d["xi_lo"], d["xi_hi"], d["K"], dc_floor=False)
    cs = CoeffSpline(bank)
    K = d["K"]
    rng = np.random.default_rng(10)                 # E10's seed and draw order
    est_A = {f"UKF-GL-A(L={L})": (lambda L: lambda x, y, r: ukf_gl_A(x, y, TS, L, Q, r, **EKF_A_OPTS)[0])(L)
             for L in (100, 500, N)}
    est_A["UKF-bank-A"] = lambda x, y, r: ukf_bank_A(cs, x, y, Q, r, **EKF_A_OPTS)[0]
    est_B = {f"UKF-GL-B(W={W})": (lambda W: lambda x, y, r: ukf_gl_B(x, y, TS, W, Q, r, **EKF_A_OPTS)[0])(W)
             for W in (5, 20)}
    rec = {(snr, name): [] for snr in SNRS for name in list(est_A) + list(est_B)}
    secs = {name: [] for name in list(est_A) + list(est_B)}
    max_diff = 0.0
    for run in range(M):
        e_in = rng.standard_normal(N)
        x = np.zeros(N)
        for k in range(1, N):
            x[k] = 0.98 * x[k - 1] + e_in[k]
        data = {"A": gl_A(x, ALPHA, TS), "B": gl_B(x, ALPHA, TS)}
        noise = {T: rng.standard_normal(N) for T in "AB"}
        for snr in SNRS:
            for T, ests in (("A", est_A), ("B", est_B)):
                y = data[T]
                sig = np.std(y) * 10 ** (-snr / 20)
                yn = y + sig * noise[T]
                out = {}
                for name, f in ests.items():
                    t0 = time.time()
                    out[name] = f(x, yn, sig ** 2)
                    secs[name].append(time.time() - t0)
                    rec[(snr, name)].append(rmse(out[name], WIN_ALL))
                if T == "A":
                    max_diff = max(max_diff, float(np.max(np.abs(out[f"UKF-GL-A(L={N})"] - out["UKF-bank-A"]))))
        if run % 10 == 9:
            print(f"run {run + 1}/{M}", flush=True)
    res = {"design": d, "M": M, "snr_db": SNRS, "q": Q, "opts": EKF_A_OPTS,
           "macs_per_sample": {**{f"UKF-GL-A(L={L})": 6 * L for L in (100, 500)},
                               f"UKF-GL-A(L={N})": 3 * N, "UKF-bank-A": 6 * (K + 2),
                               **{f"UKF-GL-B(W={W})": (2 * W + 1) * W * W + N for W in (5, 20)}},
           "max_diff_full_GL_vs_bank": max_diff,
           "rmse": {f"{snr}dB/{name}": {"median": float(np.median(v)), "p90": float(np.percentile(v, 90)),
                                        "max": float(np.max(v))} for (snr, name), v in rec.items()},
           "seconds_per_run": {k: float(np.mean(v)) for k, v in secs.items()}}
    for snr in SNRS:
        print(f"{snr} dB: " + " | ".join(f"{name} {res['rmse'][f'{snr}dB/{name}']['median']:.4f}"
                                         f"[{res['rmse'][f'{snr}dB/{name}']['p90']:.3f}]"
                                         for name in list(est_A) + list(est_B)), flush=True)
    print(f"max |UKF-GL-A(n) - UKF-bank-A| = {max_diff:.1e}", flush=True)
    with open(os.path.join(os.path.dirname(__file__), "..", "results", "e11_ufokf.json"), "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
