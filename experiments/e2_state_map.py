"""E2: can a state map rescue order-dependent-pole realizations?

Theorem (necessity): an exact A-type (B-type) switch for every input needs
the two pole sets to coincide. E2 measures how much a *best-case* linear
state map x+ = Phi x- recovers in practice, and at what price.

Part 1, single switch alpha1 -> alpha2 at nT = 2000 (Ts = 1 ms, window
L = 2000). Oustaloup (band 1e-3..1e5 rad/s, ZOH) in parallel and cascade
form; Phi fitted by truncated least squares on a mixed training ensemble
(white / piecewise-constant / multisine / Brownian inputs) and tested on
fresh ensembles plus a unit step. Reported per case:
  identity-map error (hot swap), best LS error (rcond by validation),
  ||Phi||_2 and cond(Phi), error after rounding Phi to float32 and to
  b-bit fixed point, and the output effect of b-bit state quantization
  amplified by Phi. The fixed-pole bank needs no map (Phi = I) and its
  definitional error is computed for the same inputs.

Part 2, continuous scheduling: a smooth order quantized to a grid; the
parallel Oustaloup realization applies a fitted map at every grid crossing.
Compared with the hot swap and with the fixed-pole bank.

Outputs: results/e2_state_map.json, results/e2_chained.json, results/fig_e2_*.png
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.statemap import (dt_oustaloup, end_states, fit_phi_A, fit_phi_B, input_ensemble,  # noqa: E402
                             obsv, rel_err, zero_state_output)

OUT = os.path.join(os.path.dirname(__file__), "..", "results")
TS, NT, L = 1e-3, 2000, 2000
BAND = (1e-3, 1e5)
PAIRS = [(0.3, 0.7), (0.7, 0.3), (-0.3, -0.7), (-0.7, -0.3), (-0.5, 0.5), (0.5, -0.5)]
NS = [3, 5, 7, 10, 15]
CLASSES = ["white", "pwc", "multisine", "brown"]
M_TRAIN, M_TEST = 200, 150
RCONDS = 10.0 ** -np.arange(3, 16)
BITS = [18, 24, 32]


def quantize(P, bits):
    """Round to a signed fixed-point grid whose range just covers max|P|."""
    ib = int(np.ceil(np.log2(np.abs(P).max() + 1e-300)))
    q = 2.0 ** (ib - (bits - 1))
    return np.round(P / q) * q


def dfp_definitional(a1, a2, U):
    """Definitional error of the fixed-pole bank on the same inputs (Phi = I)."""
    bank = DiscreteFixedPoleBank(TS, 1e-4, 4e5, 32)
    th = np.append(bank.theta, 0.0)       # delay mode as theta = 0
    Ad, Bd = np.diag(th), np.ones(len(th))
    X1 = end_states(Ad, Bd, U[:, :NT])     # state does not depend on the order
    X2 = end_states(Ad, Bd, U[:, :NT])
    g0, cd, c = bank.coeffs(a2)
    O2 = obsv(Ad, np.append(c, cd), L)
    return rel_err(O2 @ (X1 - X2), O2 @ X2 + 1e-300)


def single_switch(rng):
    train = {c: input_ensemble(c, M_TRAIN, NT + L, TS, rng) for c in CLASSES}
    test = {c: input_ensemble(c, M_TEST, NT + L, TS, rng) for c in CLASSES}
    test["step"] = input_ensemble("step", 1, NT + L, TS, rng)
    rows = []
    for a1, a2 in PAIRS:
        for N in NS:
            for form in ("parallel", "cascade"):
                s1 = dt_oustaloup(a1, *BAND, N, form, TS)
                s2 = dt_oustaloup(a2, *BAND, N, form, TS)
                O1, O2 = obsv(s1[0], s1[2], L), obsv(s2[0], s2[2], L)

                def states(U):
                    return (end_states(s1[0], s1[1], U[:, :NT]), end_states(s2[0], s2[1], U[:, :NT]),
                            zero_state_output(*s2, U[:, NT:]).T)

                tr = [states(train[c]) for c in CLASSES]
                X1 = np.hstack([s[0] for s in tr])
                X2 = np.hstack([s[1] for s in tr])
                te = {c: states(U) for c, U in test.items()}
                S = X1.shape[0]

                def err_A(P, extra=None):
                    out = {}
                    for c, (x1, x2, F2) in te.items():
                        e = O2 @ (P @ x1 - x2)
                        if extra is not None:
                            e = e + O2 @ (P @ extra(x1))
                        out[c] = rel_err(e, O2 @ x2 + F2)
                    return out

                def err_B(P):
                    return {c: rel_err(O1 @ x1 - O2 @ (P @ x1), O1 @ x1 + F2) for c, (x1, x2, F2) in te.items()}

                # rcond by validation on a split of the training ensemble
                ev, od = slice(0, None, 2), slice(1, None, 2)
                pareto_A, pareto_B = [], []
                for rc in RCONDS:
                    PA = fit_phi_A(X1[:, ev], X2[:, ev], rc)
                    PB = fit_phi_B(O1, O2, X1[:, ev], rc)
                    vA = rel_err(O2 @ (PA @ X1[:, od] - X2[:, od]), O2 @ X2[:, od])
                    vB = rel_err((O1 - O2 @ PB) @ X1[:, od], O1 @ X1[:, od])
                    pareto_A.append((float(rc), vA, float(np.linalg.norm(PA, 2))))
                    pareto_B.append((float(rc), vB, float(np.linalg.norm(PB, 2))))
                # "best": minimum validation error; "robust": smallest-norm map
                # whose validation error is within 2x of the best (fair to
                # finite-precision implementations)
                def pick(pareto, robust):
                    best = min(p[1] for p in pareto)
                    if not robust:
                        return min(pareto, key=lambda p: p[1])[0]
                    return min((p for p in pareto if p[1] <= 2.0 * best), key=lambda p: p[2])[0]

                # b-bit state quantization noise amplified by the map
                xr = np.abs(X1).max(axis=1)

                def state_noise(bits):
                    lsb = xr * 2.0 ** -(bits - 1)
                    return lambda x1: (np.random.default_rng(7).uniform(-0.5, 0.5, x1.shape) * lsb[:, None])

                def variant(robust):
                    rcA, rcB = pick(pareto_A, robust), pick(pareto_B, robust)
                    PA, PB = fit_phi_A(X1, X2, rcA), fit_phi_B(O1, O2, X1, rcB)
                    return {"A": err_A(PA), "B": err_B(PB), "rcond_A": rcA, "rcond_B": rcB,
                            "norm_A": float(np.linalg.norm(PA, 2)), "norm_B": float(np.linalg.norm(PB, 2)),
                            "cond_A": float(np.linalg.cond(PA)), "cond_B": float(np.linalg.cond(PB)),
                            "float32": {"A": err_A(PA.astype(np.float32).astype(float)),
                                        "B": err_B(PB.astype(np.float32).astype(float))},
                            "fixed": {str(b): {"A": err_A(quantize(PA, b)), "B": err_B(quantize(PB, b))} for b in BITS},
                            "state_noise_24b_A": err_A(PA, state_noise(24))}

                ls, rob = variant(False), variant(True)
                row = {
                    "alpha1": a1, "alpha2": a2, "N": N, "S": S, "form": form,
                    "identity": {"A": err_A(np.eye(S)), "B": err_B(np.eye(S)),
                                 "state_noise_24b_A": err_A(np.eye(S), state_noise(24))},
                    "ls": ls, "ls_robust": rob,
                    "pareto_A": pareto_A, "pareto_B": pareto_B,
                }
                if form == "parallel" and N == NS[-1]:
                    row["dfp_definitional_A"] = dfp_definitional(a1, a2, test["white"])
                rows.append(row)
                w = lambda d: max(d.values())
                print(f"{a1:+.1f}->{a2:+.1f} S={S:2d} {form:8s} | I: A {w(row['identity']['A']):.1e} B {w(row['identity']['B']):.1e}"
                      + "".join(f" | {tag}: A {w(v['A']):.1e} B {w(v['B']):.1e} |Phi| {v['norm_A']:.0e}"
                                f" f32 {w(v['float32']['A']):.0e} Q24 {w(v['fixed']['24']['A']):.0e}"
                                f" xq24 {w(v['state_noise_24b_A']):.0e}" for tag, v in (("LS", ls), ("rob", rob))),
                      flush=True)
    return rows


def chained(rng):
    """Smooth order on a grid; parallel Oustaloup with a fitted map at each crossing."""
    n = 4000
    t = np.arange(n) * TS
    profiles = {
        "derivative": (np.linspace(0.2, 0.8, 41), 0.5 + 0.3 * np.sin(np.pi * t / 2)),
        "integral": (np.linspace(-0.8, -0.2, 41), -0.5 + 0.3 * np.sin(np.pi * t / 2)),
    }
    sample_times = [250, 500, 1000, 2000, 3000, 4000]
    train = np.vstack([input_ensemble(c, 100, n, TS, rng) for c in CLASSES])
    tests = {"white": input_ensemble("white", 1, n, TS, rng)[0],
             "multisine": input_ensemble("multisine", 1, n, TS, rng)[0],
             "step": np.ones(n)}
    out = {}
    for pname, (grid, alpha) in profiles.items():
        idx = np.abs(alpha[:, None] - grid[None, :]).argmin(axis=1)
        aq = grid[idx]
        used = np.unique(idx)
        for N in (7, 15):
            sys_ = {i: dt_oustaloup(grid[i], *BAND, N, "parallel", TS) for i in used}
            # training states of every grid system at several times
            Xs = {}
            for i in used:
                d, Bd = np.diag(sys_[i][0]), sys_[i][1]   # parallel form: diagonal dynamics
                X = np.zeros((len(d), train.shape[0]))
                snaps = []
                for k in range(n):
                    X = d[:, None] * X + np.outer(Bd, train[:, k])
                    if k + 1 in sample_times:
                        snaps.append(X.copy())
                Xs[i] = np.hstack(snaps)
            maps = {}
            for k in range(1, n):
                i, j = idx[k - 1], idx[k]
                if i != j and (i, j) not in maps:
                    O = obsv(sys_[j][0], sys_[j][2], L)
                    ev, od = slice(0, None, 2), slice(1, None, 2)
                    cand = []
                    for rc in RCONDS:
                        P = fit_phi_A(Xs[i][:, ev], Xs[j][:, ev], rc)
                        cand.append((rc, rel_err(O @ (P @ Xs[i][:, od] - Xs[j][:, od]), O @ Xs[j][:, od]),
                                     np.linalg.norm(P, 2)))
                    e_best = min(c[1] for c in cand)
                    rc_rob = min((c for c in cand if c[1] <= 2.0 * e_best), key=lambda c: c[2])[0]
                    maps[(i, j)] = fit_phi_A(Xs[i], Xs[j], rc_rob)
            res = {}
            for iname, u in tests.items():
                ref = np.empty(n)
                for i in used:
                    Ad, Bd, C, D = sys_[i]
                    y = zero_state_output(Ad, Bd, C, D, u[None, :])[0]
                    ref[idx == i] = y[idx == i]
                ys = {}
                for mode in ("identity", "ls"):
                    x = np.zeros(sys_[used[0]][0].shape[0])
                    y = np.empty(n)
                    for k in range(n):
                        if k > 0 and idx[k] != idx[k - 1] and mode == "ls":
                            x = maps[(idx[k - 1], idx[k])] @ x
                        Ad, Bd, C, D = sys_[idx[k]]
                        y[k] = C @ x + D * u[k]
                        x = Ad @ x + Bd * u[k]
                    ys[mode] = y
                bank = DiscreteFixedPoleBank(TS, 1e-4, 4e5, 32)
                y_dfp = bank.simulate(u, aq, "output")
                own_dfp = np.empty(n)
                for i in used:
                    yi = bank.simulate(u, np.full(n, grid[i]), "output")
                    own_dfp[idx == i] = yi[idx == i]
                r = lambda y, ref_: float(np.sqrt(np.mean((y - ref_)[100:] ** 2) / np.mean(ref_[100:] ** 2)))
                res[iname] = {"identity": r(ys["identity"], ref), "ls_chain": r(ys["ls"], ref),
                              "dfp": r(y_dfp, own_dfp)}
            out[f"{pname}_N{N}"] = {"crossings": int(np.sum(idx[1:] != idx[:-1])), "maps": len(maps),
                                    "S": 2 * N + 1, "results": res}
            print(f"chained {pname} N={N}: crossings {out[f'{pname}_N{N}']['crossings']} "
                  + " ".join(f"{k}: I {v['identity']:.1e} LS {v['ls_chain']:.1e} DFP {v['dfp']:.1e}" for k, v in res.items()),
                  flush=True)
    return out


def figures(rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8))
    for ax, form in zip(axes, ("parallel", "cascade")):
        for N, color in zip((5, 7, 10, 15), ("#9ecae1", "#6baed6", "#3182bd", "#08519c")):
            r = next(x for x in rows if (x["alpha1"], x["alpha2"]) == (0.3, 0.7) and x["N"] == N and x["form"] == form)
            p = np.array(r["pareto_A"])
            ax.loglog(p[:, 2], p[:, 1], "o-", ms=3, color=color, label=f"S = {2 * N + 1}")
            ax.axhline(max(r["identity"]["A"].values()), color=color, ls=":", lw=1)
        ax.set_xlabel("||Phi||_2")
        ax.set_ylabel("validation definitional error (A)")
        ax.set_title(f"Oustaloup {form}, alpha 0.3 -> 0.7 (dotted: hot swap)")
        ax.grid(True, which="both", alpha=0.3)
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_e2_pareto.png"), dpi=150)

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.9), sharey=True)
    in_dist = [c for c in CLASSES]
    for ax, form in zip(axes, ("parallel", "cascade")):
        series = (
            ("hot swap (Phi = I)", "#9467bd", lambda x: x["identity"]["A"]),
            ("LS Phi, float64", "#2ca02c", lambda x: x["ls"]["A"]),
            ("min-norm LS Phi, float32", "#ff7f0e", lambda x: x["ls_robust"]["float32"]["A"]),
            ("min-norm LS Phi, 24-bit", "#d62728", lambda x: x["ls_robust"]["fixed"]["24"]["A"]),
        )
        for label, color, src in series:
            for classes, ls_, suffix in ((in_dist, "-", "in-distribution"), (["step"], "--", "step (OOD)")):
                S, E = [], []
                for N in NS:
                    sel = [x for x in rows if x["N"] == N and x["form"] == form]
                    E.append(max(src(x)[c] for x in sel for c in classes))
                    S.append(2 * N + 1)
                ax.semilogy(S, E, "o" + ls_, ms=3, color=color, label=f"{label}, {suffix}")
        ax.axhline(1.0, color="k", lw=0.6)
        ax.set_xlabel("state count S")
        ax.set_title(f"Oustaloup {form}: worst over 6 switches")
        ax.grid(True, which="both", alpha=0.3)
    axes[0].set_ylabel("definitional error vs own A-type")
    axes[1].legend(fontsize=6, ncol=2)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_e2_worstcase.png"), dpi=150)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    if "--figures" in sys.argv:
        with open(os.path.join(OUT, "e2_state_map.json")) as f:
            figures(json.load(f)["rows"])
        sys.exit(0)
    rng = np.random.default_rng(2026)
    rows = single_switch(rng)
    with open(os.path.join(OUT, "e2_state_map.json"), "w") as f:
        json.dump({"Ts": TS, "nT": NT, "L": L, "band": BAND, "classes": CLASSES,
                   "M_train": M_TRAIN, "M_test": M_TEST, "rows": rows}, f, indent=1)
    figures(rows)
    ch = chained(rng)
    with open(os.path.join(OUT, "e2_chained.json"), "w") as f:
        json.dump(ch, f, indent=1)
