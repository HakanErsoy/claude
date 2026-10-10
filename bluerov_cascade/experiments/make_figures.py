"""Figures for the manuscript, built only from results/*.json and results/x3_traces.npz.

Style: validated categorical palette in fixed slot order (each series also has
its own marker or line style; legends always shown), one sequential blue ramp
for the heat map, thin marks, recessive grid, one y-axis per panel.

    python3 -I experiments/make_figures.py       # figs/*.pdf and figs/*.png
"""

import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402,F401
import numpy as np  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rovc import scenarios  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
FIG = os.path.join(HERE, "..", "figs")

C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
GREY, INK, INK2 = "#8a8986", "#0b0b0b", "#52514e"
MK = ["o", "s", "^", "D", "v", "P", "X", "*"]
LS = ["-", "--", "-.", ":", "-", "--", "-.", ":"]
FULL, HALF = 6.3, 3.1

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["STIXGeneral", "DejaVu Serif"], "mathtext.fontset": "stix",
    "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8, "legend.fontsize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "axes.linewidth": 0.6,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "grid.color": "#e3e2de", "grid.linewidth": 0.5, "lines.linewidth": 1.2, "lines.markersize": 3.5,
    "legend.frameon": False, "pdf.fonttype": 42, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
})


def load(name):
    p = os.path.join(RES, name)
    return json.load(open(p)) if os.path.exists(p) else None


def style(ax, logy=False):
    if logy:
        ax.set_yscale("log")
    ax.grid(True, which="major")
    ax.spines[["top", "right"]].set_visible(False)


def panel(ax, label, title=""):
    ax.set_title(f"({label}) {title}".rstrip(), loc="left")


def save(fig, name):
    os.makedirs(FIG, exist_ok=True)
    fig.savefig(os.path.join(FIG, name + ".pdf"))
    fig.savefig(os.path.join(FIG, name + ".png"), dpi=200)
    plt.close(fig)


def fig_x0(d):
    funcs = list(dict.fromkeys(k.split("|")[0] for k in d))
    methods = list(dict.fromkeys(k.split("|")[2] for k in d))
    fig, axs = plt.subplots(1, len(funcs), figsize=(FULL, 1.9), sharey=False)
    x = np.arange(len(methods))
    for i, (ax, f) in enumerate(zip(axs, funcs)):
        for j, (case, lab) in enumerate((("origin", "optimum at origin"), ("shifted", "shifted optimum"))):
            v = [np.array(d[f"{f}|{case}|{m}"]) + 1e-16 for m in methods]
            med = np.array([np.median(a) for a in v])
            lo = med - np.array([np.percentile(a, 25) for a in v])
            hi = np.array([np.percentile(a, 75) for a in v]) - med
            ax.errorbar(x + (j - 0.5) * 0.3, med, yerr=[lo, hi], fmt=MK[j], color=C[j], ms=3.5, lw=0.8,
                        mfc=C[j] if j == 0 else "white", label=lab)
        style(ax, logy=True)
        ax.set_xticks(x, methods, rotation=60, ha="right")
        panel(ax, "abcd"[i], f)
        if i == 0:
            ax.set_ylabel("final error (median, IQR)")
    axs[0].legend(loc="lower left", bbox_to_anchor=(0, 1.12), ncol=2)
    save(fig, "fig_x0_bias")


def _x1_groups(d):
    g = {}
    for k, r in d.items():
        m, box, _ = k.split("|")
        g.setdefault((m, box), []).append(r)
    return g


def fig_x1(d):
    g = _x1_groups(d)
    methods = [m for m in ("SOO", "BC-SOO", "PSO", "DE", "GWO", "GJO", "RS") if (m, "plain") in g]
    fig, ax = plt.subplots(figsize=(HALF, 2.2))
    for j, (box, lab) in enumerate((("plain", "original box"), ("mirror", "mirrored box"))):
        for i, m in enumerate(methods):
            v = np.array([r["f"] for r in g.get((m, box), [])])
            if v.size == 0:
                continue
            xs = i + (j - 0.5) * 0.32 + np.linspace(-0.07, 0.07, v.size)
            ax.plot(xs, v, MK[j], color=C[j], mfc=C[j] if j == 0 else "white", ms=3, lw=0,
                    label=lab if i == 0 else None)
            ax.plot([i + (j - 0.5) * 0.32 - 0.12, i + (j - 0.5) * 0.32 + 0.12], [np.median(v)] * 2,
                    color=INK, lw=1.0)
    style(ax, logy=True)
    ax.set_xticks(range(len(methods)), methods, rotation=45, ha="right")
    ax.set_ylabel("training cost $J$ (10 runs, bar = median)")
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2)
    save(fig, "fig_x1_runs")

    fig, ax = plt.subplots(figsize=(HALF, 2.2))
    nfe = np.linspace(30, 3030, 101)
    for i, m in enumerate(methods):
        cur = np.array([r["curve"] for r in g[(m, "plain")]])
        color = GREY if m == "RS" else C[i]
        ax.plot(nfe, np.median(cur, 0), LS[i], color=color, label=m)
    style(ax, logy=True)
    ax.set_xlabel("objective evaluations")
    ax.set_ylabel("best $J$ so far (median of 10 runs)")
    ax.legend(ncol=2)
    save(fig, "fig_x1_convergence")


def fig_x3_tests(res):
    tests = list(next(iter(res.values()))["tests"])
    best = {}
    for k, e in res.items():
        s = e["structure"]
        if s not in best or e["train_J"] < best[s]["train_J"]:
            best[s] = e
    order = sorted(best, key=lambda s: best[s]["tests"][tests[-1]]["wITAE"], reverse=True)
    fig, axs = plt.subplots(1, len(tests), figsize=(FULL, 2.0), sharey=True)
    for i, (ax, t) in enumerate(zip(axs, tests)):
        v = [best[s]["tests"][t]["wITAE"] for s in order]
        col = [C[0] if s == "FOPID-(1+TFOID)" else GREY for s in order]
        ax.hlines(range(len(order)), 0, v, color=col, lw=1.0)
        ax.scatter(v, range(len(order)), c=col, s=14, zorder=3)
        style(ax)
        ax.set_xscale("log")
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        panel(ax, "abcd"[i], t)
        ax.set_xlabel("weighted ITAE")
    axs[0].set_yticks(range(len(order)), order)
    save(fig, "fig_x3_tests")
    return best


def fig_traces(best):
    tr = np.load(os.path.join(RES, "x3_traces.npz"))
    sc = scenarios.tests()[3]
    show = [s for s in ("FOPID-(1+TFOID)", "P-PID", "FOPID") if s in best]
    fig, axs = plt.subplots(2, 2, figsize=(FULL, 3.4), sharex=True)
    for i, (ax, d, lab) in enumerate(zip(axs.flat, (0, 1, 2, 5), ("$x$ [m]", "$y$ [m]", "$z$ [m]", r"$\psi$ [rad]"))):
        ax.plot(sc.t, sc.ref[:, d], color=GREY, lw=0.9, ls="--", label="reference")
        for j, s in enumerate(show):
            key = f"{s}|{best[s]['tuner']}|{sc.name}"
            ax.plot(sc.t[::5], tr[key][:, d], LS[j], color=C[j], lw=1.0, label=s)
        style(ax)
        ax.set_ylabel(lab)
        panel(ax, "abcd"[i])
    for ax in axs[1]:
        ax.set_xlabel("time [s]")
    axs[0, 0].legend(loc="lower left", bbox_to_anchor=(0, 1.12), ncol=4)
    save(fig, "fig_t4_traces")


def fig_robust(best):
    structs = sorted(best, key=lambda s: s != "FOPID-(1+TFOID)")
    variants = list(best[structs[0]]["robustness"])
    M = np.array([[best[s]["robustness"][v]["J"] / best[s]["tests"][v.split("|")[0]]["J"] for s in structs]
                  for v in variants])
    fig, ax = plt.subplots(figsize=(HALF + 1.4, 5.4))
    im = ax.imshow(np.log10(np.clip(M, 0.5, 1e3)), cmap="Blues", aspect="auto", vmin=np.log10(0.5), vmax=1.0)
    ax.set_xticks(range(len(structs)), structs, rotation=60, ha="right")
    ax.set_yticks(range(len(variants)), variants)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{M[i, j]:.2f}" if M[i, j] < 100 else ">100", ha="center", va="center", fontsize=5.5,
                    color="white" if M[i, j] > 4 else INK)
    cb = fig.colorbar(im, ax=ax, fraction=0.05)
    cb.set_label("$J$ / $J_{nominal}$ (log scale)")
    cb.set_ticks(np.log10([0.5, 1, 2, 5, 10]), labels=["0.5", "1", "2", "5", "10"])
    save(fig, "fig_robustness")


def main():
    d0 = load("x0_center_bias.json")
    if d0:
        fig_x0(d0)
    d1 = load("x1_optimizers.json")
    if d1:
        fig_x1(d1)
    d3 = load("x3_evaluate.json")
    if d3:
        best = fig_x3_tests(d3)
        fig_traces(best)
        fig_robust(best)


if __name__ == "__main__":
    main()
