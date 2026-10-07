import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac import cm  # noqa: E402
from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.baselines import kernel_from  # noqa: E402
from vofrac.design import design_dt  # noqa: E402
from vofrac.opnorm import bank_table, gl_table, operator_matrix, rel_weight_error  # noqa: E402

TS = 1e-3
N = 200


def _bank():
    d = design_dt(TS, N, -0.9, 0.9, 1e-4)
    return DiscreteFixedPoleBank(TS, d["xi_lo"], d["xi_hi"], d["K"])


def test_time_varying_distributed_order_is_A_and_B_type():
    bank = _bank()
    xg, wg = np.polynomial.legendre.leggauss(6)
    centre = 0.45 + 0.3 * np.sin(2 * np.pi * np.arange(N) / N)
    nodes = centre[:, None] + 0.15 * xg[None, :]
    w = 0.5 * wg
    orders, inv = np.unique(nodes.ravel(), return_inverse=True)
    Bt, Gt = bank_table(bank, orders, N), gl_table(orders, N, TS)
    inv = inv.reshape(nodes.shape)
    Kh = np.einsum("q,nqr->nr", w, Bt[inv])
    Kx = np.einsum("q,nqr->nr", w, Gt[inv])
    # one sign: the mixture is no less accurate than its worst member
    assert rel_weight_error(Kh, Kx) <= rel_weight_error(Bt, Gt) * (1 + 1e-9)
    coeffs = [cm.mixture_coeffs(bank, nodes[k], w) for k in range(N)]
    x = np.random.default_rng(3).standard_normal(N)
    idx = np.arange(N)
    for T, sched in (("A", "output"), ("B", "input")):
        assert np.allclose(cm.run(bank.theta, coeffs, x, sched), operator_matrix(Kh, idx, T) @ x,
                           rtol=1e-12, atol=1e-9)


def test_fixed_tempering_keeps_the_relative_error():
    bank = _bank()
    lam = 0.02
    damp = np.exp(-lam * np.arange(N))
    for a in (-0.7, 0.4):
        th, co = cm.tempered(bank, a, lam)
        gh = kernel_from(*co, th, N)
        g = gl_table([a], N, TS)[0]
        e_t = rel_weight_error(gh[None, :], (g * damp)[None, :])
        e_0 = rel_weight_error(bank_table(bank, [a], N), g[None, :])
        assert abs(e_t - e_0) <= 1e-9 * max(e_0, 1e-300) + 1e-13


def test_closed_form_strip_bound_dominates_numerical_ratio():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "experiments"))
    from e9_cm_kernels import strip_ratio
    for d in (0.8, 1.3):
        for a in (-0.9, -0.3, 0.4, 0.9):
            for r in (1, 3, 100):
                assert strip_ratio(a, r, d) <= cm.gl_strip_bound(0.9, d)


def test_theorem_design_meets_tolerance():
    from vofrac.design import measure_dt
    t = cm.theorem_design(1e-3, 300, 0.9)
    b = DiscreteFixedPoleBank(TS, t["u_lo"] / TS, t["u_hi"] / TS, t["K"], dc_floor=False)
    assert measure_dt(b, 300, -0.9, 0.9) <= 1e-3
