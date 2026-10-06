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

Tail closures (``tails``):
  "geometric" (default) all nodes carry the full weight h and each tail is
              the geometric series of the virtual trapezoid nodes beyond
              the grid, in its asymptotic form. The bank then equals the
              infinite trapezoid rule up to the asymptotic tail error, so
              no h^2 endpoint (Euler-Maclaurin) term appears.
  "integral"  half weights at the end nodes and tails replaced by the
              analytic integral beyond the end nodes (the first version).
  None        plain truncated trapezoid rule.
"""

import numpy as np


def _closure(tails):
    if tails is True:
        return "integral"
    if tails in (None, False):
        return None
    if tails not in ("geometric", "integral"):
        raise ValueError(tails)
    return tails


def _trapezoid_weights(K, h, closure):
    c = np.full(K, h)
    if closure != "geometric":
        c[0] = c[-1] = 0.5 * h
    return c


class FixedPoleBank:
    def __init__(self, xi_lo, xi_hi, K, tails="geometric"):
        if K < 2:
            raise ValueError("K must be at least 2")
        self.xi = np.geomspace(xi_lo, xi_hi, K)
        self.K = K
        self.h = np.log(xi_hi / xi_lo) / (K - 1)
        self.closure = _closure(tails)
        self.c = _trapezoid_weights(K, self.h, self.closure)

    def _tail_factor(self, p):
        """Integral closure: int_0^inf e^(-p x) dx = 1/p; geometric: sum_j>=1 h e^(-p j h)."""
        if self.closure == "geometric":
            return self.h / np.expm1(p * self.h)
        return 1.0 / p

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
            if self.closure:
                m[0] += S * xi[0] ** (-a) * self._tail_factor(1.0 - a)  # xi < xi_lo, lumped on xi_lo
                d = S * xi[-1] ** (-a) * self._tail_factor(a)           # xi > xi_hi, quasi-static
            return m, d
        S = np.sin(alpha * np.pi) / np.pi
        v = c * S * xi ** alpha
        d_lo = 0.0
        if self.closure:
            v[-1] += S * xi[-1] ** alpha * self._tail_factor(1.0 - alpha)  # xi > xi_hi, lumped on xi_hi
            d_lo = S * xi[0] ** alpha * self._tail_factor(alpha)           # xi < xi_lo, ~ all-pass 1
        return -v, v.sum() + d_lo

    def freqresp(self, alpha, w):
        s = 1j * np.asarray(w, dtype=float)[:, None]
        m, d = self.coeffs(alpha)
        if alpha > 0.0:
            # d = sum(v) + d_lo with v = -m; evaluating sum v s/(s+xi) + d_lo
            # avoids cancelling the large high-pole weights
            v = -m
            d_lo = d - v.sum() if not self.closure else (
                np.sin(alpha * np.pi) / np.pi * self.xi[0] ** alpha * self._tail_factor(alpha))
            return (v * s / (s + self.xi)).sum(axis=1) + d_lo
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

    def __init__(self, Ts, xi_lo, xi_hi, K, tails="geometric", dc_floor=True):
        if K < 2:
            raise ValueError("K must be at least 2")
        self.Ts = Ts
        self.K = K
        self.xi = np.geomspace(xi_lo, xi_hi, K)
        self.theta = np.exp(-self.xi * Ts)
        self.one_minus_theta = -np.expm1(-self.xi * Ts)
        self.dc_floor = dc_floor
        self.h = np.log(xi_hi / xi_lo) / (K - 1)
        self.closure = _closure(tails)
        c = _trapezoid_weights(K, self.h, self.closure)
        # dtheta = -Ts xi theta dx (orientation absorbed in the sign); one
        # factor theta is moved into the coefficient so that the states are
        # plain one-pole recursions s[n+1] = theta s[n] + u[n]
        self.jac = c * Ts * self.xi

    @staticmethod
    def _node(u, alpha):
        """u theta^(1-a) (1-theta)^a with theta = e^-u, finite for large u."""
        return u * np.exp(-(1.0 - alpha) * u) * (-np.expm1(-u)) ** alpha

    def _virtual_sums(self, alpha):
        """Geometric closure: virtual nodes beyond each end of the u = xi Ts grid.

        Upper nodes only matter at lag r = 1 (delay mode); lower nodes have
        theta ~ 1 and are lumped on theta_lo, matched at r = 1.
        """
        h = self.h
        u_hi, u_lo = self.xi[-1] * self.Ts, self.xi[0] * self.Ts
        j = np.arange(1, 400)
        log_uj = np.log(u_hi) + j * h
        uj = np.exp(log_uj[log_uj < np.log(745.0 / (1.0 - alpha))])
        upper = h * self._node(uj, alpha).sum()
        J = int(min(2e6, np.ceil(43.0 / ((1.0 + alpha) * h))))
        uj = u_lo * np.exp(-np.arange(1, J + 1) * h)
        uj = uj[uj > 1e-300]                 # below: u^(1+a) contributes < 1e-14
        lower = h * self._node(uj, alpha).sum()
        return upper, lower

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
        if self.closure == "integral":
            c[0] += scale * th[0] * (-np.expm1(-self.xi[0] * Ts)) ** (alpha + 1.0) / (alpha + 1.0)
            c_delay = scale * np.exp(-(1.0 - alpha) * self.xi[-1] * Ts) / (1.0 - alpha)
        elif self.closure == "geometric":
            upper, lower = self._virtual_sums(alpha)
            c[0] += scale * lower
            c_delay = scale * upper
        if self.dc_floor and alpha > 0.0:
            # Inverse stability. For a derivative bank all residues are
            # negative, so H(z) increases on z > 1 and its only zero there
            # (the inverse's slowest pole) lies inside the unit circle iff
            # H(1) = sum_r g_r > 0. The exact GL value is 0; the truncated
            # memory adds a positive tail ~ S g0 u_lo^a / (a (1 + a)), which
            # for large orders is smaller than the quadrature error of the DC
            # sum, so H(1) can come out negative. The floor (1% of that tail)
            # is reached through the delay mode: H(z) rises by d/z on all of
            # z >= 1 and only g_1 changes, by about the DC quadrature error.
            H1 = g0 + c_delay + np.sum(c / self.one_minus_theta)
            H_min = 0.01 * abs(scale) * (self.xi[0] * Ts) ** alpha / (alpha * (1.0 + alpha))
            if H1 < H_min:
                c_delay += H_min - H1
        return g0, c_delay, c

    def dc_gain(self, alpha):
        """Realized sum of all weights, H(z = 1)."""
        g0, cd, c = self.coeffs(alpha)
        return float(g0 + cd + np.sum(c / self.one_minus_theta))

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

    def _run(self, alpha, schedule, step, n):
        """Core loop shared by all operator types.

        At sample n the bank operator of order alpha[n] maps its input v[n]
        to g0 v[n] + hist[n], where hist depends only on past inputs (the
        poles are order-independent). ``step(n, g0, hist)`` returns
        (v[n], y[n]); this covers forward operators, their algebraic
        inverses and implicit equations with one code path.
        """
        alpha = np.asarray(alpha, dtype=float)
        th = self.theta
        cache = {}
        s = np.zeros(self.K)   # output: sum_{r>=1} theta^(r-1) v[n-r]; input: pre-weighted
        dl = 0.0               # delay-mode state
        y = np.empty(n)
        for k in range(n):
            a = float(alpha[k])
            if a not in cache:
                cache[a] = self.coeffs(a)
            g0, cd, c = cache[a]
            if schedule == "output":
                v, y[k] = step(k, g0, cd * dl + c @ s)
                s = th * s + v
                dl = v
            elif schedule == "input":
                v, y[k] = step(k, g0, dl + s.sum())
                s = th * s + c * v
                dl = cd * v
            else:
                raise ValueError(schedule)
        return y

    def simulate_batch(self, X, alpha, vo_type="A"):
        """A- or B-type for many realizations at once; X has shape (M, n).

        Same recursion as _run, vectorized over the rows (one shared order
        sequence), for Monte Carlo work.
        """
        X = np.asarray(X, dtype=float)
        alpha = np.asarray(alpha, dtype=float)
        M, n = X.shape
        th = self.theta[:, None]
        s = np.zeros((self.K, M))
        dl = np.zeros(M)
        Y = np.empty_like(X)
        cache = {}
        for k in range(n):
            a = float(alpha[k])
            if a not in cache:
                cache[a] = self.coeffs(a)
            g0, cd, c = cache[a]
            v = X[:, k]
            if vo_type == "A":
                Y[:, k] = g0 * v + cd * dl + c @ s
                s = th * s + v
                dl = v
            elif vo_type == "B":
                Y[:, k] = g0 * v + dl + s.sum(axis=0)
                s = th * s + c[:, None] * v
                dl = cd * v
            else:
                raise ValueError("batch mode supports the forward types A and B")
        return Y

    def simulate(self, u, alpha, schedule="output"):
        """schedule="output" realizes Def. 2 (A-type), "input" Def. 3 (B-type)."""
        return self.simulate_type(u, alpha, "A" if schedule == "output" else "B")

    def simulate_type(self, x, alpha, vo_type="A"):
        """VO difference of type A, B (forward) or D, E (recursive).

        D^a = (A^-a)^-1 and E^a = (B^-a)^-1 (Sierociuk et al. duality), so the
        recursive types are the exact algebraic inverses of the output- and
        input-scheduled banks of the opposite order; g0 = Ts^(-a) never
        vanishes, so the inverse is always well posed.
        """
        x = np.asarray(x, dtype=float)
        alpha = np.asarray(alpha, dtype=float)
        schedule = "output" if vo_type in ("A", "D") else "input"
        if vo_type in ("A", "B"):
            return self._run(alpha, schedule, lambda k, g0, hist: (x[k], g0 * x[k] + hist), len(x))
        if vo_type in ("D", "E"):
            def step(k, g0, hist):
                v = (x[k] - hist) / g0
                return v, v
            return self._run(-alpha, schedule, step, len(x))
        raise ValueError(vo_type)

    def solve_relaxation(self, u, alpha, lam, vo_type="A"):
        """Solve T^alpha y + lam y = u, T in {A, B, D, E}, at O(K) per sample.

        A, B: the operator acts on y, so y = (u - hist) / (g0 + lam).
        D, E: y = T'^-alpha z with z = u - lam y (dual form), so
              y = (g0 u + hist) / (1 + lam g0) and the bank is driven by z.
        """
        u = np.asarray(u, dtype=float)
        alpha = np.asarray(alpha, dtype=float)
        schedule = "output" if vo_type in ("A", "D") else "input"
        if vo_type in ("A", "B"):
            def step(k, g0, hist):
                y = (u[k] - hist) / (g0 + lam)
                return y, y
            return self._run(alpha, schedule, step, len(u))
        if vo_type in ("D", "E"):
            def step(k, g0, hist):
                y = (g0 * u[k] + hist) / (1.0 + lam * g0)
                return u[k] - lam * y, y
            return self._run(-alpha, schedule, step, len(u))
        raise ValueError(vo_type)

    def inverse_is_stable(self, alpha):
        """Exact-sign stability test of the frozen-order inverse (D/E types).

        Integral orders: all residues are positive, so the zeros of H
        interlace its poles in (0, 1) and the inverse is always stable.
        Derivative orders: all residues except possibly the delay mode are
        negative and H(z) >= H(1) on z >= 1, so the inverse is stable iff
        H(1) > 0. Unlike eigenvalues near z = 1, the sign of H(1) is
        computed to full relative precision.
        """
        g0, cd, c = self.coeffs(alpha)
        if alpha <= 0.0:
            return bool(np.all(c >= 0.0) and cd >= 0.0)
        return bool(np.all(c <= 0.0) and self.dc_gain(alpha) > 0.0)

    def inverse_spectral_radius(self, alpha):
        """Spectral radius of the inverse dynamics A - B C / D at frozen order.

        The same value holds for the input-scheduled (transposed) bank, so it
        decides the stability of both recursive types at that order.
        """
        g0, cd, c = self.coeffs(alpha)
        A = np.diag(np.append(self.theta, 0.0))
        B = np.ones(self.K + 1)
        C = np.append(c, cd)
        return float(np.max(np.abs(np.linalg.eigvals(A - np.outer(B, C) / g0))))
