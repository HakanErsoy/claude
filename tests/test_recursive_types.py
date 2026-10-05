import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.design import design_dt  # noqa: E402
from vofrac.reference import gl_A, gl_B, gl_D, gl_E, gl_matrix, gl_relaxation  # noqa: E402
from vofrac.types import OwnTypes  # noqa: E402

H = 1e-3
GL = {"A": gl_A, "B": gl_B, "D": gl_D, "E": gl_E}


def _case(n=600, seed=0):
    rng = np.random.default_rng(seed)
    return rng.standard_normal(n), np.repeat(rng.uniform(-0.9, 0.9, 6), n // 6 + 1)[:n]


def test_literal_recursive_definitions_are_dual_inverses():
    x, al = _case()
    assert np.allclose(gl_D(x, al, H), np.linalg.solve(gl_matrix(-al, H, "A"), x), rtol=1e-10, atol=1e-10)
    assert np.allclose(gl_E(x, al, H), np.linalg.solve(gl_matrix(-al, H, "B"), x), rtol=1e-10, atol=1e-10)
    for T1, T2 in (("A", "D"), ("D", "A"), ("B", "E"), ("E", "B")):
        assert np.allclose(GL[T1](GL[T2](x, -al, H), al, H), x, atol=1e-9)
    assert not np.allclose(gl_A(gl_A(x, -al, H), al, H), x, atol=1e-3)


def test_bank_realizes_all_four_types():
    x, al = _case()
    d = design_dt(H, len(x), -0.9, 0.9, 1e-5)
    bank = DiscreteFixedPoleBank(H, d["xi_lo"], d["xi_hi"], d["K"])
    rel = lambda y, r: np.sqrt(np.mean((y - r) ** 2) / np.mean(r ** 2))
    for T in "ABDE":
        assert rel(bank.simulate_type(x, al, T), GL[T](x, al, H)) < 1e-4
    assert np.allclose(bank.simulate_type(bank.simulate_type(x, -al, "D"), al, "A"), x, atol=1e-10)
    assert np.allclose(bank.simulate_type(bank.simulate_type(x, -al, "E"), al, "B"), x, atol=1e-10)


def test_own_types_reproduce_gl_definitions():
    x, al = _case(n=400)
    own = OwnTypes(lambda u, a: gl_A(u, a, H), len(x))
    for T in "ABDE":
        assert np.allclose(getattr(own, T)(x, al), GL[T](x, al, H), rtol=1e-9, atol=1e-9)


@pytest.mark.parametrize("T", list("ABDE"))
def test_relaxation_solver_matches_gl(T):
    n = 800
    t = np.arange(n) * H
    al = 0.5 + 0.4 * np.sin(np.pi * t / 0.8)
    u = np.ones(n)
    d = design_dt(H, n, -0.9, 0.9, 1e-6)   # D/E use the opposite order
    bank = DiscreteFixedPoleBank(H, d["xi_lo"], d["xi_hi"], d["K"])
    y, r = bank.solve_relaxation(u, al, 1.0, T), gl_relaxation(u, al, 1.0, H, T)
    assert np.sqrt(np.mean((y - r) ** 2) / np.mean(r ** 2)) < 1e-5


def test_dc_floor_makes_every_inverse_stable():
    d = design_dt(H, 1000, -0.95, 0.95, 1e-2)
    grid = [a for a in np.linspace(-0.95, 0.95, 39) if abs(a) > 1e-9]
    with_floor = DiscreteFixedPoleBank(H, d["xi_lo"], d["xi_hi"], d["K"])
    without = DiscreteFixedPoleBank(H, d["xi_lo"], d["xi_hi"], d["K"], dc_floor=False)
    assert all(with_floor.inverse_is_stable(a) for a in grid)
    assert not all(without.inverse_is_stable(a) for a in grid)
    # sign test agrees with the spectral radius where the latter is resolvable
    assert without.inverse_spectral_radius(0.95) > 1.0 + 1e-5
