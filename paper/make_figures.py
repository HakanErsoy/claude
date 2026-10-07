"""Vector figures for the manuscript, built only from results/*.json.

Style: validated categorical palette (slots 1-4 pass the light-mode CVD and
normal-vision checks; aqua and yellow fall below 3:1 contrast, so every
series also carries its own marker and line style and the legend is always
shown), one ordinal blue ramp for word lengths, thin marks, recessive grid,
neutral grey reference lines, one y-axis per panel.
"""

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
FIG = os.path.join(HERE, "figs")

C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]          # categorical slots 1-4
RAMP = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]       # ordinal blue (steps 250/400/550/700)
GREY, INK, INK2 = "#8a8986", "#0b0b0b", "#52514e"
MK = ["o", "s", "^", "D"]
LS = ["-", "-", "--", "--"]
FULL, HALF = 6.3, 3.1                                     # inches

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["STIXGeneral", "DejaVu Serif"], "mathtext.fontset": "stix",
    "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8, "legend.fontsize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "axes.linewidth": 0.6,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "grid.color": "#e3e2de", "grid.linewidth": 0.5, "lines.linewidth": 1.2, "lines.markersize": 3.5,
    "legend.frameon": False, "pdf.fonttype": 42, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
})


def load(name):
    with open(os.path.join(RES, name)) as f:
        return json.load(f)


def style(ax, logy=True):
    if logy:
        ax.set_yscale("log")
    ax.grid(True, which="major")
    ax.spines[["top", "right"]].set_visible(False)


def panel(ax, label, title=""):
    """Left-aligned title carrying the panel label, so labels never collide with titles."""
    ax.set_title(f"({label}) {title}".rstrip(), loc="left")


def save(fig, name):
    fig.savefig(os.path.join(FIG, name))
    plt.close(fig)


# ---------------------------------------------------------------- E1
def fig_definition():
    d = load("e1_switched.json")
    names = ["FP-out", "FP-in", "Ou-par", "Ou-cas"]
    labels = ["fixed-pole, output schedule", "fixed-pole, input schedule",
              "Oustaloup parallel, hot swap", "Oustaloup cascade, hot swap"]
    cases = [c for c in d["cases"] if (c["alpha1"], c["alpha2"]) in [(-0.3, -0.7), (0.3, 0.7)]]
    fig, axes = plt.subplots(2, 2, figsize=(FULL, 3.9), sharex=True)
    for j, case in enumerate(cases):
        S = [r["S"] for r in case["rows"]]
        for i, ref in enumerate(["post_A", "post_B"]):
            ax = axes[i, j]
            for k, n in enumerate(names):
                ax.plot(S, [r[n][ref] for r in case["rows"]], LS[k], marker=MK[k], color=C[k],
                        label=labels[k] if (i, j) == (0, 0) else None)
            ax.axhline(case["gap_AB"], color=GREY, ls=":", lw=0.9,
                       label="A-B gap" if (i, j) == (0, 0) else None)
            style(ax)
            if j == 0:
                ax.set_ylabel(f"rel. RMS error vs {ref[-1]}-type")
            if i == 1:
                ax.set_xlabel("state count $S$")
            ttl = rf"$\alpha$: {case['alpha1']:+.1f} $\to$ {case['alpha2']:+.1f} at $t$ = 2 s" if i == 0 else ""
            panel(ax, "abcd"[2 * i + j], ttl)
    fig.legend(loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.07))
    fig.tight_layout()
    save(fig, "fig_definition.pdf")


# ---------------------------------------------------------------- E3
def fig_rule():
    tm, hold = load("e3_terms.json"), load("e3_holdout.json")
    fig, axes = plt.subplots(1, 3, figsize=(FULL, 2.25))
    terms = [("quad", "quadrature"), ("lo", "low tail"), ("hi", "high tail")]
    for ax, key, title, lab in ((axes[0], "dt", "discrete time (GL weights)", "a"),
                                (axes[1], "ct", "continuous time (freq. response)", "b")):
        for k, (t, name) in enumerate(terms):
            p = np.array([(r["pred"], r["meas"]) for r in tm[key] if r["term"] == t and r["pred"] > 1e-10])
            ax.loglog(p[:, 0], p[:, 1], MK[k], color=C[k], ms=3.5, ls="none", label=name, alpha=0.9)
        lim = [1e-10, 1e-1]
        ax.plot(lim, lim, color=GREY, lw=0.8)
        ax.set_xlim(lim)
        ax.set_ylim(lim)
        ax.set_xlabel("predicted")
        style(ax, logy=False)
        panel(ax, lab, title)
    axes[0].set_ylabel("measured")
    axes[0].legend(loc="upper left")
    ax = axes[2]
    for k, (kind, name) in enumerate((("dt", "discrete-time rule"), ("ct", "continuous-time rule"))):
        rows = [r for r in hold["rows"] if r["kind"] == kind]
        ax.loglog([r["eps"] for r in rows], [r["err"] for r in rows], MK[k], color=C[k], ms=2.8, ls="none",
                  mfc=C[k] if k == 0 else "none", mew=0.6, label=name, alpha=0.85)
    lim = [1e-6, 3e-2]
    ax.plot(lim, lim, color=GREY, lw=0.8, label=r"error $=\varepsilon$")
    ax.set_xlim(lim)
    ax.set_ylim(1e-6, 1e-1)
    ax.set_xlabel(r"requested $\varepsilon$")
    ax.set_ylabel("measured worst case")
    ax.legend(loc="upper left")
    style(ax, logy=False)
    panel(ax, "c", "sealed holdout, 400 specs")
    fig.tight_layout()
    save(fig, "fig_rule.pdf")


# ---------------------------------------------------------------- E2
def fig_maps():
    d = load("e2_state_map.json")
    rows = d["rows"]
    Ns = sorted({r["N"] for r in rows})
    series = [("hot swap ($\\Phi = I$)", lambda r: r["identity"]["A"]),
              ("LS map, float64", lambda r: r["ls"]["A"]),
              ("min-norm LS map, float32", lambda r: r["ls_robust"]["float32"]["A"]),
              ("min-norm LS map, 24-bit fixed", lambda r: r["ls_robust"]["fixed"]["24"]["A"])]
    fig, axes = plt.subplots(1, 2, figsize=(FULL, 2.35), sharey=True)
    for ax, form, lab in zip(axes, ("parallel", "cascade"), "ab"):
        for k, (name, src) in enumerate(series):
            S, E = [], []
            for N in Ns:
                sel = [r for r in rows if r["N"] == N and r["form"] == form]
                E.append(max(max(src(r).values()) for r in sel))
                S.append(2 * N + 1)
            ax.plot(S, E, LS[k], marker=MK[k], color=C[k], label=name if form == "parallel" else None)
        ax.axhline(1.0, color=GREY, lw=0.7, ls=":")
        ax.set_xlabel("state count $S$")
        style(ax)
        panel(ax, lab, f"Oustaloup, {form} form")
    axes[0].set_ylabel("worst definitional error (A-type)")
    fig.legend(loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.08))
    fig.tight_layout()
    save(fig, "fig_maps.pdf")


# ---------------------------------------------------------------- E4
def fig_types():
    tr, d = load("e4_traces.json"), load("e4_recursive_types.json")
    fig, axes = plt.subplots(1, 2, figsize=(FULL, 2.35))
    ax = axes[0]
    t = np.array(tr["t"])
    for k, T in enumerate("ABDE"):
        ax.plot(t, tr["gl"][T], color=C[k], lw=3.0, alpha=0.25)
        ax.plot(t, tr["bank"][T], LS[k], color=C[k], lw=1.0, label=f"{T}-type")
    ax.axvline(2.0, color=GREY, lw=0.6, ls=":")
    ax.set_xlabel("$t$ [s]")
    ax.set_ylabel("$y(t)$")
    ax.legend(loc="lower right", ncol=2)
    style(ax, logy=False)
    panel(ax, "a", r"${}^{T}\!D^{\alpha(t)}y + y = 1$, $\alpha$: 0.3 $\to$ 0.8 at 2 s")
    ax = axes[1]
    lr = d["part3"]["long_run_rms_per_2000"]
    k = np.arange(len(lr["True"])) * 2000
    ax.plot(k, lr["False"], "-", color=C[1], label="without DC floor")
    ax.plot(k, lr["True"], "-", color=C[0], label="with DC floor")
    ax.set_xlabel("sample")
    ax.set_ylabel("output RMS (2000-sample blocks)")
    ax.legend(loc="upper left")
    style(ax)
    panel(ax, "b", "D-type integral of order 0.95, white noise")
    fig.tight_layout()
    save(fig, "fig_types.pdf")


# ---------------------------------------------------------------- E5
def fig_wordlength():
    d = load("e5_fixed_point.json")
    env = d["envelopes"]["ABDE"]
    WMs = sorted({r["WM"] for r in env["sweep"]})
    fig, axes = plt.subplots(1, 4, figsize=(FULL, 2.0), sharey=True)
    for ax, T, lab in zip(axes, "ABDE", "abcd"):
        for k, WM in enumerate(WMs):
            rows = sorted([r for r in env["sweep"] if r["WM"] == WM], key=lambda r: r["WS"])
            ax.plot([r["WS"] for r in rows], [r["worst"][T]["gl"] for r in rows], "-", marker=MK[k],
                    color=RAMP[k], label=f"$W_M$ = {WM}" if T == "A" else None)
        ax.axhline(env["float_err"][T], color=GREY, lw=0.8, ls=":", label="floating point" if T == "A" else None)
        ax.axhline(env["float_err"][T] + 0.1 * d["eps"], color=GREY, lw=0.8, ls="--",
                   label=r"floating point $+\,0.1\varepsilon$" if T == "A" else None)
        ax.set_xlabel("signal word $W_S$")
        style(ax)
        panel(ax, lab, f"{T}-type")
    axes[0].set_ylabel("worst rel. RMS error vs GL")
    fig.legend(loc="lower center", ncol=6, bbox_to_anchor=(0.5, -0.12))
    fig.tight_layout()
    save(fig, "fig_wordlength.pdf")


# ---------------------------------------------------------------- E6
def fig_mbm():
    tr = load("e6_traces.json")
    fig, axes = plt.subplots(2, 2, figsize=(FULL, 3.9))
    for ax, name, lab in ((axes[0, 0], "ramp 0.2->0.8", "a"), (axes[0, 1], "step 0.3->0.8", "b")):
        for k, T in enumerate("AB"):
            h = tr["hurst"][f"{name}|{T}"]
            c, m, s = np.array(h["c"]), np.array(h["mean"]), np.array(h["std"])
            ax.plot(c, m, LS[k], color=C[k], label=f"{T}-type, mean")
            ax.fill_between(c, m - s, m + s, color=C[k], alpha=0.10, lw=0)
        ax.plot(c, h["truth"], color=INK, lw=0.8, ls=":", label="$H(t)$, window average")
        ax.set_xlabel("sample")
        ax.set_ylabel(r"local Hurst estimate $\hat H$")
        pretty = name.replace("->", r" $\to$ ")
        style(ax, logy=False)
        panel(ax, lab, "Hurst function: " + pretty)
    axes[0, 0].legend(loc="upper left")
    st = tr["step"]
    k = np.arange(len(st["VA"]))
    ax = axes[1, 0]
    ax.plot(k, st["VA"], "-", color=C[0], label="A-type (RL-mBm)")
    ax.plot(k, st["VB"], "--", color=C[1], label="B-type")
    ax.set_xlabel("sample")
    ax.set_ylabel("exact variance")
    ax.legend(loc="upper left")
    style(ax)
    panel(ax, "c", r"$H$: 0.3 $\to$ 0.8 at $n/2$")
    ax = axes[1, 1]
    ax.plot(k, st["pathA"], "-", color=C[0], lw=0.8, label="A-type path")
    ax.plot(k, st["pathB"], "--", color=C[1], lw=0.8, label="B-type path (same noise)")
    ax.axvline(len(k) // 2, color=GREY, lw=0.6, ls=":")
    ax.set_xlabel("sample")
    ax.set_ylabel("$X[n]$")
    ax.legend(loc="upper left")
    style(ax, logy=False)
    panel(ax, "d", "sample paths")
    fig.tight_layout()
    save(fig, "fig_mbm.pdf")


# ---------------------------------------------------------------- E8
def fig_pareto():
    rows = load("e8_baselines.json")["rows"]

    def series(method):
        return [r for r in rows if r["method"] == method]

    def mem(r):
        return r["state_A"] + r["rom"]

    spec = [  # method, label, colour, marker, line style, filled
        ("FP-rule", "fixed poles, analytic rule (this paper)", C[0], "o", "-", True),
        ("FP-LPs", "fixed poles, LP residues with sign/DC constraints", C[2], "^", "-", True),
        ("FP-LP", "fixed poles, unconstrained LP residues", C[2], "v", "--", False),
        ("MP-rule", "moving poles, hot swap", C[1], "s", "-", True),
        ("FIR", "truncated GL convolution", C[3], "D", "--", True),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(FULL, 3.1), sharey=True)
    for ax, xkey, xlabel, lab in ((axes[0], "mac", "multiplications per sample", "a"),
                                  (axes[1], "mem", "memory words (states + coefficient ROM)", "b")):
        for method, label, col, mk, ls, filled in spec:
            rs = [r for r in series(method) if r["vo"]["A"] > 0]
            x = [r["mac"] if xkey == "mac" else mem(r) for r in rs]
            y = [r["vo"]["A"] for r in rs]
            ax.plot(x, y, ls, color=col, marker=mk, mfc=col if filled else "white", label=label)
            if method == "MP-rule":
                yc = [r["const"] for r in rs]
                ax.plot(x, yc, ":", color=col, marker=mk, mfc="white", label="moving poles, constant order only")
        fir_exact = [r for r in series("FIR") if r["vo"]["A"] == 0][0]
        xe = fir_exact["mac"] if xkey == "mac" else mem(fir_exact)
        # the convolution is exact only at L = N; mark it on the bottom edge
        ax.plot([xe], [1.6e-10], "v", color=C[3], ms=5, clip_on=False)
        ax.annotate("exact at $L=N$", xy=(xe, 1.6e-10), xytext=(-4, 3), textcoords="offset points",
                    ha="right", va="bottom", fontsize=6.5, color=INK2)
        ax.set_xscale("log")
        ax.set_xlim(right=xe * 1.6)
        ax.set_xlabel(xlabel)
        style(ax)
        ax.set_ylim(1e-10, 3)
        panel(ax, lab, "A-type, worst over 8 order sequences")
    axes[0].set_ylabel(r"relative operator error in $\ell^\infty$")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, fontsize=6.5, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    save(fig, "fig_pareto.pdf")


# ---------------------------------------------------------------- E10
def fig_tracking():
    d = load("e10_order_tracking.json")
    tr = d["traces"]
    t = np.array(tr["t"])
    fig, axes = plt.subplots(1, 2, figsize=(FULL, 2.6), sharey=True)
    for ax, T, lab in ((axes[0], "A", "a"), (axes[1], "B", "b")):
        for name, col, label in (("A-grid", C[0], "A-type grid filter"), ("B-EKF", C[1], "B-type EKF")):
            matched = name[0] == T
            q = tr[f"60dB/{T}/{name}"]
            ls = "-" if matched else "--"
            ax.fill_between(t, np.maximum(q["abs_err_p50"], 1e-5), np.maximum(q["abs_err_p90"], 1e-5),
                            color=col, alpha=0.15, lw=0)
            ax.plot(t, np.maximum(q["abs_err_p50"], 1e-5), ls, color=col, lw=1.1,
                    label=f"{label} ({'matched' if matched else 'wrong type'})")
        for tb in (1.0, 2.0, 2.5):
            ax.axvline(tb, color=GREY, lw=0.6, ls=":")
        ax.set_xlabel("time [s] (2000 samples)")
        style(ax)
        ax.set_ylim(1e-5, 2)
        ax.legend(loc="lower right", fontsize=6.3)
        panel(ax, lab, f"{T}-type data, 60 dB, 50 runs")
    axes[0].set_ylabel(r"$|\hat\alpha_n-\alpha_n|$ (median, band to 90 %)")
    fig.tight_layout()
    save(fig, "fig_tracking.pdf")


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    for f in (fig_definition, fig_rule, fig_maps, fig_types, fig_wordlength, fig_mbm, fig_pareto, fig_tracking):
        f()
        print("wrote", f.__name__)
