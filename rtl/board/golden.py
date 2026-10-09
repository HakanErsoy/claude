"""Golden-side helpers for the board measurements (rtl/board).

* build(cfg): the FixedPointBank of a configuration, rebuilt exactly as
  experiments/e5_rtl_parity.py builds it, and checked against the ROM files
  in rtl/build/<cfg>/ (the bitstream is built from those files);
* lfsr_inputs(seed, n): the long-run input sequence of board_top.v;
* block_records(y, lgb, WS): the per-block records board_top.v stores.
"""

import filecmp
import json
import os
import sys
import tempfile
import zlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.design import design_dt  # noqa: E402
from vofrac.fixedpoint import FixedPointBank  # noqa: E402

R, EPS, AMAX, P = 4000, 1e-4, 0.95, 1024
CFG_ENV = {"WS36_WM16": "AB", "WS48_WM25": "ABDE"}
TYPE_CODE = {"A": 0, "B": 1, "D": 2, "E": 3}

LFSR_MASK = 0x80200003       # Galois, x^32 + x^22 + x^2 + x + 1
LFSR_STEPS = 32              # steps per sample
X_SHIFT = 10                 # x = (signed 32-bit state) >> 10, |x| <= 2^21


def build(cfg, check_roms=True):
    d = design_dt(1.0, R, -AMAX, AMAX, EPS)
    bank = DiscreteFixedPoleBank(1.0, d["xi_lo"], d["xi_hi"], d["K"])
    with open(os.path.join(ROOT, "results", "e5_fixed_point.json")) as f:
        e = json.load(f)["envelopes"][CFG_ENV[cfg]]
    c = e["choice"]
    fp = FixedPointBank(bank, P=P, amax=AMAX, WS=c["WS"], WM=c["WM"], n_max=R, V_max=e["V_max"])
    assert f"WS{fp.WS}_WM{fp.WM}" == cfg and fp.WST == c["WST"] and fp.F == c["F"]
    if check_roms:
        with tempfile.TemporaryDirectory() as tmp:
            fp.export_mem(tmp)
            for m in ("coef.mem", "upole.mem", "gain.mem"):
                if not filecmp.cmp(os.path.join(tmp, m), os.path.join(ROOT, "rtl", "build", cfg, m), shallow=False):
                    raise RuntimeError(f"rebuilt {m} differs from rtl/build/{cfg}/{m}")
    return fp


def lfsr_inputs(seed, n):
    """x_n = (s_{n+1} as signed 32-bit) >> 10, s_{n+1} = 32 Galois steps of s_n, s_0 = seed."""
    s = seed & 0xFFFFFFFF
    out = []
    for _ in range(n):
        for _ in range(LFSR_STEPS):
            s = (s >> 1) ^ LFSR_MASK if s & 1 else s >> 1
        v = s - (1 << 32) if s & 0x80000000 else s
        out.append(v >> X_SHIFT)
    return out


def block_records(y, lgb, WS):
    """Per block of 2^lgb outputs: max|y|, sum y^2, CRC-32 of the outputs as
    64-bit little-endian sign-extended words, count of |y| >= 2^(WS-2)."""
    B = 1 << lgb
    guard = 1 << (WS - 2)
    recs = []
    for b in range(len(y) // B):
        blk = y[b * B:(b + 1) * B]
        crc = 0
        for v in blk:
            crc = zlib.crc32((v & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "little"), crc)
        recs.append({"max_abs": max(abs(v) for v in blk), "sumsq": sum(v * v for v in blk),
                     "crc32": crc, "guard_hits": sum(1 for v in blk if abs(v) >= guard)})
    return recs


def read_hex_signed(path, WS):
    mask, sign = (1 << WS) - 1, 1 << (WS - 1)
    with open(path) as f:
        vals = [int(line, 16) & mask for line in f if line.strip()]
    return [v - ((v & sign) << 1) for v in vals]
