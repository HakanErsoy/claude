"""Stability margins of the linearized per-DOF loops (exact fractional frequency responses).

Linearization about hover: y'' + c1 y' + c0 y = H(s) a, c1 = D_lin / M,
c0 = z_b B / M for roll and pitch (restoring), 0 otherwise, and
H(s) = exp(-T_d s) / (tau_m s + 1) with T_d = (delay + 1/2) dt (transport
delay of the simulator plus the zero-order hold). Broken at the acceleration
demand a:

    cascade:      L(s) = G2(s) (G1(s) + s) P(s),      single loop:  L(s) = G1(s) P(s),

P = H / (s^2 + c1 s + c0). The fractional terms are evaluated either as the
Oustaloup approximation that the simulator implements (default) or as the exact
(j w)^alpha. The phase margin is the smallest distance of the phase from
-180 deg over all gain crossovers below W[-1] = 300 rad/s (the Nyquist frequency
is 314 rad/s); a loop with |L| > 1 at W[-1] has its crossover out of reach of
the sampled controller and gets PM = -180 deg. The delay margin is the
smallest PM_i / w_i over the crossovers with PM_i > 0.
"""

import numpy as np

from . import params, thruster
from .fractional import W_HI, freqresp

W = np.logspace(-2, np.log10(300.0), 2400)       # rad/s, below the Nyquist frequency at dt = 10 ms
W_FAST = np.logspace(-2, np.log10(300.0), 800)   # grid used inside the optimization


def plant_coeffs(v=params.VEHICLE):
    M = params.mass_diag(v)
    k = abs(v["rb"][2]) * params.RHO * params.G * v["volume"]
    return np.array([0, 0, 0, k, k, 0]) / M, np.array(v["lin"]) / M


def _slot(kind, gain, alpha, s, exact=False):
    if not exact:
        return freqresp(kind, gain, alpha, s.imag)
    if kind == "int":
        return gain / s
    if kind == "dfilt":
        return gain * s / (s / W_HI + 1)
    w = s.imag
    return gain * np.exp(alpha * np.log(w)) * complex(np.cos(0.5 * np.pi * alpha), np.sin(0.5 * np.pi * alpha))


def loop(struct, xg, d, dt, delay, tau_m=thruster.TAU_MOTOR, w=W, exact=False):
    """L(j w) of DOF d for one group's parameter vector xg."""
    c0, c1 = plant_coeffs()
    s = 1j * w
    kp1, kp2, slots = struct.group(xg)
    G1 = kp1 + sum(_slot(k, g, a, s, exact) for st, k, g, a in slots if st == 0)
    P = np.exp(-(delay + 0.5) * dt * s) / (tau_m * s + 1) / (s * s + c1[d] * s + c0[d])
    if struct.cascade:
        G2 = kp2 + sum(_slot(k, g, a, s, exact) for st, k, g, a in slots if st == 1)
        return G2 * (G1 + s) * P
    return G1 * P


def margins(L, w=W):
    """(phase margin [deg], crossover [rad/s], delay margin [s]); PM = +inf without a crossover."""
    mag = np.abs(L)
    if mag[-1] > 1.0:
        return -180.0, float(w[-1]), 0.0
    ph = np.degrees(np.unwrap(np.angle(L)))
    idx = np.nonzero(np.diff(np.sign(mag - 1.0)))[0]
    if idx.size == 0:
        return np.inf, np.nan, np.inf
    # interpolate the crossing in log |L|
    lm = np.log(mag)
    f = lm[idx] / (lm[idx] - lm[idx + 1])
    wc = w[idx] * (w[idx + 1] / w[idx]) ** f
    phc = ph[idx] + f * (ph[idx + 1] - ph[idx])
    pm = (phc + 360.0) % 360.0 - 180.0
    i = int(np.argmin(pm))
    pos = pm > 0
    dm = float(np.min(np.radians(pm[pos]) / wc[pos])) if pos.any() else 0.0
    return float(pm[i]), float(wc[i]), dm


def phase_margins(struct, X, dt, delay, tau_m=thruster.TAU_MOTOR, w=W_FAST):
    """Phase margins [P, 6] for a batch of parameter vectors (stage responses computed once per group)."""
    X = np.atleast_2d(X)
    half = len(struct.names)
    c0, c1 = plant_coeffs()
    s = 1j * w
    H = np.exp(-(delay + 0.5) * dt * s) / (tau_m * s + 1)
    out = np.zeros((X.shape[0], 6))
    for i, x in enumerate(X):
        for g in range(2):
            kp1, kp2, slots = struct.group(x[g * half:(g + 1) * half])
            G = kp1 + sum(_slot(k, gn, a, s) for st, k, gn, a in slots if st == 0)
            if struct.cascade:
                G = (kp2 + sum(_slot(k, gn, a, s) for st, k, gn, a in slots if st == 1)) * (G + s)
            for d in range(3 * g, 3 * g + 3):
                out[i, d] = margins(G * H / (s * s + c1[d] * s + c0[d]), w)[0]
    return out
