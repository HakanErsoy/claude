import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.crb import gl_weight_derivs, jacobian, pcrb, pcrb_A_scalar  # noqa: E402
from vofrac.reference import gl_A, gl_B  # noqa: E402


def _case(n=60):
    rng = np.random.default_rng(4)
    x = rng.standard_normal(n)
    alpha = 0.3 + 0.2 * np.sin(np.arange(n) / 9.0)
    return x, alpha


def test_weight_derivatives_match_finite_differences():
    a = np.array([-0.7, -0.2, 0.0, 0.35, 0.9])
    W, D = gl_weight_derivs(a, 50)
    h = 1e-6
    Wp, _ = gl_weight_derivs(a + h, 50)
    Wm, _ = gl_weight_derivs(a - h, 50)
    assert np.max(np.abs(D - (Wp - Wm) / (2 * h))) < 1e-7


def test_jacobians_match_literal_gl():
    x, alpha = _case()
    h = 1e-6
    for vo, f in (("A", gl_A), ("B", gl_B)):
        G = jacobian(x, alpha, vo)
        for m in (0, 7, 30, 58):
            e = np.zeros(len(x)); e[m] = h
            fd = (f(x, alpha + e, 1.0) - f(x, alpha - e, 1.0)) / (2 * h)
            assert np.max(np.abs(G[:, m] - fd)) < 1e-6 * max(1.0, np.max(np.abs(fd)))


def test_pcrb_reduces_to_scalar_recursion_for_A():
    x, alpha = _case()
    G = jacobian(x, alpha, "A")
    filt, smooth = pcrb(G, 1e-3, 1e-4, 0.25)
    assert np.allclose(filt, pcrb_A_scalar(np.diag(G), 1e-3, 1e-4, 0.25), rtol=1e-10)
    assert np.all(smooth <= filt * (1 + 1e-12)) and np.isclose(smooth[-1], filt[-1])
    # B-type: the current order is not observed at its own sample
    fB, sB = pcrb(jacobian(x, alpha, "B"), 1e-3, 1e-4, 0.25)
    assert np.all(sB <= fB * (1 + 1e-12))


def test_batch_bound_with_one_run_equals_pcrb():
    from vofrac.crb import bcrb_batch
    x, alpha = _case(40)
    for vo in "AB":
        G = jacobian(x, alpha, vo)
        f1, s1 = pcrb(G, 1e-3, 1e-4, 0.25)
        f2, s2 = bcrb_batch(lambda k: G[k:k + 1, :k + 1], len(x), 1e-3, 1e-4, 0.25)
        assert np.allclose(f1, f2, rtol=1e-9) and np.allclose(s1, s2, rtol=1e-9)


def test_batch_bound_averages_information():
    # A-type: M runs equal the scalar recursion with the mean squared sensitivity
    from vofrac.crb import bcrb_batch
    rng = np.random.default_rng(1)
    H = rng.standard_normal((5, 30))
    f, _ = bcrb_batch(lambda k: np.pad(H[:, k:k + 1], ((0, 0), (k, 0))), 30, 1e-2, 1e-3, 0.5)
    assert np.allclose(f, pcrb_A_scalar(np.sqrt(np.mean(H ** 2, axis=0)), 1e-2, 1e-3, 0.5), rtol=1e-9)


def test_interpolated_derivative_table():
    from vofrac.crb import gl_derivative_table, interp_rows
    grid = np.round(np.arange(-0.95, 0.9501, 0.001), 6)
    T = gl_derivative_table(grid, 200)
    a = np.array([0.1234, -0.4321, 0.777])
    r = np.array([3, 50, 199])
    exact = np.array([gl_weight_derivs([ai], 200)[1][0, ri] for ai, ri in zip(a, r)])
    assert np.max(np.abs(interp_rows(T, grid, a, r) - exact) / np.abs(exact)) < 1e-4
