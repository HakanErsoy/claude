import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.design import design_dt  # noqa: E402
from vofrac.mbm import exact_variance, generate, local_hurst  # noqa: E402
from vofrac.reference import gl_A, gl_B, gl_matrix  # noqa: E402


def _bank(n):
    d = design_dt(1.0, n, -0.45, 0.45, 1e-5)
    return DiscreteFixedPoleBank(1.0, d["xi_lo"], d["xi_hi"], d["K"])


def test_integer_split_is_exact_only_in_the_right_place():
    rng = np.random.default_rng(0)
    n = 600
    xi = rng.standard_normal(n)
    a = 0.6 + 0.8 * np.arange(n) / n            # H from 0.1 to 0.9
    assert np.allclose(gl_A(np.cumsum(xi), -(a - 1), 1.0), gl_A(xi, -a, 1.0), atol=1e-9)
    assert np.allclose(np.cumsum(gl_B(xi, -(a - 1), 1.0)), gl_B(xi, -a, 1.0), atol=1e-9)
    assert not np.allclose(np.cumsum(gl_A(xi, -(a - 1), 1.0)), gl_A(xi, -a, 1.0), atol=1e-3)


def test_generator_matches_gl_paths():
    n = 1200
    bank = _bank(n)
    rng = np.random.default_rng(1)
    xi = rng.standard_normal((2, n))
    H = np.where(np.arange(n) < n // 2, 0.25, 0.75)
    for T, f in (("A", gl_A), ("B", gl_B)):
        X = generate(bank, xi, H, T)
        for i in range(2):
            r = f(xi[i], -(H + 0.5), 1.0)
            assert np.sqrt(np.mean((X[i] - r) ** 2) / np.mean(r ** 2)) < 1e-5


def test_exact_variance_matches_operator_matrix():
    n = 300
    H = 0.3 + 0.4 * np.sin(np.arange(n) / 40.0) ** 2
    for T in "AB":
        W = gl_matrix(-(H + 0.5), 1.0, T)
        assert np.allclose(np.sum(W ** 2, axis=1), exact_variance(H, T), rtol=1e-10)


def test_local_hurst_recovers_constant_h_roughly():
    n = 8192
    bank = _bank(n)
    rng = np.random.default_rng(2)
    X = generate(bank, rng.standard_normal((50, n)), np.full(n, 0.7), "A")
    c, Hh = local_hurst(X, 1024)
    assert abs(Hh[:, c > n // 4].mean() - 0.7) < 0.1
