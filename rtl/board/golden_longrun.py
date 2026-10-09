"""Golden block records of the whole long run (all 2^lgn samples), beyond the
2^17-sample prefix that BOARD_SESSION.md asks for. The golden model is fast
enough (~4 s per 2^17 samples) to run the full 2^24 samples.

    python rtl/board/golden_longrun.py [--lgn 24] [--lgb 16] [--seed 0x9E3779B9] [--aidx 51] [--type D]

Output: rtl/build/WS48_WM25/board/longrun_golden_full.json. run(check=True)
raises at the first sample where a state or signal word would overflow; that
sample is recorded instead of the records.
"""

import argparse
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import golden as g  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lgn", type=int, default=24)
    ap.add_argument("--lgb", type=int, default=16)
    ap.add_argument("--seed", default="0x9E3779B9")
    ap.add_argument("--aidx", type=int, default=51)
    ap.add_argument("--type", default="D", choices=list("ABDE"))
    a = ap.parse_args()
    seed = int(a.seed, 0)
    fp = g.build("WS48_WM25")
    n = 1 << a.lgn
    t0 = time.time()
    x = g.lfsr_inputs(seed, n)
    res = {"lgn": a.lgn, "lgb": a.lgb, "seed": seed, "aidx": a.aidx, "type": a.type}
    try:
        y = fp.run(x, [a.aidx] * n, a.type)
        del x
        res["overflow"] = None
        res["blocks"] = g.block_records(y, a.lgb, fp.WS)
    except OverflowError as e:
        res["overflow"] = str(e)
    res["peak_state_bits"] = math.log2(fp.peak_state + 1)
    res["peak_signal_bits"] = math.log2(fp.peak_signal + 1)
    res["WST"], res["WS"], res["F"] = fp.WST, fp.WS, fp.F
    res["seconds"] = time.time() - t0
    odir = os.path.join(g.ROOT, "rtl", "build", "WS48_WM25", "board")
    os.makedirs(odir, exist_ok=True)
    with open(os.path.join(odir, "longrun_golden_full.json"), "w") as f:
        json.dump({**res, "blocks": [{**b, "sumsq": str(b["sumsq"])} for b in res.get("blocks", [])]}, f)
    print({k: v for k, v in res.items() if k != "blocks"})


if __name__ == "__main__":
    main()
