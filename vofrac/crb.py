"""Bayesian Cramer-Rao bounds for tracking a time-varying order (E13).

Model (sample units, Ts = 1, as in E10):

    y_n = (T^{alpha} x)_n + v_n,   v_n ~ N(0, s2),   T in {A, B},
    alpha_{n+1} = alpha_n + w_n,   w_n ~ N(0, q),    alpha_0 ~ N(a0, p0),

with the literal GL weights and a known input x. With Gaussian noise of
known variance, the Fisher information of the order path given the path is
G^T G / s2, where G is the Jacobian of the noise-free output:

    A-type:  dy_n/dalpha_m = [m = n] sum_r w'_r(alpha_n) x_{n-r}
    B-type:  dy_n/dalpha_m = w'_{n-m}(alpha_m) x_m  (m < n; w'_0 = 0)

The Bayesian (Van Trees) information is E[G^T G] / s2 plus the information
of the random-walk prior, the expectation taken over the prior of the path
(and here also over the input); its inverse bounds the mean-square error of
every estimator of the path (Tichavsky et al. 1998 give the recursive form
for filtering). The expectation is estimated by averaging over M Monte Carlo
paths and inputs, which is the same as M measurements per sample with
variance M s2. Two bounds are returned per sample:

    filtering  the bound for alpha_n from y_0..y_n (causal estimators)
    smoothing  the bound for alpha_n from all data

For the A-type the information is diagonal and the filtering bound obeys
J_n = 1/(q + 1/J_{n-1}) + E[h_n^2]/s2. For the B-type the current order is
not seen in y_n (w_0 = 1 for every order), so its information arrives only
later, through the memory.

pcrb() evaluates the same recursion for one Jacobian (M = 1); evaluated at a
single fixed path it is not a bound for that path (the expectation over the
prior is missing) and is kept for checks.
"""

import numpy as np


def gl_weight_derivs(alphas, n):
    """GL weights w_r(a) and dw_r/da for r = 0..n-1, one row per order: (len(alphas), n) each."""
    a = np.asarray(alphas, float)
    W = np.empty((len(a), n))
    D = np.empty((len(a), n))
    W[:, 0], D[:, 0] = 1.0, 0.0
    for r in range(1, n):
        f = (r - 1 - a) / r
        W[:, r] = W[:, r - 1] * f
        D[:, r] = D[:, r - 1] * f - W[:, r - 1] / r
    return W, D


def jacobian(x, alpha, vo_type):
    """dy_n/dalpha_m along the path (dense, lower triangular)."""
    x = np.asarray(x, float)
    n = len(x)
    _, D = gl_weight_derivs(alpha, n)
    G = np.zeros((n, n))
    if vo_type == "A":
        h = np.zeros(n)
        for r in range(1, n):
            h[r:] += D[r:, r] * x[:n - r]
        G[np.arange(n), np.arange(n)] = h
    elif vo_type == "B":
        for m in range(n - 1):
            G[m + 1:, m] = D[m, 1:n - m] * x[m]
    else:
        raise ValueError(vo_type)
    return G


def pcrb(G, s2, q, p0):
    """Filtering and smoothing PCRB of the path from the Jacobian G.

    A covariance-form Kalman recursion on the growing path (alpha_0..alpha_n):
    exact for the linearized model, O(n^3) in total.
    """
    n = G.shape[0]
    S = np.zeros((n, n))
    filt = np.empty(n)
    for k in range(n):
        if k == 0:
            S[0, 0] = p0
        else:                                  # alpha_k = alpha_{k-1} + w
            S[k, :k] = S[k - 1, :k]
            S[:k, k] = S[:k, k - 1]
            S[k, k] = S[k - 1, k - 1] + q
        h = G[k, :k + 1]
        nz = np.flatnonzero(h)
        if nz.size:
            lo = nz[0]                         # entries before the first nonzero do not enter
            v = S[:k + 1, lo:k + 1] @ h[lo:]
            S[:k + 1, :k + 1] -= np.outer(v, v) / (h[lo:] @ v[lo:] + s2)
        filt[k] = S[k, k]
    return filt, np.diag(S).copy()


def pcrb_A_scalar(h, s2, q, p0):
    """Filtering PCRB of the A-type by the scalar recursion (check of pcrb)."""
    J = np.empty(len(h))
    prev = None
    for k, hk in enumerate(h):
        prior = 1.0 / p0 if prev is None else 1.0 / (q + 1.0 / prev)
        J[k] = prior + hk ** 2 / s2
        prev = J[k]
    return 1.0 / J


def gl_derivative_table(grid, n):
    """dw_r/da on an order grid, lags 0..n-1, for interpolation: (len(grid), n)."""
    return gl_weight_derivs(grid, n)[1]


def interp_rows(table, grid, a, r):
    """dw_r/da at orders a (array) and lags r (array), linear in the order between grid points."""
    j = np.clip(np.searchsorted(grid, a, side="right") - 1, 0, len(grid) - 2)
    t = (a - grid[j]) / (grid[j + 1] - grid[j])
    return (1 - t) * table[j, r] + t * table[j + 1, r]


def bcrb_batch(row, n, s2, q, p0):
    """Filtering and smoothing BCRB with Monte Carlo-averaged information.

    row(k) returns the (M, k+1) block of Jacobian rows k of the M Monte Carlo
    runs. Each sample is M measurements with noise variance M*s2 (so that
    their information is the average over runs); a covariance-form Kalman
    recursion on the growing path gives both bounds.
    """
    S = np.zeros((n, n))
    filt = np.empty(n)
    for k in range(n):
        if k == 0:
            S[0, 0] = p0
        else:
            S[k, :k] = S[k - 1, :k]
            S[:k, k] = S[:k, k - 1]
            S[k, k] = S[k - 1, k - 1] + q
        H = row(k)                                   # (M, k+1)
        M = H.shape[0]
        nz = np.flatnonzero(np.any(H != 0, axis=0))
        if nz.size:
            lo = nz[0]
            Hs = H[:, lo:]
            P = S[:k + 1, lo:k + 1] @ Hs.T              # (k+1, M)
            C = Hs @ P[lo:] + M * s2 * np.eye(M)
            S[:k + 1, :k + 1] -= P @ np.linalg.solve(C, P.T)
        filt[k] = S[k, k]
    return filt, np.diag(S).copy()
