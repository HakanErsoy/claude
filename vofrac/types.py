"""Own-type references for any family of LTI order approximants.

Given frozen-order members R_v (impulse responses h_v), the four VO types
built *from that family* are

    A:  y_k = sum_j h_{a_k}[k-j] x_j          (current order on all history)
    B:  y_k = sum_j h_{a_j}[k-j] x_j          (order at entry)
    D:  inverse of A of the opposite order    (D^a = (A^-a)^-1)
    E:  inverse of B of the opposite order    (E^a = (B^-a)^-1)

Comparing a switched realization with these isolates its definitional
behaviour from how well each member approximates s^a. Orders must be
piecewise constant with few distinct values.
"""

import numpy as np


class OwnTypes:
    def __init__(self, sim, n):
        """sim(u, alpha_array) simulates the realization; n is the horizon."""
        self.sim = sim
        self.n = n
        self._h = {}

    def impulse(self, v):
        v = float(v)
        if v not in self._h:
            d = np.zeros(self.n)
            d[0] = 1.0
            self._h[v] = self.sim(d, np.full(self.n, v))
        return self._h[v]

    def A(self, x, alpha):
        y = np.empty(self.n)
        for v in np.unique(alpha):
            m = alpha == v
            y[m] = np.convolve(x, self.impulse(v))[: self.n][m]
        return y

    def B(self, x, alpha):
        y = np.zeros(self.n)
        for v in np.unique(alpha):
            y += np.convolve(x * (alpha == v), self.impulse(v))[: self.n]
        return y

    def D(self, x, alpha):
        z = np.empty(self.n)
        for k in range(self.n):
            h = self.impulse(-alpha[k])
            acc = np.dot(h[k:0:-1], z[:k]) if k else 0.0
            z[k] = (x[k] - acc) / h[0]
        return z

    def E(self, x, alpha):
        z = np.empty(self.n)
        acc = np.zeros(self.n)
        for k in range(self.n):
            h = self.impulse(-alpha[k])
            z[k] = (x[k] - acc[k]) / h[0]
            acc[k + 1:] += h[1: self.n - k] * z[k]
        return z

    def all(self, x, alpha):
        return {t: getattr(self, t)(x, alpha) for t in "ABDE"}
