"""Operator-level error of a realized VO operator (dense matrices, small n).

For an order sequence alpha_0..alpha_{n-1} the A- and B-type operators are
lower-triangular matrices whose entries are kernel values at the lag n - j,
taken at the output order (A) or at the input order (B):

    [W_A]_{n,j} = k_{alpha_n}(n - j),     [W_B]_{n,j} = k_{alpha_j}(n - j).

With an error kernel e_a(r) = k^_a(r) - k_a(r) (e_a(0) = 0), every row of
E_A = W^_A - W_A holds one order and every column of E_B holds one order.
The Schur constants over a set S of orders

    rho_row(S) = max_{a in S} sum_{r=1}^{n-1} |e_a(r)|
    rho_col(S) = sum_{r=1}^{n-1} max_{a in S} |e_a(r)|

therefore bound ||E_A||_inf, ||E_B||_1 (rho_row) and ||E_A||_1, ||E_B||_inf
(rho_col) for every order sequence with values in S, and ||E||_2 by their
geometric mean.
"""

import numpy as np
from scipy.linalg import solve_triangular

from .reference import _gl_weights


def gl_table(orders, n, Ts):
    """Exact GL weights g_r(a) = Ts^-a w_r(a), r = 0..n-1, one row per order."""
    return np.array([Ts ** (-a) * _gl_weights(a, n) for a in orders])


def bank_table(bank, orders, n):
    """Realized weights g^_r(a) of a DiscreteFixedPoleBank, one row per order."""
    r = np.arange(1, n)
    P = bank.theta[None, :] ** (r[:, None] - 1)          # (n-1, K)
    out = np.empty((len(orders), n))
    for i, a in enumerate(orders):
        g0, cd, c = bank.coeffs(float(a))
        out[i, 0] = g0
        out[i, 1:] = P @ c
        if n > 1:
            out[i, 1] += cd
    return out


def operator_matrix(table, idx, vo_type):
    """Dense W_A or W_B from a weight table and the order index of each sample."""
    n = len(idx)
    lag = np.subtract.outer(np.arange(n), np.arange(n))
    low = lag >= 0
    lag = np.where(low, lag, 0)
    if vo_type == "A":
        W = table[np.asarray(idx)[:, None], lag]
    elif vo_type == "B":
        W = table[np.asarray(idx)[None, :], lag]
    else:
        raise ValueError(vo_type)
    return np.where(low, W, 0.0)


def schur_constants(err_table):
    """(rho_row, rho_col) of an error-kernel table (orders x lags), lag 0 ignored."""
    e = np.abs(err_table[:, 1:])
    return float(e.sum(axis=1).max()), float(e.max(axis=0).sum())


def weight_sums(table):
    """(gamma_row, gamma_col) = (max_a sum_r |k_a(r)|, sum_r max_a |k_a(r)|), r >= 1."""
    return schur_constants(table)


def rel_weight_error(bank_tab, gl_tab):
    """eps_R over the orders in the tables: max |g^_r / g_r - 1|, 1 <= r < n."""
    g = gl_tab[:, 1:]
    e = bank_tab[:, 1:] - g
    nz = g != 0.0
    return float(np.max(np.abs(e[nz] / g[nz]))) if nz.any() else 0.0


def norm(M, p):
    if p == 1:
        return float(np.abs(M).sum(axis=0).max())
    if p == np.inf:
        return float(np.abs(M).sum(axis=1).max())
    if p == 2:
        return float(np.linalg.svd(M, compute_uv=False)[0])
    raise ValueError(p)


def lower_inverse(W):
    return solve_triangular(W, np.eye(W.shape[0]), lower=True)


def gl_partial_abs_sum(a, m):
    """sum_{r=1}^{m} |w_r(a)| in closed form (partial sums of (1-z)^a are (1-z)^(a-1))."""
    from scipy.special import gammaln
    if a == 0:
        return 0.0
    partial = np.exp(gammaln(m + 1 - a) - gammaln(m + 1) - gammaln(1 - a))   # sum_{r=0}^m w_r(a)
    # derivative: w_0 = 1 and w_r < 0 for r >= 1; integral: all w_r > 0
    return float(1.0 - partial) if a > 0 else float(partial - 1.0)
