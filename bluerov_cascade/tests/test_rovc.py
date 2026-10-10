import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rovc import controllers, fractional, optim, params, scenarios, sim, thruster  # noqa: E402
from rovc.controllers import STRUCTURES  # noqa: E402


@pytest.mark.parametrize("alpha", [-1.0, -0.7, -0.3, 0.4, 0.9])
def test_oustaloup_midband(alpha):
    w = np.logspace(np.log10(0.03), np.log10(3.0), 41)      # 1.5 decades inside each band edge
    h = fractional.freqresp("fo", 1.0, alpha, w)
    ref = (1j * w) ** alpha
    assert np.max(np.abs(20 * np.log10(np.abs(h / ref)))) < 0.1
    assert np.max(np.abs(np.angle(h / ref, deg=True))) < 2.0


def test_split_integrator():
    w = np.logspace(-2, 1, 31)
    h = fractional.freqresp("fo", 2.0, -1.4, w)
    assert np.max(np.abs(h / (2.0 * (1j * w) ** -1.4) - 1)) < 0.05


def test_discrete_half_integral_step():
    dt = 0.01
    zs, ps, k, it = fractional.slot_sections("fo", 1.0, -0.5)
    sec = fractional.tustin(zs, ps, dt)
    z = np.zeros(fractional.NSEC + 1)
    iz = np.zeros(2)
    t = np.arange(0, 10 + dt / 2, dt)
    y = np.array([k * sim._op(1.0, sec, z, iz, it, dt) for _ in t])
    exact = np.sqrt(t) / math.gamma(1.5)
    sel = t >= 1.0
    assert np.max(np.abs(y[sel] / exact[sel] - 1)) < 0.03


def test_allocation_and_mass():
    T = params.allocation()
    assert np.allclose(T @ np.linalg.pinv(T), np.eye(6))
    assert np.allclose(params.mass_diag()[:3], [19.857, 20.621, 32.19])


@pytest.mark.parametrize("volt", [12, 16, 20])
def test_thruster_inverse(volt):
    ca = thruster.coef_array(volt)
    F = np.linspace(ca[17], ca[16], 101)
    u = np.array([sim._inverse(f, ca) for f in F])
    assert np.max(np.abs(thruster.force(u, ca) - F)) < 1e-6
    assert np.all(np.diff(thruster.force(np.linspace(-1, 1, 401), ca)) >= -1e-9)


def _open_loop(dist_vec, T=40.0):
    t = np.arange(0, T + 0.005, 0.01)
    z = np.zeros((t.size, 6))
    sc = scenarios.Scenario("ol", t, z, z.copy(), np.tile(dist_vec, (t.size, 1)), np.zeros((t.size, 3)),
                            np.zeros((t.size, 12)))
    _, tr = sim.run(STRUCTURES["PID"], np.zeros(6), sc, trace=True)
    return tr


def test_surge_terminal_speed():
    tr = _open_loop(np.array([30.0, 0, 0, 0, 0, 0]))
    u_exp = (-13.7 + math.sqrt(13.7 ** 2 + 4 * 141 * 30)) / (2 * 141)
    assert abs(tr[-1, 6] - u_exp) < 1e-3
    assert np.max(np.abs(tr[:, 7:12])) < 1e-9


def test_roll_restoring():
    tr = _open_loop(np.array([0, 0, 0, 0.5, 0, 0]), T=60.0)
    assert abs(tr[-1, 3] - math.asin(0.5 / (0.01 * params.RHO * params.G * 0.0135))) < 2e-3


def test_closed_loop_converges():
    sc = scenarios.tests()[0]
    x = [4.35, 15.3, 20.0, 0.0, 19.7, 4.94, 20.0, 1.18]
    m, tr = sim.run(STRUCTURES["P-PID"], np.array(x), sc, trace=True)
    assert m[sim.I_FAIL] == 0
    err = sc.ref[-1] - tr[-1, :6]
    assert np.max(np.abs(err)) < 0.01


def test_structures_build():
    for s in STRUCTURES.values():
        x = 0.5 * (s.lb + s.ub)
        arrs = controllers.build(s, np.stack([x, s.lb]), 0.01)
        assert arrs[0].shape == (2, 6) and arrs[2].shape[2] == controllers.NOP
        assert len(s.labels()) == s.dim == s.lb.size


def test_optimizers_budget_and_invariance():
    D = 5
    for name in optim.METHODS:
        r = optim.minimize(name, lambda X: np.sum((X - 1.0) ** 2, 1), -5 * np.ones(D), 5 * np.ones(D), 333, pop=10)
        assert r["nfe"] <= 333 and np.isfinite(r["f"])
    # BC-SOO and DE do not depend on where the origin is; SOO does
    def run(name, shift):
        return [optim.minimize(name, lambda X: np.sum((X - shift) ** 2, 1), shift - 10 * np.ones(D),
                               shift + 10 * np.ones(D), 600, pop=10, seed=s)["f"] for s in range(3)]
    for name in ("BC-SOO", "DE"):
        assert np.allclose(run(name, 0.0), run(name, 50.0), rtol=1e-6, atol=1e-9)
