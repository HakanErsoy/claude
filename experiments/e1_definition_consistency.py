"""E1: which variable-order definition does each switched realization track?

Unit-step input, Ts = 1 ms, horizon 4 s. Two order profiles:
  (a) a single switch alpha1 -> alpha2 at T = 2 s (closed-form A/B references)
  (b) a smooth order alpha(t) (A closed form, B by adaptive quadrature)

Realizations, compared at equal state count S:
  FP-out  fixed-pole bank, order scheduled in the output map
  FP-in   fixed-pole bank, order scheduled in the input map
  Ou-par  Oustaloup, modal form, state kept on coefficient swap
  Ou-cas  Oustaloup, first-order cascade, state kept on coefficient swap

Metric: relative RMS error against each reference over a window.
Outputs: results/e1_switched.json, results/e1_smooth.json, results/fig_e1_*.png
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.bank import FixedPoleBank  # noqa: E402
from vofrac.oustaloup import SwitchedOustaloup  # noqa: E402
from vofrac.reference import step_A, step_B_piecewise, step_B_smooth  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "results")
TS, TEND, TSW = 1e-3, 4.0, 2.0
W_LO, W_HI = 1e-3, 1e5          # common design band for all realizations
NS = [3, 5, 7, 10, 12, 15, 20]  # Oustaloup N; state count S = 2N + 1
SWITCH_CASES = [(-0.3, -0.7), (-0.7, -0.3), (0.3, 0.7), (0.7, 0.3), (-0.5, 0.5), (0.5, -0.5)]
SMOOTH_CASES = {
    "integral":   (lambda t: -0.5 + 0.3 * np.sin(np.pi * t / 2), lambda t: 0.3 * np.pi / 2 * np.cos(np.pi * t / 2)),
    "derivative": (lambda t: 0.5 + 0.3 * np.sin(np.pi * t / 2), lambda t: 0.3 * np.pi / 2 * np.cos(np.pi * t / 2)),
    "crossing":   (lambda t: 0.6 * np.sin(np.pi * t / 2), lambda t: 0.6 * np.pi / 2 * np.cos(np.pi * t / 2)),
}
REALIZATIONS = ["FP-out", "FP-in", "Ou-par", "Ou-cas"]


def rel_rms(y, r):
    return float(np.sqrt(np.mean((y - r) ** 2)) / np.sqrt(np.mean(r ** 2)))


def run(name, N, u, alpha):
    S = 2 * N + 1
    if name == "FP-out":
        return FixedPoleBank(W_LO, W_HI, S).simulate(u, alpha, TS, "output")
    if name == "FP-in":
        return FixedPoleBank(W_LO, W_HI, S).simulate(u, alpha, TS, "input")
    if name == "Ou-par":
        return SwitchedOustaloup(W_LO, W_HI, N, "parallel").simulate(u, alpha, TS)
    if name == "Ou-cas":
        return SwitchedOustaloup(W_LO, W_HI, N, "cascade").simulate(u, alpha, TS)
    raise ValueError(name)


def switched():
    n = int(round(TEND / TS)) + 1
    t = np.arange(n) * TS
    u = np.ones(n)
    pre = (t > 0.05) & (t < TSW)
    post = t > TSW + 0.05
    out = {"Ts": TS, "Tend": TEND, "Tsw": TSW, "band": [W_LO, W_HI], "cases": []}
    traces = {}
    for a1, a2 in SWITCH_CASES:
        alpha = np.where(t < TSW - 1e-12, a1, a2)
        rA = step_A(t, alpha)
        rB = step_B_piecewise(t, [TSW], [a1, a2])
        case = {"alpha1": a1, "alpha2": a2, "gap_AB": rel_rms(rA[post], rB[post]), "rows": []}
        for N in NS:
            row = {"N": N, "S": 2 * N + 1}
            for name in REALIZATIONS:
                y = run(name, N, u, alpha)
                row[name] = {"pre": rel_rms(y[pre], rA[pre]),
                             "post_A": rel_rms(y[post], rA[post]),
                             "post_B": rel_rms(y[post], rB[post])}
                if (a1, a2) == (0.3, 0.7) and N == 7:
                    traces[name] = y
            case["rows"].append(row)
            print(f"{a1:+.1f}->{a2:+.1f} S={2*N+1:2d} " + " ".join(
                f"{k}:A={row[k]['post_A']:.1e}/B={row[k]['post_B']:.1e}" for k in REALIZATIONS), flush=True)
        if (a1, a2) == (0.3, 0.7):
            traces["t"], traces["A"], traces["B"] = t, rA, rB
        out["cases"].append(case)
    with open(os.path.join(OUT, "e1_switched.json"), "w") as f:
        json.dump(out, f, indent=1)
    return out, traces


def smooth():
    n = int(round(TEND / TS)) + 1
    t = np.arange(n) * TS
    u = np.ones(n)
    stride = 20                                   # B reference every 20 ms
    idx = np.arange(stride, n, stride)
    idx = idx[t[idx] > 0.05]
    out = {"Ts": TS, "Tend": TEND, "band": [W_LO, W_HI], "eval_stride": stride, "cases": {}}
    for label, (fa, dfa) in SMOOTH_CASES.items():
        alpha = fa(t)
        rA = step_A(t, alpha)[idx]
        rB = step_B_smooth(t[idx], fa, dfa)
        case = {"gap_AB": rel_rms(rA, rB), "rows": []}
        for N in NS:
            row = {"N": N, "S": 2 * N + 1}
            for name in REALIZATIONS:
                y = run(name, N, u, alpha)[idx]
                row[name] = {"A": rel_rms(y, rA), "B": rel_rms(y, rB)}
            case["rows"].append(row)
            print(f"smooth {label:10s} S={2*N+1:2d} " + " ".join(
                f"{k}:A={row[k]['A']:.1e}/B={row[k]['B']:.1e}" for k in REALIZATIONS), flush=True)
        out["cases"][label] = case
    with open(os.path.join(OUT, "e1_smooth.json"), "w") as f:
        json.dump(out, f, indent=1)
    return out


def figures(sw, traces, sm):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"FP-out": "#1f77b4", "FP-in": "#d62728", "Ou-par": "#2ca02c", "Ou-cas": "#9467bd"}

    # convergence: post-switch error vs state count, against A and against B
    sel = [c for c in sw["cases"] if (c["alpha1"], c["alpha2"]) in [(-0.3, -0.7), (0.3, 0.7), (-0.5, 0.5)]]
    fig, axes = plt.subplots(2, len(sel), figsize=(4.2 * len(sel), 6.4), sharex=True)
    for j, case in enumerate(sel):
        S = [r["S"] for r in case["rows"]]
        for i, ref in enumerate(["post_A", "post_B"]):
            ax = axes[i, j]
            for name in REALIZATIONS:
                ax.semilogy(S, [r[name][ref] for r in case["rows"]], "o-", ms=3, color=colors[name], label=name)
            ax.axhline(case["gap_AB"], color="k", ls=":", lw=1, label="A-B gap")
            ax.grid(True, which="both", alpha=0.3)
            if i == 0:
                ax.set_title(f"alpha: {case['alpha1']:+.1f} -> {case['alpha2']:+.1f}")
            if j == 0:
                ax.set_ylabel(f"rel. RMS error vs {ref[-1]}-type")
            if i == 1:
                ax.set_xlabel("state count S")
    axes[0, 0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_e1_convergence.png"), dpi=150)

    # time traces around the switch (alpha 0.3 -> 0.7, S = 15)
    fig, ax = plt.subplots(figsize=(7, 3.6))
    t = traces["t"]
    w = (t > 1.5) & (t < 4.0)
    ax.plot(t[w], traces["A"][w], "k-", lw=2.2, label="A-type ref")
    ax.plot(t[w], traces["B"][w], "k--", lw=2.2, label="B-type ref")
    for name in REALIZATIONS:
        ax.plot(t[w], traces[name][w], color=colors[name], lw=1, label=name)
    ax.set_ylim(-0.5, 3.0)
    ax.set_xlabel("t [s]")
    ax.set_ylabel("y(t)")
    ax.set_title("Step response, alpha 0.3 -> 0.7 at t = 2 s, S = 15 states")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, ncol=3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_e1_traces.png"), dpi=150)

    # smooth profiles
    fig, axes = plt.subplots(2, 3, figsize=(12.6, 6.4), sharex=True)
    for j, (label, case) in enumerate(sm["cases"].items()):
        S = [r["S"] for r in case["rows"]]
        for i, ref in enumerate(["A", "B"]):
            ax = axes[i, j]
            for name in REALIZATIONS:
                ax.semilogy(S, [r[name][ref] for r in case["rows"]], "o-", ms=3, color=colors[name], label=name)
            ax.axhline(case["gap_AB"], color="k", ls=":", lw=1, label="A-B gap")
            ax.grid(True, which="both", alpha=0.3)
            if i == 0:
                ax.set_title(f"smooth alpha(t): {label}")
            if j == 0:
                ax.set_ylabel(f"rel. RMS error vs {ref}-type")
            if i == 1:
                ax.set_xlabel("state count S")
    axes[0, 0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_e1_smooth.png"), dpi=150)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    sw, traces = switched()
    sm = smooth()
    figures(sw, traces, sm)
