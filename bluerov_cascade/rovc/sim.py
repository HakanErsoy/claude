"""Closed-loop simulation of the BlueROV2 Heavy (6 DOF) with eight T200 thrusters.

Plant (Fossen 2011, irrotational current, M_A d(nu_c)/dt neglected):

    M nu_dot + C_RB(nu) nu + C_A(nu_r) nu_r + D(nu_r) nu_r + g(eta) = T f + tau_d,
    eta_dot = J(eta) nu,   nu_r = nu - [R^T v_c; 0],

integrated by RK4 at the control period dt with the thrust held. Each thruster:
allocation f_d = T^+ tau (scaled down as a whole if a limit is hit), command
u = F_nom^{-1}(f_d) with the nominal 16 V curve (dead band compensated), static
thrust F_true(u) of the actual curve, first-order lag tau_m. The command reaches
the thrusters `delay` samples after the measurement it was computed from
(computation, communication and ESC latency; 1 sample = 10 ms by default).

Metrics per run (true state, NED / Euler-angle errors against the filtered
reference): ITAE, IAE, ISE per DOF, electrical energy (power of the actual,
lagged thrust from the T200 curves), peak |error| per DOF, the fraction of the
horizon lost to divergence and the command activity (total variation of the
eight normalized commands per second).
"""

import math

import numpy as np
from numba import njit, prange

from . import params, thruster
from .controllers import NOP, build
from .fractional import NSEC

NM = 6 * 4 + 3           # itae, iae, ise, peak (6 each), energy, fail fraction, command activity
I_ITAE, I_IAE, I_ISE, I_PEAK, I_E, I_FAIL, I_TV = 0, 6, 12, 18, 24, 25, 26


@njit(cache=True, fastmath=False)
def _deriv(x, tau, veh, vcn, dx):
    phi, th, psi = x[3], x[4], x[5]
    u, v, w, p, q, r = x[6], x[7], x[8], x[9], x[10], x[11]
    cf, sf = math.cos(phi), math.sin(phi)
    ct, st = math.cos(th), math.sin(th)
    cp, sp = math.cos(psi), math.sin(psi)
    R00, R01, R02 = cp * ct, cp * st * sf - sp * cf, cp * st * cf + sp * sf
    R10, R11, R12 = sp * ct, sp * st * sf + cp * cf, sp * st * cf - cp * sf
    R20, R21, R22 = -st, ct * sf, ct * cf
    dx[0] = R00 * u + R01 * v + R02 * w
    dx[1] = R10 * u + R11 * v + R12 * w
    dx[2] = R20 * u + R21 * v + R22 * w
    tt = st / ct
    dx[3] = p + sf * tt * q + cf * tt * r
    dx[4] = cf * q - sf * r
    dx[5] = (sf * q + cf * r) / ct
    # current in the body frame
    ub = R00 * vcn[0] + R10 * vcn[1] + R20 * vcn[2]
    vb = R01 * vcn[0] + R11 * vcn[1] + R21 * vcn[2]
    wb = R02 * vcn[0] + R12 * vcn[1] + R22 * vcn[2]
    ur, vr, wr = u - ub, v - vb, w - wb
    m, Ix, Iy, Iz = veh[0], veh[1], veh[2], veh[3]
    A0, A1, A2, A3, A4, A5 = veh[4], veh[5], veh[6], veh[7], veh[8], veh[9]
    W, B = veh[22], veh[23]
    xg, yg, zg, xb, yb, zb = veh[24], veh[25], veh[26], veh[27], veh[28], veh[29]
    # rigid-body Coriolis
    c0 = m * (q * w - r * v)
    c1 = m * (r * u - p * w)
    c2 = m * (p * v - q * u)
    c3 = (Iz - Iy) * q * r
    c4 = (Ix - Iz) * r * p
    c5 = (Iy - Ix) * p * q
    # added-mass Coriolis C_A(nu_r) nu_r
    av0, av1, av2 = A0 * ur, A1 * vr, A2 * wr
    aw0, aw1, aw2 = A3 * p, A4 * q, A5 * r
    c0 += q * av2 - r * av1
    c1 += r * av0 - p * av2
    c2 += p * av1 - q * av0
    c3 += vr * av2 - wr * av1 + q * aw2 - r * aw1
    c4 += wr * av0 - ur * av2 + r * aw0 - p * aw2
    c5 += ur * av1 - vr * av0 + p * aw1 - q * aw0
    # damping
    d0 = (veh[10] + veh[16] * abs(ur)) * ur
    d1 = (veh[11] + veh[17] * abs(vr)) * vr
    d2 = (veh[12] + veh[18] * abs(wr)) * wr
    d3 = (veh[13] + veh[19] * abs(p)) * p
    d4 = (veh[14] + veh[20] * abs(q)) * q
    d5 = (veh[15] + veh[21] * abs(r)) * r
    # restoring
    g0 = (W - B) * st
    g1 = -(W - B) * ct * sf
    g2 = -(W - B) * ct * cf
    g3 = -(yg * W - yb * B) * ct * cf + (zg * W - zb * B) * ct * sf
    g4 = (zg * W - zb * B) * st + (xg * W - xb * B) * ct * cf
    g5 = -(xg * W - xb * B) * ct * sf - (yg * W - yb * B) * st
    dx[6] = (tau[0] - c0 - d0 - g0) / (m + A0)
    dx[7] = (tau[1] - c1 - d1 - g1) / (m + A1)
    dx[8] = (tau[2] - c2 - d2 - g2) / (m + A2)
    dx[9] = (tau[3] - c3 - d3 - g3) / (Ix + A3)
    dx[10] = (tau[4] - c4 - d4 - g4) / (Iy + A4)
    dx[11] = (tau[5] - c5 - d5 - g5) / (Iz + A5)


@njit(cache=True)
def _rk4(x, tau, veh, vcn, dt, k1, k2, k3, k4, tmp):
    _deriv(x, tau, veh, vcn, k1)
    for i in range(12):
        tmp[i] = x[i] + 0.5 * dt * k1[i]
    _deriv(tmp, tau, veh, vcn, k2)
    for i in range(12):
        tmp[i] = x[i] + 0.5 * dt * k2[i]
    _deriv(tmp, tau, veh, vcn, k3)
    for i in range(12):
        tmp[i] = x[i] + dt * k3[i]
    _deriv(tmp, tau, veh, vcn, k4)
    for i in range(12):
        x[i] += dt / 6.0 * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i])


@njit(cache=True)
def _op(e, sec, z, iz, integ, dt):
    """One sample of a slot: optional Tustin integrator, then NSEC Tustin sections."""
    x = e
    if integ:
        y = iz[0] + 0.5 * dt * (x + iz[1])
        iz[1] = x
        iz[0] = y
        x = y
    for k in range(sec.shape[0]):
        y = sec[k, 0] * x + sec[k, 1] * z[k] - sec[k, 2] * z[k + 1]
        z[k] = x
        x = y
    z[sec.shape[0]] = x
    return x


@njit(cache=True)
def _cubic(z, k0, k1, k2):
    return z * (k0 + z * (k1 + z * k2))


@njit(cache=True)
def _force(u, ca):
    if u > ca[0]:
        return _cubic(u - ca[0], ca[2], ca[3], ca[4])
    if u < -ca[1]:
        return -_cubic(-u - ca[1], ca[5], ca[6], ca[7])
    return 0.0


@njit(cache=True)
def _power(u, ca):
    p = 0.0
    if u > ca[8]:
        p = _cubic(u - ca[8], ca[10], ca[11], ca[12])
    elif u < -ca[9]:
        p = _cubic(-u - ca[9], ca[13], ca[14], ca[15])
    return max(p, 0.0)


@njit(cache=True)
def _power_f(F, ca):
    z = abs(F)
    if F > 0.0:
        p = _cubic(z, ca[18], ca[19], ca[20])
    else:
        p = _cubic(z, ca[21], ca[22], ca[23])
    return max(p, 0.0)


@njit(cache=True)
def _inverse(F, ca):
    """Command u with F_nom(u) = F (monotone curve, Newton with clamping)."""
    if F == 0.0:
        return 0.0
    if F > 0.0:
        d, k0, k1, k2, fm = ca[0], ca[2], ca[3], ca[4], ca[16]
        F = min(F, fm)
        sgn = 1.0
    else:
        d, k0, k1, k2, fm = ca[1], ca[5], ca[6], ca[7], -ca[17]
        F = min(-F, fm)
        sgn = -1.0
    zmax = 1.0 - d
    z = zmax * F / fm
    for _ in range(12):
        g = _cubic(z, k0, k1, k2) - F
        dg = k0 + z * (2.0 * k1 + 3.0 * k2 * z)
        z = min(max(z - g / dg, 0.0), zmax)
    return sgn * (d + z)


@njit(cache=True)
def _wrap(a):
    return (a + math.pi) % (2.0 * math.pi) - math.pi


@njit(cache=True)
def simulate(kp1, kp2, sec, gain, integ, stage, cascade,
             ref, dist, vcn, noise, veh, Mnom, Tal, Tpinv, ca_true, ca_nom, tau_m, fail, dt, nd, rec, trace):
    """One closed-loop run with an nd-sample command delay; returns the metric vector (layout NM)."""
    nt = ref.shape[0]
    out = np.zeros(NM)
    x = np.zeros(12)
    f = np.zeros(8)
    fd = np.zeros(8)
    ucmd = np.zeros(8)
    ubuf = np.zeros((nd + 1, 8))
    tau_c = np.zeros(6)
    tau = np.zeros(6)
    e1 = np.zeros(6)
    k1, k2, k3, k4, tmp = np.zeros(12), np.zeros(12), np.zeros(12), np.zeros(12), np.zeros(12)
    z = np.zeros((6, NOP, NSEC + 1))
    iz = np.zeros((6, NOP, 2))
    lag = math.exp(-dt / tau_m)
    T = (nt - 1) * dt
    for k in range(nt):
        t = k * dt
        # cost on the true state
        for d in range(6):
            e = ref[k, d] - x[d]
            if d == 5:
                e = _wrap(e)
            ae = abs(e)
            out[I_ITAE + d] += t * ae * dt
            out[I_IAE + d] += ae * dt
            out[I_ISE + d] += e * e * dt
            if ae > out[I_PEAK + d]:
                out[I_PEAK + d] = ae
        # measurement and errors (translation in the body frame)
        phi, th, psi = x[3] + noise[k, 3], x[4] + noise[k, 4], x[5] + noise[k, 5]
        cf, sf = math.cos(phi), math.sin(phi)
        ct, st = math.cos(th), math.sin(th)
        cp, sp = math.cos(psi), math.sin(psi)
        en0 = ref[k, 0] - x[0] - noise[k, 0]
        en1 = ref[k, 1] - x[1] - noise[k, 1]
        en2 = ref[k, 2] - x[2] - noise[k, 2]
        e1[0] = cp * ct * en0 + sp * ct * en1 - st * en2
        e1[1] = (cp * st * sf - sp * cf) * en0 + (sp * st * sf + cp * cf) * en1 + ct * sf * en2
        e1[2] = (cp * st * cf + sp * sf) * en0 + (sp * st * cf - cp * sf) * en1 + ct * cf * en2
        e1[3] = ref[k, 3] - phi
        e1[4] = ref[k, 4] - th
        e1[5] = _wrap(ref[k, 5] - psi)
        for d in range(6):
            u1 = kp1[d] * e1[d]
            for j in range(NOP):
                if stage[j] == 0 and gain[d, j] != 0.0:
                    u1 += gain[d, j] * _op(e1[d], sec[d, j], z[d, j], iz[d, j], integ[d, j], dt)
            a = u1
            if cascade:
                e2 = u1 - (x[6 + d] + noise[k, 6 + d])
                a = kp2[d] * e2
                for j in range(NOP):
                    if stage[j] == 1 and gain[d, j] != 0.0:
                        a += gain[d, j] * _op(e2, sec[d, j], z[d, j], iz[d, j], integ[d, j], dt)
            tau_c[d] = Mnom[d] * a
        # allocation with direction-preserving scaling
        s = 1.0
        for i in range(8):
            acc = 0.0
            for d in range(6):
                acc += Tpinv[i, d] * tau_c[d]
            fd[i] = acc
            if acc > ca_nom[16]:
                s = min(s, ca_nom[16] / acc)
            elif acc < ca_nom[17]:
                s = min(s, ca_nom[17] / acc)
        pw = 0.0
        wr = k % (nd + 1)
        rd = (k - nd) % (nd + 1)
        for i in range(8):
            ubuf[wr, i] = _inverse(fd[i] * s, ca_nom)
        for i in range(8):
            if k > 0:
                out[I_TV] += abs(ubuf[rd, i] - ucmd[i])
            ucmd[i] = ubuf[rd, i]
            Fs = _force(ucmd[i], ca_true) * fail[i]
            f[i] = Fs + (f[i] - Fs) * lag
            if fail[i] > 0.0:
                pw += _power_f(f[i], ca_true)
        out[I_E] += pw * dt
        for d in range(6):
            acc = dist[k, d]
            for i in range(8):
                acc += Tal[d, i] * f[i]
            tau[d] = acc
        if rec:
            for i in range(12):
                trace[k, i] = x[i]
            for i in range(8):
                trace[k, 12 + i] = f[i]
            for d in range(6):
                trace[k, 20 + d] = tau_c[d]
        _rk4(x, tau, veh, vcn[k], dt, k1, k2, k3, k4, tmp)
        bad = False
        for i in range(12):
            if not math.isfinite(x[i]):
                bad = True
        if bad or abs(x[3]) > 1.4 or abs(x[4]) > 1.4 or abs(x[6]) + abs(x[7]) + abs(x[8]) > 5.0 \
                or abs(x[0]) + abs(x[1]) + abs(x[2]) > 100.0:
            out[I_FAIL] = (T - t) / T if T > 0 else 1.0
            return out
    if T > 0:
        out[I_TV] /= T
    return out


@njit(cache=True, parallel=True)
def _batch(kp1, kp2, sec, gain, integ, stage, cascade,
           ref, dist, vcn, noise, veh, Mnom, Tal, Tpinv, ca_true, ca_nom, tau_m, fail, dt, nd):
    P = kp1.shape[0]
    out = np.zeros((P, NM))
    dummy = np.zeros((1, 26))
    for i in prange(P):
        out[i] = simulate(kp1[i], kp2[i], sec[i], gain[i], integ[i], stage, cascade,
                          ref, dist, vcn, noise, veh, Mnom, Tal, Tpinv, ca_true, ca_nom, tau_m, fail, dt, nd,
                          False, dummy)
    return out


class Plant:
    """Nominal model data shared by the controller (inertia, allocation, thrust map)."""

    def __init__(self):
        self.Mnom = params.mass_diag()
        self.Tal = params.allocation()
        self.Tpinv = np.linalg.pinv(self.Tal)
        self.ca_nom = thruster.coef_array(thruster.NOMINAL_VOLT)


PLANT = Plant()


def run(struct, X, sc, trace=False):
    """Metrics [P, NM] of a batch of parameter vectors on scenario `sc` (rovc.scenarios.Scenario).

    trace=True runs the first candidate only and also returns its trace [nt, 26]:
    eta (6), nu (6), thrust (8), commanded tau (6).
    """
    arrs = build(struct, X, sc.dt)
    common = (sc.ref, sc.dist, sc.vcn, sc.noise, sc.veh, PLANT.Mnom, sc.Tal, PLANT.Tpinv,
              sc.ca_true, PLANT.ca_nom, sc.tau_m, sc.fail, sc.dt, int(sc.delay))
    if trace:
        tr = np.zeros((sc.ref.shape[0], 26))
        a = [v[0] if isinstance(v, np.ndarray) and v.ndim and k in (0, 1, 2, 3, 4) else v
             for k, v in enumerate(arrs)]
        m = simulate(*a, *common, True, tr)
        return m, tr
    return _batch(*arrs, *common)
