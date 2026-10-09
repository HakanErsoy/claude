"""Bit-exact parity on the board (BOARD_SESSION.md step 5).

    python rtl/board/host_parity.py <cfg> <bitdir> [--host root@192.168.2.99]

<bitdir> holds vob_<cfg>.bit and vob_<cfg>.hwh (rtl/board/build_board.tcl).
The bitstream, the hwh, rtl/build/<cfg>/stim.mem and board_runner.py go to
the board over scp; board_runner.py loads the overlay and streams every
vector through the core (one soft reset at the start, no reset in between);
the outputs come back and are compared with rtl/build/<cfg>/out.txt, both
byte for byte and as integers. Result: rtl/build/<cfg>/board/parity.json.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import golden as g  # noqa: E402

WS_OF = {"WS36_WM16": 36, "WS48_WM25": 48}
REMOTE = "/home/xilinx/vob"
PY = "source /etc/profile.d/pynq_venv.sh; source /etc/profile.d/xrt_setup.sh; python3"


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"failed: {' '.join(cmd)}\n{r.stdout}\n{r.stderr}")
    return r.stdout


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def push(host, cfg, bitdir, extra):
    rdir = f"{REMOTE}/{cfg}"
    sh(["ssh", "-o", "BatchMode=yes", host, f"mkdir -p {rdir}"])
    files = [os.path.join(bitdir, f"vob_{cfg}.bit"), os.path.join(bitdir, f"vob_{cfg}.hwh"),
             os.path.join(HERE, "board_runner.py")] + extra
    sh(["scp", "-q", "-o", "BatchMode=yes"] + files + [f"{host}:{rdir}/"])
    return rdir


def run_remote(host, args):
    return sh(["ssh", "-o", "BatchMode=yes", host, f"bash -lc '{PY} {args}'"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cfg", choices=sorted(WS_OF))
    ap.add_argument("bitdir")
    ap.add_argument("--host", default="root@192.168.2.99")
    a = ap.parse_args()
    WS = WS_OF[a.cfg]
    bdir = os.path.join(g.ROOT, "rtl", "build", a.cfg)
    odir = os.path.join(bdir, "board")
    os.makedirs(odir, exist_ok=True)
    bit = os.path.join(a.bitdir, f"vob_{a.cfg}.bit")
    rdir = push(a.host, a.cfg, a.bitdir, [os.path.join(bdir, "stim.mem")])
    print(run_remote(a.host, f"{rdir}/board_runner.py parity {rdir}/vob_{a.cfg}.bit {rdir}/stim.mem {WS} "
                             f"{rdir}/board_out.txt {rdir}/parity_board.json"), end="")
    sh(["scp", "-q", "-o", "BatchMode=yes", f"{a.host}:{rdir}/board_out.txt", f"{a.host}:{rdir}/parity_board.json", odir])
    brd = json.load(open(os.path.join(odir, "parity_board.json")))
    os.remove(os.path.join(odir, "parity_board.json"))

    got_txt = open(os.path.join(odir, "board_out.txt"), "rb").read()
    # committed bytes (the working copy may carry CRLF line ends under core.autocrlf)
    exp_txt = subprocess.run(["git", "-C", g.ROOT, "show", f"HEAD:rtl/build/{a.cfg}/out.txt"],
                             capture_output=True, check=True).stdout
    got = g.read_hex_signed(os.path.join(odir, "board_out.txt"), WS)
    exp = g.read_hex_signed(os.path.join(bdir, "out.txt"), WS)
    mism = [i for i, (x, y) in enumerate(zip(got, exp)) if x != y]
    first = None
    if mism:
        i = mism[0]
        first = {"index": i, "expected": exp[i], "got": got[i]}
    res = {"config": a.cfg, "bitstream_sha256_host": sha256(bit), **brd,
           "parity": {"vectors": len(exp), "received": len(got),
                      "mismatches": len(mism) + abs(len(exp) - len(got)),
                      "byte_identical_to_out_txt": got_txt == exp_txt, "first_mismatch": first}}
    if res["bitstream_sha256_host"] != res["bitstream_sha256"]:
        sys.exit("bitstream hash differs between host and board")
    json.dump(res, open(os.path.join(odir, "parity.json"), "w"), indent=1)
    if got_txt == exp_txt:          # identical to the committed out.txt: no need to keep a copy
        os.remove(os.path.join(odir, "board_out.txt"))
    print(f"{a.cfg}: {len(got)}/{len(exp)} outputs, mismatches {res['parity']['mismatches']}, "
          f"byte-identical {got_txt == exp_txt}, first {first}, latency {brd['latency_cycles']}, "
          f"fclk {brd['clock']['fclk0_mhz_measured']:.4f} MHz")


if __name__ == "__main__":
    main()
