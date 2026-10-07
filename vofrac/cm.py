"""Completely monotone kernel families on a fixed-pole bank.

A CM family has k_a(r) = sigma_a int_0^inf e^{-(r-1)u} m_a(u) du for r >= 1.
Its bank uses the same poles for every member, so any linear combination of
members, for instance a distributed order with a time-varying density, is
realized by combining residues, and a fixed tempering e^{-lambda r} only
scales the poles and residues.
"""

import numpy as np


def mixture_coeffs(bank, orders, weights):
    """(g0, cd, c) of sum_q weights[q] * member(orders[q]) on the bank's poles."""
    g0 = cd = 0.0
    c = np.zeros(bank.K)
    for a, w in zip(orders, weights):
        g0q, cdq, cq = bank.coeffs(float(a))
        g0 += w * g0q
        cd += w * cdq
        c += w * cq
    return g0, cd, c


def run(theta, coeff_seq, x, schedule="output"):
    """Stream x through one-pole states theta with per-sample (g0, cd, c).

    schedule="output": the coefficients of sample n weight the whole history (A-type);
    schedule="input":  each sample enters with the coefficients of its own time (B-type).
    """
    s = np.zeros(len(theta))
    dl = 0.0
    y = np.empty(len(x))
    for k, (g0, cd, c) in enumerate(coeff_seq):
        if schedule == "output":
            y[k] = g0 * x[k] + cd * dl + c @ s
            s = theta * s + x[k]
            dl = x[k]
        elif schedule == "input":
            y[k] = g0 * x[k] + dl + s.sum()
            s = theta * s + c * x[k]
            dl = cd * x[k]
        else:
            raise ValueError(schedule)
    return y


def tempered(bank, a, lam):
    """Poles and (g0, cd, c) realizing e^{-lam r} g^_r(a) exactly."""
    g0, cd, c = bank.coeffs(float(a))
    q = np.exp(-lam)
    return q * bank.theta, (g0, q * cd, q * c)
