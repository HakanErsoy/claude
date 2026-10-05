"""Reference variable-order (VO) differintegrals.

Sign convention (Grunwald-Letnikov, Sierociuk et al.): alpha > 0 is a
derivative, alpha < 0 an integral, alpha = 0 the identity. Orders are
restricted to -1 < alpha < 1.

Two VO definitions are used throughout:

* A-type ("1st type", no order memory): every past sample is weighted with
  the *current* order alpha(t).
* B-type ("2nd type", weak order memory): every past sample is weighted with
  the order alpha(tau) that was active when the sample entered.

For a unit-step input both have closed forms built on
F(s, a) = s^(-a) / Gamma(1 - a):

    y_A(t) = F(t, alpha(t))
    y_B(t) = F(t, alpha(0)) + int_0^t dF/da(t - tau, alpha(tau)) alpha'(tau) dtau

The B-type formula follows from integrating the kernel by parts in tau; for a
piecewise-constant order it collapses to a finite sum of F terms.
"""

import numpy as np
from scipy.integrate import quad
from scipy.special import gamma, digamma


def F(s, a):
    """Step response of the constant-order operator s^a: s^(-a)/Gamma(1-a)."""
    s = np.asarray(s, dtype=float)
    out = np.zeros_like(s)
    pos = s > 0
    out[pos] = s[pos] ** (-a) / gamma(1.0 - a)
    return out


def dF_da(s, a):
    """Partial derivative of F with respect to the order."""
    return s ** (-a) / gamma(1.0 - a) * (digamma(1.0 - a) - np.log(s))


def step_A(t, alpha_t):
    """A-type VO step response; alpha_t holds alpha evaluated at each t."""
    t = np.asarray(t, dtype=float)
    alpha_t = np.broadcast_to(np.asarray(alpha_t, dtype=float), t.shape)
    out = np.zeros_like(t)
    pos = t > 0
    out[pos] = t[pos] ** (-alpha_t[pos]) / gamma(1.0 - alpha_t[pos])
    return out


def step_B_piecewise(t, breaks, orders):
    """B-type VO step response for a piecewise-constant order.

    breaks: switching instants 0 < T_1 < T_2 < ...; orders[i] is active on
    [T_i, T_{i+1}) with T_0 = 0, so len(orders) == len(breaks) + 1.
    """
    t = np.asarray(t, dtype=float)
    y = F(t, orders[0])
    for Ti, a_prev, a_next in zip(breaks, orders[:-1], orders[1:]):
        y = y + F(t - Ti, a_next) - F(t - Ti, a_prev)
    return y


def step_B_smooth(t, alpha_fn, dalpha_fn, epsabs=1e-12, epsrel=1e-10):
    """B-type VO step response for a smooth order alpha(tau).

    The integrand dF/da(s, a) ~ s^(-a) log s is weakly singular at s = 0;
    the substitution s = v^m with m(1 - a_max) >= 2 removes it.
    """
    t = np.atleast_1d(np.asarray(t, dtype=float))
    out = np.empty_like(t)
    a0 = float(alpha_fn(0.0))
    for i, ti in enumerate(t):
        if ti <= 0:
            out[i] = 0.0
            continue
        a_max = max(0.0, float(np.max(alpha_fn(np.linspace(0.0, ti, 257)))))
        m = 2.0 / (1.0 - a_max)

        def integrand(v):
            s = v ** m
            tau = ti - s
            return dF_da(s, alpha_fn(tau)) * dalpha_fn(tau) * m * v ** (m - 1.0)

        val, _ = quad(integrand, 0.0, ti ** (1.0 / m), limit=400,
                      epsabs=epsabs, epsrel=epsrel)
        out[i] = ti ** (-a0) / gamma(1.0 - a0) + val
    return out


def _gl_weights(a, n):
    """(-1)^j binom(a, j) for j = 0..n-1, via the standard recursion."""
    w = np.empty(n)
    w[0] = 1.0
    if n > 1:
        j = np.arange(1, n)
        w[1:] = np.cumprod(1.0 - (a + 1.0) / j)
    return w


def gl_A(u, alpha, h):
    """Grunwald-Letnikov A-type VO differintegral (Sierociuk Def. 2)."""
    u = np.asarray(u, dtype=float)
    alpha = np.asarray(alpha, dtype=float)
    n = len(u)
    y = np.empty(n)
    for k in range(n):
        w = _gl_weights(alpha[k], k + 1)
        y[k] = h ** (-alpha[k]) * np.dot(w, u[k::-1])
    return y


def gl_B(u, alpha, h):
    """Grunwald-Letnikov B-type VO differintegral (Sierociuk Def. 3).

    Sample j is weighted with (-1)^r binom(alpha_j, r) h^(-alpha_j), r = k - j.
    """
    u = np.asarray(u, dtype=float)
    alpha = np.asarray(alpha, dtype=float)
    n = len(u)
    y = np.zeros(n)
    for j in range(n):
        if u[j] == 0.0:
            continue
        w = _gl_weights(alpha[j], n - j)
        y[j:] += h ** (-alpha[j]) * w * u[j]
    return y
