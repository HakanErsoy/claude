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


# ------------------------------------------------- a-priori design from the CM theorem

KAPPA0 = (1.0 - np.exp(-2.0)) / 2.0        # min over u of (1 - e^-u) / min(u, 2)


def gl_strip_bound(abar, d):
    """Closed-form bound on L_d for GL orders |a| <= abar < 1 (Lemma: GL constants)."""
    return KAPPA0 ** (-abar) * np.cos(d) ** (-(1.0 + abar))


def gl_constants(abar):
    """(H2)-(H3) constants of the GL family for |a| <= abar, with u_* = 1."""
    from scipy.special import gamma, gammainc
    c_minus = (1.0 - np.exp(-1.0)) * np.exp(-2.0)
    c_plus = c_inf = 1.0 / (1.0 - np.exp(-1.0))
    beta_lo, beta_hi, gam = 1.0 - abar, 1.0 + abar, 1.0 - abar
    # theta = min over beta of int_0^1 t^(beta-1) e^-t dt, decreasing in beta
    theta = float(gammainc(beta_hi, 1.0) * gamma(beta_hi))
    return {"c_minus": c_minus, "c_plus": c_plus, "C_inf": c_inf, "beta_lo": beta_lo, "beta_hi": beta_hi,
            "gamma": gam, "u_star": 1.0, "theta": theta,
            "C_lo": c_plus / (c_minus * beta_lo * theta), "C_hi": c_inf / ((1.0 + gam) * c_minus * theta)}


def theorem_design(eps, R, abar, d_grid=np.linspace(0.3, 1.55, 126)):
    """Part (c) of the CM theorem with the GL constants; the strip width d minimizes K."""
    k = gl_constants(abar)
    if not 0 < eps <= min(1.0, 4 * k["C_lo"]):
        raise ValueError("eps out of range")
    u_lo = min(k["u_star"], (eps / (4 * k["C_lo"])) ** (1.0 / (1.0 + k["beta_lo"])) / (R - 1))
    u_hi = max(k["u_star"], 1.0, k["beta_hi"] * np.log(2.0), np.log(4 * k["C_hi"] / eps) / (1.0 + k["gamma"]))
    best = None
    for d in d_grid:
        h = 2 * np.pi * d / np.log1p(4 * gl_strip_bound(abar, d) / eps)
        K = int(np.ceil(np.log(u_hi / u_lo) / h)) + 1
        if best is None or K < best["K"]:
            best = {"d": float(d), "h": float(h), "K": K}
    return {**best, "u_lo": float(u_lo), "u_hi": float(u_hi), "constants": k}
