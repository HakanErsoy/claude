"""Fractional operators s^alpha as cascades of first-order sections (Oustaloup), discretized by Tustin.

An operator slot is (kind, gain, alpha):
  "fo"    gain * s^alpha, alpha in [-2, 1]; for alpha < -1 an exact integrator is split off
          and the remainder s^(alpha+1) is approximated;
  "int"   gain / s (exact Tustin integrator);
  "dfilt" gain * s / (s/w_h + 1) (integer derivative with the same high-frequency limit).

Every slot is NSEC sections (s + z_k)/(s + p_k) times a constant, plus an
optional exact integrator in front. Unused sections are identities (z = p).
"""

import numpy as np

W_LO, W_HI = 1e-3, 1e2      # rad/s, approximation band
N_OUST = 5                  # Oustaloup order: 2N+1 sections
NSEC = 2 * N_OUST + 1


def oustaloup(alpha, wb=W_LO, wh=W_HI, N=N_OUST):
    """Zeros, poles (as positive numbers) and gain of the Oustaloup approximation of s^alpha, |alpha| <= 1."""
    k = np.arange(-N, N + 1)
    r = wh / wb
    z = wb * r ** ((k + N + 0.5 * (1 - alpha)) / (2 * N + 1))
    p = wb * r ** ((k + N + 0.5 * (1 + alpha)) / (2 * N + 1))
    return z, p, wh ** alpha


def slot_sections(kind, gain, alpha=0.0):
    """(zeros[NSEC], poles[NSEC], total gain, integrator flag) of one slot."""
    zs = np.ones(NSEC)
    ps = np.ones(NSEC)
    integ = 0
    if kind == "int":
        return zs, ps, gain, 1
    if kind == "dfilt":
        zs[0], ps[0] = 0.0, W_HI
        return zs, ps, gain * W_HI, 0
    if kind != "fo":
        raise ValueError(kind)
    if alpha < -1.0:
        integ, alpha = 1, alpha + 1.0
    if alpha > 1.0 or alpha < -1.0:
        raise ValueError("order out of range")
    z, p, k = oustaloup(alpha)
    return z, p, gain * k, integ


def tustin(z, p, dt):
    """(b0, b1, a1) of y_n = b0 x_n + b1 x_{n-1} - a1 y_{n-1} for (s + z)/(s + p)."""
    c = 2.0 / dt
    d = c + p
    return np.stack([(c + z) / d, (z - c) / d, (p - c) / d], axis=-1)


def freqresp(kind, gain, alpha, w):
    """Continuous-time frequency response of a slot (for tests and figures)."""
    zs, ps, k, integ = slot_sections(kind, gain, alpha)
    s = 1j * np.asarray(w, float)
    h = k * np.prod((s[:, None] + zs) / (s[:, None] + ps), axis=1)
    return h / s if integ else h
