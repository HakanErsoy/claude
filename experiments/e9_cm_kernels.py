"""E9: completely monotone kernel families (Theorem: fixed-node banks for CM families).

Part 1  Strip constant of the GL family. For f_{a,r}(x) = e^x m_a(e^x)
        e^{-(r-1) e^x}, m_a(u) = e^{-(1-a)u} (1 - e^{-u})^a, the ratio
        L_d = sup_{a,r} int |f_{a,r}(x + i d)| dx / int f_{a,r}(x) dx is
        evaluated for strip half-widths d < pi/2. The general quadrature
        bound 2 L_d / (e^{2 pi d/h} - 1), minimized over d, is compared with
        the measured worst relative error of the infinite trapezoidal rule
        (eight grid offsets) and with the sharper GL estimate E_q.
Part 2  Bank size. K from the rule for R = 1e2..1e6 and eps = 1e-2..1e-8,
        least-squares fit K = c0 + c1 ln(1/eps) + c2 ln R + c3 ln(1/eps) ln(R/eps);
        the theorem predicts c3 -> 1/pi^2 for the GL family (d -> pi/2).
Part 3  Time-varying distributed order. The order density at sample n is
        uniform on [c_n - 0.15, c_n + 0.15]; the kernel is its average of
        GL kernels (16-point Gauss-Legendre in the order). The same bank,
        with the averaged residues, is run in both schedules and compared
        with the dense A- and B-type operators of the averaged kernel.
Part 4  Fixed tempering: k_a(r) = e^{-lambda r} g_r(a) is realized with the
        poles e^{-lambda} theta_k and the same relative error.

Outputs: results/e9_cm_kernels.json
"""

import json
import os
import sys

import numpy as np
from scipy.special import betaln

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac import cm  # noqa: E402
from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.baselines import kernel_from  # noqa: E402
from vofrac.design import design_dt, dt_quadrature  # noqa: E402
from vofrac.opnorm import bank_table, gl_table, norm, operator_matrix, rel_weight_error  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "results")
TS = 1e-3
A_GRID = np.round(np.linspace(-0.95, 0.95, 13), 10)
R_GRID = (1, 2, 3, 5, 10, 30, 100, 1000, 10 ** 4, 10 ** 5)


def one_minus_exp(u):
    """1 - e^-u for complex u, accurate for small |u|."""
    small = np.abs(u) < 1e-4
    out = np.where(small, u * (1.0 - u / 2.0 + u * u / 6.0), 1.0 - np.exp(-np.where(small, 1.0, u)))
    return out


def f_abs(x, y, a, r):
    z = x + 1j * y
    u = np.exp(z)
    val = u * np.exp(-(1.0 - a) * u) * one_minus_exp(u) ** a * np.exp(-(r - 1) * u)
    return np.abs(val)


def log_beta_exact(p, q):
    """ln B(p, q) to full double precision (scipy's betaln cancels for large p)."""
    import mpmath
    mpmath.mp.dps = 30
    return float(mpmath.log(mpmath.beta(mpmath.mpf(p), mpmath.mpf(q))))


def strip_ratio(a, r, y, dx=0.01):
    """int |f(x + i y)| dx / B(r - a, 1 + a) by a fine trapezoid on a truncated line."""
    c = np.cos(y)
    x_lo = max(-40.0 / (1.0 + a) - 8.0, -690.0)        # e^x > 1e-300; the cut tail is < 1e-13
    x_hi = np.log(60.0 / (((r - 1) + (1.0 - a)) * c))
    x = np.arange(x_lo, x_hi, dx)
    return float(dx * f_abs(x, y, a, r).sum() / np.exp(betaln(r - a, 1.0 + a)))


def part1():
    ds = (0.6, 0.8, 1.0, 1.2, 1.3, 1.4, 1.45, 1.5, 1.53)
    L = {}
    for d in ds:
        L[d] = max(strip_ratio(a, r, d) for a in A_GRID for r in R_GRID)
        print(f"P1 d={d:.2f} L_d={L[d]:.3e}", flush=True)
    rows = []
    for h in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0):
        gen = min(2 * L[d] / np.expm1(2 * np.pi * d / h) for d in ds)
        meas = 0.0
        for a in A_GRID:
            if a == 0:
                continue
            for r in R_GRID:
                logB = log_beta_exact(r - a, 1.0 + a)
                x_lo = max(-45.0 / (1.0 + a) - 8.0, -690.0)
                x_hi = np.log(800.0 / (r - a))
                for off in np.arange(8) * h / 8:
                    x = off + h * np.arange(np.floor(x_lo / h), np.ceil(x_hi / h) + 1)
                    u = np.exp(x)
                    T = h * np.sum(u * np.exp(-(r - a) * u) * (-np.expm1(-u)) ** a)
                    err = abs(np.exp(np.log(T) - logB) - 1.0)
                    if err > meas:
                        meas, where = err, (float(a), int(r), float(off))
        sharp = max(dt_quadrature(a, h) for a in A_GRID if a != 0)
        rows.append({"h": h, "measured": meas, "at": where, "gl_estimate": sharp, "general_bound": gen})
        print(f"P1 h={h:.2f} measured={meas:.2e} at {where} GL estimate={sharp:.2e} general bound={gen:.2e}",
              flush=True)
    return {"L_d": {str(k): v for k, v in L.items()}, "rows": rows}


def part2():
    rows = []
    beta_min = 1.0 - 0.95
    for R in (10 ** 2, 10 ** 3, 10 ** 4, 10 ** 5, 10 ** 6):
        for eps in (1e-2, 1e-3, 1e-4, 1e-5, 1e-6, 1e-7, 1e-8):
            K = design_dt(TS, R, -0.95, 0.95, eps)["K"]
            lead = np.log(1 / eps) * (np.log(R) + np.log(1 / eps) / (1 + beta_min)) / np.pi ** 2
            rows.append({"R": R, "eps": eps, "K": K, "lead": float(lead), "ratio": K / lead})
    K = np.array([r["K"] for r in rows], dtype=float)
    le = np.log(1 / np.array([r["eps"] for r in rows]))
    lR = np.log(np.array([r["R"] for r in rows], dtype=float))
    X = np.column_stack([np.ones_like(K), le, lR, le * (lR + le)])
    coef = np.linalg.lstsq(X, K, rcond=None)[0]
    resid = float(np.max(np.abs(X @ coef - K)))
    print(f"P2 K = {coef[0]:.2f} + {coef[1]:.3f} ln(1/eps) + {coef[2]:.3f} ln R + {coef[3]:.4f} ln(1/eps) ln(R/eps)"
          f" (1/pi^2 = {1 / np.pi ** 2:.4f}); max |residual| {resid:.2f} over {len(rows)} designs", flush=True)
    return {"rows": rows, "fit": {"coef": coef.tolist(), "max_abs_residual": resid,
                                  "terms": ["1", "ln(1/eps)", "ln R", "ln(1/eps) ln(R/eps)"]}}


def part3(rng):
    n = 1000
    d = design_dt(TS, n, -0.95, 0.95, 1e-5)
    bank = DiscreteFixedPoleBank(TS, d["xi_lo"], d["xi_hi"], d["K"])
    xg, wg = np.polynomial.legendre.leggauss(16)
    out = {"design": d, "cases": []}
    for name, centre in (("derivative", 0.45 + 0.3 * np.sin(2 * np.pi * np.arange(n) / n)),
                         ("integral", -0.45 - 0.3 * np.sin(2 * np.pi * np.arange(n) / n)),
                         ("switched", np.where(np.arange(n) < n // 2, -0.5, 0.5))):
        nodes = centre[:, None] + 0.15 * xg[None, :]           # (n, 16) orders
        w = 0.5 * wg                                           # uniform density, unit mass
        orders, inv = np.unique(nodes.ravel(), return_inverse=True)
        Bt, Gt = bank_table(bank, orders, n), gl_table(orders, n, TS)
        inv = inv.reshape(nodes.shape)
        Kh = np.einsum("q,nqr->nr", w, Bt[inv])                # averaged realized kernel per sample
        Kx = np.einsum("q,nqr->nr", w, Gt[inv])                # averaged exact kernel per sample
        idx = np.arange(n)
        rec = {"case": name, "kernel_rel_err": rel_weight_error(Kh, Kx),
               "member_eps_R": rel_weight_error(Bt, Gt)}
        x = rng.standard_normal(n)
        coeffs = [cm.mixture_coeffs(bank, nodes[k], w) for k in range(n)]
        for T, sched in (("A", "output"), ("B", "input")):
            Wh, W = operator_matrix(Kh, idx, T), operator_matrix(Kx, idx, T)
            rec[T] = {"op_rel_inf": norm(Wh - W, np.inf) / norm(W, np.inf)}
            # streaming: per-sample averaged residues on the fixed poles
            y = cm.run(bank.theta, coeffs, x, sched)
            rec[T]["stream_vs_matrix"] = float(np.max(np.abs(y - Wh @ x)) / np.max(np.abs(Wh @ x)))
        out["cases"].append(rec)
        print(f"P3 {name:10s} kernel rel err {rec['kernel_rel_err']:.1e} (members {rec['member_eps_R']:.1e}) "
              f"op rel A/B {rec['A']['op_rel_inf']:.1e}/{rec['B']['op_rel_inf']:.1e} "
              f"stream {rec['A']['stream_vs_matrix']:.0e}/{rec['B']['stream_vs_matrix']:.0e}", flush=True)
    return out


def part4():
    n = 1000
    d = design_dt(TS, n, -0.95, 0.95, 1e-5)
    bank = DiscreteFixedPoleBank(TS, d["xi_lo"], d["xi_hi"], d["K"])
    lam = 0.01
    a_grid = A_GRID[A_GRID != 0]
    Bt, Gt = bank_table(bank, a_grid, n), gl_table(a_grid, n, TS)
    damp = np.exp(-lam * np.arange(n))
    # tempered bank: poles e^-lam theta_k, residues e^-lam c_k, delay residue e^-lam c_d
    Tt = []
    for a in a_grid:
        th, co = cm.tempered(bank, a, lam)
        Tt.append(kernel_from(*co, th, n))
    Tt = np.array(Tt)
    e_plain = rel_weight_error(Bt, Gt)
    e_temp = rel_weight_error(Tt, Gt * damp[None, :])
    print(f"P4 tempered (lambda={lam}) eps_R {e_temp:.3e} vs untempered {e_plain:.3e}", flush=True)
    return {"lambda": lam, "eps_R_tempered": e_temp, "eps_R_plain": e_plain}


def main():
    rng = np.random.default_rng(9)
    res = {"part1": part1(), "part2": part2(), "part3": part3(rng), "part4": part4()}
    with open(os.path.join(OUT, "e9_cm_kernels.json"), "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
