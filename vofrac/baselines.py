"""Baselines for the cost/accuracy comparison (E8).

All realizations are linear and time-varying for a given order sequence,
so each is compared through its dense operator matrix (opnorm.py).

* Fitted fixed poles: geometric pole grid, residues of every order level
  fitted by a linear program that minimizes the worst relative weight error
  over the lags 1..R-1 (g_0 stays exact). The structure, and hence the
  definition, is that of the rule-designed bank; only the residues differ.
  Optionally the residue signs and DC gains are constrained so that the
  inverse-stability proposition applies.
* Moving poles: every order level has its own rule-designed grid (same
  state count), and an order change keeps the state ("hot swap"). By the
  necessity theorem no state map makes this exact.
* Truncated GL: exact weights up to lag L-1 (short-memory principle).
"""

import numpy as np
from scipy.optimize import linprog

from .bank import DiscreteFixedPoleBank
from .design import design_dt
from .opnorm import gl_table


def lp_lags(R, n_small=200, n_log=400):
    return np.unique(np.concatenate([np.arange(1, min(R, n_small + 1)),
                                     np.geomspace(1, R - 1, n_log).astype(int)]))


def lp_residues(g, theta, lags, signed=False, h_min=0.0):
    """Minimax relative fit of g_r, r in lags, by cd [r = 1] + sum_k c_k theta_k^(r-1).

    Returns (cd, c, t) with t the worst relative error on the fitted lags.
    Columns are scaled to unit maximum for the solver.

    signed=True keeps the hypotheses of the inverse-stability proposition:
    residues of the sign of the GL weights (c_k >= 0, cd >= 0 for integrals;
    c_k <= 0 for derivatives), H(-1) >= g0/100 and, for derivatives,
    H(1) >= h_min. All are linear constraints.
    """
    gr = g[lags]
    w = 1.0 / np.abs(gr)
    A = np.column_stack([theta[None, :] ** (lags[:, None] - 1), (lags == 1).astype(float)]) * w[:, None]
    scale = np.abs(A).max(axis=0)
    scale[scale == 0] = 1.0
    A = A / scale
    s = np.sign(gr)
    m, nv = A.shape
    one = np.ones((m, 1))
    A_ub = np.block([[A, -one], [-A, -one]])
    b_ub = np.concatenate([s, -s])
    cost = np.zeros(nv + 1)
    cost[-1] = 1.0
    bounds = [(None, None)] * nv + [(0, None)]
    if signed:
        g0, derivative = g[0], gr[0] < 0
        rows, rhs = [], []
        # H(-1) = g0 - cd - sum c/(1+theta) >= g0/100
        rows.append(np.append(np.append(1.0 / (1.0 + theta), 1.0) / scale, 0.0))
        rhs.append(0.99 * g0)
        if derivative:
            # H(1) = g0 + cd + sum c/(1-theta) >= h_min
            rows.append(-np.append(np.append(1.0 / (1.0 - theta), 1.0) / scale, 0.0))
            rhs.append(g0 - h_min)
            bounds = [(None, 0.0)] * (nv - 1) + [(None, None), (0, None)]
        else:
            bounds = [(0.0, None)] * nv + [(0, None)]
        A_ub = np.vstack([A_ub, np.array(rows)])
        b_ub = np.concatenate([b_ub, rhs])
    # The problem is badly scaled (theta_k^(r-1) for theta_k near 1), so a solver can stop
    # at a poor vertex; every method is tried and the best solution, verified on the
    # fitted lags, is kept.
    attempts = [("highs-ds", {}), ("highs-ipm", {}), ("highs-ds", {"presolve": False}),
                ("highs-ipm", {"presolve": False})]
    best, msg = None, ""
    for method, opts in attempts:
        res = linprog(cost, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method=method, options=opts)
        msg = res.message
        if res.status != 0:
            continue
        x = res.x[:-1]
        err = float(np.max(np.abs(A @ x - s)))
        if best is None or err < best[0]:
            best = (err, x / scale)
    if best is None:
        raise RuntimeError(msg)
    x = best[1]
    return float(x[-1]), x[:-1], best[0]


def kernel_from(g0, cd, c, theta, R):
    r = np.arange(1, R)
    g = np.empty(R)
    g[0] = g0
    g[1:] = (theta[None, :] ** (r[:, None] - 1)) @ c
    g[1] += cd
    return g


class FittedFixedPole:
    """Fixed geometric poles u_lo..u_hi (u = xi Ts), LP-fitted residues per order level.

    signed=True adds the sign and DC constraints of lp_residues; the DC floor
    is the one of the rule-designed bank, 1 % of S_a g0 u_lo^a / (a (1 + a)).
    """

    def __init__(self, Ts, R, u_lo, u_hi, K, signed=False):
        self.Ts, self.R, self.K, self.signed = Ts, R, K, signed
        self.u_lo = u_lo
        self.theta = np.exp(-np.geomspace(u_lo, u_hi, K))
        self.lags = lp_lags(R)

    def level(self, a):
        g = gl_table([a], self.R, self.Ts)[0]
        if a == 0.0:
            return g[0], 0.0, np.zeros(self.K), self.theta
        h_min = 0.0
        if self.signed and a > 0:
            h_min = 0.01 * np.sin(np.pi * a) / np.pi * g[0] * self.u_lo ** a / (a * (1.0 + a))
        cd, c, _ = lp_residues(g, self.theta, self.lags, signed=self.signed, h_min=h_min)
        return g[0], cd, c, self.theta


def best_fitted(Ts, R, K, probe_orders, u_lo_grid, u_hi_grid, signed=False):
    """Grid search of (u_lo, u_hi) minimizing the worst fitted error over probe orders."""
    best = None
    for u_lo in u_lo_grid:
        for u_hi in u_hi_grid:
            f = FittedFixedPole(Ts, R, u_lo, u_hi, K, signed=signed)
            worst = 0.0
            try:
                for a in probe_orders:
                    g = gl_table([a], R, Ts)[0]
                    worst = max(worst, rel_err_all(kernel_from(*f.level(a), R), g))
            except RuntimeError:          # solver failure on an ill-conditioned grid: skip it
                continue
            if best is None or worst < best[0]:
                best = (worst, u_lo, u_hi)
    return best


def rel_err_all(gh, g):
    nz = g[1:] != 0
    return float(np.max(np.abs(gh[1:][nz] / g[1:][nz] - 1))) if nz.any() else 0.0


def moving_pole_levels(Ts, R, levels, eps):
    """Per-level rule designs on a common state count K = max_a K(a)."""
    designs = {a: design_dt(Ts, R, a if a != 0 else 1e-6, a if a != 0 else 1e-6, eps) for a in levels}
    K = max(d["K"] for d in designs.values())
    out = []
    for a in levels:
        d = designs[a]
        b = DiscreteFixedPoleBank(Ts, d["xi_lo"], d["xi_hi"], K)
        g0, cd, c = b.coeffs(float(a))
        out.append((g0, cd, c, b.theta))
    return K, out


def ltv_matrix(level_coeffs, idx, vo_type):
    """Dense operator of a switched one-pole bank with per-level (g0, cd, c, theta).

    The state is kept on an order change. Column j is the response to an
    impulse at sample j; at sample n the coefficients of level idx[n] are
    used for the output and for the update n -> n+1.
    """
    n = len(idx)
    K = len(level_coeffs[0][2])
    S = np.zeros((K, n))
    dl = np.zeros(n)
    W = np.zeros((n, n))
    for k in range(n):
        g0, cd, c, th = level_coeffs[idx[k]]
        if vo_type == "A":
            W[k] = cd * dl + c @ S
            W[k, k] += g0
            S *= th[:, None]
            S[:, k] += 1.0
            dl = np.zeros(n)
            dl[k] = 1.0
        elif vo_type == "B":
            W[k] = dl + S.sum(axis=0)
            W[k, k] += g0
            S *= th[:, None]
            S[:, k] += c
            dl = np.zeros(n)
            dl[k] = cd
        else:
            raise ValueError(vo_type)
    return W
