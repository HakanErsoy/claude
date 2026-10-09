"""Collect the board-session measurements into results/e5_board.json.

Sources (all under rtl/build/<cfg>/):
  vivado/summary.txt, vivado/utilization.rpt, vivado/fmax_search.txt   OOC (step 4)
  board/summary.txt, board/utilization.rpt                              board bitstream
  board/parity.json                                                     step 5
  board/longrun.json                                                    step 7 (WS48_WM25)
"""

import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CFGS = {"WS36_WM16": 31744, "WS48_WM25": 62464}
CYCLES_CLAIMED = 136                      # 4K + 8, rtl/README.md and the testbench


def kv(path):
    out = {}
    for line in open(path):
        k, _, v = line.strip().partition(" ")
        out[k] = v
    return out


def util(path):
    """Slice LUTs, slice registers, DSP48E1, block RAM tiles (RAMB36 equivalent) from report_utilization."""
    txt = open(path).read()

    def row(name):
        m = re.search(r"^\|\s*" + re.escape(name) + r"\s*\|\s*([\d.]+)\s*\|", txt, re.M)
        return float(m.group(1)) if m else None
    lut = row("Slice LUTs") or row("CLB LUTs")
    ff = row("Slice Registers") or row("CLB Registers") or row("Register as Flip Flop")
    return {"lut": int(lut), "ff": int(ff), "dsp48": int(row("DSPs")), "bram36_equiv": row("Block RAM Tile"),
            "lutram": int(row("LUT as Memory") or 0)}


def main():
    res = {"board": "PYNQ-Z1 (Digilent)", "part": "xc7z020clg400-1", "date": datetime.date.today().isoformat(),
           "configs": {}}
    notes = []
    for cfg, nvec in CFGS.items():
        b = os.path.join(ROOT, "rtl", "build", cfg)
        ooc_s = kv(os.path.join(b, "vivado", "summary.txt"))
        trials = [ln.split() for ln in open(os.path.join(b, "vivado", "fmax_search.txt")) if not ln.startswith("#")]
        ooc = {"clock_constraint_ns": float(ooc_s["period_ns"]), "wns_ns": float(ooc_s["wns_ns"]),
               "whs_ns": float(ooc_s["whs_ns"]), "fmax_mhz": float(ooc_s["fmax_mhz"]),
               **util(os.path.join(b, "vivado", "utilization.rpt")),
               "trials": [{"period_ns": float(t[1]), "wns_ns": float(t[2]), "fmax_mhz": float(t[4])} for t in trials],
               "flow": "non-project, synth_design -mode out_of_context, opt/place/route default directives, "
                       "clock on reg-to-reg paths only (no I/O delays)"}
        res["vivado_version"] = ooc_s["vivado"]
        entry = {"ooc": ooc}
        par_p = os.path.join(b, "board", "parity.json")
        if os.path.exists(par_p):
            par = json.load(open(par_p))
            bs = kv(os.path.join(b, "board", "summary.txt"))
            f_meas = par["clock"]["fclk0_mhz_measured"]
            lat = par["latency_cycles"]
            entry["board"] = {
                "clock_mhz": par["clock"]["fclk0_mhz_pynq"], "clock_mhz_measured": f_meas,
                "clock_constraint_ns": float(bs["clk_fpga_0_period_ns"]), "wns_ns": float(bs["wns_ns"]),
                "whs_ns": float(bs["whs_ns"]),
                "bitstream_sha256": par["bitstream_sha256"],
                "design_utilization": util(os.path.join(b, "board", "utilization.rpt")),
                "parity": {"vectors": par["parity"]["vectors"], "mismatches": par["parity"]["mismatches"],
                           "byte_identical_to_out_txt": par["parity"]["byte_identical_to_out_txt"],
                           "first_mismatch": par["parity"]["first_mismatch"]},
                "latency_cycles": lat,
                "cycles_per_sample": lat["max"],
                "samples_per_s_theoretical": ooc["fmax_mhz"] * 1e6 / CYCLES_CLAIMED,
                "samples_per_s_theoretical_135": ooc["fmax_mhz"] * 1e6 / lat["max"],
                "samples_per_s_at_board_clock": par["clock"]["fclk0_mhz_pynq"] * 1e6 / lat["max"],
                "parity_host_elapsed_s": par["host_elapsed_s"]}
            assert par["parity"]["vectors"] == nvec
        lr_p = os.path.join(b, "board", "longrun.json")
        if os.path.exists(lr_p):
            lr = json.load(open(lr_p))
            entry["board"]["cycles_per_sample"] = lr["period_cycles"]["max"]
            entry["board"]["period_cycles"] = lr["period_cycles"]
            entry["board"]["samples_per_s_theoretical_measured_period"] = ooc["fmax_mhz"] * 1e6 / lr["period_cycles"]["max"]
            entry["board"]["samples_per_s_measured"] = lr["samples"] / (lr["lr_cycles"] / (lr["clock"]["fclk0_mhz_measured"] * 1e6))
            entry["long_run"] = {k: lr[k] for k in (
                "type", "aidx", "row", "alpha_effective", "samples", "input", "block", "max_abs_y", "max_abs_y_int",
                "rms_first_block", "rms_last_block", "rms_min_block", "rms_max_block", "guard_threshold",
                "guard_hits", "overflow", "golden_prefix_samples", "golden_prefix_block_mismatches",
                "golden_capture_samples", "golden_capture_mismatches", "lr_cycles", "cycles_per_sample_avg",
                "wall_s", "bitstream_sha256_host", "golden_full_length")}
        res["configs"][cfg] = entry
    res["clock_source_mhz"] = "PS FCLK_CLK0 (IO PLL 1000 MHz / integer dividers, set by PYNQ from the .hwh)"
    notes += [
        "Cycles: accept -> out_valid is 135 cycles on the board and in xsim, and back-to-back samples (in_valid held "
        "high) follow every 135 cycles, i.e. 4K+7. The 136 = 4K+8 of rtl/README.md is the testbench period, which "
        "raises in_valid one cycle after it sees out_valid. samples_per_s_theoretical uses 136 as BOARD_SESSION.md "
        "asks; samples_per_s_theoretical_135 uses the measured 135.",
        "Board clock: Vivado's PS7 configuration assumed an IO PLL of 1600 MHz (WS36) / 1400 MHz (WS48) for the "
        "50 MHz crystal, the PYNQ-Z1 IO PLL runs at 1000 MHz. board_runner.py therefore sets FCLK0 to the fastest "
        "1000/(d0*d1) not above the frequency timing was closed at: 40 MHz (exact) for WS36_WM16, 1000/29 = "
        "34.48 MHz for WS48_WM25 (closed at 35 MHz). Both are confirmed by the 64-bit cycle counter against the ARM "
        "clock (clock_mhz_measured).",
        "OOC Fmax is register-to-register inside vo_bank_core; the board designs add the AXI interconnect and "
        "board_top and were closed only at the board clock, not searched for their own Fmax.",
        "Parity is run through AXI4-Lite from the PS, one soft reset at the start, then all vectors in one stream; "
        "the outputs are byte-identical to the committed out.txt.",
        "Long run: the overflow flag is an output-range guard (|y| >= 2^(WS-2)) because the unmodified core does not "
        "expose its state or saturate. Internal overflow is excluded by the golden model instead: run(check=True) "
        "over all 2^24 samples raised nothing (peak state 51.3 of 61 bits, peak signal 29.4 of 48 bits), and all "
        "256 block records (CRC-32, max|y|, sum y^2) are identical to the board's.",
        "Long-run RMS does not stay flat and does not grow monotonically: block RMS ranges 2.14 (block 131) to 79.0 "
        "(block 255), first block 7.69. max|y| = 85.7 against a 2^24 full scale. With the quantized DC floor the "
        "row is stable; the output wanders as a fractional integral of order 0.855 of white noise does.",
        "The float-floor instability of this row has an e-folding time of 5.2e8 samples (e5c), so over 2^24 = "
        "1.68e7 samples it would grow by only exp(1.68e7/5.2e8) = 1.03: this run shows boundedness and bit-exactness "
        "on hardware, it cannot by itself separate the quantized floor from the float floor.",
    ]
    res["notes"] = notes
    with open(os.path.join(ROOT, "results", "e5_board.json"), "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    sys.exit(main())
