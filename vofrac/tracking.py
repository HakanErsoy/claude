"""Online tracking of a time-varying order with extended Kalman filters (E10).

Data model: y_n = (T^alpha x)_n + v_n, known input x, white noise v, T in {A, B},
and a random-walk prior alpha_{n+1} = alpha_n + w_n.

* A-type: with the order in the output weights, the bank states are driven by
  the known input only, so the state does not depend on the order and the
  filter is scalar. The model and its Jacobian are O(K) per sample:
      h_n(a) = g0(a) x_n + cd(a) sd_n + c(a)' s_n,
      h_n'(a) = g0'(a) x_n + cd'(a) sd_n + c'(a)' s_n.
* B-type: with the order in the input weights, the bank state carries the
  order history, and the filter state is (s, sd, alpha), K + 2 entries. The
  model and its Jacobians are O(K); the covariance update is O((K+2)^2).
* Reference: an A-type filter on the literal GL weights, O(n) per sample.

The residues are tabulated on a fine order grid and interpolated by cubic
splines (value and derivative), as a ROM with interpolation would do.
"""

import numpy as np
from scipy.interpolate import CubicSpline


class CoeffSpline:
    """Spline of the bank coefficients (cd, c_0..c_{K-1}) over the order."""

    def __init__(self, bank, a_min=-0.95, a_max=0.95, step=0.0025):
        self.bank = bank
        self.a_min, self.a_max = a_min, a_max
        grid = np.linspace(a_min, a_max, int(round((a_max - a_min) / step)) + 1)
        tab = np.array([np.append(bank.coeffs(float(a))[2], bank.coeffs(float(a))[1]) for a in grid])
        self.spline = CubicSpline(grid, tab, axis=0)
        self.dspline = self.spline.derivative()
        self.lnTs = np.log(bank.Ts)

    def __call__(self, a):
        """(g0, g0', cd, cd', c, c') at order a."""
        v, dv = self.spline(a), self.dspline(a)
        g0 = np.exp(-a * self.lnTs)
        return g0, -self.lnTs * g0, v[-1], dv[-1], v[:-1], dv[:-1]


def _clip(a, lo, hi):
    return min(max(a, lo), hi)


def _scalar_iekf(n, y, model, advance, q, r_v, a0, p0, iters, gate, p_jump, lo, hi):
    """Iterated EKF for a scalar random-walk order with measurement model(b, k) -> (h, h')."""
    a, P = a0, p0
    ah, Ph = np.empty(n), np.empty(n)
    for k in range(n):
        P += q
        h, H = model(a, k)
        if (y[k] - h) ** 2 > gate * (H * H * P + r_v):
            P += p_jump
        b = a
        for _ in range(iters):
            hb, Hb = model(b, k)
            G = P * Hb / (Hb * Hb * P + r_v)
            b_new = _clip(a + G * (y[k] - hb - Hb * (a - b)), lo, hi)
            done = abs(b_new - b) < 1e-9
            b = b_new
            if done:
                break
        hb, Hb = model(b, k)
        P = P * r_v / (Hb * Hb * P + r_v)
        a = b
        ah[k], Ph[k] = a, P
        advance(k)
    return ah, Ph


def ekf_A(cs, x, y, q, r_v, a0=0.0, p0=0.25, iters=5, gate=25.0, p_jump=0.05):
    """Scalar iterated EKF for the A-type on the bank; returns (alpha_hat, variance).

    iters: Gauss-Newton iterations of the measurement update (1 = plain EKF).
    gate, p_jump: if the normalized innovation exceeds gate, the order
    variance is inflated by p_jump before the update (jump detection).
    """
    th = cs.bank.theta
    st = {"s": np.zeros(len(th)), "sd": 0.0}

    def model(b, k):
        g0, dg0, cd, dcd, c, dc = cs(b)
        return (g0 * x[k] + cd * st["sd"] + c @ st["s"],
                dg0 * x[k] + dcd * st["sd"] + dc @ st["s"])

    def advance(k):                 # output schedule: the states see the input only
        st["s"] = th * st["s"] + x[k]
        st["sd"] = x[k]

    return _scalar_iekf(len(x), y, model, advance, q, r_v, a0, p0, iters, gate, p_jump, cs.a_min, cs.a_max)


def ekf_B(cs, x, y, q, r_v, a0=0.0, p0=0.25, gate=25.0, p_jump=0.05):
    """Augmented EKF for the B-type, state (s_0..s_{K-1}, sd, alpha).

    gate, p_jump: covariance inflation of the order on large innovations, as in ekf_A.
    """
    th = cs.bank.theta
    K = len(th)
    z = np.zeros(K + 2)
    z[-1] = a0
    P = np.zeros((K + 2, K + 2))
    P[-1, -1] = p0
    n = len(x)
    ah, Ph = np.empty(n), np.empty(n)
    Hrow = np.ones(K + 2)
    for k in range(n):
        a = z[-1]
        g0, dg0, cd, dcd, c, dc = cs(a)
        # measurement update: y = g0(a) x + sd + 1's
        h = g0 * x[k] + z[K] + z[:K].sum()
        Hrow[-1] = dg0 * x[k]
        PH = P @ Hrow
        if (y[k] - h) ** 2 > gate * (Hrow @ PH + r_v):
            P[-1, -1] += p_jump
            PH = P @ Hrow
        S = Hrow @ PH + r_v
        G = PH / S
        z = z + G * (y[k] - h)
        z[-1] = _clip(z[-1], cs.a_min, cs.a_max)
        P = P - np.outer(G, PH)
        P = 0.5 * (P + P.T)
        ah[k], Ph[k] = z[-1], P[-1, -1]
        # time update: s <- theta s + c(a) x, sd <- cd(a) x, a <- a
        a = z[-1]
        g0, dg0, cd, dcd, c, dc = cs(a)
        z_new = np.empty_like(z)
        z_new[:K] = th * z[:K] + c * x[k]
        z_new[K] = cd * x[k]
        z_new[-1] = a
        # F = [[diag(th), 0, dc x], [0, 0, dcd x], [0, 0, 1]]
        Fa = np.append(np.append(dc * x[k], dcd * x[k]), 1.0)
        diag = np.append(np.append(th, 0.0), 0.0)
        Pa = P[:, -1].copy()
        P = diag[:, None] * P * diag[None, :]
        cross = diag * Pa                         # (diag-part of F) P e_alpha
        P += np.outer(cross, Fa) + np.outer(Fa, cross) + Pa[-1] * np.outer(Fa, Fa)
        P[-1, -1] += q
        z = z_new
    return ah, Ph


def ekf_gl_A(x, y, Ts, q, r_v, a0=0.0, p0=0.25, iters=5, gate=25.0, p_jump=0.05,
             a_min=-0.95, a_max=0.95):
    """The same iterated EKF on the literal GL weights, O(n) per sample."""
    lnT = np.log(Ts)

    def model(a, k):
        # lags r = 1..k: w_r = -a P_r with P_r = prod_{j=2}^r (j-1-a)/j (no division by a)
        r = np.arange(2, k + 1)
        Pr = np.cumprod(np.concatenate([[1.0], (r - 1 - a) / r]))[:k]
        dPr = Pr * np.cumsum(np.concatenate([[0.0], -1.0 / (r - 1 - a)]))[:k]
        w = np.concatenate([[1.0], -a * Pr])
        dw = np.concatenate([[0.0], -Pr - a * dPr])
        past = x[k::-1]
        T = np.exp(-a * lnT)
        h = T * (w @ past)
        return h, T * (dw @ past) - lnT * h

    return _scalar_iekf(len(x), y, model, lambda k: None, q, r_v, a0, p0, iters, gate, p_jump, a_min, a_max)


def grid_filter_A(bank, x, y, q, r_v, grid=np.linspace(-0.95, 0.95, 381), p_switch=1e-3):
    """Point-mass (grid) Bayes filter for the A-type, O(G K) per sample.

    Because the output-scheduled bank state does not depend on the order,
    one state serves every order hypothesis: the predicted outputs of all G
    grid orders are one (G x (K+1)) matrix-vector product. The transition is
    a Gaussian random walk (variance q) mixed with a uniform jump of
    probability p_switch. The likelihood of each cell includes the spread
    of the prediction across the cell, so that the grid spacing does not
    have to resolve the likelihood at high SNR. Returns the posterior mean
    and variance.
    """
    th = bank.theta
    coef = np.array([np.append(bank.coeffs(float(a))[2], bank.coeffs(float(a))[1]) for a in grid])  # (G, K+1)
    g0 = np.array([bank.coeffs(float(a))[0] for a in grid])
    G = len(grid)
    step = grid[1] - grid[0]
    half = int(np.ceil(5 * np.sqrt(q) / step))
    ker = np.exp(-0.5 * (np.arange(-half, half + 1) * step) ** 2 / q) if q > 0 else np.array([1.0])
    ker /= ker.sum()
    post = np.full(G, 1.0 / G)
    s = np.zeros(len(th) + 1)          # (s_0..s_{K-1}, sd)
    n = len(x)
    mean, var = np.empty(n), np.empty(n)
    for k in range(n):
        prior = np.convolve(post, ker, mode="same")
        prior = (1 - p_switch) * prior / prior.sum() + p_switch / G
        h = g0 * x[k] + coef @ s
        # cell-averaged likelihood: the order is uniform within a grid cell
        r_eff = r_v + (np.gradient(h, step) * step) ** 2 / 12.0
        logl = -0.5 * (y[k] - h) ** 2 / r_eff - 0.5 * np.log(r_eff)
        w = prior * np.exp(logl - logl.max())
        post = w / w.sum()
        mean[k] = post @ grid
        var[k] = post @ (grid - mean[k]) ** 2
        s[:-1] = th * s[:-1] + x[k]
        s[-1] = x[k]
    return mean, var
