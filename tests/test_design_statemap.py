import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.bank import DiscreteFixedPoleBank, FixedPoleBank  # noqa: E402
from vofrac.design import (ct_quadrature, design_ct, design_dt, dt_quadrature,  # noqa: E402
                           measure_ct, measure_dt)
from vofrac.statemap import dt_oustaloup, end_states, fit_phi_A, input_ensemble, obsv, rel_err  # noqa: E402


@pytest.mark.parametrize("a", [-0.5, 0.5])
def test_ct_quadrature_model_is_exact(a):
    w1, w2, h = 1.0, 100.0, 0.9
    lo, hi = 1e-12, 1e14
    K = int(np.ceil(np.log(hi / lo) / h)) + 1
    bank = FixedPoleBank(lo, hi, K)
    meas = measure_ct(bank, w1, w2, a, a)
    assert abs(meas / ct_quadrature(a, bank.h) - 1) < 0.02


@pytest.mark.parametrize("a", [-0.9, 0.5])
def test_dt_quadrature_model_bounds_measurement(a):
    R, h, Ts = 5000, 0.8, 1e-3
    u_lo, u_hi = 1e-14 / R, 80.0 / (1 - a)
    K = int(np.ceil(np.log(u_hi / u_lo) / h)) + 1
    bank = DiscreteFixedPoleBank(Ts, u_lo / Ts, u_hi / Ts, K)
    ratio = measure_dt(bank, R, a, a) / dt_quadrature(a, bank.h)
    assert 0.3 < ratio < 1.1


@pytest.mark.parametrize("spec", [(4000, -0.9, 0.9, 1e-3), (100000, -0.95, -0.4, 1e-5), (500, 0.3, 0.95, 1e-2)])
def test_dt_rule_meets_tolerance(spec):
    R, amin, amax, eps = spec
    d = design_dt(1e-3, R, amin, amax, eps)
    bank = DiscreteFixedPoleBank(1e-3, d["xi_lo"], d["xi_hi"], d["K"])
    assert measure_dt(bank, R, amin, amax) <= eps


@pytest.mark.parametrize("spec", [((0.1, 1e3), -0.9, 0.9, 1e-3), ((1.0, 1e6), -0.5, 0.5, 1e-4), ((2.0, 20.0), 0.2, 0.9, 1e-2)])
def test_ct_rule_meets_tolerance(spec):
    (w1, w2), amin, amax, eps = spec
    d = design_ct(w1, w2, amin, amax, eps)
    bank = FixedPoleBank(d["xi_lo"], d["xi_hi"], d["K"])
    assert measure_ct(bank, w1, w2, amin, amax) <= eps


def test_similar_realizations_admit_exact_state_map():
    """Same order, parallel vs cascade: similar realizations, so the fitted map is exact."""
    Ts, n, L = 1e-3, 800, 400
    U = input_ensemble("white", 60, n, Ts, np.random.default_rng(3))
    sp = dt_oustaloup(0.4, 1e-2, 1e4, 4, "parallel", Ts)
    sc = dt_oustaloup(0.4, 1e-2, 1e4, 4, "cascade", Ts)
    Xp, Xc = end_states(sp[0], sp[1], U), end_states(sc[0], sc[1], U)
    P = fit_phi_A(Xp, Xc, 1e-14)
    O = obsv(sc[0], sc[2], L)
    assert rel_err(O @ (P @ Xp - Xc), O @ Xc) < 1e-8


def test_hot_swap_cascade_has_large_definitional_error():
    Ts, n, L = 1e-3, 1000, 1000
    U = np.ones((1, n))
    s1 = dt_oustaloup(-0.5, 1e-3, 1e5, 5, "cascade", Ts)
    s2 = dt_oustaloup(0.5, 1e-3, 1e5, 5, "cascade", Ts)
    x1, x2 = end_states(s1[0], s1[1], U), end_states(s2[0], s2[1], U)
    O2 = obsv(s2[0], s2[2], L)
    assert rel_err(O2 @ (x1 - x2), O2 @ x2) > 1.0
