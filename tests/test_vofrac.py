import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.bank import FixedPoleBank  # noqa: E402
from vofrac.oustaloup import SwitchedOustaloup  # noqa: E402
from vofrac.reference import gl_A, gl_B, step_A, step_B_piecewise, step_B_smooth  # noqa: E402


@pytest.mark.parametrize("a1,a2", [(-0.3, -0.7), (0.3, 0.7), (-0.5, 0.5), (0.7, 0.2)])
def test_closed_form_matches_gl_first_order(a1, a2):
    T, Tend = 1.0, 2.0
    errs = []
    for h in (2e-3, 1e-3):
        t = np.arange(int(round(Tend / h)) + 1) * h
        alpha = np.where(t < T - 1e-12, a1, a2)
        u = np.ones_like(t)
        w = t > T + 0.05
        eA = np.abs(gl_A(u, alpha, h) - step_A(t, alpha))[w].max()
        eB = np.abs(gl_B(u, alpha, h) - step_B_piecewise(t, [T], [a1, a2]))[w].max()
        errs.append((eA, eB))
    # GL is O(h): halving h halves the error
    for k in range(2):
        assert errs[1][k] < 0.6 * errs[0][k]
        assert errs[1][k] < 1e-2


@pytest.mark.parametrize("offset", [-0.5, 0.5, 0.0])
def test_smooth_B_formula_matches_gl(offset):
    amp = 0.6 if offset == 0.0 else 0.3
    fa = lambda t: offset + amp * np.sin(np.pi * t / 2)
    dfa = lambda t: amp * np.pi / 2 * np.cos(np.pi * t / 2)
    h = 1e-3
    t = np.arange(2001) * h
    y = gl_B(np.ones_like(t), fa(t), h)
    ts = np.array([0.5, 1.0, 1.5, 2.0])
    ref = step_B_smooth(ts, fa, dfa)
    assert np.allclose(y[np.round(ts / h).astype(int)], ref, atol=3e-3)


def test_bank_frequency_response_uniform_in_order():
    bank = FixedPoleBank(1e-4, 1e6, 20)
    w = np.logspace(-1, 3, 200)
    for a in (-0.9, -0.5, -0.1, -0.01, 0.01, 0.1, 0.5, 0.9):
        ratio = bank.freqresp(a, w) / (1j * w) ** a
        assert np.abs(20 * np.log10(np.abs(ratio))).max() < 0.01
        assert np.abs(np.degrees(np.angle(ratio))).max() < 0.06


def test_bank_continuous_through_zero():
    bank = FixedPoleBank(1e-3, 1e5, 21)
    for a in (-1e-9, 1e-9):
        m, d = bank.coeffs(a)
        assert np.abs(m).max() < 1e-7
        assert abs(d - 1.0) < 1e-7


def test_oustaloup_forms_share_transfer_function():
    w = np.logspace(-1, 3, 50)
    for a in (-0.6, 0.4):
        Hp = SwitchedOustaloup(1e-3, 1e5, 6, "parallel").freqresp(a, w)
        Hc = SwitchedOustaloup(1e-3, 1e5, 6, "cascade").freqresp(a, w)
        assert np.allclose(Hp, Hc, rtol=1e-8)


@pytest.mark.parametrize("a1,a2", [(-0.3, -0.7), (0.3, 0.7)])
def test_fixed_pole_schedules_select_definition(a1, a2):
    Ts, T, Tend = 1e-3, 1.0, 2.0
    t = np.arange(int(round(Tend / Ts)) + 1) * Ts
    alpha = np.where(t < T - 1e-12, a1, a2)
    u = np.ones_like(t)
    rA = step_A(t, alpha)
    rB = step_B_piecewise(t, [T], [a1, a2])
    w = t > T + 0.05
    rel = lambda y, r: np.sqrt(np.mean((y - r)[w] ** 2) / np.mean(r[w] ** 2))
    bank = FixedPoleBank(1e-3, 1e5, 25)
    y_out = bank.simulate(u, alpha, Ts, "output")
    y_in = bank.simulate(u, alpha, Ts, "input")
    gap = rel(rA, rB)
    assert rel(y_out, rA) < 0.01 * gap
    assert rel(y_in, rB) < 0.01 * gap


def test_discrete_bank_reproduces_gl_weights():
    from vofrac.bank import DiscreteFixedPoleBank
    from vofrac.reference import _gl_weights
    Ts, R = 1e-3, 4000
    bank = DiscreteFixedPoleBank(Ts, 1e-4, 4e5, 32)
    for a in (-0.9, -0.5, -0.1, 0.1, 0.5, 0.9):
        ref = _gl_weights(a, R) * Ts ** (-a)
        g = bank.weights(a, R)
        assert g[0] == ref[0]
        assert np.max(np.abs(g[1:] - ref[1:]) / np.abs(ref[1:])) < 5e-4


def test_discrete_bank_definitional_error_is_zero():
    """Output schedule equals its own frozen-order A-type, input schedule its
    own B-type, to rounding, for any input and piecewise-constant order."""
    from vofrac.bank import DiscreteFixedPoleBank
    rng = np.random.default_rng(0)
    n = 600
    u = rng.standard_normal(n)
    alpha = np.repeat(rng.uniform(-0.8, 0.8, 6), n // 6)
    bank = DiscreteFixedPoleBank(1e-3, 1e-3, 4e5, 24)
    y_out = bank.simulate(u, alpha, "output")
    y_in = bank.simulate(u, alpha, "input")
    ownA = np.empty(n)
    ownB = np.zeros(n)
    for v in np.unique(alpha):
        mask = alpha == v
        const = np.full(n, v)
        ownA[mask] = bank.simulate(u, const, "output")[mask]
        ownB += bank.simulate(u * mask, const, "output")
    assert np.max(np.abs(y_out - ownA)) < 1e-12 * np.max(np.abs(ownA))
    assert np.max(np.abs(y_in - ownB)) < 1e-12 * np.max(np.abs(ownB))


def test_discrete_bank_tracks_gl_definitions():
    from vofrac.bank import DiscreteFixedPoleBank
    rng = np.random.default_rng(2)
    Ts, n = 1e-3, 1500
    t = np.arange(n) * Ts
    u = rng.standard_normal(n)
    alpha = 0.6 * np.sin(np.pi * t / 1.5)
    bank = DiscreteFixedPoleBank(Ts, 1e-4, 4e5, 32)
    rel = lambda y, r: np.sqrt(np.mean((y - r) ** 2) / np.mean(r ** 2))
    rA, rB = gl_A(u, alpha, Ts), gl_B(u, alpha, Ts)
    assert rel(bank.simulate(u, alpha, "output"), rA) < 1e-4
    assert rel(bank.simulate(u, alpha, "input"), rB) < 1e-4
