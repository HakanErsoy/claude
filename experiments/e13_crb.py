"""E13: Bayesian Cramer-Rao bounds for order tracking, and the estimators against them.

The bound is a Bayesian (Van Trees) bound: it holds for the mean-square error
averaged over the prior of the order path. The order paths are therefore
drawn from the random-walk prior that the filters assume,

    alpha_0 ~ N(0.3, 0.01),  alpha_{n+1} = alpha_n + w_n,  w_n ~ N(0, 1e-5),

(paths leaving |alpha| <= 0.9 are redrawn), with n = 2000, Ts = 1, the AR(1)
input of E10 (pole 0.98) and literal GL data of both types, at SNR 20, 40 and
60 dB (noise variance fixed per SNR and type from the pooled output variance).
50 Monte Carlo runs, each with a new path, input and noise.

Estimators (bank of E10, eps = 1e-5, K = 40), tuned to this model (no jump
gating, no switch probability): A-type grid filter (381 orders) and iterated
EKF on A-type data, B-type augmented EKF on B-type data, all with q = 1e-5
(the EKFs with the prior N(0.3, 0.01); the grid filter starts uniform).

Bounds (vofrac.crb): the input is known to the estimators, so the bound is
conditioned on it. For each run, the information E[G^T G | x]/s2 is averaged
over P = 10 paths drawn from the prior for that run's input; the filtering
bound (data up to n) and the smoothing bound (all data) follow from a Kalman
recursion on the growing path, and the bounds are then averaged over the 50
inputs (a bound on the MSE averaged over paths, inputs and noise). For
comparison, the looser bound with the information also averaged over the
inputs (Jensen) is reported. Reported per SNR and type: RMSE over runs and
over 0.2 <= t < 4 (n >= 100), the RMS of the bounds over the same window,
their ratio, and traces over time.

Outputs: results/e13_crb.json
"""

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from e10_order_tracking import N, TS  # noqa: E402
from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.crb import bcrb_batch, gl_derivative_table, interp_rows, jacobian  # noqa: E402
from vofrac.design import design_dt  # noqa: E402
from vofrac.reference import gl_A, gl_B  # noqa: E402
from vofrac.tracking import CoeffSpline, ekf_A, ekf_B, grid_filter_A  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "results")
M = 50
P_PATHS = 10
Q = 1e-5
A0, P0 = 0.3, 0.01
SNRS = (20, 40, 60)
NO_GATE = dict(gate=np.inf, p_jump=0.0)
t = np.arange(N) / N * 4.0
WIN = t >= 0.2
_W = {}


def draw_paths(rng, m=M):
    paths = []
    while len(paths) < m:
        a = A0 + np.sqrt(P0) * rng.standard_normal() + np.r_[0.0, np.cumsum(np.sqrt(Q) * rng.standard_normal(N - 1))]
        if np.all(np.abs(a) <= 0.9):
            paths.append(a)
    return np.array(paths)


def _init():
    d = design_dt(TS, N, -0.95, 0.95, 1e-5)
    _W["bank"] = DiscreteFixedPoleBank(TS, d["xi_lo"], d["xi_hi"], d["K"], dc_floor=False)
    _W["cs"] = CoeffSpline(_W["bank"])


def _estimate(args):
    x, a, data, noise, sig = args
    out = {}
    for snr in SNRS:
        for T in "AB":
            s = sig[(snr, T)]
            yn = data[T] + s * noise[T]
            if T == "A":
                out[(snr, "A-grid")] = grid_filter_A(_W["bank"], x, yn, Q, s ** 2, p_switch=0.0)[0] - a
                out[(snr, "A-EKF")] = ekf_A(_W["cs"], x, yn, Q, s ** 2, a0=A0, p0=P0, **NO_GATE)[0] - a
            else:
                out[(snr, "B-EKF")] = ekf_B(_W["cs"], x, yn, Q, s ** 2, a0=A0, p0=P0, **NO_GATE)[0] - a
    return out


def _bounds(args):
    """Bounds conditional on one input x: information averaged over prior paths."""
    x, seed, sig = args
    rng = np.random.default_rng(seed)
    paths = draw_paths(rng, P_PATHS)
    hA = np.array([np.diag(jacobian(x, a, "A")) for a in paths])
    hA_rms = np.sqrt(np.mean(hA ** 2, axis=0))
    grid = np.round(np.arange(-0.95, 0.9501, 0.001), 6)
    table = _W.setdefault("table", gl_derivative_table(grid, N))

    def rowB(k):
        H = np.zeros((P_PATHS, k + 1))
        if k:
            j = np.arange(k)
            H[:, :k] = interp_rows(table, grid, paths[:, :k], (k - j)[None, :].repeat(P_PATHS, 0)) * x[None, :k]
        return H

    out = {}
    for snr in SNRS:
        out[(snr, "A")] = bcrb_batch(lambda k: np.pad(hA_rms[k:k + 1][None, :], ((0, 0), (k, 0))), N,
                                     sig[(snr, "A")] ** 2, Q, P0)
        out[(snr, "B")] = bcrb_batch(rowB, N, sig[(snr, "B")] ** 2, Q, P0)
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(13)
    paths = draw_paths(rng)
    xs = []
    for _ in range(M):
        e = rng.standard_normal(N)
        x = np.zeros(N)
        for k in range(1, N):
            x[k] = 0.98 * x[k - 1] + e[k]
        xs.append(x)
    xs = np.array(xs)
    data = [{"A": gl_A(x, a, TS), "B": gl_B(x, a, TS)} for x, a in zip(xs, paths)]
    noise = [{T: rng.standard_normal(N) for T in "AB"} for _ in range(M)]
    pooled = {T: np.sqrt(np.mean([np.var(d[T]) for d in data])) for T in "AB"}
    sig = {(snr, T): pooled[T] * 10 ** (-snr / 20) for snr in SNRS for T in "AB"}
    with ProcessPoolExecutor(max_workers=min(4, os.cpu_count() or 1), initializer=_init) as ex:
        errs = list(ex.map(_estimate, [(x, a, d, nz, sig) for x, a, d, nz in zip(xs, paths, data, noise)]))
        print(f"estimators done ({time.time() - t0:.0f} s)", flush=True)
        cond = list(ex.map(_bounds, [(x, 1000 + m, sig) for m, x in enumerate(xs)]))
    print(f"conditional bounds done ({time.time() - t0:.0f} s)", flush=True)
    # A-type sensitivities h_n = dy_n/dalpha_n, averaged information E[h_n^2]
    hA = np.array([np.diag(jacobian(x, a, "A")) for x, a in zip(xs, paths)])
    hA_rms = np.sqrt(np.mean(hA ** 2, axis=0))
    # B-type Jacobian rows from an interpolated derivative table
    grid = np.round(np.arange(-0.95, 0.9501, 0.001), 6)
    table = gl_derivative_table(grid, N)

    def rowB(k):
        H = np.zeros((M, k + 1))
        if k:
            j = np.arange(k)
            H[:, :k] = interp_rows(table, grid, paths[:, :k], (k - j)[None, :].repeat(M, 0)) * xs[:, :k]
        return H

    res = {"M": M, "paths_per_input": P_PATHS, "q": Q, "a0": A0, "p0": P0, "sigma": {f"{snr}dB/{T}": float(v) for (snr, T), v in sig.items()},
           "window": [float(t[WIN][0]), float(t[-1])], "table": {}, "traces": {"t": t[::4].tolist()}}
    for snr in SNRS:
        for T, names in (("A", ("A-grid", "A-EKF")), ("B", ("B-EKF",))):
            s2 = sig[(snr, T)] ** 2
            t1 = time.time()
            if T == "A":
                fu, su = bcrb_batch(lambda k: np.pad(hA_rms[k:k + 1][None, :], ((0, 0), (k, 0))), N, s2, Q, P0)
            else:
                fu, su = bcrb_batch(rowB, N, s2, Q, P0)
            filt = np.mean([c[(snr, T)][0] for c in cond], axis=0)
            smooth = np.mean([c[(snr, T)][1] for c in cond], axis=0)
            entry = {"bound_filt_rms": float(np.sqrt(filt[WIN].mean())),
                     "bound_smooth_rms": float(np.sqrt(smooth[WIN].mean())),
                     "bound_filt_rms_input_averaged_info": float(np.sqrt(fu[WIN].mean())),
                     "bound_smooth_rms_input_averaged_info": float(np.sqrt(su[WIN].mean())),
                     "seconds": time.time() - t1}
            tr = {"filt_rms": np.sqrt(filt)[::4].tolist(), "smooth_rms": np.sqrt(smooth)[::4].tolist()}
            for name in names:
                e = np.array([err[(snr, name)] for err in errs])
                mse_t = np.mean(e ** 2, axis=0)
                per_run = np.sqrt(np.mean(e[:, WIN] ** 2, axis=1))
                entry[name] = {"rmse": float(np.sqrt(mse_t[WIN].mean())),
                               "ratio_to_filt_bound": float(np.sqrt(mse_t[WIN].mean() / filt[WIN].mean())),
                               "ratio_to_smooth_bound": float(np.sqrt(mse_t[WIN].mean() / smooth[WIN].mean())),
                               "rmse_run_median": float(np.median(per_run)), "rmse_run_p90": float(np.percentile(per_run, 90))}
                tr[name] = np.sqrt(mse_t)[::4].tolist()
            res["table"][f"{snr}dB/{T}"] = entry
            res["traces"][f"{snr}dB/{T}"] = tr
            print(f"{snr} dB {T}: bound filt {entry['bound_filt_rms']:.2e} smooth {entry['bound_smooth_rms']:.2e} "
                  f"(input-averaged info: {entry['bound_filt_rms_input_averaged_info']:.2e}) | "
                  + " ".join(f"{n} {entry[n]['rmse']:.2e} (x{entry[n]['ratio_to_filt_bound']:.2f} filt, "
                             f"x{entry[n]['ratio_to_smooth_bound']:.2f} smooth)" for n in names)
                  + f" [{entry['seconds']:.0f} s]", flush=True)
    res["seconds"] = time.time() - t0
    with open(os.path.join(OUT, "e13_crb.json"), "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
