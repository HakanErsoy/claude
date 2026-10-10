"""Test scenarios: references, wave and current disturbances, sensor noise, plant variations.

The four test cases extend the single-axis tests of the earlier surge study
(step; step with strong white noise; sinusoidal "storm"; multi-level set
points under the storm) to all six DOF. Optimization uses two separate
training cases with other disturbance realizations.
"""

from dataclasses import dataclass, field, replace

import numpy as np
from scipy.linalg import expm

from . import params, thruster

DT = 0.01
W_REF = 1.0                                         # rad/s, critically damped reference model
WAVE_AMP = np.array([20.0, 20.0, 15.0, 1.0, 1.0, 1.0])     # N, N m (per DOF, sum of 5 sinusoids)
WAVE_W = (0.4, 1.6)                                 # rad/s (periods 4 to 16 s)
CURRENT = (0.25, np.deg2rad(30.0))                  # m/s, direction in the horizontal plane
# Sensor noise at the control rate (one sigma): USBL/DVL-aided position, depth
# sensor, IMU attitude; DVL velocity, gyro rates. T2 uses SEVERE times these
# values and adds white process noise.
NOISE_ETA = np.array([0.01, 0.01, 0.005, 0.003, 0.003, 0.005])   # m, rad
NOISE_NU = np.array([0.01, 0.01, 0.01, 0.005, 0.005, 0.005])     # m/s, rad/s
SEVERE = 3.0
PROC_NOISE = np.array([5.0, 5.0, 5.0, 0.3, 0.3, 0.3])            # N, N m
W_DOF = np.array([1.0, 1.0, 1.0, 2.0, 2.0, 2.0])   # cost weights: 1 m of error ~ 0.5 rad


@dataclass
class Scenario:
    name: str
    t: np.ndarray
    raw: np.ndarray          # piecewise-constant set points [nt, 6]
    ref: np.ndarray          # filtered reference [nt, 6]
    dist: np.ndarray         # tau_d [nt, 6]
    vcn: np.ndarray          # current in NED [nt, 3]
    noise: np.ndarray        # [nt, 12] added to (eta, nu)
    veh: np.ndarray = field(default_factory=params.pack)
    Tal: np.ndarray = field(default_factory=params.allocation)
    ca_true: np.ndarray = field(default_factory=thruster.coef_array)
    tau_m: float = thruster.TAU_MOTOR
    fail: np.ndarray = field(default_factory=lambda: np.ones(8))
    dt: float = DT

    def variant(self, name, **kw):
        return replace(self, name=name, **kw)


def setpoints(t, steps):
    """Piecewise-constant set points from [(t0, dof, value), ...]."""
    raw = np.zeros((t.size, 6))
    for t0, d, v in sorted(steps):
        raw[t >= t0, d] = v
    return raw


def prefilter(raw, dt, w=W_REF):
    """Critically damped second-order reference model, exact ZOH discretization."""
    A = np.array([[0.0, 1.0], [-w * w, -2.0 * w]])
    Bv = np.array([0.0, w * w])
    E = expm(np.block([[A, Bv[:, None]], [np.zeros((1, 3))]]) * dt)
    Ad, Bd = E[:2, :2], E[:2, 2]
    out = np.zeros_like(raw)
    s = np.zeros((2, raw.shape[1]))
    for k in range(raw.shape[0]):
        out[k] = s[0]
        s = Ad @ s + Bd[:, None] * raw[k]
    return out


def waves(t, seed, amp=WAVE_AMP, K=5):
    """Sum of K sinusoids per DOF with random frequencies in WAVE_W and random phases."""
    rng = np.random.default_rng(seed)
    w = rng.uniform(*WAVE_W, size=(6, K))
    ph = rng.uniform(0, 2 * np.pi, size=(6, K))
    return np.sum(np.sin(w[None] * t[:, None, None] + ph[None]), axis=2) * (amp / np.sqrt(K))


def current(t, speed=CURRENT[0], beta=CURRENT[1]):
    v = speed * (1.0 + 0.2 * np.sin(0.05 * t))
    return np.stack([v * np.cos(beta), v * np.sin(beta), np.zeros_like(t)], 1)


def make(name, T, steps, storm=None, noise=None, severe=False, dt=DT):
    t = np.arange(0.0, T + 0.5 * dt, dt)
    raw = setpoints(t, steps)
    dist = np.zeros((t.size, 6))
    vcn = np.zeros((t.size, 3))
    nz = np.zeros((t.size, 12))
    if storm is not None:
        dist += waves(t, storm)
        vcn = current(t)
    if noise is not None:
        rng = np.random.default_rng(noise)
        nz = rng.standard_normal((t.size, 12)) * np.concatenate([NOISE_ETA, NOISE_NU]) * (SEVERE if severe else 1.0)
        if severe:
            dist += rng.standard_normal((t.size, 6)) * PROC_NOISE
    return Scenario(name, t, raw, prefilter(raw, dt), dist, vcn, nz, dt=dt)


PI4, PI6 = np.pi / 4, np.pi / 6
STEP = [(1.0, 0, 1.0), (1.0, 1, 0.5), (1.0, 2, 0.5), (1.0, 5, PI4)]
MULTI = [(1.0, 0, 1.0), (20.0, 0, 0.5), (40.0, 0, 1.5),
         (10.0, 1, 0.5), (30.0, 1, -0.5),
         (1.0, 2, 0.5), (25.0, 2, 1.0), (45.0, 2, 0.3),
         (5.0, 5, PI4), (35.0, 5, -PI4), (50.0, 5, 0.0)]


def training():
    """Cases used inside the optimization (disturbance seeds differ from the tests)."""
    return [make("train-step", 20.0, STEP, noise=11),
            make("train-storm", 30.0, [(15.0, 5, PI6), (15.0, 2, 0.3)], storm=101, noise=12)]


def tests():
    """The four test cases (T1-T4)."""
    return [make("T1-step", 25.0, STEP),
            make("T2-noise", 25.0, STEP, noise=202, severe=True),
            make("T3-storm", 40.0, [(10.0, 0, 0.5), (20.0, 5, PI6), (30.0, 2, 0.3)], storm=303, noise=303),
            make("T4-multi-storm", 60.0, MULTI, storm=404, noise=404)]


def robustness(base):
    """Plant and actuator variations on a base scenario (the controller is not retuned)."""
    out = []
    for f in (0.8, 1.2):
        out.append(base.variant(f"{base.name}|mass x{f}", veh=params.pack(mass=f)))
    for f in (0.5, 1.5):
        out.append(base.variant(f"{base.name}|added x{f}", veh=params.pack(added=f)))
        out.append(base.variant(f"{base.name}|damping x{f}", veh=params.pack(damping=f)))
    out.append(base.variant(f"{base.name}|buoyancy +3%", veh=params.pack(buoyancy=1.03)))
    for v in (12, 20):
        out.append(base.variant(f"{base.name}|battery {v} V", ca_true=thruster.coef_array(v)))
    for tm in (0.05, 0.2):
        out.append(base.variant(f"{base.name}|tau_m {tm}", tau_m=tm))
    for i in (0, 4):
        fl = np.ones(8)
        fl[i] = 0.0
        out.append(base.variant(f"{base.name}|thruster {i + 1} lost", fail=fl))
    return out
