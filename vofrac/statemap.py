"""Best-case state maps for switching order-dependent-pole realizations.

When the order switches alpha1 -> alpha2 at sample nT, a single-state-vector
realization can only apply a linear map x+ = Phi x- and continue with the
alpha2 dynamics. With x1 = state of the alpha1 system and x2 = state the
frozen alpha2 system would have under the same input history, the
post-switch deviations from the realization's own frozen-order references
over a window of L samples are

    A-type:  e[k] = C2 Ad2^k (Phi x1 - x2)       (state estimation problem)
    B-type:  e[k] = C1 Ad1^k x1 - C2 Ad2^k Phi x1 (output matching problem)

since all post-switch forced terms cancel. Exact A-type for every input
needs e^{A2 s} B2 = Phi e^{A1 s} B1 for all s, and exact B-type needs
C2 e^{A2 s} Phi = C1 e^{A1 s}; for minimal realizations both force the two
pole sets to coincide. This module fits the least-squares Phi on input
ensembles to measure how much of the definitional error a map can remove.
"""

import numpy as np

from .oustaloup import SwitchedOustaloup, _zoh


def dt_oustaloup(alpha, w_b, w_h, N, form, Ts):
    A, B, C, D = SwitchedOustaloup(w_b, w_h, N, form).ss(alpha)
    Ad, Bd = _zoh(A, B, Ts)
    return Ad, Bd, np.asarray(C, dtype=float), float(D)


def end_states(Ad, Bd, U):
    """States after len(U[0]) steps from rest; U has one input per row."""
    X = np.zeros((Ad.shape[0], U.shape[0]))
    for k in range(U.shape[1]):
        X = Ad @ X + np.outer(Bd, U[:, k])
    return X


def zero_state_output(Ad, Bd, C, D, U):
    X = np.zeros((Ad.shape[0], U.shape[0]))
    Y = np.empty_like(U)
    for k in range(U.shape[1]):
        Y[:, k] = C @ X + D * U[:, k]
        X = Ad @ X + np.outer(Bd, U[:, k])
    return Y


def obsv(Ad, C, L):
    O = np.empty((L, Ad.shape[0]))
    row = np.array(C, dtype=float)
    for k in range(L):
        O[k] = row
        row = row @ Ad
    return O


def pinv_trunc(M, rcond):
    U, s, Vt = np.linalg.svd(M, full_matrices=False)
    keep = s > rcond * s[0]
    return (Vt[keep].T / s[keep]) @ U[:, keep].T


def fit_phi_A(X1, X2, rcond):
    """argmin_Phi sum ||O2 (Phi x1 - x2)||^2; independent of O2 when X1 has full row rank."""
    return X2 @ pinv_trunc(X1, rcond)


def fit_phi_B(O1, O2, X1, rcond):
    """argmin_Phi sum ||(O1 - O2 Phi) x1||^2 = O2^+ O1 (data-weighted, truncated)."""
    T = O1 @ X1
    return pinv_trunc(O2, rcond) @ T @ pinv_trunc(X1, rcond)


def rel_err(E, Y):
    """Ensemble relative RMS: sqrt(sum ||e||^2 / sum ||y||^2)."""
    return float(np.sqrt(np.sum(E ** 2) / np.sum(Y ** 2)))


def input_ensemble(kind, M, n, Ts, rng):
    t = np.arange(n) * Ts
    if kind == "white":
        return rng.standard_normal((M, n))
    if kind == "pwc":
        U = np.empty((M, n))
        for m in range(M):
            k = 0
            while k < n:
                L = 1 + rng.geometric(1.0 / 200.0)
                U[m, k:k + L] = rng.standard_normal()
                k += L
        return U
    if kind == "multisine":
        f = np.geomspace(0.1, 100.0, 12)
        ph = rng.uniform(0, 2 * np.pi, (M, len(f)))
        return np.sin(2 * np.pi * f[None, :, None] * t[None, None, :] + ph[:, :, None]).sum(axis=1) / np.sqrt(6.0)
    if kind == "brown":
        return np.cumsum(rng.standard_normal((M, n)), axis=1) * np.sqrt(Ts)
    if kind == "step":
        return np.ones((M, n))
    raise ValueError(kind)
