"""Order-dependent-pole baseline: Oustaloup approximant with hot-swapped
coefficients.

Changing alpha moves every pole and zero. A switched implementation keeps
its state vector and swaps the coefficients, which is how runtime
reconfiguration is done in practice. Which variable-order definition (if
any) results depends on what the states mean, so two realizations of the
same transfer function are provided:

* "parallel": modal form with unit-DC-gain states x' = -p x + p u
* "cascade":  first-order sections (s + z)/(s + p) in ascending pole order,
              section state q' = -p q + v_in, v_out = v_in + (z - p) q
"""

import numpy as np
from scipy.linalg import expm


def oustaloup_zpk(alpha, w_b, w_h, N):
    k = np.arange(-N, N + 1)
    r = w_h / w_b
    z = w_b * r ** ((k + N + 0.5 * (1.0 - alpha)) / (2 * N + 1))
    p = w_b * r ** ((k + N + 0.5 * (1.0 + alpha)) / (2 * N + 1))
    return z, p, w_h ** alpha


def _parallel_ss(z, p, K):
    n = len(p)
    m = np.empty(n)
    for i in range(n):
        others = np.delete(p, i)
        # residue at -p_i divided by p_i (unit-DC-gain state scaling)
        m[i] = K * (z[i] - p[i]) * np.prod((z[np.arange(n) != i] - p[i]) / (others - p[i])) / p[i]
    A = np.diag(-p)
    B = p.copy()
    return A, B, m, K


def _cascade_ss(z, p, K):
    n = len(p)
    A = np.zeros((n, n))
    B = np.zeros(n)
    # v_1 = u; v_{i+1} = v_i + (z_i - p_i) q_i; q_i' = -p_i q_i + v_i
    gain = z - p
    for i in range(n):
        A[i, i] = -p[i]
        A[i, :i] = gain[:i]
        B[i] = 1.0
    C = K * gain
    return A, B, C, K


def _zoh(A, B, Ts):
    n = A.shape[0]
    M = np.zeros((n + 1, n + 1))
    M[:n, :n] = A
    M[:n, n] = B
    E = expm(M * Ts)
    return E[:n, :n], E[:n, n]


class SwitchedOustaloup:
    def __init__(self, w_b, w_h, N, form="parallel"):
        self.w_b, self.w_h, self.N, self.form = w_b, w_h, N, form

    def ss(self, alpha):
        z, p, K = oustaloup_zpk(alpha, self.w_b, self.w_h, self.N)
        idx = np.argsort(p)
        z, p = z[idx], p[idx]
        if self.form == "parallel":
            return _parallel_ss(z, p, K)
        if self.form == "cascade":
            return _cascade_ss(z, p, K)
        raise ValueError(self.form)

    def freqresp(self, alpha, w):
        A, B, C, D = self.ss(alpha)
        n = A.shape[0]
        return np.array([C @ np.linalg.solve(1j * wi * np.eye(n) - A, B) + D for wi in w])

    def simulate(self, u, alpha, Ts):
        """ZOH simulation; on an order change the state vector is kept."""
        u = np.asarray(u, dtype=float)
        alpha = np.asarray(alpha, dtype=float)
        cache = {}
        x = np.zeros(2 * self.N + 1)
        y = np.empty(len(u))
        for n in range(len(u)):
            a = float(alpha[n])
            if a not in cache:
                A, B, C, D = self.ss(a)
                Ad, Bd = _zoh(A, B, Ts)
                cache[a] = (Ad, Bd, C, D)
            Ad, Bd, C, D = cache[a]
            y[n] = C @ x + D * u[n]
            x = Ad @ x + Bd * u[n]
        return y
