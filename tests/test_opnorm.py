import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.baselines import (FittedFixedPole, kernel_from, ltv_matrix, lp_residues, lp_lags,  # noqa: E402
                              moving_pole_levels)
from vofrac.design import design_dt  # noqa: E402
from vofrac.opnorm import (bank_table, gl_partial_abs_sum, gl_table, lower_inverse, norm,  # noqa: E402
                           operator_matrix, rel_weight_error, schur_constants)
from vofrac.reference import _gl_weights  # noqa: E402

TS = 1e-3
N = 240


@pytest.fixture(scope="module")
def bank():
    d = design_dt(TS, N, -0.9, 0.9, 1e-3)
    return DiscreteFixedPoleBank(TS, d["xi_lo"], d["xi_hi"], d["K"])


def _seq(rng, levels):
    return np.repeat(rng.choice(levels, 8), N // 8 + 1)[:N]


def test_operator_matrix_is_the_streaming_bank(bank):
    rng = np.random.default_rng(0)
    al = _seq(rng, np.array([-0.8, -0.3, 0.2, 0.7]))
    orders, idx = np.unique(al, return_inverse=True)
    tab = bank_table(bank, orders, N)
    x = rng.standard_normal(N)
    for T in "AB":
        y = bank.simulate_type(x, al, T)
        assert np.allclose(operator_matrix(tab, idx, T) @ x, y, rtol=1e-12, atol=1e-10)


def test_schur_bounds_hold_and_are_attained(bank):
    rng = np.random.default_rng(1)
    levels = np.array([-0.85, -0.4, 0.3, 0.85])
    Bt, Gt = bank_table(bank, levels, N), gl_table(levels, N, TS)
    err = Bt - Gt
    rho_row, rho_col = schur_constants(err)
    for al_idx in (rng.integers(0, 4, N), np.repeat(rng.integers(0, 4, 6), N // 6 + 1)[:N]):
        EA = operator_matrix(Bt, al_idx, "A") - operator_matrix(Gt, al_idx, "A")
        EB = operator_matrix(Bt, al_idx, "B") - operator_matrix(Gt, al_idx, "B")
        assert norm(EA, np.inf) <= rho_row * (1 + 1e-12)
        assert norm(EA, 1) <= rho_col * (1 + 1e-12)
        assert norm(EB, 1) <= rho_row * (1 + 1e-12)
        assert norm(EB, np.inf) <= rho_col * (1 + 1e-12)
        assert norm(EA, 2) <= np.sqrt(rho_row * rho_col) * (1 + 1e-12)
    # attainment: constant order maximizing the row sum; per-lag maximizing sequence
    a_star = np.abs(err[:, 1:]).sum(axis=1).argmax()
    const = np.full(N, a_star)
    EA = operator_matrix(Bt, const, "A") - operator_matrix(Gt, const, "A")
    assert norm(EA, np.inf) == pytest.approx(rho_row, rel=1e-12)
    adv = np.abs(err).argmax(axis=0)
    EA = operator_matrix(Bt, adv, "A") - operator_matrix(Gt, adv, "A")
    EB = operator_matrix(Bt, adv[::-1], "B") - operator_matrix(Gt, adv[::-1], "B")
    assert norm(EA, 1) == pytest.approx(rho_col, rel=1e-12)
    assert norm(EB, np.inf) == pytest.approx(rho_col, rel=1e-12)


def test_relative_operator_error_below_weight_error(bank):
    rng = np.random.default_rng(2)
    levels = np.linspace(-0.9, 0.9, 7)
    Bt, Gt = bank_table(bank, levels, N), gl_table(levels, N, TS)
    eps_R = rel_weight_error(Bt, Gt)
    idx = rng.integers(0, 7, N)
    for T in "AB":
        W = operator_matrix(Gt, idx, T)
        E = operator_matrix(Bt, idx, T) - W
        for p in (1, np.inf):
            assert norm(E, p) <= eps_R * norm(W, p) * (1 + 1e-12)


def test_recursive_integral_certificate(bank):
    al = np.where(np.arange(N) < N // 2, -0.3, -0.8)
    neg = -al
    orders, idx = np.unique(neg, return_inverse=True)
    Bt, Gt = bank_table(bank, orders, N), gl_table(orders, N, TS)
    rho_row, rho_col = schur_constants(Bt - Gt)
    for T, F, rho in (("D", "A", rho_row), ("E", "B", rho_col)):
        Wh = lower_inverse(operator_matrix(Bt, idx, F))
        W = lower_inverse(operator_matrix(Gt, idx, F))
        assert np.all(Wh >= -1e-12)                        # nonnegative for negative orders
        step = bank.simulate_type(np.ones(N), al, T)
        nh = float(np.max(step))
        assert nh == pytest.approx(norm(Wh, np.inf), rel=1e-9)
        q = nh * rho
        assert q < 1
        assert norm(Wh - W, np.inf) <= nh * q / (1 - q)


def test_partial_sums_and_condition_number():
    for a in (-0.7, -0.2, 0.3, 0.9):
        assert gl_partial_abs_sum(a, N - 1) == pytest.approx(np.abs(_gl_weights(a, N)[1:]).sum(), rel=1e-10)
    a = 0.5
    W = gl_table([a], N, TS)
    Wm = operator_matrix(W, np.zeros(N, int), "A")
    kappa = norm(Wm, np.inf) * norm(lower_inverse(Wm), np.inf)
    w = lambda b, m: _gl_weights(b, m + 1)[m]
    assert kappa == pytest.approx((2 - w(a - 1, N - 1)) * w(-a - 1, N - 1), rel=1e-9)


def test_fixed_poles_switched_equal_table_and_moving_poles_do_not(bank):
    levels = np.array([-0.5, 0.5])
    idx = np.where(np.arange(N) < N // 2, 0, 1)
    lv = [(*bank.coeffs(float(a)), bank.theta) for a in levels]
    tab = np.array([kernel_from(*c, N) for c in lv])
    G = gl_table(levels, N, TS)
    for T in "AB":
        assert np.allclose(ltv_matrix(lv, idx, T), operator_matrix(tab, idx, T), rtol=1e-12, atol=1e-12)
    K, mv = moving_pole_levels(TS, N, levels, 1e-3)
    W = operator_matrix(G, idx, "A")
    err = norm(ltv_matrix(mv, idx, "A") - W, np.inf) / norm(W, np.inf)
    assert err > 0.05


def test_signed_lp_keeps_stability_hypotheses():
    f = FittedFixedPole(TS, N, 1e-4, 3.0, 12, signed=True)
    for a in (-0.8, -0.2, 0.2, 0.8):
        g0, cd, c, th = f.level(a)
        if a > 0:
            assert np.all(c <= 0)
            assert g0 + cd + np.sum(c / (1 - th)) > 0
        else:
            assert np.all(c >= 0) and cd >= 0
        assert g0 - cd - np.sum(c / (1 + th)) > 0


def test_lp_fit_is_at_least_as_good_on_its_lags():
    th = np.exp(-np.geomspace(1e-4, 3.0, 12))
    g = gl_table([0.6], N, TS)[0]
    cd, c, t = lp_residues(g, th, lp_lags(N))
    gh = kernel_from(g[0], cd, c, th, N)
    lags = lp_lags(N)
    assert np.max(np.abs(gh[lags] / g[lags] - 1)) <= t * (1 + 1e-6) + 1e-12
