import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.battery import FOPath, GainFit, hat_basis, rc_regressors, resample, trim_rest  # noqa: E402
from vofrac.design import design_dt  # noqa: E402
from vofrac.reference import gl_A, gl_B  # noqa: E402

N = 600
BETAS = np.round(np.arange(0.02, 0.9501, 0.01), 3)


def _setup():
    d = design_dt(1.0, N, -0.95, -0.02, 1e-5)
    bank = DiscreteFixedPoleBank(1.0, d["xi_lo"], d["xi_hi"], d["K"])
    rng = np.random.default_rng(3)
    i = np.repeat(rng.standard_normal(N // 20), 20)          # piecewise-constant current
    return bank, i


def test_order_paths_match_gl_types():
    bank, i = _setup()
    beta = 0.2 + 0.5 * np.arange(N) / N + 0.003                # between grid points
    fo = FOPath(bank, i, BETAS)
    for vo, ref in (("A", gl_A), ("B", gl_B)):
        y = fo.run(beta, vo)
        r = ref(i, -beta, 1.0)
        assert np.max(np.abs(y - r)) < 2e-3 * np.max(np.abs(r))
    # a constant order is the same for both types and equals the grid column
    g = 37
    yA, yB = fo.run(np.full(N, BETAS[g]), "A"), fo.run(np.full(N, BETAS[g]), "B")
    assert np.allclose(yA, yB, rtol=0, atol=1e-12) and np.allclose(yA, fo.columns_A()[:, g], atol=1e-12)


def test_hat_basis_and_gain_fit_recover_scheduled_gains():
    bank, i = _setup()
    z = np.linspace(1.0, 0.3, N)
    kn = np.linspace(0.3, 1.0, 8)
    H = hat_basis(z, kn)
    assert np.allclose(H.sum(axis=1), 1.0) and np.allclose(H @ kn, z)
    psi = rc_regressors(i, [30.0])[:, 0]
    fo = FOPath(bank, i, BETAS).run(np.full(N, 0.4), "B")
    a, r, b1, b2 = (np.sin(3 * kn), 0.02 + 0.01 * kn, 0.01 * kn ** 2, 0.005 + 0 * kn)
    y = H @ a + (H @ r) * i + (H @ b1) * psi + (H @ b2) * fo
    gf = GainFit(y, i, H)
    assert gf.sse(psi, fo) < 1e-20
    assert np.allclose(gf.coef(psi, fo), np.r_[a, r, b1, b2], atol=1e-8)


def test_resample_preserves_charge_and_trim_keeps_states_zero():
    t = np.arange(1000) / 10.0                                 # 10 samples per 1 s bin
    cur = np.where(t > 30.0, -2.0 * np.sin(t) ** 2, 0.0)
    tt, (ii,) = resample(t, cur, Ts=1.0)
    assert abs(ii.sum() * 1.0 - cur.sum() * 0.1) < 1e-9
    d = {"i": ii, "y": np.arange(len(ii), dtype=float)}
    k = int(np.argmax(np.abs(ii) > 0.05))
    dt = trim_rest(d, lead=5)
    assert len(dt["i"]) == len(ii) - (k - 5) and np.all(dt["i"][:5] == 0.0)
