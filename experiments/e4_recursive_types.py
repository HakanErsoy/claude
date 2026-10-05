"""E4: recursive D/E types and the full A/B/D/E family from one bank.

Definitions (Sierociuk et al., Electronics 2020 eqs. 7-8; CSSP 2016
Remark 2): D^a = (A^-a)^-1 and E^a = (B^-a)^-1.

Part 1  literal recursive GL definitions vs inverses of A/B matrices;
        dual vs non-dual compositions.
Part 2  rule-designed fixed-pole bank (eps = 1e-5, |alpha| <= 0.95):
        A, B forward and D, E by exact algebraic inversion vs literal GL;
        duality preserved by the bank; own-type (definitional) error.
Part 3  inverse stability: exact-sign test over orders for the holdout
        designs of E3 with and without the DC floor; long-run demo.
Part 4  which type does a hot-swapped Oustaloup realization implement?
        Distances to its own A/B/D/E (frozen-member) references.
Part 5  VO relaxation equation T^alpha y + lam y = u for T in A,B,D,E:
        O(K) bank solver vs O(n^2) GL triangular solve; type differences.

Outputs: results/e4_*.json, results/fig_e4_*.png
"""

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.design import design_dt  # noqa: E402
from vofrac.oustaloup import SwitchedOustaloup  # noqa: E402
from vofrac.reference import gl_A, gl_B, gl_D, gl_E, gl_matrix, gl_relaxation  # noqa: E402
from vofrac.types import OwnTypes  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "results")
TS = 1e-3
N = 4000
GL = {"A": gl_A, "B": gl_B, "D": gl_D, "E": gl_E}


def rel(y, r, skip=0):
    return float(np.sqrt(np.mean((y - r)[skip:] ** 2) / np.mean(r[skip:] ** 2)))


def profiles(t, rng):
    n = len(t)
    return {
        "switch +0.3->+0.8": np.where(t < t[-1] / 2, 0.3, 0.8),
        "switch -0.3->-0.8": np.where(t < t[-1] / 2, -0.3, -0.8),
        "switch -0.5->+0.5": np.where(t < t[-1] / 2, -0.5, 0.5),
        "random piecewise": np.repeat(rng.uniform(-0.9, 0.9, 20), n // 20 + 1)[:n],
        "smooth crossing": 0.6 * np.sin(2 * np.pi * t / t[-1]),
    }


def inputs(t, rng):
    return {
        "step": np.ones_like(t),
        "noise": rng.standard_normal(len(t)),
        "multisine": sum(np.sin(2 * np.pi * f * t + p) for f, p in [(0.5, 0.1), (3, 1.0), (17, 2.0), (60, 0.5)]),
    }


def part1(rng):
    n = 1500
    t = np.arange(n) * TS
    x = rng.standard_normal(n)
    out = []
    for pname, al in profiles(t, rng).items():
        WAm, WBm = gl_matrix(-al, TS, "A"), gl_matrix(-al, TS, "B")
        D, E = gl_D(x, al, TS), gl_E(x, al, TS)
        mx = lambda a, b: float(np.max(np.abs(a - b)) / np.max(np.abs(b)))
        op = lambda T, v, a: GL[T](v, a, TS)
        row = {"profile": pname,
               "D_vs_inv_WA": mx(D, np.linalg.solve(WAm, x)), "E_vs_inv_WB": mx(E, np.linalg.solve(WBm, x)),
               "dual": {f"{T1}^a {T2}^-a": mx(op(T1, op(T2, x, -al), al), x)
                        for T1, T2 in (("A", "D"), ("D", "A"), ("B", "E"), ("E", "B"))},
               "non_dual": {f"{T1}^a {T2}^-a": mx(op(T1, op(T2, x, -al), al), x)
                            for T1, T2 in (("A", "A"), ("B", "B"), ("A", "B"), ("B", "A"), ("A", "E"),
                                           ("B", "D"), ("D", "E"), ("D", "D"))}}
        out.append(row)
        print(f"P1 {pname:18s} literal D/E vs inverses {row['D_vs_inv_WA']:.1e}/{row['E_vs_inv_WB']:.1e} | dual max "
              f"{max(row['dual'].values()):.1e} | non-dual min {min(row['non_dual'].values()):.1e}", flush=True)
    return out


def part2(rng):
    t = np.arange(N) * TS
    d = design_dt(TS, N, -0.95, 0.95, 1e-5)
    bank = DiscreteFixedPoleBank(TS, d["xi_lo"], d["xi_hi"], d["K"])
    own = OwnTypes(lambda u, a: bank.simulate_type(u, a, "A"), N)
    rows = []
    for pname, al in profiles(t, rng).items():
        piecewise = len(np.unique(al)) <= 40
        for iname, x in inputs(t, rng).items():
            row = {"profile": pname, "input": iname}
            for T in "ABDE":
                y = bank.simulate_type(x, al, T)
                rec = {"vs_GL": rel(y, GL[T](x, al, TS))}
                if piecewise:
                    rec["vs_own"] = rel(y, getattr(own, T)(x, al))
                row[T] = rec
            row["duality_AD"] = rel(bank.simulate_type(bank.simulate_type(x, -al, "D"), al, "A"), x)
            row["duality_BE"] = rel(bank.simulate_type(bank.simulate_type(x, -al, "E"), al, "B"), x)
            rows.append(row)
            print(f"P2 {pname:18s} {iname:9s} " + " ".join(f"{T}:{row[T]['vs_GL']:.1e}" for T in "ABDE")
                  + f" | duality {row['duality_AD']:.0e}/{row['duality_BE']:.0e}", flush=True)
    return {"design": d, "rows": rows}


def part3(rng):
    with open(os.path.join(OUT, "e3_holdout_specs.json")) as f:
        specs = [s for s in json.load(f)["specs"] if s["kind"] == "dt"]
    counts = {True: 0, False: 0}
    for s in specs:
        d = design_dt(TS, s["R"], s["alpha_min"], s["alpha_max"], s["eps"])
        grid = [a for a in np.linspace(s["alpha_min"], s["alpha_max"], 25) if abs(a) > 1e-9]
        for floor in (True, False):
            b = DiscreteFixedPoleBank(TS, d["xi_lo"], d["xi_hi"], d["K"], dc_floor=floor)
            counts[floor] += all(b.inverse_is_stable(a) for a in grid)
    print(f"P3 stable inverse at all orders: with floor {counts[True]}/{len(specs)}, without {counts[False]}/{len(specs)}",
          flush=True)
    # long run: D-type integral of order 0.95 (inverts the 0.95 derivative bank)
    d = design_dt(TS, 1000, -0.95, 0.95, 1e-2)
    n = 200000
    x = rng.standard_normal(n)
    demo = {}
    for floor in (False, True):
        b = DiscreteFixedPoleBank(TS, d["xi_lo"], d["xi_hi"], d["K"], dc_floor=floor)
        y = b.simulate_type(x, np.full(n, -0.95), "D")
        demo[str(floor)] = [float(np.sqrt(np.mean(y[i:i + 2000] ** 2))) for i in range(0, n, 2000)]
    print(f"P3 long run rms (no floor) {demo['False'][-1]:.1e} vs (floor) {demo['True'][-1]:.1e}", flush=True)
    return {"n_specs": len(specs), "stable_with_floor": counts[True], "stable_without_floor": counts[False],
            "long_run_design": d, "long_run_rms_per_2000": demo}


def part4(rng):
    t = np.arange(N) * TS
    prof = {k: v for k, v in profiles(t, rng).items() if k != "smooth crossing"}
    ins = {k: v for k, v in inputs(t, rng).items() if k != "multisine"}
    d = design_dt(TS, N, -0.95, 0.95, 1e-5)
    bank = DiscreteFixedPoleBank(TS, d["xi_lo"], d["xi_hi"], d["K"])
    reals = {"DFP-out": (lambda u, a: bank.simulate_type(u, a, "A")),
             "DFP-in": (lambda u, a: bank.simulate_type(u, a, "B"))}
    # w_h = 1e5 exceeds Nyquist (pi/Ts ~ 3.1e3); under ZOH its integral
    # members are then non-minimum-phase, so their D/E inverses diverge.
    # w_h = 1e3 keeps the members minimum-phase and all four references exist.
    for w_h in (1e5, 1e3):
        for Nn in (7, 15):
            for form in ("parallel", "cascade"):
                o = SwitchedOustaloup(1e-3, w_h, Nn, form)
                reals[f"Ou-{form[:3]} N={Nn} wh={w_h:.0e}"] = (lambda o_: (lambda u, a: o_.simulate(u, a, TS)))(o)
    rows = []
    with np.errstate(all="ignore"):
        for name, sim in reals.items():
            own = OwnTypes(sim, N)
            for pname, al in prof.items():
                for iname, x in ins.items():
                    y = sim(x, al)
                    dist = {}
                    for T, r in own.all(x, al).items():
                        v = rel(y, r, skip=50)
                        dist[T] = v if np.isfinite(v) else None   # None: own inverse diverges
                    finite = {T: v for T, v in dist.items() if v is not None}
                    rows.append({"realization": name, "profile": pname, "input": iname, "dist": dist,
                                 "nearest": min(finite, key=finite.get)})
                    print(f"P4 {name:22s} {pname:18s} {iname:6s} "
                          + " ".join(f"{T}:{v:.1e}" if v is not None else f"{T}:diverges" for T, v in dist.items())
                          + f" -> {rows[-1]['nearest']}", flush=True)
    return rows


def part5(rng):
    t = np.arange(N) * TS
    prof = {"switch +0.3->+0.8": np.where(t < 2.0, 0.3, 0.8), "smooth": 0.5 + 0.4 * np.sin(np.pi * t / 2),
            "switch -0.3->-0.8": np.where(t < 2.0, -0.3, -0.8)}
    ins = {"step": np.ones(N), "noise": rng.standard_normal(N)}
    # D and E run the bank at the opposite order, so cover +-max|alpha|
    amax = max(np.abs(v).max() for v in prof.values())
    d = design_dt(TS, N, -amax, amax, 1e-5)
    bank = DiscreteFixedPoleBank(TS, d["xi_lo"], d["xi_hi"], d["K"])
    rows, traces = [], {}
    for lam in (1.0, 100.0):
        for pname, al in prof.items():
            for iname, u in ins.items():
                sol, ref = {}, {}
                t_bank = t_gl = 0.0
                for T in "ABDE":
                    t0 = time.time()
                    sol[T] = bank.solve_relaxation(u, al, lam, T)
                    t_bank += time.time() - t0
                    t0 = time.time()
                    ref[T] = gl_relaxation(u, al, lam, TS, T)
                    t_gl += time.time() - t0
                row = {"lam": lam, "profile": pname, "input": iname,
                       "err": {T: rel(sol[T], ref[T]) for T in "ABDE"},
                       "type_gap": {f"{a}-{b}": rel(ref[a], ref[b]) for a, b in (("A", "B"), ("A", "D"), ("B", "E"), ("D", "E"))},
                       "time_bank_s": t_bank, "time_gl_s": t_gl}
                rows.append(row)
                if lam == 1.0 and pname == "switch +0.3->+0.8" and iname == "step":
                    traces = {"t": t.tolist(), "bank": {T: sol[T].tolist() for T in "ABDE"},
                              "gl": {T: ref[T].tolist() for T in "ABDE"}}
                print(f"P5 lam={lam:5.0f} {pname:18s} {iname:5s} err " + " ".join(f"{T}:{v:.1e}" for T, v in row["err"].items())
                      + " | gaps " + " ".join(f"{k}:{v:.2f}" for k, v in row["type_gap"].items()), flush=True)
    return {"design": d, "rows": rows}, traces


def figures(p3, traces):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    t = np.array(traces["t"])
    colors = {"A": "#1f77b4", "B": "#d62728", "D": "#2ca02c", "E": "#9467bd"}
    for T in "ABDE":
        axes[0].plot(t, traces["gl"][T], color=colors[T], lw=2.4, alpha=0.35)
        axes[0].plot(t, traces["bank"][T], color=colors[T], lw=1.0, label=f"{T}-type")
    axes[0].axvline(2.0, color="k", lw=0.6, ls=":")
    axes[0].set_xlabel("t [s]")
    axes[0].set_ylabel("y(t)")
    axes[0].set_title("T^alpha y + y = 1, alpha 0.3 -> 0.8 at t = 2 s\n(thin: O(K) bank, thick: O(n^2) GL)")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.3)
    k = np.arange(len(p3["long_run_rms_per_2000"]["True"])) * 2000
    axes[1].semilogy(k, p3["long_run_rms_per_2000"]["False"], color="#d62728", label="no DC floor")
    axes[1].semilogy(k, p3["long_run_rms_per_2000"]["True"], color="#1f77b4", label="with DC floor")
    axes[1].set_xlabel("sample")
    axes[1].set_ylabel("RMS of output (2000-sample blocks)")
    axes[1].set_title("D-type integral of order 0.95, white-noise input,\nbank designed for R = 1000, eps = 1e-2")
    axes[1].legend(fontsize=8)
    axes[1].grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_e4_types.png"), dpi=150)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(44)
    res = {"part1": part1(rng), "part2": part2(rng), "part3": part3(rng), "part4": part4(rng)}
    res["part5"], traces = part5(rng)
    with open(os.path.join(OUT, "e4_recursive_types.json"), "w") as f:
        json.dump(res, f, indent=1)
    figures(res["part3"], traces)
