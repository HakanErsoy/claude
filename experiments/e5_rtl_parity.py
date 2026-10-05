"""E5b: RTL bit-exact parity, lint and synthesis estimate for vo_bank_core.

For each word-length configuration:
  1. build the bit-accurate model (vofrac.fixedpoint) and export its ROMs;
  2. generate test vectors: every type with constant, piecewise, per-sample
     and sign-changing orders; full-scale inputs; runtime type changes;
  3. run the Icarus Verilog testbench and compare every output word with the
     golden integer model (any mismatch fails the configuration);
  4. Verilator lint, Yosys synth_xilinx (xc7) resource estimate.

Outputs: results/e5_rtl_parity.json, rtl/build/<config>/ (ROMs, vectors, logs)
"""

import json
import os
import re
import shutil
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vofrac.bank import DiscreteFixedPoleBank  # noqa: E402
from vofrac.design import design_dt  # noqa: E402
from vofrac.fixedpoint import FixedPointBank, output_bound, stress_bound  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RTL = os.path.join(ROOT, "rtl")
OUT = os.path.join(ROOT, "results")
R, EPS, AMAX, P = 4000, 1e-4, 0.95, 1024
TYPE_CODE = {"A": 0, "B": 1, "D": 2, "E": 3}


def vectors(fp, rng, types, n_case=1024):
    """List of (name, types per sample, aidx, x_int) for the envelope's types."""
    t = np.arange(n_case)
    profiles = {
        "const +0.7": np.full(n_case, 0.7),
        "const -0.9": np.full(n_case, -0.9),
        "piecewise": np.repeat(rng.uniform(-AMAX, AMAX, 8), n_case // 8),
        "per-sample": AMAX * np.sin(2 * np.pi * 3 * t / n_case),
        "switch -0.95->+0.95": np.where(t < n_case // 2, -AMAX, AMAX),
    }
    lim = 0.999
    inputs = {
        "noise": np.clip(0.3 * rng.standard_normal(n_case), -lim, lim),
        "full-scale alternating": lim * np.where(t % 2 == 0, 1.0, -1.0),
        "full-scale step": np.full(n_case, lim),
    }
    cases = []
    for T in types:
        for pname, al in profiles.items():
            for iname, x in inputs.items():
                cases.append((f"{T} | {pname} | {iname}", [T] * n_case, fp.index(al), fp.to_int(x)))
    # runtime type changes (variable-type operation): the hardware and the
    # golden model must agree on whatever this means
    seq = list(np.array(list(types))[rng.integers(0, len(types), n_case // 64)].repeat(64))
    cases.append(("type changes every 64 samples", seq, fp.index(rng.uniform(-AMAX, AMAX, n_case)),
                  fp.to_int(np.clip(0.3 * rng.standard_normal(n_case), -lim, lim))))
    return cases


def run(cmd, cwd, log):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    with open(log, "a") as f:
        f.write("$ " + " ".join(cmd) + "\n" + r.stdout + r.stderr + "\n")
    return r


def parity(cfg, bank, V, rng, types):
    name = f"WS{cfg['WS']}_WM{cfg['WM']}"
    bdir = os.path.join(RTL, "build", name)
    shutil.rmtree(bdir, ignore_errors=True)
    os.makedirs(bdir)
    log = os.path.join(bdir, "log.txt")
    fp = FixedPointBank(bank, P=P, amax=AMAX, WS=cfg["WS"], WM=cfg["WM"], n_max=R, V_max=V)
    meta = fp.export_mem(bdir)
    cases = vectors(fp, rng, types)
    # one continuous stream: the hardware keeps its state across cases, so the
    # golden model runs the concatenated stream too
    types_all = [T for _, ty, _, _ in cases for T in ty]
    aidx_all = [int(a) for _, _, ai, _ in cases for a in ai]
    x_all = [int(v) for _, _, _, xx in cases for v in xx]
    expect = fp.run(x_all, aidx_all, types_all)
    sw_hex = (2 + 10 + fp.WS + 3) // 4
    stim, bounds, start = [], [], 0
    for cname, ty, ai, xx in cases:
        for T, a, xv in zip(ty, ai, xx):
            word = (TYPE_CODE[T] << (10 + fp.WS)) | (int(a) << fp.WS) | (xv & ((1 << fp.WS) - 1))
            stim.append(f"{word:0{sw_hex}x}")
        bounds.append((cname, start, start + len(ty)))
        start += len(ty)
    with open(os.path.join(bdir, "stim.mem"), "w") as f:
        f.write("\n".join(stim) + "\n")
    n = len(stim)
    params = {"K": fp.K, "P": P, "AW": 10, "WS": fp.WS, "WST": fp.WST, "WM": fp.WM, "SB": meta["SBITS"], "N": n}
    strp = {"COEF_FILE": os.path.join(bdir, "coef.mem"), "UPOLE_FILE": os.path.join(bdir, "upole.mem"),
            "GAIN_FILE": os.path.join(bdir, "gain.mem"), "STIM_FILE": os.path.join(bdir, "stim.mem"),
            "OUT_FILE": os.path.join(bdir, "out.txt")}
    cmd = ["iverilog", "-g2012", "-o", os.path.join(bdir, "sim.vvp")]
    cmd += [f"-Ptb_vo_bank.{k}={v}" for k, v in params.items()]
    cmd += [f'-Ptb_vo_bank.{k}="{v}"' for k, v in strp.items()]
    cmd += [os.path.join(RTL, "tb_vo_bank.v"), os.path.join(RTL, "vo_bank_core.v")]
    r = run(cmd, bdir, log)
    if r.returncode:
        raise RuntimeError(f"iverilog failed, see {log}")
    r = run(["vvp", "-n", os.path.join(bdir, "sim.vvp")], bdir, log)
    m = re.search(r"CYCLES_PER_SAMPLE (\d+)", r.stdout)
    cps = int(m.group(1)) if m else None
    mask, sign = (1 << fp.WS) - 1, 1 << (fp.WS - 1)
    with open(os.path.join(bdir, "out.txt")) as f:
        got = [int(line, 16) for line in f if line.strip()]
    got = [(g & mask) - ((g & sign) << 1) for g in got]
    mism = [i for i, (g, e) in enumerate(zip(got, expect)) if g != e]
    per_case = {c: sum(1 for i in mism if s <= i < e) for c, s, e in bounds}
    # lint and synthesis
    lint = run(["verilator", "--lint-only", "-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSEDPARAM",
                f"-GK={fp.K}", f"-GWS={fp.WS}", f"-GWST={fp.WST}", f"-GWM={fp.WM}",
                os.path.join(RTL, "vo_bank_core.v")], bdir, log)
    ys = os.path.join(bdir, "synth.ys")
    with open(ys, "w") as f:
        f.write(f"read_verilog {os.path.join(RTL, 'vo_bank_core.v')}\n")
        f.write("chparam " + " ".join(f"-set {k} {v}" for k, v in params.items() if k != "N")
                + " " + " ".join(f'-set {k} "{v}"' for k, v in strp.items() if k in ("COEF_FILE", "UPOLE_FILE", "GAIN_FILE"))
                + " vo_bank_core\n")
        f.write("synth_xilinx -top vo_bank_core -family xc7 -flatten\nstat\n")
    syn = run(["yosys", "-q", "-s", ys, "-l", os.path.join(bdir, "synth.log")], bdir, log)
    res = {}
    try:
        txt = open(os.path.join(bdir, "synth.log")).read()
        stat = txt[txt.rfind("Printing statistics"):]
        for cell in ("LUT1", "LUT2", "LUT3", "LUT4", "LUT5", "LUT6", "FDRE", "FDSE", "FDCE", "FDPE",
                     "DSP48E1", "RAMB36E1", "RAMB18E1", "CARRY4", "MUXF7", "MUXF8", "RAM32M", "RAM64M"):
            mm = re.search(rf"\s{cell}\s+(\d+)", stat)
            if mm:
                res[cell] = int(mm.group(1))
    except FileNotFoundError:
        pass
    luts = sum(v for k, v in res.items() if k.startswith("LUT"))
    ffs = sum(v for k, v in res.items() if k.startswith("FD"))
    out = {"config": name, "params": params, "samples": n, "mismatches": len(mism), "per_case_mismatches": per_case,
           "cycles_per_sample": cps, "lint_returncode": lint.returncode, "lint_warnings": lint.stderr.count("%Warning"),
           "synth_returncode": syn.returncode, "cells": res, "LUT": luts, "FF": ffs,
           "DSP48E1": res.get("DSP48E1", 0), "BRAM36_equiv": res.get("RAMB36E1", 0) + 0.5 * res.get("RAMB18E1", 0)}
    print(f"{name}: {n} samples, mismatches {len(mism)}, cycles/sample {cps}, lint rc {lint.returncode} "
          f"({out['lint_warnings']} warnings), synth: LUT {luts} FF {ffs} DSP {out['DSP48E1']} BRAM36 {out['BRAM36_equiv']}",
          flush=True)
    return out


def main():
    rng = np.random.default_rng(56)
    d = design_dt(1.0, R, -AMAX, AMAX, EPS)
    bank = DiscreteFixedPoleBank(1.0, d["xi_lo"], d["xi_hi"], d["K"])
    with open(os.path.join(OUT, "e5_fixed_point.json")) as f:
        e5 = json.load(f)
    results = []
    for env in ("AB", "ABDE"):
        e = e5["envelopes"][env]
        cfg = e["choice"]
        results.append(dict(parity(cfg, bank, e["V_max"], rng, env), envelope=env))
    with open(os.path.join(OUT, "e5_rtl_parity.json"), "w") as f:
        json.dump({"design": d, "results": results}, f, indent=1)


if __name__ == "__main__":
    main()
