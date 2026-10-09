"""E12c: the fitted battery models of E12 run by other realizations of the operator.

E12 fits SOC-scheduled RC + fractional-integral models with A- and B-type
order paths on the fixed-pole bank. Here the fitted models (leave one cycle
out, same gains, same order law) simulate the held-out cycle with the
fractional term realized by
  bank        the fixed-pole bank of E12 (the reference)
  GL          the literal GL sum of the model's type, full memory (FFT)
  GL L=60     the same sum truncated to 60 lags (about the bank's multiplications)
  GL L=600    truncated to 600 lags (ten times the bank's cost)
  MP          moving poles: every order level of the 0.01 grid has its own
              rule-designed bank (same eps and R, common K), switched with the
              state kept (hot swap) whenever the level of the order changes;
              output weights for the A-type model, input weights for B
Orders between grid points use linearly interpolated weights (bank, GL) or
the nearest level (MP). The bank with the nearest-level path is also run to
separate the effect of quantizing the path from that of the structure.

Inputs: results/e12_battery.json and the data directory of E12.
Outputs: results/e12c_realizations.json
"""

import json
import os
import sys
import time

import numpy as np
from scipy.signal import fftconvolve

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from e12_battery import BETAS, OUT, TS, GROUPS, Joint, Rec, _worker_init, _W, load_record  # noqa: E402
from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.battery import frac_index, hat_basis  # noqa: E402
from vofrac.design import design_dt  # noqa: E402

R = 25000
EPS = 1e-4
L_SHORT = (60, 600)
VO_MODELS = ("RC+FO VO-A", "RC+FO VO-B")
METHODS = ("bank", "bank, nearest level", "GL", "GL L=60", "GL L=600", "MP")


def gl_table(betas, n):
    """GL weights of the integrals of orders betas (Ts = 1), lags 0..n-1: (G, n)."""
    a = -np.asarray(betas, float)[:, None]
    r = np.arange(1, n)[None, :]
    w = np.ones((len(betas), n))
    w[:, 1:] = np.cumprod((r - 1 - a) / r, axis=1)
    return w


def gl_path(x, beta, vo, W, L=None):
    """Literal GL sum with a sample-wise order (interpolated weights), A- or B-type."""
    n = len(x)
    j, w = frac_index(BETAS, beta)
    Wl = W[:, :n] if L is None else W[:, :L]
    y = np.zeros(n)
    for g in np.unique(np.r_[j, j + 1]):
        lam = np.where(j == g, 1 - w, 0.0) + np.where(j + 1 == g, w, 0.0)
        if vo == "A":
            y += lam * fftconvolve(x, Wl[g])[:n]
        else:
            y += fftconvolve(lam * x, Wl[g])[:n]
    return y


def mp_levels():
    """Per-level rule designs (poles move with the order) on a common state count."""
    designs = [design_dt(TS, R, -float(b), -float(b), EPS) for b in BETAS]
    K = max(d["K"] for d in designs)
    lev = []
    for b, d in zip(BETAS, designs):
        bank = DiscreteFixedPoleBank(TS, d["xi_lo"], d["xi_hi"], K)
        g0, cd, c = bank.coeffs(-float(b))
        lev.append((g0, cd, c, bank.theta))
    return K, lev


def mp_path(x, idx, vo, lev):
    """Hot-swapped moving-pole bank: the state is kept when the level changes."""
    K = len(lev[0][2])
    s = np.zeros(K)
    sd = 0.0
    y = np.empty(len(x))
    for n, (xn, k) in enumerate(zip(x, idx)):
        g0, cd, c, th = lev[k]
        if vo == "A":
            y[n] = g0 * xn + cd * sd + c @ s
            s = th * s + xn
            sd = xn
        else:
            y[n] = g0 * xn + sd + s.sum()
            s = th * s + c * xn
            sd = cd * xn
    return y


def simulate_fo(J, P, fo):
    """Model output with the fractional term replaced by `fo` (the gains are unchanged)."""
    H = hat_basis(J.z, np.array(P["gain_knots_z"]))
    psis = [J.Psi[:, g] for g in P["g_tau"]] + [fo]
    X = np.column_stack([H, H * J.i[:, None]] + [H * p[:, None] for p in psis])
    return X @ np.array(P["coef"])


def main():
    data = sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
        "VOFRAC_DATA", os.path.expanduser("~/.cache/vofrac/panasonic18650pf"))
    t0 = time.time()
    e12 = json.load(open(os.path.join(OUT, "e12_battery.json")))
    _worker_init(data)
    K_mp, lev = mp_levels()
    W = gl_table(BETAS, R)
    res = {"K_bank": _W["dsg"]["K"], "K_moving_poles": K_mp, "R": R, "eps": EPS,
           "cost_mult_per_sample": {"bank": 2 * _W["dsg"]["K"] + 2, "MP": 2 * K_mp + 2,
                                    "GL L=60": 60, "GL L=600": 600, "GL": "n/2 on average"},
           "groups": {}}
    for gname in GROUPS:
        G = e12["groups"][gname]
        runs = []
        for fold in G["folds"]:
            te = fold["tests"][0]["test"]
            rec = Rec(load_record(data, te, _W["ocv"]), _W["bank"])
            J = Joint([rec])
            for m in VO_MODELS:
                P = fold["fits"][m]
                vo = m[-1]
                beta = hat_basis(rec.z, np.array(P["beta_knots_z"])) @ np.array(P["beta_knots"])
                near = np.clip(np.rint((beta - BETAS[0]) / 0.01).astype(int), 0, len(BETAS) - 1)
                fos = {"bank": rec.fo.run(beta, vo),
                       "bank, nearest level": rec.fo.run(BETAS[near], vo),
                       "GL": gl_path(rec.i, beta, vo, W),
                       "GL L=60": gl_path(rec.i, beta, vo, W, 60),
                       "GL L=600": gl_path(rec.i, beta, vo, W, 600),
                       "MP": mp_path(rec.i, near, vo, lev)}
                rmse = {k: 1e3 * float(np.sqrt(np.mean((rec.y - simulate_fo(J, P, f)) ** 2))) for k, f in fos.items()}
                ref = fos["GL"]
                rel = {k: float(np.max(np.abs(f - ref)) / np.max(np.abs(ref))) for k, f in fos.items()}
                runs.append({"test": te, "model": m, "rmse_mV": rmse, "fo_rel_err_vs_GL": rel,
                             "level_switches": int(np.sum(np.diff(near) != 0))})
                print(f"{gname:14s} {te:24s} {m[-4:]} " + " ".join(f"{k} {v:.1f}" for k, v in rmse.items())
                      + f" | switches {runs[-1]['level_switches']}", flush=True)
        summ = {}
        for m in VO_MODELS:
            rr = [r for r in runs if r["model"] == m]
            summ[m] = {k: {"rmse_mean_mV": float(np.mean([r["rmse_mV"][k] for r in rr])),
                           "fo_rel_err_max": float(np.max([r["fo_rel_err_vs_GL"][k] for r in rr]))}
                       for k in METHODS}
        res["groups"][gname] = {"runs": runs, "summary": summ}
        for m in VO_MODELS:
            print(f"{gname:14s} {m}: " + " | ".join(f"{k} {v['rmse_mean_mV']:.1f} (fo err {v['fo_rel_err_max']:.1e})"
                                                     for k, v in summ[m].items()), flush=True)
    allr = [r for g in res["groups"].values() for r in g["runs"]]
    res["overall"] = {}
    for m in VO_MODELS:
        rr = [r for r in allr if r["model"] == m]
        res["overall"][m] = {k: {"rmse_mean_mV": float(np.mean([r["rmse_mV"][k] for r in rr])),
                                 "ratio_to_bank_median": float(np.median([r["rmse_mV"][k] / r["rmse_mV"]["bank"]
                                                                          for r in rr])),
                                 "worse_than_bank": int(sum(r["rmse_mV"][k] > r["rmse_mV"]["bank"] for r in rr)),
                                 "fo_rel_err_max": float(np.max([r["fo_rel_err_vs_GL"][k] for r in rr]))}
                             for k in METHODS}
        print(f"overall {m}: " + " | ".join(
            f"{k} {v['rmse_mean_mV']:.1f} x{v['ratio_to_bank_median']:.2f} worse {v['worse_than_bank']}/{len(rr)}"
            for k, v in res["overall"][m].items()), flush=True)
    res["seconds"] = time.time() - t0
    with open(os.path.join(OUT, "e12c_realizations.json"), "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
