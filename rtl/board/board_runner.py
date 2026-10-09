"""Board-side driver (runs on the PYNQ-Z1 ARM, as root, in the PYNQ venv).

  board_runner.py parity  <bit> <stim.mem> <WS> <out_hex> <out_json>
  board_runner.py longrun <bit> <aidx> <type> <lgn> <lgb> <seed> <out_json>

Loading the overlay sets FCLK_CLK0 from the .hwh next to the .bit. Each run
starts with one soft reset of the core (CTRL bit 0) and then streams without
further resets. Register map: rtl/board/README.md.
"""

import hashlib
import json
import re
import sys
import time

from pynq import MMIO, Overlay
from pynq.ps import Clocks

BASE, SPAN = 0x43C00000, 0x1000
CTRL, STATUS, X0, X1, CMD, Y0, Y1, NSAMP = 0x00, 0x04, 0x08, 0x0C, 0x10, 0x14, 0x18, 0x1C
LAT_LAST, LAT_MIN, LAT_MAX, PER_LAST, PER_MIN, PER_MAX = 0x20, 0x24, 0x28, 0x2C, 0x30, 0x34
CYC0, CYC1 = 0x38, 0x3C
LR_CFG, LR_LGB, LR_SEED, LR_NBLK, LR_CYC0, LR_CYC1 = 0x40, 0x44, 0x48, 0x4C, 0x50, 0x54
BLK_ADDR, BLK0, CAP_ADDR, CAP0, CAP1, PARAMS, ID = 0x58, 0x5C, 0x7C, 0x80, 0x84, 0x88, 0x8C
ISSUED, OCOUNT = 0x90, 0x94
CAP_N = 4096


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def set_fclk0(bit):
    """Set FCLK_CLK0 to the fastest rate this board's PLL gives that does not
    exceed the frequency timing was closed at (PCW_ACT_FPGA0_PERIPHERAL_FREQMHZ
    in the .hwh). Overlay() alone applies the .hwh divisors, which Vivado
    computed for its own IO PLL setting (1400-1600 MHz with a 50 MHz crystal),
    while the PYNQ-Z1 IO PLL runs at 1000 MHz."""
    txt = open(bit[:-4] + ".hwh").read()
    target = float(re.search(r'NAME="PCW_ACT_FPGA0_PERIPHERAL_FREQMHZ" VALUE="([\d.]+)"', txt).group(1))
    inst = Clocks._instance
    src = inst._get_src_clk_mhz(inst.PL_CLK_CTRLS[0].SRCSEL)
    best = max(((src / (d0 * d1), d0, d1) for d0 in range(1, 64) for d1 in range(1, 64)
                if src / (d0 * d1) <= target + 1e-9), key=lambda t: (t[0], -t[1]))
    Clocks.set_pl_clk(0, best[1], best[2])
    return {"timing_closed_mhz": target, "pll_src_mhz": src, "div0": best[1], "div1": best[2],
            "set_mhz": best[0]}


class Board:
    def __init__(self, bit):
        self.ol = Overlay(bit)
        self.fclk = set_fclk0(bit)
        self.m = MMIO(BASE, SPAN)
        self.a = self.m.array                       # uint32 view, one entry per word
        if self.rd(ID) != 0x564F4231:
            raise RuntimeError(f"unexpected ID {self.rd(ID):08x}")

    def rd(self, off):
        return int(self.a[off >> 2])

    def wr(self, off, v):
        self.a[off >> 2] = v & 0xFFFFFFFF

    def cyc(self):
        lo = self.rd(CYC0)
        return (self.rd(CYC1) << 32) | lo

    def params(self):
        p = self.rd(PARAMS)
        return {"K": p & 0xFF, "WS": (p >> 8) & 0xFF, "WST": (p >> 16) & 0xFF, "WM": (p >> 24) & 0xFF}

    def soft_reset(self):
        self.wr(CTRL, 1)
        while self.rd(STATUS) & 0x20:
            pass

    def clock(self, seconds=2.0):
        c0, t0 = self.cyc(), time.monotonic()
        time.sleep(seconds)
        c1, t1 = self.cyc(), time.monotonic()
        return {**self.fclk, "fclk0_mhz_pynq": Clocks.fclk0_mhz,
                "fclk0_mhz_measured": (c1 - c0) / (t1 - t0) / 1e6, "measure_s": t1 - t0}


def sext(v, bits):
    return v - (1 << bits) if v >> (bits - 1) else v


def parity(bit, stim, WS, out_hex, out_json):
    b = Board(bit)
    words = [int(t, 16) for t in open(stim) if t.strip()]
    mask = (1 << WS) - 1
    width = (WS + 3) // 4
    clk = b.clock()
    b.soft_reset()
    a = b.a
    iX0, iX1, iCMD, iST, iY0, iY1 = X0 >> 2, X1 >> 2, CMD >> 2, STATUS >> 2, Y0 >> 2, Y1 >> 2
    out = []
    polls = 0
    t0 = time.monotonic()
    for w in words:
        x = w & mask
        aidx = (w >> WS) & 0x3FF
        typ = (w >> (WS + 10)) & 0x3
        a[iX0] = x & 0xFFFFFFFF
        a[iX1] = (x >> 32) & 0xFFFFFFFF
        a[iCMD] = (typ << 16) | aidx
        while not (int(a[iST]) & 2):
            polls += 1
        y = (int(a[iY1]) << 32) | int(a[iY0])
        out.append(f"{y & mask:0{width}x}")
    elapsed = time.monotonic() - t0
    with open(out_hex, "w") as f:
        f.write("\n".join(out) + "\n")
    res = {"bitstream_sha256": sha256(bit), "params": b.params(), "clock": clk,
           "vectors": len(words), "nsamp_counter": b.rd(NSAMP),
           "latency_cycles": {"last": b.rd(LAT_LAST), "min": b.rd(LAT_MIN), "max": b.rd(LAT_MAX)},
           "extra_status_polls": polls, "host_elapsed_s": elapsed}
    json.dump(res, open(out_json, "w"), indent=1)
    print(json.dumps(res))


def longrun(bit, aidx, typ, lgn, lgb, seed, out_json):
    b = Board(bit)
    clk = b.clock()
    b.soft_reset()
    b.wr(LR_CFG, (lgn << 24) | (typ << 16) | aidx)
    b.wr(LR_LGB, lgb)
    b.wr(LR_SEED, seed)
    t0 = time.monotonic()
    b.wr(CTRL, 2)
    while not (b.rd(STATUS) & 8):
        time.sleep(0.05)
    wall = time.monotonic() - t0
    nblk = b.rd(LR_NBLK)
    blocks = []
    for i in range(nblk):
        b.wr(BLK_ADDR, i)
        w = [b.rd(BLK0 + 4 * j) for j in range(8)]
        blocks.append({"max_abs": w[0] | (w[1] << 32),
                       "sumsq": w[2] | (w[3] << 32) | (w[4] << 64) | (w[5] << 96),
                       "crc32": w[6], "guard_hits": w[7]})
    cap = []
    for i in range(min(CAP_N, 1 << lgn)):
        b.wr(CAP_ADDR, i)
        cap.append(sext(b.rd(CAP0) | (b.rd(CAP1) << 32), 64))
    res = {"bitstream_sha256": sha256(bit), "params": b.params(), "clock": clk,
           "aidx": aidx, "type": typ, "lgn": lgn, "lgb": lgb, "seed": seed,
           "issued": b.rd(ISSUED), "ocount": b.rd(OCOUNT), "nsamp_counter": b.rd(NSAMP),
           "lr_cycles": b.rd(LR_CYC0) | (b.rd(LR_CYC1) << 32), "wall_s": wall,
           "latency_cycles": {"min": b.rd(LAT_MIN), "max": b.rd(LAT_MAX)},
           "period_cycles": {"last": b.rd(PER_LAST), "min": b.rd(PER_MIN), "max": b.rd(PER_MAX)},
           "blocks": blocks, "capture": cap}
    json.dump(res, open(out_json, "w"))
    print(json.dumps({k: v for k, v in res.items() if k not in ("blocks", "capture")}))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "parity":
        parity(sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5], sys.argv[6])
    elif cmd == "longrun":
        longrun(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]),
                int(sys.argv[7], 0), sys.argv[8])
    else:
        sys.exit(__doc__)
