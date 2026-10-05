"""Analytic error model and design rule for fixed-pole banks.

No fitted constants: every term follows from the integral representation.

Continuous time (relative frequency-response error |H/s^alpha - 1| over
w1 <= w <= w2, geometric tail closure, grid spacing h in ln(xi)):

  quadrature (Poisson, first alias)   E_q  = 2 |sin(pi a)| exp(-pi^2 / h)
  integral  a = -alpha > 0:
     low tail (lumped on xi_lo)       S (xi_lo/w1)^(2-a) H(1-a, 2-a)
     high tail (feedthrough)          S (w2/xi_hi)^(1+a) G(1+a)
  derivative a = alpha > 0:
     low tail (feedthrough)           S (xi_lo/w1)^(1+a) G(1+a)
     high tail (lumped on xi_hi)      S (w2/xi_hi)^(2-a) H(1-a, 2-a)

with S = sin(pi a)/pi, G(p) = h/(e^{ph} - 1), H(p, q) = G(p) - G(q).

Discrete time (relative error of the realized GL weights g_r, 1 <= r < R,
u = xi Ts):

  quadrature   large-r alias  2 sqrt(2 pi) (2 pi/h)^(a+1/2) e^{-pi^2/h} / Gamma(1+a)
               small r        alias amplitude evaluated from the representation
  low tail     (r-1) u_lo^(2+a) H(1+a, 2+a) / B(r-a, 1+a), worst at r = R-1
  high tail    sum_j h u_j e^{-(2-a) u_j} (1-e^{-u_j})^a / B(2-a, 1+a), u_j = u_hi e^{jh}

The rule splits the tolerance eps as eps/2 (quadrature) + eps/4 (each tail),
picks the largest h and the narrowest grid meeting each share over the
requested order range, and sets K = ceil(ln(xi_hi/xi_lo)/h) + 1.
"""

import numpy as np
from scipy.optimize import brentq
from scipy.special import betaln, gammaln

SPLIT = (0.5, 0.25, 0.25)


def _G(p, h):
    return h / np.expm1(p * h)


def _H(p, q, h):
    return _G(p, h) - _G(q, h)


def order_grid(alpha_min, alpha_max, n=33):
    a = np.linspace(alpha_min, alpha_max, n)
    a[np.abs(a) < 1e-6] = 1e-6
    return a


# ---------------------------------------------------------------- continuous

def ct_quadrature(a, h):
    return 2.0 * np.abs(np.sin(np.pi * a)) * np.exp(-np.pi ** 2 / h)


def ct_tail_terms(alpha, h):
    """(C_lo, p_lo, C_hi, p_hi): low tail C_lo (xi_lo/w1)^p_lo, high tail C_hi (w2/xi_hi)^p_hi."""
    a = abs(alpha)
    S = np.sin(np.pi * a) / np.pi
    if alpha < 0:
        return S * _H(1 - a, 2 - a, h), 2 - a, S * _G(1 + a, h), 1 + a
    return S * _G(1 + a, h), 1 + a, S * _H(1 - a, 2 - a, h), 2 - a


def ct_error_model(alpha, h, xi_lo, xi_hi, w1, w2):
    C_lo, p_lo, C_hi, p_hi = ct_tail_terms(alpha, h)
    return {"quad": ct_quadrature(alpha, h),
            "lo": C_lo * (xi_lo / w1) ** p_lo,
            "hi": C_hi * (w2 / xi_hi) ** p_hi}


def design_ct(w1, w2, alpha_min, alpha_max, eps, split=SPLIT):
    a = order_grid(alpha_min, alpha_max)
    smax = np.abs(np.sin(np.pi * a)).max()
    h = np.pi ** 2 / np.log(2.0 * smax / (split[0] * eps))
    rho_lo, rho_hi = np.inf, np.inf
    for ai in a:
        C_lo, p_lo, C_hi, p_hi = ct_tail_terms(ai, h)
        rho_lo = min(rho_lo, (split[1] * eps / C_lo) ** (1.0 / p_lo))
        rho_hi = min(rho_hi, (split[2] * eps / C_hi) ** (1.0 / p_hi))
    xi_lo, xi_hi = w1 * rho_lo, w2 / rho_hi
    K = int(np.ceil(np.log(xi_hi / xi_lo) / h)) + 1
    return {"xi_lo": xi_lo, "xi_hi": xi_hi, "K": K, "h": np.log(xi_hi / xi_lo) / (K - 1), "h_rule": h}


# ------------------------------------------------------------------ discrete

def _F(x, a, r):
    """Integrand of g_r / scale in x = ln u."""
    u = np.exp(x)
    return u * np.exp(-(r - a) * u) * (-np.expm1(-u)) ** a


def dt_alias_small_r(a, h, r):
    """Alias amplitude of the infinite trapezoid rule at lag r (two grid offsets)."""
    x_lo = max(-700.0, -45.0 / (1.0 + a) - 5.0)   # below: u^(1+a) contributes < 1e-14
    x_hi = np.log(800.0 / (r - a))
    logB = betaln(r - a, 1.0 + a)
    errs = []
    for off in (0.0, 0.25 * h):
        x = off + h * np.arange(np.floor(x_lo / h), np.ceil(x_hi / h) + 1)
        T = h * _F(x, a, r).sum()
        errs.append(np.exp(np.log(T) - logB) - 1.0)
    return float(np.hypot(*errs))


def dt_alias_large_r(a, h):
    return float(2.0 * np.sqrt(2 * np.pi) * np.exp((a + 0.5) * np.log(2 * np.pi / h) - np.pi ** 2 / h - gammaln(1.0 + a)))


def dt_quadrature(a, h, small_r=(1, 2, 3, 5, 8)):
    return max([dt_alias_large_r(a, h)] + [dt_alias_small_r(a, h, r) for r in small_r])


def dt_lower_tail(a, u_lo, h, R):
    r = R - 1
    return float((r - 1) * u_lo ** (2 + a) * _H(1 + a, 2 + a, h) / np.exp(betaln(r - a, 1 + a)))


def dt_upper_tail(a, u_hi, h):
    log_uj = np.log(u_hi) + h * np.arange(1, 200)
    uj = np.exp(log_uj[log_uj < np.log(745.0 / (2 - a))])
    s = h * np.sum(uj * np.exp(-(2 - a) * uj) * (-np.expm1(-uj)) ** a)
    return float(s / np.exp(betaln(2 - a, 1 + a)))


def dt_error_model(alpha, h, u_lo, u_hi, R):
    return {"quad": dt_quadrature(alpha, h),
            "lo": dt_lower_tail(alpha, u_lo, h, R),
            "hi": dt_upper_tail(alpha, u_hi, h)}


def design_dt(Ts, R, alpha_min, alpha_max, eps, split=SPLIT):
    a = order_grid(alpha_min, alpha_max, 17)
    target_q = split[0] * eps
    f = lambda h: max(dt_quadrature(ai, h) for ai in a) - target_q
    h = brentq(lambda lh: f(np.exp(lh)), np.log(0.05), np.log(3.0), xtol=1e-4)
    h = float(np.exp(h))
    # low tail: closed form per order, narrowest wins
    u_lo = np.inf
    for ai in a:
        c = dt_lower_tail(ai, 1.0, h, R)
        u_lo = min(u_lo, (split[1] * eps / c) ** (1.0 / (2 + ai)))
    # high tail: monotone in u_hi
    u_hi = max(brentq(lambda u: dt_upper_tail(ai, u, h) - split[2] * eps, 1e-3, 800.0) for ai in a)
    K = int(np.ceil(np.log(u_hi / u_lo) / h)) + 1
    return {"xi_lo": u_lo / Ts, "xi_hi": u_hi / Ts, "K": K,
            "h": float(np.log(u_hi / u_lo) / (K - 1)), "h_rule": h}


# ------------------------------------------------------------- measurements

def measure_ct(bank, w1, w2, alpha_min, alpha_max, n_w_per_dec=80):
    w = np.geomspace(w1, w2, max(50, int(n_w_per_dec * np.log10(w2 / w1)) + 1))
    worst = 0.0
    for ai in order_grid(alpha_min, alpha_max, 17):
        worst = max(worst, float(np.abs(bank.freqresp(ai, w) / (1j * w) ** ai - 1).max()))
    return worst


def measure_dt(bank, R, alpha_min, alpha_max):
    from .reference import _gl_weights
    r = np.unique(np.concatenate([np.arange(1, min(R, 301)), np.geomspace(1, R - 1, 700).astype(int)]))
    worst = 0.0
    for ai in order_grid(alpha_min, alpha_max, 17):
        ref = _gl_weights(ai, R)[r] * bank.Ts ** (-ai)
        g0, cd, c = bank.coeffs(ai)
        g = (c[None, :] * bank.theta[None, :] ** (r[:, None] - 1)).sum(axis=1)
        g[r == 1] += cd
        worst = max(worst, float(np.abs(g / ref - 1).max()))
    return worst
