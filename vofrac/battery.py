"""Panasonic 18650PF data (Kollmeyer, doi:10.17632/wykht8y7tg.1, CC BY 4.0) for E12.

Model of the terminal voltage v under the current i (discharge negative):

    v_n - OCV(z_n) = c0 + R0 i_n + kappa (Delta^{-beta} i)_n,

with the state of charge z from coulomb counting, an open-circuit-voltage
curve from the C/20 test, and a fractional integral of order beta in (0, 1)
for the diffusion and polarization (a Warburg-type element; beta = 1/2 is
the classical Warburg). beta may vary in time (A- or B-type).
"""

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.io import loadmat

Q_REF = 2.968          # Ah, discharged capacity of the C/20 test at 25 degC (reference for z)


def load(path):
    """(time [s], voltage [V], current [A], Ah, cell temperature [degC]) from one test file."""
    m = loadmat(path, squeeze_me=True, struct_as_record=False)["meas"]
    t = np.asarray(m.Time, dtype=float)
    keep = np.r_[True, np.diff(t) > 0]                    # drop repeated time stamps
    return (t[keep], np.asarray(m.Voltage, float)[keep], np.asarray(m.Current, float)[keep],
            np.asarray(m.Ah, float)[keep], np.asarray(m.Battery_Temp_degC, float)[keep])


def resample(t, *signals, Ts=1.0):
    """Bin means on a uniform grid of step Ts (charge-preserving for the current)."""
    edges = np.arange(t[0], t[-1] + Ts, Ts)
    idx = np.clip(np.searchsorted(edges, t, side="right") - 1, 0, len(edges) - 2)
    n = len(edges) - 1
    cnt = np.bincount(idx, minlength=n).astype(float)
    ok = cnt > 0
    out = []
    for s in signals:
        acc = np.bincount(idx, weights=s, minlength=n)
        mean = np.full(n, np.nan)
        mean[ok] = acc[ok] / cnt[ok]
        # empty bins (logging gaps): hold the previous value
        for k in np.where(~ok)[0]:
            mean[k] = mean[k - 1] if k else s[0]
        out.append(mean)
    return edges[:-1], out


def ocv_curve(path_c20):
    """OCV(z) as the mean of the C/20 discharge and charge curves at equal charge."""
    t, v, i, ah, _ = load(path_c20)
    z = 1.0 + (ah - ah.max()) / Q_REF
    dis, ch = i < -0.01, i > 0.01
    grid = np.linspace(0.0, 1.0, 201)

    def branch(mask):
        zz, vv = z[mask], v[mask]
        order = np.argsort(zz)
        zz, uniq = np.unique(zz[order], return_index=True)
        return np.interp(grid, zz, vv[order][uniq])

    ocv = 0.5 * (branch(dis) + branch(ch))
    return PchipInterpolator(grid, ocv, extrapolate=True)


def prepare(path, ocv, Ts=1.0):
    """Uniform series: time, current, residual y = v - OCV(z), z, temperature, voltage."""
    t, v, i, ah, T = load(path)
    tt, (vv, ii, aa, TT) = resample(t, v, i, ah, T, Ts=Ts)
    z = 1.0 + aa / Q_REF
    return {"t": tt - tt[0], "i": ii, "y": vv - ocv(np.clip(z, 0.0, 1.0)), "z": z, "T": TT, "v": vv}


def trim_rest(d, i_min=0.05, lead=60):
    """Drop the leading rest (e.g. the soak to the chamber temperature) up to `lead`
    samples before the first |i| > i_min. The input is zero there, so every bank
    and RC state is zero at the new start and nothing else changes."""
    k = int(np.argmax(np.abs(d["i"]) > i_min))
    k = max(0, k - lead)
    return {key: v[k:] for key, v in d.items()}


# ------------------------------------------------------------------ regressors
#
# All models share  y_n = c(z_n) + R0(z_n) i_n + sum_m b_m(z_n) psi_m(i)_n,
# with the gains piecewise linear in the state of charge z (hat basis) and
# nonlinear parameters (lag time constants, the order path beta(z)) fitted
# by search; for fixed nonlinear parameters the gains follow from least squares.

def rc_regressors(i, taus, Ts=1.0):
    """Unit-DC-gain first-order lags of the current (zero-order hold), one column per tau."""
    from scipy.signal import lfilter
    out = np.empty((len(i), len(taus)))
    for g, tau in enumerate(taus):
        a = np.exp(-Ts / tau)
        out[:, g] = lfilter([0.0, 1.0 - a], [1.0, -a], i)
    return out


# ------------------------------------------------------------------ order paths
#
# An order path beta_n = beta(z_n) changes from sample to sample. Orders
# between grid points use linearly interpolated bank coefficients; for the
# A-type this equals interpolating the columns of FOPath.columns_A.

def frac_index(grid, x):
    """(j, w) with x = (1 - w) grid[j] + w grid[j + 1], clipped to the grid."""
    grid = np.asarray(grid, float)
    x = np.clip(np.asarray(x, float), grid[0], grid[-1])
    j = np.clip(np.searchsorted(grid, x, side="right") - 1, 0, len(grid) - 2)
    return j, (x - grid[j]) / (grid[j + 1] - grid[j])


def pick(P, j, w):
    """Row-wise interpolation between columns j and j + 1 of P."""
    n = np.arange(P.shape[0])
    return (1.0 - w) * P[n, j] + w * P[n, j + 1]


class FOPath:
    """Unit-gain (Delta^{-beta_n} i)_n of one input record for sample-wise order
    paths: A-type (output schedule; one shared state, so a new path only changes
    the output weights) or B-type (input schedule; the order of each input sample
    stays with it)."""

    def __init__(self, bank, i, betas):
        from scipy.signal import lfilter
        self._lfilter = lfilter
        self.bank, self.i, self.betas = bank, np.asarray(i, float), np.asarray(betas, float)
        co = [bank.coeffs(-float(b)) for b in self.betas]
        self.g0 = np.array([c[0] for c in co])
        self.cd = np.array([c[1] for c in co])
        self.C = np.array([c[2] for c in co])                  # (G, K)
        self.S = np.column_stack([lfilter([0.0, 1.0], [1.0, -th], self.i) for th in bank.theta])
        self.sd = np.r_[0.0, self.i[:-1]]

    def columns_A(self):
        """A-type output for every grid order (n, G), the regressors of a constant order."""
        return self.i[:, None] * self.g0 + self.sd[:, None] * self.cd + self.S @ self.C.T

    def run(self, beta, vo_type):
        j, w = frac_index(self.betas, beta)
        g0 = (1 - w) * self.g0[j] + w * self.g0[j + 1]
        cd = (1 - w) * self.cd[j] + w * self.cd[j + 1]
        Cn = (1 - w)[:, None] * self.C[j] + w[:, None] * self.C[j + 1]      # (n, K)
        out = g0 * self.i
        if vo_type == "A":
            out += cd * self.sd + np.einsum("nk,nk->n", Cn, self.S)
        elif vo_type == "B":
            out[1:] += cd[:-1] * self.i[:-1]
            for k, th in enumerate(self.bank.theta):
                out += self._lfilter([0.0, 1.0], [1.0, -th], Cn[:, k] * self.i)
        else:
            raise ValueError(vo_type)
        return out


def hat_basis(z, knots):
    """Piecewise-linear (hat) basis on `knots`; z outside the knot range is clipped."""
    j, w = frac_index(knots, z)
    H = np.zeros((len(j), len(knots)))
    n = np.arange(len(j))
    H[n, j] += 1.0 - w
    H[n, j + 1] += w
    return H


class GainFit:
    """Least squares for  y = H a + (H * i) r + sum_m (H * psi_m) b_m  with the
    columns [H, H*i] fixed and the psi_m varying between calls."""

    def __init__(self, y, i, H):
        self.H = H
        self.y = y
        X0 = np.column_stack([H, H * i[:, None]])
        self.X0 = X0
        self.Q = np.linalg.qr(X0)[0]
        self.yp = y - self.Q @ (self.Q.T @ y)

    def design(self, *psis):
        return np.column_stack([self.X0] + [self.H * p[:, None] for p in psis])

    def sse(self, *psis):
        E = np.column_stack([self.H * p[:, None] for p in psis])
        Ep = E - self.Q @ (self.Q.T @ E)
        coef = np.linalg.lstsq(Ep, self.yp, rcond=None)[0]
        r = self.yp - Ep @ coef
        return float(r @ r)

    def coef(self, *psis):
        return np.linalg.lstsq(self.design(*psis), self.y, rcond=None)[0]
