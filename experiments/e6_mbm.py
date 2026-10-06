"""E6: real-time multifractional Brownian motion with the fixed-pole bank.

RL-mBm (Lim 2001) is the A-type VO integral of white noise of order
H(t) + 1/2; the B-type integral is the "order at input time" variant
(cf. Surgailis 2008). One bank of order 1/2 - H (|order| < 1/2) covers
0 < H < 1 via exact integer splitting (A: integrate first, B: last).

Part 1  composition identities (exact) and the wrong orders (not exact)
Part 2  pathwise agreement with the O(n^2) GL generator (same noise)
Part 3  exact second-order statistics: the generator's realized n x n
        weight matrix vs the exact discrete covariance (no Monte Carlo)
Part 4  local Hurst tracking (Monte Carlo): constant H (estimator bias),
        ramp, sine, step; A vs B
Part 5  A vs B at a Hurst jump: exact variance functions and path jumps
Part 6  cost: streaming O(K) per sample vs O(n) per sample (GL direct)
Part 7  bit-accurate generation with the E5 fixed-point core (A/B envelope)

Outputs: results/e6_mbm.json, results/fig_e6_*.png
"""

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.design import design_dt  # noqa: E402
from vofrac.fixedpoint import FixedPointBank  # noqa: E402
from vofrac.mbm import exact_variance, generate, local_hurst  # noqa: E402
from vofrac.reference import gl_A, gl_B, gl_matrix  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "results")
EPS = 1e-4
HMIN, HMAX = 0.05, 0.95


def make_bank(n):
    d = design_dt(1.0, n, -(0.5 - HMIN), 0.5 - HMIN, EPS)
    return d, DiscreteFixedPoleBank(1.0, d["xi_lo"], d["xi_hi"], d["K"])


def profiles(n):
    t = np.arange(n)
    return {"ramp 0.2->0.8": 0.2 + 0.6 * t / n,
            "sine 0.5+-0.3": 0.5 + 0.3 * np.sin(2 * np.pi * t / n),
            "step 0.3->0.8": np.where(t < n // 2, 0.3, 0.8)}


def rel(y, r):
    return float(np.sqrt(np.mean((y - r) ** 2) / np.mean(r ** 2)))


def part1(rng):
    n = 1500
    xi = rng.standard_normal(n)
    S = np.cumsum(xi)
    out = {}
    for name, H in profiles(n).items():
        a = H + 0.5
        XA, XB = gl_A(xi, -a, 1.0), gl_B(xi, -a, 1.0)
        mx = lambda u, v: float(np.max(np.abs(u - v)) / np.max(np.abs(v)))
        out[name] = {"A_integrate_first": mx(gl_A(S, -(a - 1), 1.0), XA),
                     "A_integrate_last": mx(np.cumsum(gl_A(xi, -(a - 1), 1.0)), XA),
                     "B_integrate_last": mx(np.cumsum(gl_B(xi, -(a - 1), 1.0)), XB),
                     "B_integrate_first": mx(gl_B(S, -(a - 1), 1.0), XB)}
        print("P1", name, {k: f"{v:.1e}" for k, v in out[name].items()}, flush=True)
    return out


def part2(rng):
    n = 4096
    d, bank = make_bank(n)
    out = {"K": d["K"]}
    xi = rng.standard_normal((3, n))
    for name, H in profiles(n).items():
        rec = {}
        for T, f in (("A", gl_A), ("B", gl_B)):
            X = generate(bank, xi, H, T)
            rec[T] = max(rel(X[i], f(xi[i], -(H + 0.5), 1.0)) for i in range(3))
        out[name] = rec
        print(f"P2 {name}: pathwise vs GL  A {rec['A']:.1e}  B {rec['B']:.1e}", flush=True)
    return out


def part3():
    n = 2048
    d, bank = make_bank(n)
    out = {"n": n, "K": d["K"]}
    I = np.eye(n)
    for name, H in profiles(n).items():
        rec = {}
        for T in "AB":
            G = generate(bank, I, H, T).T           # column m = response to an impulse at m
            W = gl_matrix(-(H + 0.5), 1.0, T)       # exact discrete operator
            V_exact = exact_variance(H, T)
            V_bank = np.sum(G ** 2, axis=1)
            C_err = np.linalg.norm(G @ G.T - W @ W.T) / np.linalg.norm(W @ W.T)
            rec[T] = {"var_max_rel_err": float(np.max(np.abs(V_bank / V_exact - 1.0))),
                      "cov_rel_frob_err": float(C_err),
                      "var_check_W": float(np.max(np.abs(np.sum(W ** 2, axis=1) / V_exact - 1.0)))}
        out[name] = rec
        print(f"P3 {name}: " + " | ".join(f"{T}: var {rec[T]['var_max_rel_err']:.1e} cov {rec[T]['cov_rel_frob_err']:.1e}"
                                          for T in "AB"), flush=True)
    return out


def part4(rng):
    n, M, win, dil = 16384, 400, 1024, (4, 8)
    d, bank = make_bank(n)
    out = {"n": n, "M": M, "window": win, "dilations": dil, "K": d["K"], "const": {}, "varying": {}}

    def est(X):
        j1, j2 = dil
        c, h1 = local_hurst_dil(X, win, j1, j2)
        return c, h1

    for H0 in (0.2, 0.5, 0.8):
        H = np.full(n, H0)
        c, Hh = est(generate(bank, rng.standard_normal((M, n)), H, "A"))
        late = c > n // 4
        out["const"][str(H0)] = {"bias": float(Hh[:, late].mean() - H0), "std": float(Hh[:, late].std())}
        print(f"P4 const H={H0}: bias {out['const'][str(H0)]['bias']:+.3f} std {out['const'][str(H0)]['std']:.3f}", flush=True)
    traces = {}
    for name, H in profiles(n).items():
        rec = {}
        for T in "AB":
            c, Hh = est(generate(bank, rng.standard_normal((M, n)), H, T))
            Hc = np.array([H[max(0, ci - win // 2):ci + win // 2].mean() for ci in c])   # window-averaged truth
            late = c > n // 4
            if name.startswith("step"):
                late &= np.abs(c - n // 2) > win                                       # exclude the jump region
            rec[T] = {"rmse_mean": float(np.sqrt(np.mean((Hh[:, late].mean(axis=0) - Hc[late]) ** 2))),
                      "std": float(Hh[:, late].std(axis=0).mean())}
            traces[f"{name}|{T}"] = {"c": c.tolist(), "mean": Hh.mean(axis=0).tolist(),
                                     "std": Hh.std(axis=0).tolist(), "truth": Hc.tolist()}
        out["varying"][name] = rec
        print(f"P4 {name}: " + " | ".join(f"{T}: RMSE(mean) {rec[T]['rmse_mean']:.3f} std {rec[T]['std']:.3f}" for T in "AB"),
              flush=True)
    return out, traces


def local_hurst_dil(X, window, j1, j2, step=None):
    """Quadratic-variation estimator at dilations j1 < j2 = 2 j1 (second-order increments)."""
    X = np.atleast_2d(X)
    step = step or window // 4
    d1 = X[:, 2 * j1:] - 2 * X[:, j1:-j1] + X[:, :-2 * j1]
    d2 = X[:, 2 * j2:] - 2 * X[:, j2:-j2] + X[:, :-2 * j2]
    m = d2.shape[1]
    starts = np.arange(0, m - window + 1, step)
    c1 = np.concatenate([np.zeros((X.shape[0], 1)), np.cumsum(d1[:, :m] ** 2, axis=1)], axis=1)
    c2 = np.concatenate([np.zeros((X.shape[0], 1)), np.cumsum(d2 ** 2, axis=1)], axis=1)
    V1 = (c1[:, starts + window] - c1[:, starts]) / window
    V2 = (c2[:, starts + window] - c2[:, starts]) / window
    return starts + window // 2 + j2, np.log2(V2 / V1) / (2.0 * np.log2(j2 / j1))


def part5(rng):
    n = 4096
    d, bank = make_bank(n)
    H = np.where(np.arange(n) < n // 2, 0.3, 0.8)
    VA, VB = exact_variance(H, "A"), exact_variance(H, "B")
    xi = rng.standard_normal((200, n))
    XA, XB = generate(bank, xi, H, "A"), generate(bank, xi, H, "B")
    k = n // 2
    jump = lambda X: float(np.mean((X[:, k] - X[:, k - 1]) ** 2) / np.mean((X[:, k - 1] - X[:, k - 2]) ** 2))
    out = {"var_A_before_after": [float(VA[k - 1]), float(VA[k])], "var_B_before_after": [float(VB[k - 1]), float(VB[k])],
           "increment_ratio_at_jump_A": jump(XA), "increment_ratio_at_jump_B": jump(XB)}
    print(f"P5 step: Var A {VA[k-1]:.1f} -> {VA[k]:.1f} | Var B {VB[k-1]:.1f} -> {VB[k]:.1f} | "
          f"increment^2 at jump / before: A {out['increment_ratio_at_jump_A']:.1f}, B {out['increment_ratio_at_jump_B']:.1f}",
          flush=True)
    trace = {"VA": VA.tolist(), "VB": VB.tolist(), "pathA": XA[0].tolist(), "pathB": XB[0].tolist()}
    return out, trace


def part6(rng):
    rows = []
    for n in (1024, 4096, 16384):
        d, bank = make_bank(n)
        H = profiles(n)["sine 0.5+-0.3"]
        xi = rng.standard_normal((64, n))
        t0 = time.time()
        generate(bank, xi, H, "A")
        t_batch = (time.time() - t0) / 64
        t0 = time.time()
        generate(bank, xi[:1], H, "A")
        t_single = time.time() - t0
        t0 = time.time()
        gl_A(np.cumsum(xi[0]), -(H - 0.5), 1.0)
        t_gl = time.time() - t0
        rows.append({"n": n, "K": d["K"], "macs_per_sample_bank": 2 * d["K"] + 3, "macs_per_sample_gl_avg": n / 2,
                     "t_bank_per_path_batched_s": t_batch, "t_bank_single_path_s": t_single, "t_gl_direct_s": t_gl})
        print(f"P6 n={n}: K={d['K']} bank {2*d['K']+3} MAC/sample vs GL {n/2:.0f} avg | time per path: bank batched "
              f"{t_batch*1e3:.1f} ms, bank single {t_single*1e3:.0f} ms, GL direct {t_gl*1e3:.0f} ms", flush=True)
    return rows


def part7(rng):
    """Bit-accurate generation with the E5 fixed-point cores (R = 4000, |order| <= 0.95).

    A integrates first: an exact integer accumulator feeds the core, so the
    random walk must stay inside |x| <= 1 over the horizon (input 2^-9 N(0,1)).
    B integrates last: the core sees the white noise itself (0.25 N(0,1)) and
    the accumulator after it, which needs its own headroom, sums the core's
    low-frequency rounding errors; B therefore needs the wider core.
    """
    with open(os.path.join(OUT, "e5_fixed_point.json")) as f:
        e5 = json.load(f)
    d5 = e5["design"]
    bank5 = DiscreteFixedPoleBank(1.0, d5["xi_lo"], d5["xi_hi"], d5["K"])
    n, M = 4000, 20
    scale = {"A": 2.0 ** -9, "B": 0.25}
    H = 0.2 + 0.6 * np.arange(n) / n
    out = {"n": n, "M": M, "input_scale": scale, "cores": {}}
    for env in ("AB", "ABDE"):
        ch = e5["envelopes"][env]["choice"]
        fp = FixedPointBank(bank5, P=e5["P"], amax=0.95, WS=ch["WS"], WM=ch["WM"], n_max=4000,
                            V_max=e5["envelopes"][env]["V_max"])
        idx = fp.index(0.5 - H)
        Hq = 0.5 - fp.grid[idx]
        errs = {"A": [], "B": []}
        for _ in range(M):
            for T in "AB":
                xi_int = fp.to_int(scale[T] * rng.standard_normal(n))
                xi_q = fp.to_float(xi_int)
                if T == "A":
                    X = fp.to_float(fp.run([int(v) for v in np.cumsum(xi_int)], idx, "A"))
                else:
                    X = np.cumsum(fp.to_float(fp.run(xi_int, idx, "B")))
                errs[T].append(rel(X, generate(bank5, xi_q[None, :], Hq, T)[0]))
        rec = {"config": [ch["WS"], ch["WST"], ch["WM"]],
               "max_rel_err_vs_float": {T: float(np.max(v)) for T, v in errs.items()},
               "median_rel_err_vs_float": {T: float(np.median(v)) for T, v in errs.items()}}
        out["cores"][env] = rec
        print(f"P7 core {env} {ch['WS']}/{ch['WST']}/{ch['WM']}: mBm paths vs float bank, max rel err "
              f"A {rec['max_rel_err_vs_float']['A']:.1e}  B {rec['max_rel_err_vs_float']['B']:.1e}", flush=True)
    return out


def figures(traces4, trace5, n4):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 3.7), sharey=True)
    colors = {"A": "#1f77b4", "B": "#d62728"}
    for ax, name in zip(axes, ["ramp 0.2->0.8", "sine 0.5+-0.3", "step 0.3->0.8"]):
        for T in "AB":
            tr = traces4[f"{name}|{T}"]
            c, m, s = np.array(tr["c"]), np.array(tr["mean"]), np.array(tr["std"])
            ax.plot(c, m, color=colors[T], lw=1.2, label=f"{T}-type mean")
            ax.fill_between(c, m - s, m + s, color=colors[T], alpha=0.15)
        ax.plot(c, tr["truth"], "k--", lw=1, label="H(t) (window avg.)")
        ax.set_title(name)
        ax.set_xlabel("sample")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("local Hurst estimate")
    axes[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_e6_hurst.png"), dpi=150)

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
    k = np.arange(len(trace5["VA"]))
    axes[0].semilogy(k, trace5["VA"], color=colors["A"], label="A-type (RL-mBm)")
    axes[0].semilogy(k, trace5["VB"], color=colors["B"], label="B-type")
    axes[0].set_title("exact variance, H: 0.3 -> 0.8 at n/2")
    axes[0].set_xlabel("sample")
    axes[0].legend(fontsize=8)
    axes[0].grid(True, which="both", alpha=0.3)
    axes[1].plot(k, trace5["pathA"], color=colors["A"], lw=0.8, label="A-type path")
    axes[1].plot(k, trace5["pathB"], color=colors["B"], lw=0.8, label="B-type path (same noise)")
    axes[1].axvline(len(k) // 2, color="k", lw=0.6, ls=":")
    axes[1].set_title("sample paths: A jumps at the Hurst jump, B stays continuous")
    axes[1].set_xlabel("sample")
    axes[1].legend(fontsize=8)
    axes[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_e6_step.png"), dpi=150)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(66)
    res = {"part1": part1(rng), "part2": part2(rng), "part3": part3()}
    res["part4"], tr4 = part4(rng)
    res["part5"], tr5 = part5(rng)
    res["part6"] = part6(rng)
    res["part7"] = part7(rng)
    with open(os.path.join(OUT, "e6_mbm.json"), "w") as f:
        json.dump(res, f, indent=1)
    figures(tr4, tr5, res["part4"]["n"])
