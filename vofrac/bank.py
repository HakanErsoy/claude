"""Fixed-pole diffusive approximant of s^alpha for -1 < alpha < 1.

The diffusive representations

    s^(-a) = sin(a pi)/pi * int_0^inf xi^(-a)  / (s + xi)    dxi   (0 < a < 1)
    s^(+a) = sin(a pi)/pi * int_0^inf xi^(a-1) * s / (s + xi) dxi   (0 < a < 1)

are discretised with the trapezoidal rule on a geometric grid
xi_k = xi_lo * q^k, k = 0..K-1. The poles xi_k do not depend on the order;
only the output weights do. Every order is written in the common form

    H_alpha(s) = sum_k m_k(alpha) * xi_k / (s + xi_k) + d(alpha),

so a single bank of unit-DC-gain first-order states serves integrals,
derivatives and the identity. The truncated tails of the integrals are
folded back analytically: one tail becomes a feedthrough term, the other is
lumped onto the outermost pole. This is what keeps the bank exact at
alpha = 0 and continuous when the order crosses zero.
"""

import numpy as np


class FixedPoleBank:
    def __init__(self, xi_lo, xi_hi, K, tails=True):
        if K < 2:
            raise ValueError("K must be at least 2")
        self.xi = np.geomspace(xi_lo, xi_hi, K)
        self.K = K
        self.h = np.log(xi_hi / xi_lo) / (K - 1)
        c = np.full(K, self.h)
        c[0] = c[-1] = 0.5 * self.h
        self.c = c
        self.tails = tails

    def coeffs(self, alpha):
        """Output weights m (shape K) and feedthrough d for order alpha."""
        xi, c = self.xi, self.c
        if alpha == 0.0:
            return np.zeros(self.K), 1.0
        if alpha < 0.0:
            a = -alpha
            S = np.sin(a * np.pi) / np.pi
            m = c * S * xi ** (-a)
            d = 0.0
            if self.tails:
                m[0] += S * xi[0] ** (-a) / (1.0 - a)   # xi < xi_lo, lumped on xi_lo
                d = S * xi[-1] ** (-a) / a              # xi > xi_hi, quasi-static
            return m, d
        S = np.sin(alpha * np.pi) / np.pi
        v = c * S * xi ** alpha
        d_lo = 0.0
        if self.tails:
            v[-1] += S * xi[-1] ** alpha / (1.0 - alpha)  # xi > xi_hi, lumped on xi_hi
            d_lo = S * xi[0] ** alpha / alpha             # xi < xi_lo, ~ all-pass 1
        return -v, v.sum() + d_lo

    def freqresp(self, alpha, w):
        m, d = self.coeffs(alpha)
        s = 1j * np.asarray(w, dtype=float)[:, None]
        return (m * self.xi / (s + self.xi)).sum(axis=1) + d

    def simulate(self, u, alpha, Ts, schedule="output"):
        """Exact ZOH simulation with a sample-wise order sequence.

        schedule="output": states x' = -xi x + xi u, y = m(alpha(t)) x + d u
                           (order applied to the whole history: A-type).
        schedule="input":  states x' = -xi x + xi m(alpha(t)) u, y = 1'x + d u
                           (order frozen into each sample on entry: B-type).
        """
        u = np.asarray(u, dtype=float)
        alpha = np.asarray(alpha, dtype=float)
        Ad = np.exp(-self.xi * Ts)
        Bd = 1.0 - Ad
        cache = {}
        x = np.zeros(self.K)
        y = np.empty(len(u))
        for n in range(len(u)):
            a = float(alpha[n])
            if a not in cache:
                cache[a] = self.coeffs(a)
            m, d = cache[a]
            if schedule == "output":
                y[n] = m @ x + d * u[n]
                x = Ad * x + Bd * u[n]
            elif schedule == "input":
                y[n] = x.sum() + d * u[n]
                x = Ad * x + Bd * m * u[n]
            else:
                raise ValueError(schedule)
        return y


class DiscreteFixedPoleBank:
    """Fixed-pole realization of the Grunwald-Letnikov weights themselves.

    For r >= 1 and -1 < a < 1 the GL weights have the representation

        (-1)^r binom(a, r) = -(sin a pi)/pi * int_0^1 theta^r theta^(-a-1) (1-theta)^a dtheta,

    i.e. a superposition of geometric sequences theta^r with order-dependent
    density. With theta_k = exp(-xi_k Ts) on a geometric xi grid the discrete
    poles are order-independent, and the A-type (Def. 2) and B-type (Def. 3)
    VO differences are realized up to quadrature error only. This avoids the
    continuous-time issue that modes faster than 1/Ts respond to the
    staircase of a sampled order.

    Modes: K geometric poles theta_k, plus a pure one-sample delay (theta = 0)
    carrying the theta < theta_hi tail; the theta > theta_lo tail is lumped
    on theta_lo. The r = 0 weight Ts^(-a) is an exact feedthrough.
    """

    def __init__(self, Ts, xi_lo, xi_hi, K, tails=True):
        if K < 2:
            raise ValueError("K must be at least 2")
        self.Ts = Ts
        self.K = K
        self.xi = np.geomspace(xi_lo, xi_hi, K)
        self.theta = np.exp(-self.xi * Ts)
        hx = np.log(xi_hi / xi_lo) / (K - 1)
        c = np.full(K, hx)
        c[0] = c[-1] = 0.5 * hx
        # dtheta = -Ts xi theta dx (orientation absorbed in the sign); one
        # factor theta is moved into the coefficient so that the states are
        # plain one-pole recursions s[n+1] = theta s[n] + u[n]
        self.jac = c * Ts * self.xi
        self.tails = tails

    def coeffs(self, alpha):
        """(g0, c_delay, c): g_r = g0 [r=0] + c_delay [r=1] + sum_k c_k theta_k^(r-1), r>=1."""
        Ts, th = self.Ts, self.theta
        g0 = Ts ** (-alpha)
        if alpha == 0.0:
            return g0, 0.0, np.zeros(self.K)
        S = np.sin(alpha * np.pi) / np.pi
        scale = -S * Ts ** (-alpha)
        # theta^(1-a) (1-theta)^a, written to stay finite when theta underflows
        c = self.jac * scale * np.exp(-(1.0 - alpha) * self.xi * Ts) * (-np.expm1(-self.xi * Ts)) ** alpha
        c_delay = 0.0
        if self.tails:
            c[0] += scale * th[0] * (-np.expm1(-self.xi[0] * Ts)) ** (alpha + 1.0) / (alpha + 1.0)
            c_delay = scale * np.exp(-(1.0 - alpha) * self.xi[-1] * Ts) / (1.0 - alpha)
        return g0, c_delay, c

    def weights(self, alpha, R):
        """Realized GL weights g_0..g_{R-1} (for checking the quadrature)."""
        g0, cd, c = self.coeffs(alpha)
        r = np.arange(R)
        g = np.zeros(R)
        g[1:] = (c[None, :] * self.theta[None, :] ** (r[1:, None] - 1)).sum(axis=1)
        g[0] = g0
        if R > 1:
            g[1] += cd
        return g

    def simulate(self, u, alpha, schedule="output"):
        """schedule="output" realizes Def. 2 (A-type), "input" Def. 3 (B-type)."""
        u = np.asarray(u, dtype=float)
        alpha = np.asarray(alpha, dtype=float)
        th = self.theta
        cache = {}
        s = np.zeros(self.K)   # output: sum_{r>=1} theta^(r-1) u[n-r]; input: pre-weighted
        dl = 0.0               # delay-mode state
        y = np.empty(len(u))
        for n in range(len(u)):
            a = float(alpha[n])
            if a not in cache:
                cache[a] = self.coeffs(a)
            g0, cd, c = cache[a]
            if schedule == "output":
                y[n] = g0 * u[n] + cd * dl + c @ s
                s = th * s + u[n]
                dl = u[n]
            elif schedule == "input":
                y[n] = g0 * u[n] + dl + s.sum()
                s = th * s + c * u[n]
                dl = cd * u[n]
            else:
                raise ValueError(schedule)
        return y
