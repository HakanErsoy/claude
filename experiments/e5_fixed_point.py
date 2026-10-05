"""E5a: fixed-point word-length study of the discrete bank (all four types).

Design point (sample units, Ts = 1): memory R = 4000, eps = 1e-4,
|alpha| <= 0.95 -> K from the E3 rule; order grid P = 1024 (per-sample
order updates are a table lookup). The bit-accurate model is
vofrac.fixedpoint.FixedPointBank (the RTL golden).

Two operating envelopes, each with its own headroom:
  "AB"   : forward types only (A, B); any order switching
  "ABDE" : all four types; any order switching. D/E switching between
           integral and derivative orders grows the output far beyond the
           frozen-order bounds (characterized by fixedpoint.stress_bound)
Headroom V_max = 2 x max(frozen l1 bound, switching stress peak).

Test set: 3 order profiles (random piecewise, smooth with a new grid index
every sample, a sign-changing switch) x 3 inputs (white noise, step,
multisine) x the envelope's types, n = 4000. Errors: relative RMS against
the literal GL definition (h = 1, same quantized orders) and against the
floating-point bank. Acceptance ("transparent"): for every type,
err_fixed_vs_GL <= err_float_vs_GL + 0.1 eps.

Also: inverse stability under quantization (long run with and without the
quantization-aware DC floor).

Outputs: results/e5_fixed_point.json, results/fig_e5_wordlength.png
"""

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.design import design_dt  # noqa: E402
from vofrac.fixedpoint import FixedPointBank, output_bound, stress_bound  # noqa: E402
from vofrac.reference import gl_A, gl_B, gl_D, gl_E  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "results")
GL = {"A": gl_A, "B": gl_B, "D": gl_D, "E": gl_E}
R, EPS, AMAX, P, N = 4000, 1e-4, 0.95, 1024, 4000
WS_LIST = [32, 36, 40, 44, 48, 52, 56]
WM_LIST = [16, 18, 25, 32]
ENVELOPES = {"AB": "AB", "ABDE": "ABDE"}


def rel(y, r):
    return float(np.sqrt(np.mean((y - r) ** 2) / np.mean(r ** 2)))


def test_set(rng):
    t = np.arange(N)
    prof = {"random piecewise": np.repeat(rng.uniform(-0.9, 0.9, 10), N // 10),
            "smooth per-sample": 0.9 * np.sin(2 * np.pi * t / N),
            "switch -0.6->+0.8": np.where(t < N // 2, -0.6, 0.8)}
    inp = {"noise": np.clip(0.25 * rng.standard_normal(N), -0.99, 0.99),
           "step": np.full(N, 0.5),
           "multisine": sum(0.2 * np.sin(2 * np.pi * f * t / 1000 + p) for f, p in [(0.5, 0.1), (3, 1.0), (17, 2.0), (60, 0.5)])}
    return prof, inp


def main():
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(55)
    d = design_dt(1.0, R, -AMAX, AMAX, EPS)
    bank = DiscreteFixedPoleBank(1.0, d["xi_lo"], d["xi_hi"], d["K"])
    prof, inp = test_set(rng)
    res = {"design": d, "P": P, "eps": EPS, "envelopes": {}}
    for env, types in ENVELOPES.items():
        V_frozen = output_bound(bank, R, AMAX, types="A" if types == "AB" else "AD")
        V_stress = stress_bound(bank, R, AMAX, types=types)
        V = 2.0 * max(V_frozen, V_stress)
        probe = FixedPointBank(bank, P=P, amax=AMAX, WS=max(WS_LIST), WM=25, n_max=R, V_max=V)
        print(f"[{env}] K={d['K']} frozen bound {V_frozen:.0f}, stress peak {V_stress:.0f}, V_max={V:.0f} "
              f"-> I={probe.I} integer bits, state headroom +{probe.LOGN} bits", flush=True)
        F_fine = probe.F
        cases = []
        for pname, al in prof.items():
            idx = probe.index(al)
            aq = probe.grid[idx]
            for iname, x in inp.items():
                xq = np.round(x * 2.0 ** F_fine) / 2.0 ** F_fine
                for T in types:
                    cases.append({"type": T, "idx": idx, "x": xq, "gl": GL[T](xq, aq, 1.0),
                                  "flt": bank.simulate_type(xq, aq, T)})
        float_err = {T: max(rel(c["flt"], c["gl"]) for c in cases if c["type"] == T) for T in types}
        print(f"[{env}] float bank vs GL (worst): " + " ".join(f"{T}:{v:.1e}" for T, v in float_err.items()), flush=True)
        sweep = []
        for WS in WS_LIST:
            for WM in WM_LIST:
                t0 = time.time()
                try:
                    fp = FixedPointBank(bank, P=P, amax=AMAX, WS=WS, WM=WM, n_max=R, V_max=V)
                except ValueError as e:
                    print(f"[{env}] WS={WS} WM={WM}: {e}")
                    continue
                worst = {T: {"gl": 0.0, "flt": 0.0} for T in types}
                peak_s = peak_x = 0
                for c in cases:
                    y = fp.to_float(fp.run(fp.to_int(c["x"]), c["idx"], c["type"]))
                    worst[c["type"]]["gl"] = max(worst[c["type"]]["gl"], rel(y, c["gl"]))
                    worst[c["type"]]["flt"] = max(worst[c["type"]]["flt"], rel(y, c["flt"]))
                    peak_s, peak_x = max(peak_s, fp.peak_state), max(peak_x, fp.peak_signal)
                ok = all(worst[T]["gl"] <= float_err[T] + 0.1 * EPS for T in types)
                row = {"WS": WS, "WST": fp.WST, "WM": WM, "F": fp.F, "worst": worst, "transparent": ok,
                       "floor_hits": fp.floor_hits, "state_bits_used": float(np.log2(peak_s + 1)),
                       "signal_bits_used": float(np.log2(peak_x + 1))}
                sweep.append(row)
                print(f"[{env}] WS={WS} WST={fp.WST} WM={WM} F={fp.F} | vs GL "
                      + " ".join(f"{T}:{worst[T]['gl']:.1e}" for T in types) + " | vs float "
                      + " ".join(f"{T}:{worst[T]['flt']:.1e}" for T in types)
                      + f" | {'OK' if ok else '--'} | used state 2^{row['state_bits_used']:.1f}/{fp.WST - 1}"
                      f" signal 2^{row['signal_bits_used']:.1f}/{WS - 1} ({time.time() - t0:.0f}s)", flush=True)
        good = [r for r in sweep if r["transparent"]]
        choice = min(good, key=lambda r: (r["WST"] * (r["WM"] + 1), r["WS"])) if good else None
        print(f"[{env}] smallest transparent config: {choice and (choice['WS'], choice['WST'], choice['WM'])}", flush=True)
        res["envelopes"][env] = {"V_frozen": V_frozen, "V_stress": V_stress, "V_max": V, "I": probe.I,
                                 "LOGN": probe.LOGN, "float_err": float_err, "sweep": sweep, "choice": choice}

    # inverse stability under quantization: D-type integral of order 0.95, long run
    ch = res["envelopes"]["ABDE"]["choice"]
    V = res["envelopes"]["ABDE"]["V_max"]
    n_long = 200000
    x_long = np.clip(0.25 * rng.standard_normal(n_long), -0.99, 0.99)
    stab = {}
    for floor in (True, False):
        fp = FixedPointBank(bank, P=P, amax=AMAX, WS=ch["WS"], WM=ch["WM"], n_max=R, V_max=V, dc_floor=floor)
        try:
            y = fp.to_float(fp.run(fp.to_int(x_long), fp.index(np.full(n_long, -0.95)), "D"))
            stab[str(floor)] = {"overflow": None, "rms_first_10k": float(np.sqrt(np.mean(y[:10000] ** 2))),
                                "rms_last_10k": float(np.sqrt(np.mean(y[-10000:] ** 2)))}
        except OverflowError as e:
            stab[str(floor)] = {"overflow": str(e)}
        print(f"long run D(-0.95) at {ch['WS']}/{ch['WST']}/{ch['WM']}, floor={floor}: {stab[str(floor)]}", flush=True)
    res["long_run"] = stab
    with open(os.path.join(OUT, "e5_fixed_point.json"), "w") as f:
        json.dump(res, f, indent=1)
    figure(res)


def figure(res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    env = res["envelopes"]["ABDE"]
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.6), sharey=True)
    colors = {16: "#c6dbef", 18: "#6baed6", 25: "#2171b5", 32: "#08306b"}
    for ax, T in zip(axes, "ABDE"):
        for WM in WM_LIST:
            rows = [r for r in env["sweep"] if r["WM"] == WM]
            ax.semilogy([r["WS"] for r in rows], [r["worst"][T]["gl"] for r in rows], "o-", ms=3,
                        color=colors[WM], label=f"WM = {WM}")
        ax.axhline(env["float_err"][T], color="#d62728", lw=0.9, ls=":", label="float bank")
        ax.axhline(env["float_err"][T] + 0.1 * res["eps"], color="#d62728", lw=0.6, ls="--", label="float + 0.1 eps")
        ax.set_title(f"{T}-type (envelope A/B/D/E)")
        ax.set_xlabel(f"signal word WS (state = WS + {env['LOGN']})")
        ax.grid(True, which="both", alpha=0.3)
    axes[0].set_ylabel("worst rel. RMS error vs GL")
    axes[0].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_e5_wordlength.png"), dpi=150)


if __name__ == "__main__":
    main()
