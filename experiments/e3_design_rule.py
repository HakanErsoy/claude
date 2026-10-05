"""E3: analytic design rule for fixed-pole banks (no fitted constants).

Part A  term validation: each error term of vofrac.design is isolated by
        making the other two negligible, then predicted vs measured.
Part B  development grid: systematic specs, rule -> bank -> measured error.
Part C  sealed holdout: random specs generated from a fixed seed, written
        with their SHA-256 *before* any evaluation, then evaluated once.
        Pass rate with a one-sided 95% Clopper-Pearson lower bound, the
        achieved/eps ratio, and K_rule / K_min, where K_min is the smallest
        K (same grid endpoints) that still meets eps.

Metrics
  DT: max over 1 <= r < R and 17 orders of |g_r / g_r^GL - 1|
  CT: max over w1 <= w <= w2 and 17 orders of |H / (jw)^alpha - 1|

Outputs: results/e3_terms.json, results/e3_dev.json, results/e3_holdout_specs.json,
         results/e3_holdout.json, results/fig_e3_*.png
"""

import hashlib
import json
import os
import sys

import numpy as np
from scipy.stats import beta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.bank import DiscreteFixedPoleBank, FixedPoleBank  # noqa: E402
from vofrac.design import (ct_error_model, design_ct, design_dt, dt_lower_tail, dt_quadrature,  # noqa: E402
                           dt_upper_tail, measure_ct, measure_dt)

OUT = os.path.join(os.path.dirname(__file__), "..", "results")
TS = 1e-3


def ct_bank(d):
    return FixedPoleBank(d["xi_lo"], d["xi_hi"], d["K"])


def dt_bank(d):
    return DiscreteFixedPoleBank(TS, d["xi_lo"], d["xi_hi"], d["K"])


# ------------------------------------------------------------------ Part A

def terms():
    out = {"dt": [], "ct": []}
    R = 20000
    for a in (-0.9, -0.5, 0.2, 0.7):
        for h in (1.2, 0.9, 0.7, 0.5):          # quadrature only
            u_lo, u_hi = 1e-14 / R, 80.0 / (1 - a)
            K = int(np.ceil(np.log(u_hi / u_lo) / h)) + 1
            b = DiscreteFixedPoleBank(TS, u_lo / TS, u_hi / TS, K)
            out["dt"].append({"term": "quad", "a": a, "h": b.h, "pred": dt_quadrature(a, b.h),
                              "meas": measure_dt(b, R, a, a)})
        for rho in (1e-4, 1e-3, 1e-2, 3e-2):     # lower tail only: R u_lo = rho
            u_lo, u_hi, h = rho / R, 80.0 / (1 - a), 0.35
            K = int(np.ceil(np.log(u_hi / u_lo) / h)) + 1
            b = DiscreteFixedPoleBank(TS, u_lo / TS, u_hi / TS, K)
            out["dt"].append({"term": "lo", "a": a, "rho": rho, "pred": dt_lower_tail(a, u_lo, b.h, R),
                              "meas": measure_dt(b, R, a, a)})
        for u_hi in (1.0, 2.0, 4.0, 8.0):        # upper tail only
            u_lo, h = 1e-14 / R, 0.35
            K = int(np.ceil(np.log(u_hi / u_lo) / h)) + 1
            b = DiscreteFixedPoleBank(TS, u_lo / TS, u_hi / TS, K)
            out["dt"].append({"term": "hi", "a": a, "u_hi": u_hi, "pred": dt_upper_tail(a, u_hi, b.h),
                              "meas": measure_dt(b, R, a, a)})
    w1, w2 = 1.0, 100.0
    for a in (-0.9, -0.5, -0.1, 0.1, 0.5, 0.9):
        for h in (1.2, 0.9, 0.7):
            lo, hi = w1 * 1e-12, w2 * 1e12
            K = int(np.ceil(np.log(hi / lo) / h)) + 1
            b = FixedPoleBank(lo, hi, K)
            out["ct"].append({"term": "quad", "a": a, "h": b.h,
                              "pred": ct_error_model(a, b.h, lo, hi, w1, w2)["quad"], "meas": measure_ct(b, w1, w2, a, a)})
        for rho in (1e-4, 1e-3, 1e-2, 1e-1):
            for side in ("lo", "hi"):
                lo = w1 * (rho if side == "lo" else 1e-14)
                hi = w2 / (rho if side == "hi" else 1e-14)
                h = 0.4
                K = int(np.ceil(np.log(hi / lo) / h)) + 1
                b = FixedPoleBank(lo, hi, K)
                out["ct"].append({"term": side, "a": a, "rho": rho,
                                  "pred": ct_error_model(a, b.h, lo, hi, w1, w2)[side],
                                  "meas": measure_ct(b, w1, w2, a, a)})
    return out


# ------------------------------------------------------------- Part B / C

def k_min(make, measure, d, eps):
    """Smallest K with the rule's grid endpoints that meets eps (bisection)."""
    lo, hi = 2, d["K"]
    if measure(make(dict(d, K=hi))) > eps:
        return None
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if measure(make(dict(d, K=mid))) <= eps:
            hi = mid
        else:
            lo = mid
    return hi


def evaluate(spec):
    if spec["kind"] == "dt":
        d = design_dt(TS, spec["R"], spec["alpha_min"], spec["alpha_max"], spec["eps"])
        measure = lambda b: measure_dt(b, spec["R"], spec["alpha_min"], spec["alpha_max"])
        make = dt_bank
    else:
        d = design_ct(spec["w1"], spec["w2"], spec["alpha_min"], spec["alpha_max"], spec["eps"])
        measure = lambda b: measure_ct(b, spec["w1"], spec["w2"], spec["alpha_min"], spec["alpha_max"])
        make = ct_bank
    err = measure(make(d))
    km = k_min(make, measure, d, spec["eps"]) if err <= spec["eps"] else None
    return dict(spec, K=d["K"], xi_lo=d["xi_lo"], xi_hi=d["xi_hi"], h=d["h"], err=err,
                ratio=err / spec["eps"], passed=bool(err <= spec["eps"]), K_min=km)


def dev_specs():
    specs = []
    for eps in (1e-2, 1e-3, 1e-4, 1e-5):
        for R in (1000, 10000, 100000):
            for rng_ in ((-0.9, 0.9), (0.1, 0.9), (-0.9, -0.1)):
                specs.append({"kind": "dt", "eps": eps, "R": R, "alpha_min": rng_[0], "alpha_max": rng_[1]})
        for dec in (2, 4, 6):
            for rng_ in ((-0.9, 0.9), (0.1, 0.9), (-0.9, -0.1)):
                specs.append({"kind": "ct", "eps": eps, "w1": 1.0, "w2": 10.0 ** dec,
                              "alpha_min": rng_[0], "alpha_max": rng_[1]})
    return specs


def holdout_specs(n_each=200, seed=20261005):
    rng = np.random.default_rng(seed)
    specs = []
    for kind in ("dt", "ct"):
        for _ in range(n_each):
            eps = float(10 ** rng.uniform(-5, -2))
            amin = float(rng.uniform(-0.95, 0.85))
            amax = float(min(0.95, amin + rng.uniform(0.05, 1.8)))
            s = {"kind": kind, "eps": eps, "alpha_min": amin, "alpha_max": amax}
            if kind == "dt":
                s["R"] = int(round(10 ** rng.uniform(2, 5)))
            else:
                w1 = float(10 ** rng.uniform(-3, 3))
                s["w1"], s["w2"] = w1, float(w1 * 10 ** rng.uniform(0.5, 6))
            specs.append(s)
    return specs


def clopper_pearson_lower(k, n, conf=0.95):
    return 0.0 if k == 0 else float(beta.ppf(1 - conf, k, n - k + 1))


def summarize(rows):
    out = {}
    for kind in ("dt", "ct"):
        sel = [r for r in rows if r["kind"] == kind]
        k = sum(r["passed"] for r in sel)
        ratios = np.array([r["ratio"] for r in sel])
        over = np.array([r["K"] / r["K_min"] for r in sel if r["K_min"]])
        out[kind] = {"n": len(sel), "passed": k, "cp95_lower": clopper_pearson_lower(k, len(sel)),
                     "ratio_median": float(np.median(ratios)), "ratio_max": float(ratios.max()),
                     "ratio_p05": float(np.percentile(ratios, 5)),
                     "K_over_Kmin_median": float(np.median(over)), "K_over_Kmin_max": float(over.max()),
                     "K_minus_Kmin_median": float(np.median([r["K"] - r["K_min"] for r in sel if r["K_min"]]))}
    return out


def figures(tm, dev, hold):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    marks = {"quad": ("o", "#1f77b4", "quadrature"), "lo": ("s", "#2ca02c", "low tail"), "hi": ("^", "#d62728", "high tail")}
    for ax, key, title in ((axes[0], "dt", "discrete time (GL weights)"), (axes[1], "ct", "continuous time (freq. resp.)")):
        for term, (m, c, lab) in marks.items():
            pts = [(r["pred"], r["meas"]) for r in tm[key] if r["term"] == term and r["meas"] > 1e-13]
            if pts:
                p = np.array(pts)
                ax.loglog(p[:, 0], p[:, 1], m, color=c, ms=4, label=lab, alpha=0.8)
        lim = [1e-11, 1e-1]
        ax.plot(lim, lim, "k-", lw=0.8)
        ax.plot(lim, [x / 2 for x in lim], "k:", lw=0.8)
        ax.set_xlim(lim)
        ax.set_ylim(lim)
        ax.set_xlabel("predicted (analytic model)")
        ax.set_ylabel("measured")
        ax.set_title(title)
        ax.grid(True, which="both", alpha=0.3)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_e3_terms.png"), dpi=150)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.0))
    for ax, kind in zip(axes, ("dt", "ct")):
        for rows, m, c, lab in ((dev, "o", "#7f7f7f", "development"), (hold, ".", "#1f77b4", "sealed holdout")):
            sel = [r for r in rows if r["kind"] == kind]
            ax.loglog([r["eps"] for r in sel], [r["err"] for r in sel], m, color=c, ms=4, label=lab, alpha=0.8)
        lim = [1e-6, 3e-2]
        ax.plot(lim, lim, "k-", lw=0.8, label="err = eps")
        ax.set_xlim(lim)
        ax.set_xlabel("requested eps")
        ax.set_ylabel("measured worst-case error")
        ax.set_title(f"{kind.upper()} rule")
        ax.grid(True, which="both", alpha=0.3)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_e3_rule.png"), dpi=150)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    tm = terms()
    with open(os.path.join(OUT, "e3_terms.json"), "w") as f:
        json.dump(tm, f, indent=1)
    for key in ("dt", "ct"):
        # below ~1e-10 the measurement hits the double-precision floor
        r = np.array([x["meas"] / x["pred"] for x in tm[key] if x["pred"] > 1e-10])
        print(f"terms {key} (pred > 1e-10, n={len(r)}): meas/pred median {np.median(r):.2f}, "
              f"min {r.min():.2f}, max {r.max():.2f}", flush=True)

    dev = [evaluate(s) for s in dev_specs()]
    with open(os.path.join(OUT, "e3_dev.json"), "w") as f:
        json.dump({"rows": dev, "summary": summarize(dev)}, f, indent=1)
    print("dev:", json.dumps(summarize(dev), indent=1), flush=True)

    # seal the holdout before evaluating it
    specs = holdout_specs()
    blob = json.dumps(specs, sort_keys=True).encode()
    sha = hashlib.sha256(blob).hexdigest()
    with open(os.path.join(OUT, "e3_holdout_specs.json"), "w") as f:
        json.dump({"seed": 20261005, "sha256": sha, "specs": specs}, f, indent=1)
    print("holdout sealed, sha256", sha, flush=True)
    hold = [evaluate(s) for s in specs]
    with open(os.path.join(OUT, "e3_holdout.json"), "w") as f:
        json.dump({"specs_sha256": sha, "rows": hold, "summary": summarize(hold)}, f, indent=1)
    print("holdout:", json.dumps(summarize(hold), indent=1), flush=True)
    figures(tm, dev, hold)
