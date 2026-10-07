"""E7: operator-norm error of the four types (Theorem: operator-norm bound).

For rule-designed banks (R = n = 1000, |alpha| <= 0.95, eps = 1e-3 and
1e-6) and nine order sequences, the realized operators W^_T and the literal
GL operators W_T, T in {A, B, D, E}, are formed as dense matrices and

  * ||W^_T - W_T||_p, p = 1, 2, inf, is compared with the bounds of the
    theorem: Schur constants rho_row / rho_col of the error kernel over the
    orders that occur (A, B), and the perturbation bound q / (1 - q) with
    q = ||W_D|| * bound(||E(-alpha)||) (D, E);
  * the relative error ||E_T||_p / ||W_T||_p is compared with eps_R
    (A, B, p = 1, inf: ||E|| <= eps_R ||W|| for every order sequence);
  * for integral-only sequences the a-posteriori certificate of the D- and
    E-types is evaluated from one O(nK) step response of the bank and
    checked against the dense error.

The hypothesis g^_1 < 0 of the nonnegativity statement is checked on the
derivative orders of the 200 discrete-time holdout designs of E3.

Two sequences are adversarial: the order at each sample maximizes the error
kernel at that lag, which attains rho_col exactly (column 0 of E_A, last
row of E_B). A constant sequence at the order maximizing the row sum
attains rho_row (last row of E_A).

Outputs: results/e7_operator_norm.json
"""

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.design import design_dt  # noqa: E402
from vofrac.opnorm import (bank_table, gl_table, lower_inverse, norm, operator_matrix,  # noqa: E402
                           rel_weight_error, schur_constants)

OUT = os.path.join(os.path.dirname(__file__), "..", "results")
TS = 1e-3
N = 1000
AMAX = 0.95
EPS = (1e-3, 1e-6)
PS = (1, 2, np.inf)
PKEY = {1: "1", 2: "2", np.inf: "inf"}


def grid():
    a = np.linspace(-AMAX, AMAX, 381)
    return a[np.abs(a) > 1e-9]


def sequences(bank, rng):
    n = np.arange(N)
    g = grid()
    err = bank_table(bank, g, N) - gl_table(g, N, TS)
    worst_lag = np.abs(err).argmax(axis=0)                 # order index maximizing |e_a(r)| per lag
    adv = g[worst_lag]
    adv[0] = g[0]
    a_row = g[np.abs(err[:, 1:]).sum(axis=1).argmax()]
    return {
        "constant +0.5": np.full(N, 0.5),
        "constant -0.5": np.full(N, -0.5),
        "constant a_row*": np.full(N, a_row),
        "switch +0.3->+0.8": np.where(n < N // 2, 0.3, 0.8),
        "switch -0.3->-0.8": np.where(n < N // 2, -0.3, -0.8),
        "switch -0.5->+0.5": np.where(n < N // 2, -0.5, 0.5),
        "random piecewise": np.repeat(rng.uniform(-AMAX, AMAX, 20), N // 20 + 1)[:N],
        "iid uniform": rng.uniform(-AMAX, AMAX, N),
        "smooth crossing": 0.6 * np.sin(2 * np.pi * n / N),
        "adversarial A": adv,
        "adversarial B": adv[::-1].copy(),
    }


def tables(bank, al):
    orders, idx = np.unique(al, return_inverse=True)
    return orders, idx, bank_table(bank, orders, N), gl_table(orders, N, TS)


def forward(bank, al):
    orders, idx, Bt, Gt = tables(bank, al)
    rho_row, rho_col = schur_constants(Bt - Gt)
    eps_R = rel_weight_error(Bt, Gt)
    out, mats = {}, {}
    for T in "AB":
        Wh, W = operator_matrix(Bt, idx, T), operator_matrix(Gt, idx, T)
        E = Wh - W
        bnd = {1: rho_col if T == "A" else rho_row, np.inf: rho_row if T == "A" else rho_col}
        bnd[2] = np.sqrt(rho_row * rho_col)
        rec = {}
        for p in PS:
            e, w = norm(E, p), norm(W, p)
            rec[PKEY[p]] = {"err": e, "bound": float(bnd[p]), "ratio": e / bnd[p], "rel": e / w,
                            "rel_bound": eps_R if p != 2 else eps_R * norm(np.abs(W), 2) / w}
        out[T] = rec
        mats[T] = (Wh, W)
    return {"eps_R": eps_R, "rho_row": rho_row, "rho_col": rho_col, "n_orders": len(orders)}, out, mats


def recursive(bank, al, fwd_neg):
    """D/E from the forward matrices at -alpha (fwd_neg = (info, out, mats) of forward(bank, -al))."""
    info, _, mats = fwd_neg
    out = {}
    for T, F in (("D", "A"), ("E", "B")):
        Wh_f, W_f = mats[F]
        Wh, W = lower_inverse(Wh_f), lower_inverse(W_f)
        E = Wh - W
        rec = {}
        for p in PS:
            # bound on ||E_F(-alpha)||_p from the Schur constants
            if p == 2:
                bF = np.sqrt(info["rho_row"] * info["rho_col"])
            else:
                row_side = (F == "A") == (p == np.inf)
                bF = info["rho_row"] if row_side else info["rho_col"]
            wn, wf = norm(W, p), norm(W_f, p)
            q = wn * bF
            bound = wn * q / (1 - q) if q < 1 else np.inf
            e = norm(E, p)
            rec[PKEY[p]] = {"err": e, "bound": float(bound), "ratio": e / bound, "rel": e / wn,
                            "q": float(q), "kappa": wn * wf}
        out[T] = rec
    return out


def certificate(bank, al, info_neg):
    """A-posteriori bound for integral-only sequences: one step response per type."""
    out = {}
    for T, rho in (("D", info_neg["rho_row"]), ("E", info_neg["rho_col"])):
        s = bank.simulate_type(np.ones(N), al, T)
        nh = float(np.max(np.abs(s)))
        q = nh * rho
        out[T] = {"norm_hat_inf": nh, "q_hat": q, "cert_inf": nh * q / (1 - q) if q < 1 else np.inf}
    return out


def holdout_g1():
    """Sign of the realized first derivative weight g^_1 (hypothesis of part (c)) on the E3 holdout."""
    with open(os.path.join(OUT, "e3_holdout_specs.json")) as f:
        specs = [s for s in json.load(f)["specs"] if s["kind"] == "dt"]
    worst, checked = -np.inf, 0
    for s in specs:
        if s["alpha_max"] <= 0:
            continue
        d = design_dt(TS, s["R"], s["alpha_min"], s["alpha_max"], s["eps"])
        b = DiscreteFixedPoleBank(TS, d["xi_lo"], d["xi_hi"], d["K"])
        for a in np.linspace(max(s["alpha_min"], 0.0), s["alpha_max"], 25):
            if a <= 0:
                continue
            g0, cd, c = b.coeffs(float(a))
            worst = max(worst, float((cd + c.sum()) / g0))
            checked += 1
    print(f"holdout: max g^_1 / g_0 over {checked} derivative orders = {worst:.3f} (must be < 0)", flush=True)
    return {"designs": len(specs), "orders_checked": checked, "max_g1_over_g0": worst}


def main():
    rng = np.random.default_rng(7)
    res = {"Ts": TS, "n": N, "alpha_max": AMAX, "designs": [], "holdout_g1": holdout_g1()}
    for eps in EPS:
        t0 = time.time()
        d = design_dt(TS, N, -AMAX, AMAX, eps)
        bank = DiscreteFixedPoleBank(TS, d["xi_lo"], d["xi_hi"], d["K"])
        g = grid()
        Bg, Gg = bank_table(bank, g, N), gl_table(g, N, TS)
        rr, rc = schur_constants(Bg - Gg)
        gr, gc = schur_constants(Gg)
        des = {"eps": eps, "design": d, "range": {"eps_R": rel_weight_error(Bg, Gg), "rho_row": rr, "rho_col": rc,
                                                  "gamma_row": gr, "gamma_col": gc, "n_orders": len(g)},
               "rows": []}
        print(f"eps={eps:.0e} K={d['K']}: range eps_R={des['range']['eps_R']:.2e} rho_row={rr:.3e} "
              f"rho_col={rc:.3e} (eps_R*gamma: {des['range']['eps_R'] * gr:.3e}, {des['range']['eps_R'] * gc:.3e})",
              flush=True)
        x = rng.standard_normal(N)
        for name, al in sequences(bank, rng).items():
            info, fwd, mats = forward(bank, al)
            neg = forward(bank, -al)
            row = {"sequence": name, **info, "A": fwd["A"], "B": fwd["B"], **recursive(bank, al, neg)}
            row["sim_vs_matrix"] = max(
                float(np.max(np.abs(bank.simulate_type(x, al, T) - mats[T][0] @ x)) / np.max(np.abs(mats[T][0] @ x)))
                for T in "AB")
            if np.all(al < 0):
                row["certificate"] = certificate(bank, al, neg[0])
                for T in "DE":
                    row["certificate"][T]["err_inf"] = row[T]["inf"]["err"]
            des["rows"].append(row)
            msg = " ".join(f"{T}:{max(row[T][k]['ratio'] for k in row[T]):.2f}" for T in "ABDE")
            rel = " ".join(f"{T}:{row[T]['inf']['rel']:.1e}" for T in "ABDE")
            extra = ""
            if "certificate" in row:
                c = row["certificate"]
                extra = f" | cert D {c['D']['err_inf']:.1e}<={c['D']['cert_inf']:.1e} E {c['E']['err_inf']:.1e}<={c['E']['cert_inf']:.1e}"
            print(f"  {name:18s} eps_R={info['eps_R']:.1e} max err/bound {msg} | rel inf {rel}{extra}", flush=True)
        des["seconds"] = time.time() - t0
        res["designs"].append(des)
    with open(os.path.join(OUT, "e7_operator_norm.json"), "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
