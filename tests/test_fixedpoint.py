import os
import shutil
import subprocess
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.design import design_dt  # noqa: E402
from vofrac.fixedpoint import FixedPointBank, dq, mulsh, qcoef  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="module")
def bank():
    d = design_dt(1.0, 1000, -0.9, 0.9, 1e-3)
    return DiscreteFixedPoleBank(1.0, d["xi_lo"], d["xi_hi"], d["K"])


def test_qcoef_relative_precision():
    rng = np.random.default_rng(0)
    for c in np.concatenate([rng.uniform(-1, 1, 200), 10.0 ** rng.uniform(-15, 0, 200)]):
        M, S = qcoef(c, 18)
        assert 2 ** 16 <= abs(M) < 2 ** 17
        assert abs(dq((M, S)) - c) <= abs(c) * 2.0 ** -16


def test_mulsh_rounds_half_up():
    rng = np.random.default_rng(1)
    for _ in range(500):
        a, M, S = int(rng.integers(-2 ** 40, 2 ** 40)), int(rng.integers(-2 ** 17, 2 ** 17)), int(rng.integers(1, 60))
        assert mulsh(a, M, S) == (2 * a * M + 2 ** S) // 2 ** (S + 1)
    assert mulsh(5, 3, -2) == 60


def test_quantized_dc_floor_keeps_every_inverse_stable(bank):
    fp = FixedPointBank(bank, P=256, amax=0.9, WS=36, WM=16, n_max=1000, V_max=2000.0)
    assert all(fp._dc_gain(row) > 0 for a, row in zip(fp.grid, fp.C) if a > 0)


def test_fixed_point_tracks_float_bank(bank):
    fp = FixedPointBank(bank, P=256, amax=0.9, WS=44, WM=25, n_max=1000, V_max=2000.0)
    rng = np.random.default_rng(2)
    n = 600
    x = np.clip(0.3 * rng.standard_normal(n), -0.99, 0.99)
    idx = fp.index(np.repeat(rng.uniform(-0.9, 0.9, 6), n // 6))
    xq = fp.to_float(fp.to_int(x))
    for T in "ABDE":
        y = fp.to_float(fp.run(fp.to_int(x), idx, T))
        r = bank.simulate_type(xq, fp.grid[idx], T)
        assert np.sqrt(np.mean((y - r) ** 2) / np.mean(r ** 2)) < 1e-4


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog not installed")
def test_rtl_bit_exact_small(bank, tmp_path):
    fp = FixedPointBank(bank, P=256, amax=0.9, WS=40, WM=18, n_max=1000, V_max=2000.0)
    fp.export_mem(str(tmp_path))
    rng = np.random.default_rng(3)
    n = 60
    types, aidx, x = [], [], []
    for T in "ABDE":
        types += [T] * n
        aidx += list(fp.index(rng.uniform(-0.9, 0.9, n)))
        x += fp.to_int(np.clip(0.3 * rng.standard_normal(n), -0.99, 0.99))
    y = fp.run(x, aidx, types)
    code = {"A": 0, "B": 1, "D": 2, "E": 3}
    AW = 8
    with open(tmp_path / "stim.mem", "w") as f:
        for T, a, xv in zip(types, aidx, x):
            f.write(f"{(code[T] << (AW + 40)) | (int(a) << 40) | (xv & ((1 << 40) - 1)):x}\n")
    params = {"K": fp.K, "P": 256, "AW": AW, "WS": 40, "WST": fp.WST, "WM": 18, "N": len(x)}
    files = {k: str(tmp_path / v) for k, v in (("COEF_FILE", "coef.mem"), ("UPOLE_FILE", "upole.mem"),
                                                 ("GAIN_FILE", "gain.mem"), ("STIM_FILE", "stim.mem"),
                                                 ("OUT_FILE", "out.txt"))}
    cmd = ["iverilog", "-g2012", "-o", str(tmp_path / "sim.vvp")]
    cmd += [f"-Ptb_vo_bank.{k}={v}" for k, v in params.items()] + [f'-Ptb_vo_bank.{k}="{v}"' for k, v in files.items()]
    cmd += [os.path.join(ROOT, "rtl", "tb_vo_bank.v"), os.path.join(ROOT, "rtl", "vo_bank_core.v")]
    subprocess.run(cmd, check=True)
    subprocess.run(["vvp", "-n", str(tmp_path / "sim.vvp")], check=True, capture_output=True)
    got = [int(line, 16) for line in open(tmp_path / "out.txt") if line.strip()]
    got = [(g & ((1 << 40) - 1)) - ((g & (1 << 39)) << 1) for g in got]
    assert got == y
