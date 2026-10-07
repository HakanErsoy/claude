"""E10: online tracking of a time-varying order from a known input.

Data: y = T^alpha x + v with the literal GL operators (T = A or B), Ts = 1
(sample units), n = 2000, a known AR(1) input (pole 0.98), white noise at
SNR 20, 40 and 60 dB, and an order that is constant, ramps, jumps from 0.7
to 0.2 and then oscillates. 50 Monte Carlo runs, each with a new input and
new noise (the same draws are used at every SNR).

Estimators, all on one rule-designed bank (eps = 1e-5, |alpha| <= 0.95, K = 40):
  A-grid   point-mass Bayes filter on 381 orders; the A-type bank state does
           not depend on the order, so all hypotheses share it: O(G K)/sample
  A-EKF    scalar iterated EKF with jump gating: O(K)/sample
  B-EKF    augmented EKF on (bank state, order): O((K+2)^2)/sample
  GL-EKF   the A-EKF on the literal GL weights: O(n)/sample (cost reference,
           first run only)
Each A-type estimator is also run on B-type data and vice versa.

Reported: RMSE of the order over 0.2 <= t < 4 (all runs; median and 90th
percentile) and over the 0.5 s after the jump, time per run, and traces
(estimates and absolute errors, median and percentile bands over runs) at
40 and 60 dB for the figure.

Outputs: results/e10_order_tracking.json
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
from vofrac.tracking import CoeffSpline, ekf_A, ekf_B, ekf_gl_A, grid_filter_A  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "results")
TS = 1.0
N = 2000
M = 50
SNRS = (20, 40, 60)
Q = 1e-5
EKF_A_OPTS = dict(gate=16.0, p_jump=5e-4)
t = np.arange(N) / N * 4.0
ALPHA = np.where(t < 1, 0.3, np.where(t < 2, 0.3 + 0.4 * (t - 1), np.where(
    t < 2.5, 0.7, 0.2 + 0.15 * np.sin(2 * np.pi * (t - 2.5) / 1.5))))
WIN_ALL = (t >= 0.2)
WIN_JUMP = (t >= 2.5) & (t < 3.0)


def rmse(a, m):
    return float(np.sqrt(np.mean((a - ALPHA)[m] ** 2)))


def main():
    d = design_dt(TS, N, -0.95, 0.95, 1e-5)
    bank = DiscreteFixedPoleBank(TS, d["xi_lo"], d["xi_hi"], d["K"], dc_floor=False)
    cs = CoeffSpline(bank)
    K = d["K"]
    G = 381
    rng = np.random.default_rng(10)
    est = {
        "A-grid": lambda x, y, r: grid_filter_A(bank, x, y, Q, r)[0],
        "A-EKF": lambda x, y, r: ekf_A(cs, x, y, Q, r, **EKF_A_OPTS)[0],
        "B-EKF": lambda x, y, r: ekf_B(cs, x, y, Q, r, **EKF_A_OPTS)[0],
    }
    res = {"design": d, "M": M, "snr_db": SNRS, "q": Q, "ekf_opts": EKF_A_OPTS,
           "macs_per_sample": {"A-EKF": 3 * (K + 2), "A-grid": G * (K + 2), "B-EKF": 4 * (K + 2) ** 2,
                               "GL-EKF (mean)": 3 * N // 2},
           "rmse": {}, "rmse_jump": {}, "seconds_per_run": {}, "traces": {}}
    rec = {(snr, T, e): [] for snr in SNRS for T in "AB" for e in est}
    rec_j = {k: [] for k in rec}
    secs = {e: [] for e in est}
    traces = {(snr, T, e): [] for snr in (40, 60) for T in "AB" for e in est}
    for run in range(M):
        e_in = rng.standard_normal(N)
        x = np.zeros(N)
        for k in range(1, N):
            x[k] = 0.98 * x[k - 1] + e_in[k]
        data = {"A": gl_A(x, ALPHA, TS), "B": gl_B(x, ALPHA, TS)}
        noise = {T: rng.standard_normal(N) for T in "AB"}
        for snr in SNRS:
            for T, y in data.items():
                sig = np.std(y) * 10 ** (-snr / 20)
                yn = y + sig * noise[T]
                for name, f in est.items():
                    t0 = time.time()
                    a = f(x, yn, sig ** 2)
                    secs[name].append(time.time() - t0)
                    rec[(snr, T, name)].append(rmse(a, WIN_ALL))
                    rec_j[(snr, T, name)].append(rmse(a, WIN_JUMP))
                    if snr in (40, 60):
                        traces[(snr, T, name)].append(a)
                if run == 0 and T == "A":
                    t0 = time.time()
                    ag = ekf_gl_A(x, yn, TS, Q, sig ** 2, **EKF_A_OPTS)[0]
                    res.setdefault("gl_ekf", {})[str(snr)] = {
                        "seconds": time.time() - t0,
                        "max_diff_to_bank_ekf": float(np.max(np.abs(ag - est["A-EKF"](x, yn, sig ** 2))))}
        if run % 10 == 9:
            print(f"run {run + 1}/{M}", flush=True)
    for (snr, T, name), v in rec.items():
        key = f"{snr}dB/{T}-data/{name}"
        res["rmse"][key] = {"median": float(np.median(v)), "p90": float(np.percentile(v, 90)),
                            "max": float(np.max(v))}
        res["rmse_jump"][key] = {"median": float(np.median(rec_j[(snr, T, name)])),
                                 "p90": float(np.percentile(rec_j[(snr, T, name)], 90))}
    for name, v in secs.items():
        res["seconds_per_run"][name] = float(np.mean(v))
    sub = slice(None, None, 4)
    res["traces"] = {"t": t[sub].tolist(), "alpha": ALPHA[sub].tolist()}
    for (snr, T, name), arr in traces.items():
        arr = np.array(arr)[:, sub]
        err = np.abs(arr - ALPHA[sub][None, :])
        res["traces"][f"{snr}dB/{T}/{name}"] = {
            **{q: np.percentile(arr, p, axis=0).tolist() for q, p in (("p10", 10), ("p50", 50), ("p90", 90))},
            **{"abs_err_" + q: np.percentile(err, p, axis=0).tolist() for q, p in (("p50", 50), ("p90", 90))}}
    for snr in SNRS:
        line = " | ".join(
            f"{T}-data: " + " ".join(f"{name} {res['rmse'][f'{snr}dB/{T}-data/{name}']['median']:.4f}"
                                     f"[{res['rmse'][f'{snr}dB/{T}-data/{name}']['p90']:.3f}]" for name in est)
            for T in "AB")
        print(f"{snr} dB: {line}", flush=True)
    print("seconds per run:", {k: round(v, 3) for k, v in res["seconds_per_run"].items()},
          "GL-EKF:", {k: (round(v["seconds"], 2), f"{v['max_diff_to_bank_ekf']:.1e}") for k, v in res["gl_ekf"].items()})
    with open(os.path.join(OUT, "e10_order_tracking.json"), "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
