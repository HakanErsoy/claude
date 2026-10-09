"""Compare the tb_board_top outputs (sim_single.txt, sim_long.txt) with the
committed out.txt and the golden model. Usage: check_sim.py <cfg> <workdir> <lr_type_code>"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import golden as g  # noqa: E402

cfg, work, lr_type = sys.argv[1], sys.argv[2], int(sys.argv[3])
LGN, LGB, AIDX, SEED = 11, 8, 51, 0x9E3779B9
fp = g.build(cfg)
WS = fp.WS


def s64(h):
    v = int(h, 16)
    return v - (1 << 64) if v >> 63 else v


lines = open(os.path.join(work, "sim_single.txt")).read().split("\n")
ys = [s64(t) for t in lines if t and " " not in t]
meta = dict(t.split() for t in lines if " " in t)
exp = g.read_hex_signed(os.path.join(g.ROOT, "rtl", "build", cfg, "out.txt"), WS)[:len(ys)]
mm = [i for i, (a, b) in enumerate(zip(ys, exp)) if a != b]
print(f"single: {len(ys)} samples, mismatches {len(mm)}", f"first {mm[0]}: got {ys[mm[0]]} exp {exp[mm[0]]}" if mm else "", meta)

T = "ABDE"[lr_type]
x = g.lfsr_inputs(SEED, 1 << LGN)
y = fp.run(x, [AIDX] * len(x), T)
recs = g.block_records(y, LGB, WS)
blk, cap, info = {}, {}, {}
for t in open(os.path.join(work, "sim_long.txt")):
    f = t.split()
    if f[0] == "BLK":
        blk[int(f[1])] = (int(f[2], 16), int(f[3], 16), int(f[4], 16), int(f[5]))
    elif f[0] == "CAP":
        cap[int(f[1])] = s64(f[2])
    else:
        info[f[0]] = int(f[1])
bad = [b for b, r in enumerate(recs) if blk.get(b) != (r["max_abs"], r["sumsq"], r["crc32"], r["guard_hits"])]
cbad = [i for i in cap if cap[i] != y[i]]
print(f"long ({T}, aidx {AIDX}): blocks {len(recs)} bad {bad[:5]}, captured {len(cap)} bad {len(cbad)}", info)
ok = not mm and not bad and not cbad
print("SIM CHECK", "OK" if ok else "FAIL")
sys.exit(0 if ok else 1)
