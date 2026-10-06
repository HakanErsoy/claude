"""Multifractional Brownian motion (mBm) synthesis with the fixed-pole bank.

Riemann-Liouville mBm (Lim 2001) is the A-type VO integral of white noise
of order a(t) = H(t) + 1/2; the B-type integral of the same order gives the
"order at input time" variant. In sample units (h = 1) the discrete
processes are

    A:  X[n] = sum_r g_r(-a_n) xi[n-r]          g_r(-a) = Gamma(r+a) / (Gamma(a) r!)
    B:  X[n] = sum_j g_{n-j}(-a_j) xi[j]

For H > 1/2 the order exceeds 1. Splitting off one integer integration is
exact in discrete time, but only in the right place:
    A^{-a} xi = A^{-(a-1)} (cumsum xi)      (integrate first)
    B^{-a} xi = cumsum(B^{-(a-1)} xi)       (integrate last)
so one bank of order 1/2 - H, |1/2 - H| < 1/2, covers all of 0 < H < 1 and
crosses H = 1/2 smoothly (order 0 is exact in the bank).
Physical time step D: multiply sample n by D^{H_n} (A) or the input xi_j by
D^{H_j} (B).
"""

import numpy as np
from scipy.special import gammaln


def generate(bank, xi, H, vo_type="A"):
    """xi: (M, n) i.i.d. N(0,1) rows; H: (n,) Hurst function. Returns (M, n)."""
    xi = np.atleast_2d(np.asarray(xi, dtype=float))
    order = 0.5 - np.asarray(H, dtype=float)
    if vo_type == "A":
        return bank.simulate_batch(np.cumsum(xi, axis=1), order, "A")
    if vo_type == "B":
        return np.cumsum(bank.simulate_batch(xi, order, "B"), axis=1)
    raise ValueError(vo_type)


def gl_weights_neg(a, n):
    """g_r(-a) = Gamma(r+a) / (Gamma(a) r!), r = 0..n-1 (any a > 0)."""
    r = np.arange(n)
    return np.exp(gammaln(r + a) - gammaln(a) - gammaln(r + 1.0))


def exact_variance(H, vo_type="A"):
    """Exact variance of the discrete A- or B-type process (O(n^2))."""
    H = np.asarray(H, dtype=float)
    n = len(H)
    a = H + 0.5
    V = np.zeros(n)
    if vo_type == "A":
        for k in range(n):
            V[k] = np.sum(gl_weights_neg(a[k], k + 1) ** 2)
    else:
        for j in range(n):
            V[j:] += gl_weights_neg(a[j], n - j) ** 2
    return V


def local_hurst(X, window, step=None):
    """Quadratic-variation estimate of the local Hurst exponent.

    Second-order increments at dilations 1 and 2, d_j[n] = X[n+2j] - 2X[n+j] + X[n],
    satisfy E d_j^2 ~ j^(2H) for fBm, so H = 0.5 log2(V_2 / V_1) with V_j the
    mean of d_j^2 over a window (Istas-Lang / Coeurjolly type estimator).
    Works row-wise on (M, n); returns window centres and estimates (M, n_w).
    """
    X = np.atleast_2d(X)
    step = step or window // 4
    d1 = X[:, 2:] - 2 * X[:, 1:-1] + X[:, :-2]
    d2 = X[:, 4:] - 2 * X[:, 2:-2] + X[:, :-4]
    m = d2.shape[1]
    starts = np.arange(0, m - window + 1, step)
    c1 = np.concatenate([np.zeros((X.shape[0], 1)), np.cumsum(d1[:, :m] ** 2, axis=1)], axis=1)
    c2 = np.concatenate([np.zeros((X.shape[0], 1)), np.cumsum(d2 ** 2, axis=1)], axis=1)
    V1 = (c1[:, starts + window] - c1[:, starts]) / window
    V2 = (c2[:, starts + window] - c2[:, starts]) / window
    centres = starts + window // 2 + 2
    return centres, 0.5 * np.log2(V2 / V1)
