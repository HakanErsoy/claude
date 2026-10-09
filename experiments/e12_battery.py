"""E12: variable-order identification on measured battery data (Panasonic 18650PF).

Data: P. Kollmeyer, Panasonic 18650PF Li-ion Battery Data, Mendeley Data, v1
(2018), doi:10.17632/wykht8y7tg.1, CC BY 4.0. Fetch with
experiments/fetch_panasonic.py; the data are not part of the repository.

Model (Ts = 1 s, bin means of the logged 10 Hz data), for a whole record:
    y_n = v_n - OCV(z_n) = c(z_n) + R0(z_n) i_n + R1(z_n) psi_tau(i)_n
                           + kappa(z_n) (Delta^{-beta(.)} i)_n
with OCV from the C/20 test at 25 degC, z by coulomb counting, psi_tau a
unit-gain first-order lag and the gains c, R0, R1, kappa piecewise linear in
z (knots every 0.1 over the z range of the training records). The order is
  const    one beta for the record (A = B)
  VO-A     beta_n = beta(z_n), piecewise linear on 6 knots, output schedule
  VO-B     the same path, input schedule (each input sample keeps its order)
Baselines: 1RC and 2RC (one or two lags, constant time constants, same gains).
tau is on a 40-point grid (1 s to 5000 s), beta in 0.02..0.95; the order
knots are found by coordinate search (step 0.05, then 0.01), tau by grid search,
alternately; the gains follow from least squares. The leading rest of each
record (the soak to the chamber temperature) is dropped; all states are zero there.

Validation (leave one cycle out): in each group (one chamber temperature, or
one warming run), the models are fitted jointly to all cycles but one, with
shared gains and order law, and simulate the held-out cycle from its current
alone, every parameter, the order included, read from its z (clipped to the
training range). The fitted VO models are also run with the operator of the
other type. For comparison, models fitted to a single cycle simulate the
other three; and a fit to all four cycles gives the reported order laws.

Outputs: results/e12_battery.json
"""

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.battery import FOPath, GainFit, hat_basis, ocv_curve, prepare, rc_regressors, trim_rest  # noqa: E402
from vofrac.design import design_dt  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "results")
TS = 1.0
BETAS = np.round(np.arange(0.02, 0.9501, 0.01), 3)
TAUS = np.geomspace(1.0, 5000.0, 40)
PAIRS = [(a, b) for a in range(len(TAUS)) for b in range(a + 1, len(TAUS))]
DZ_GAIN = 0.1
N_BETA_KNOTS = 6
MODELS = ("1RC", "2RC", "RC+FO const", "RC+FO VO-A", "RC+FO VO-B")
CYCLES = {T: ("UDDS", "LA92", "US06", "HWFTa" if T == "25degC" else "HWFET")
          for T in ("25degC", "10degC", "0degC", "n10degC", "n20degC")}
GROUPS = dict({T: [f"{T}_{c}" for c in cs] for T, cs in CYCLES.items()},
              **{"10degC_trise": [f"10degC_trise_Cycle_{k}" for k in range(1, 5)],
                 "n20degC_trise": [f"n20degC_trise_Cycle_{k}" for k in range(1, 5)]})


def make_bank():
    dsg = design_dt(TS, 25000, -0.95, -0.02, 1e-4)
    return dsg, DiscreteFixedPoleBank(TS, dsg["xi_lo"], dsg["xi_hi"], dsg["K"])


def load_record(data, name, ocv):
    return trim_rest(prepare(os.path.join(data, name + "_Pan18650PF.mat"), ocv, TS))


def knots(z, n=None, dz=None):
    lo, hi = float(np.min(z)), float(np.max(z))
    if n is None:
        n = max(2, int(np.ceil((hi - lo) / dz - 1e-9)) + 1)
    return np.linspace(lo, hi, n)


class Rec:
    def __init__(self, d, bank):
        self.d, self.y, self.i, self.z = d, d["y"], d["i"], d["z"]
        self.Psi = rc_regressors(self.i, TAUS, TS)
        self.fo = FOPath(bank, self.i, BETAS)
        self.PhiA = self.fo.columns_A()


class Joint:
    """Several records fitted with shared gains and order law; every record keeps
    its own states (each starts at rest)."""

    def __init__(self, recs):
        self.recs = recs
        self.y = np.concatenate([r.y for r in recs])
        self.i = np.concatenate([r.i for r in recs])
        self.z = np.concatenate([r.z for r in recs])
        self.Psi = np.vstack([r.Psi for r in recs])
        self.PhiA = np.vstack([r.PhiA for r in recs])

    def fo_path(self, kb, bk, vo):
        return np.concatenate([r.fo.run(hat_basis(r.z, kb) @ bk, vo) for r in self.recs])

    def psis(self, P, vo=None):
        out = [self.Psi[:, g] for g in P["g_tau"]]
        if P["model"] == "RC+FO const":
            out.append(self.PhiA[:, P["g_beta"]])
        elif P["model"].startswith("RC+FO"):
            out.append(self.fo_path(np.array(P["beta_knots_z"]), np.array(P["beta_knots"]), vo or P["model"][-1]))
        return out


def _search_order_path(J, gf, gt, beta0, vo):
    """Coordinate search over the order knots and the lag time constant."""
    kb = knots(J.z, n=N_BETA_KNOTS)
    bk = np.full(len(kb), beta0)

    def cost(bk, gt):
        return gf.sse(J.Psi[:, gt], J.fo_path(kb, bk, vo))

    best = cost(bk, gt)
    for sweep in range(6):
        start = best
        for m in range(len(kb)):
            for cand in (BETAS[::5], None):
                if cand is None:          # refine around the current value
                    cand = np.clip(bk[m] + 0.01 * np.arange(-4, 5), BETAS[0], BETAS[-1])
                for b in cand:
                    if b == bk[m]:
                        continue
                    trial = bk.copy(); trial[m] = b
                    c = cost(trial, gt)
                    if c < best:
                        best, bk = c, trial
        fo = J.fo_path(kb, bk, vo)
        sse_t = [gf.sse(J.Psi[:, g], fo) for g in range(len(TAUS))]
        g = int(np.argmin(sse_t))
        if sse_t[g] < best:
            best, gt = sse_t[g], g
        if best > start * (1 - 1e-6):
            break
    return kb, bk, gt, best, sweep + 1


def fit(J, model):
    kg = knots(J.z, dz=DZ_GAIN)
    gf = GainFit(J.y, J.i, hat_basis(J.z, kg))
    P = {"model": model, "gain_knots_z": kg.tolist()}
    if model == "1RC":
        sse = [gf.sse(J.Psi[:, g]) for g in range(len(TAUS))]
        g = int(np.argmin(sse)); P["g_tau"] = [g]; best = sse[g]
    elif model == "2RC":
        sse = [gf.sse(J.Psi[:, a], J.Psi[:, b]) for a, b in PAIRS]
        j = int(np.argmin(sse)); P["g_tau"] = [int(PAIRS[j][0]), int(PAIRS[j][1])]; best = sse[j]
    else:
        # constant order: coarse (tau, beta) grid, then a local refinement
        cand = [(gt, gb) for gt in range(len(TAUS)) for gb in range(0, len(BETAS), 5)]
        sse = [gf.sse(J.Psi[:, gt], J.PhiA[:, gb]) for gt, gb in cand]
        gt, gb = cand[int(np.argmin(sse))]
        cand = [(a, b) for a in range(max(0, gt - 2), min(len(TAUS), gt + 3))
                for b in range(max(0, gb - 4), min(len(BETAS), gb + 5))]
        sse = [gf.sse(J.Psi[:, a], J.PhiA[:, b]) for a, b in cand]
        gt, gb = cand[int(np.argmin(sse))]; best = min(sse)
        if model == "RC+FO const":
            P.update(g_tau=[gt], g_beta=gb, beta=float(BETAS[gb]))
        else:
            kb, bk, gt, best, sweeps = _search_order_path(J, gf, gt, BETAS[gb], model[-1])
            P.update(g_tau=[gt], beta_knots_z=kb.tolist(), beta_knots=bk.tolist(), sweeps=sweeps)
    P["tau"] = [float(TAUS[g]) for g in P["g_tau"]]
    P["coef"] = gf.coef(*J.psis(P)).tolist()
    P["fit_rmse_mV"] = 1e3 * float(np.sqrt(best / len(J.y)))
    return P


def simulate(J, P, vo=None):
    """Model output on records J from the current alone; `vo` overrides the type
    of the order path (to run a model with the operator of the other type)."""
    H = hat_basis(J.z, np.array(P["gain_knots_z"]))
    X = np.column_stack([H, H * J.i[:, None]] + [H * p[:, None] for p in J.psis(P, vo)])
    return X @ np.array(P["coef"])


_W = {}


def _worker_init(data):
    _W["data"] = data
    _W["dsg"], _W["bank"] = make_bank()
    _W["ocv"] = ocv_curve(os.path.join(data, "C20 OCV Test_C20_25dC.mat"))
    _W["recs"] = {}


def _rec(name):
    if name not in _W["recs"]:
        _W["recs"][name] = Rec(load_record(_W["data"], name, _W["ocv"]), _W["bank"])
    return _W["recs"][name]


def _rmse(J, yh):
    return 1e3 * float(np.sqrt(np.mean((J.y - yh) ** 2)))


def _fold(task):
    """Fit all models on the training records and simulate each test record."""
    gname, kind, train, tests = task
    t0 = time.time()
    J = Joint([_rec(n) for n in train])
    fits = {m: fit(J, m) for m in MODELS}
    out = {"group": gname, "kind": kind, "train": train, "fits": fits, "tests": []}
    for te in tests:
        Jt = Joint([_rec(te)])
        out["tests"].append({
            "test": te,
            "rmse_mV": {m: _rmse(Jt, simulate(Jt, fits[m])) for m in MODELS},
            # the same fitted VO models run with the operator of the other type
            "rmse_swapped_mV": {m: _rmse(Jt, simulate(Jt, fits[m], "B" if m.endswith("A") else "A"))
                                for m in ("RC+FO VO-A", "RC+FO VO-B")}})
    out["seconds"] = time.time() - t0
    return out


def _summary(runs):
    """runs: list of (fits on the training records, results on one test record)."""
    s = {m: {"train_mean": float(np.mean([f[m]["fit_rmse_mV"] for f, _ in runs])),
             "test_mean": float(np.mean([t["rmse_mV"][m] for _, t in runs])),
             "test_wins": int(sum(min(t["rmse_mV"], key=t["rmse_mV"].get) == m for _, t in runs))}
         for m in MODELS}
    for m in ("RC+FO VO-A", "RC+FO VO-B"):
        s[m]["test_swapped_mean"] = float(np.mean([t["rmse_swapped_mV"][m] for _, t in runs]))
    return s


def main():
    data = sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
        "VOFRAC_DATA", os.path.expanduser("~/.cache/vofrac/panasonic18650pf"))
    t0 = time.time()
    _worker_init(data)
    res = {"source": "Panasonic 18650PF, doi:10.17632/wykht8y7tg.1 (CC BY 4.0)", "Ts": TS,
           "design": _W["dsg"], "records": {}, "groups": {}}
    tasks = []
    for gname, members in GROUPS.items():
        members = [n for n in members if os.path.exists(os.path.join(data, n + "_Pan18650PF.mat"))]
        res["groups"][gname] = {"members": members, "folds": [], "single": []}
        tasks.append((gname, "all", members, []))                    # all cycles: the reported order law
        tasks += [(gname, "loco", [n for n in members if n != te], [te]) for te in members]
        tasks += [(gname, "single", [tr], [n for n in members if n != tr]) for tr in members]
        for n in members:
            d = load_record(data, n, _W["ocv"])
            res["records"][n] = {"n": len(d["y"]), "T_range": [float(np.nanmin(d["T"])), float(np.nanmax(d["T"]))],
                                 "z_range": [float(d["z"].min()), float(d["z"].max())]}
    with ProcessPoolExecutor(max_workers=min(4, os.cpu_count() or 1), initializer=_worker_init,
                             initargs=(data,)) as ex:
        for out in ex.map(_fold, tasks):
            g = res["groups"][out["group"]]
            fits = out["fits"]
            if out["kind"] == "all":
                g["all"] = fits
                print(f"{out['group']:14s} all cycles, fit mV: "
                      + " ".join(f"{m} {fits[m]['fit_rmse_mV']:.2f}" for m in MODELS)
                      + f" | tau {[fits[m]['tau'] for m in MODELS]}"
                      + f" | beta const {fits['RC+FO const']['beta']:.2f}"
                      + f" A {np.round(fits['RC+FO VO-A']['beta_knots'], 2).tolist()}"
                      + f" B {np.round(fits['RC+FO VO-B']['beta_knots'], 2).tolist()} ({out['seconds']:.0f} s)",
                      flush=True)
                continue
            g["folds" if out["kind"] == "loco" else "single"].append(out)
            for t in out["tests"]:
                print(f"{out['group']:14s} {out['kind']:6s} test {t['test']:22s} mV: "
                      + " ".join(f"{m} {v:.1f}" for m, v in t["rmse_mV"].items())
                      + " | swapped " + " ".join(f"{m} {v:.1f}" for m, v in t["rmse_swapped_mV"].items()), flush=True)
    for gname, g in res["groups"].items():
        for key, label in (("folds", "leave one out"), ("single", "single cycle")):
            runs = [(o["fits"], t) for o in g[key] for t in o["tests"]]
            s = _summary(runs)
            g["summary" if key == "folds" else "summary_single"] = s
            print(f"{gname:14s} {label:13s} train / test mean (wins of {len(runs)}): "
                  + " | ".join(f"{m} {v['train_mean']:.1f}/{v['test_mean']:.1f} ({v['test_wins']})" for m, v in s.items())
                  + " | swapped A->B {:.1f}, B->A {:.1f}".format(s["RC+FO VO-A"]["test_swapped_mean"],
                                                               s["RC+FO VO-B"]["test_swapped_mean"]), flush=True)
    res["seconds"] = time.time() - t0
    with open(os.path.join(OUT, "e12_battery.json"), "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
