import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.design import design_dt  # noqa: E402
from vofrac.reference import gl_A, gl_B  # noqa: E402
from vofrac.tracking import CoeffSpline, ekf_A, ekf_B, ekf_gl_A, grid_filter_A  # noqa: E402

N = 400
TS = 1.0


def _setup():
    d = design_dt(TS, N, -0.95, 0.95, 1e-5)
    bank = DiscreteFixedPoleBank(TS, d["xi_lo"], d["xi_hi"], d["K"], dc_floor=False)
    rng = np.random.default_rng(5)
    e = rng.standard_normal(N)
    x = np.zeros(N)
    for k in range(1, N):
        x[k] = 0.95 * x[k - 1] + e[k]
    alpha = np.where(np.arange(N) < N // 2, 0.3, 0.5)
    return bank, x, alpha, rng


def test_bank_ekf_reproduces_gl_ekf():
    bank, x, alpha, rng = _setup()
    y = gl_A(x, alpha, TS)
    sig = 1e-2 * np.std(y)
    yn = y + sig * rng.standard_normal(N)
    a1 = ekf_A(CoeffSpline(bank), x, yn, 1e-5, sig ** 2)[0]
    a2 = ekf_gl_A(x, yn, TS, 1e-5, sig ** 2)[0]
    assert np.max(np.abs(a1 - a2)) < 1e-4


def test_matched_filters_track_and_wrong_type_is_biased():
    bank, x, alpha, rng = _setup()
    cs = CoeffSpline(bank)
    late = np.arange(N) >= N // 2 + 50
    yA, yB = gl_A(x, alpha, TS), gl_B(x, alpha, TS)
    sA, sB = 1e-3 * np.std(yA), 1e-3 * np.std(yB)
    grid_on_A = grid_filter_A(bank, x, yA + sA * rng.standard_normal(N), 1e-5, sA ** 2)[0]
    b_on_B = ekf_B(cs, x, yB + sB * rng.standard_normal(N), 1e-5, sB ** 2, gate=16.0, p_jump=5e-4)[0]
    grid_on_B = grid_filter_A(bank, x, yB + sB * rng.standard_normal(N), 1e-5, sB ** 2)[0]
    err = lambda a: float(np.sqrt(np.mean((a - alpha)[late] ** 2)))
    assert err(grid_on_A) < 0.01
    assert err(b_on_B) < 0.03
    assert err(grid_on_B) > 3 * err(grid_on_A)


def test_unscented_gl_filters():
    from vofrac.tracking import ukf_bank_A, ukf_gl_A, ukf_gl_B
    bank, x, alpha, rng = _setup()
    cs = CoeffSpline(bank)
    late = np.arange(N) >= N // 2 + 50
    err = lambda a: float(np.sqrt(np.mean((a - alpha)[late] ** 2)))
    yA = gl_A(x, alpha, TS)
    sA = 1e-2 * np.std(yA)
    ya = yA + sA * rng.standard_normal(N)
    a_gl = ukf_gl_A(x, ya, TS, N, 1e-5, sA ** 2, gate=16.0, p_jump=5e-4)[0]
    a_bank = ukf_bank_A(cs, x, ya, 1e-5, sA ** 2, gate=16.0, p_jump=5e-4)[0]
    assert np.max(np.abs(a_gl - a_bank)) < 1e-3          # full GL memory = bank model
    assert err(a_gl) < 0.03
    yB = gl_B(x, alpha, TS)
    sB = 1e-3 * np.std(yB)
    a_b = ukf_gl_B(x, yB + sB * rng.standard_normal(N), TS, 5, 1e-5, sB ** 2, gate=16.0, p_jump=5e-4)[0]
    assert err(a_b) < 0.03
