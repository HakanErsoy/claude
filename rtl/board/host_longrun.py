"""Long-run stability on the board (BOARD_SESSION.md step 7, WS48_WM25 only).

    python rtl/board/host_longrun.py <bitdir> [--lgn 24] [--lgb 16] [--seed 0x9E3779B9]
                                     [--aidx 51] [--type D] [--golden-blocks 2]

Type D at aidx 51: the core mirrors the row for D/E (P-1-51 = 972), i.e.
alpha = +0.8553, the worst quantized row of results/e5c_quantized_stability.json.
The input comes from the on-chip LFSR (golden.lfsr_inputs). The board returns,
per block of 2^lgb outputs, max|y|, sum y^2, CRC-32 and the count of
|y| >= 2^(WS-2), plus the first 4096 outputs verbatim. The golden model
recomputes the first golden_blocks blocks (2 x 2^16 = 2^17 samples) and the
capture; every field must agree bit for bit. Result:
rtl/build/WS48_WM25/board/longrun.json.
"""

import argparse
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import golden as g  # noqa: E402
from host_parity import push, run_remote, sh, sha256  # noqa: E402

CFG = "WS48_WM25"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bitdir")
    ap.add_argument("--host", default="root@192.168.2.99")
    ap.add_argument("--lgn", type=int, default=24)
    ap.add_argument("--lgb", type=int, default=16)
    ap.add_argument("--seed", default="0x9E3779B9")
    ap.add_argument("--aidx", type=int, default=51)
    ap.add_argument("--type", default="D", choices=list("ABDE"))
    ap.add_argument("--golden-blocks", type=int, default=2)
    a = ap.parse_args()
    seed = int(a.seed, 0)
    tcode = g.TYPE_CODE[a.type]
    odir = os.path.join(g.ROOT, "rtl", "build", CFG, "board")
    os.makedirs(odir, exist_ok=True)

    rdir = push(a.host, CFG, a.bitdir, [])
    print(run_remote(a.host, f"{rdir}/board_runner.py longrun {rdir}/vob_{CFG}.bit {a.aidx} {tcode} "
                             f"{a.lgn} {a.lgb} {seed:#x} {rdir}/longrun_board.json"), end="")
    sh(["scp", "-q", "-o", "BatchMode=yes", f"{a.host}:{rdir}/longrun_board.json", odir])
    raw_path = os.path.join(odir, "longrun_board.json")
    brd = json.load(open(raw_path))
    os.remove(raw_path)

    fp = g.build(CFG)
    F, WS, B = fp.F, fp.WS, 1 << a.lgb
    alpha = float(fp.grid[fp.P - 1 - a.aidx] if a.type in "DE" else fp.grid[a.aidx])

    # golden prefix
    t0 = time.time()
    n_pre = a.golden_blocks * B
    x = g.lfsr_inputs(seed, n_pre)
    y = fp.run(x, [a.aidx] * n_pre, a.type)          # raises OverflowError on any internal overflow
    gold = g.block_records(y, a.lgb, WS)
    t_gold = time.time() - t0
    blk_bad = [i for i, r in enumerate(gold) if brd["blocks"][i] != r]
    cap = brd["capture"]
    cap_bad = [i for i, v in enumerate(cap) if v != y[i]]

    # optional: full-length golden records from golden_longrun.py
    full = None
    full_p = os.path.join(odir, "longrun_golden_full.json")
    if os.path.exists(full_p):
        fg = json.load(open(full_p))
        if (fg["lgn"], fg["lgb"], fg["seed"], fg["aidx"], fg["type"]) == (a.lgn, a.lgb, seed, a.aidx, a.type):
            if fg["overflow"]:
                full = {"golden_overflow": fg["overflow"]}
            else:
                fb = [{**b, "sumsq": int(b["sumsq"])} for b in fg["blocks"]]
                bad = [i for i, r in enumerate(fb) if i >= len(brd["blocks"]) or brd["blocks"][i] != r]
                full = {"samples": len(fb) * B, "block_mismatches": len(bad), "first_bad_block": bad[0] if bad else None,
                        "golden_peak_state_bits": fg["peak_state_bits"], "golden_peak_signal_bits": fg["peak_signal_bits"]}

    blocks = brd["blocks"]
    rms =[math.sqrt(b["sumsq"] / B) * 2.0 ** -F for b in blocks]
    max_abs = max(b["max_abs"] for b in blocks)
    guard = sum(b["guard_hits"] for b in blocks)
    n = 1 << a.lgn
    res = {"config": CFG, "bitstream_sha256_host": sha256(os.path.join(a.bitdir, f"vob_{CFG}.bit")),
           "type": a.type, "aidx": a.aidx, "row": fp.P - 1 - a.aidx if a.type in "DE" else a.aidx,
           "alpha_effective": alpha, "samples": n, "block": B, "blocks": len(blocks),
           "input": f"LFSR32 Galois mask=0x{g.LFSR_MASK:08X} (x^32+x^22+x^2+x+1), seed=0x{seed:08X}, "
                    f"{g.LFSR_STEPS} steps/sample, x = (signed state) >> {g.X_SHIFT}, |x| <= 0.25 at F={F}",
           "issued": brd["issued"], "ocount": brd["ocount"],
           "clock": brd["clock"], "lr_cycles": brd["lr_cycles"], "wall_s": brd["wall_s"],
           "cycles_per_sample_avg": brd["lr_cycles"] / n,
           "latency_cycles": brd["latency_cycles"], "period_cycles": brd["period_cycles"],
           "max_abs_y": max_abs * 2.0 ** -F, "max_abs_y_int": max_abs,
           "rms_first_block": rms[0], "rms_last_block": rms[-1],
           "rms_min_block": min(rms), "rms_max_block": max(rms),
           "guard_threshold": f"|y| >= 2^{WS - 2} LSB (= 2^{WS - 2 - F})", "guard_hits": guard,
           "overflow": guard > 0,
           "golden_prefix_samples": n_pre, "golden_prefix_block_mismatches": len(blk_bad),
           "golden_capture_samples": len(cap), "golden_capture_mismatches": len(cap_bad),
           "golden_first_capture_mismatch": ({"index": cap_bad[0], "expected": y[cap_bad[0]], "got": cap[cap_bad[0]]}
                                             if cap_bad else None),
           "golden_peak_state_bits": math.log2(fp.peak_state + 1), "golden_peak_signal_bits": math.log2(fp.peak_signal + 1),
           "golden_seconds": t_gold,
           "golden_full_length": full,
           "blocks_detail": [{"i": i, "max_abs_int": b["max_abs"], "sumsq": str(b["sumsq"]),
                              "crc32": f"{b['crc32']:08x}", "guard_hits": b["guard_hits"], "rms": rms[i]}
                             for i, b in enumerate(blocks)]}
    json.dump(res, open(os.path.join(odir, "longrun.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "blocks_detail"}, indent=1))


if __name__ == "__main__":
    main()
