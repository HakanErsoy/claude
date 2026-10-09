"""E12b: the E12 models against independent impedance spectra (EIS) of the same cell type.

The Panasonic 18650PF set (doi:10.17632/wykht8y7tg.1, CC BY 4.0) contains EIS
sweeps (6 kHz to 1 mHz) at 25, 10, 0, -10 and -20 degC and several states of
charge. Each model of E12 fitted to all drive cycles of a temperature is
linearized at the z of a sweep (gains and order frozen at that z) and its
impedance is compared with the measured one for 1.4 mHz <= f <= 0.1 Hz:

    Z(f) = R0 + R1 H_tau(e^{jw}) + kappa H_bank(e^{jw}; -beta) + OCV'(z) / (Q j w),

with H_tau the discrete lag, H_bank the bank's frequency response at the
frozen order (the realized operator, not s^{-beta}), and the last term the
open-circuit-voltage slope removed from the time-domain residual in E12.
Reported: relative RMS impedance error per sweep and its mean per
temperature and model; the temperature of a sweep is the set point nearest
to its median cell temperature.

Inputs: results/e12_battery.json (run E12 first) and the EIS csv files.
Outputs: results/e12b_eis.json
"""

import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from e12_battery import BETAS, MODELS, OUT, TS, make_bank  # noqa: E402
from vofrac.battery import Q_REF, frac_index, hat_basis, ocv_curve  # noqa: E402

F_LO, F_HI = 1.4e-3, 0.1
SET_POINTS = {25: "25degC", 10: "10degC", 0: "0degC", -10: "n10degC", -20: "n20degC"}


def read_eis(path):
    """(f [Hz], Z [ohm], Ah, cell temperature) of one sweep; non-numeric rows are skipped."""
    lines = open(path, encoding="latin-1").read().splitlines()
    head = [k for k, line in enumerate(lines) if line.startswith("Time Stamp;")]
    if not head:
        return None
    hdr = lines[head[0]].split(";")
    cols = [hdr.index(n) for n in ("ActFreq", "Zreal1", "Zimg1", "AhAccu", "Temp45")]
    rows = []
    for line in lines[head[0] + 2:]:
        r = line.split(";")
        try:
            rows.append([float(r[j]) for j in cols])
        except (ValueError, IndexError):
            continue
    if not rows:
        return None
    f, zr, zi, ah, T = np.array(rows).T
    return f, 1e-3 * (zr + 1j * zi), float(np.median(ah)), float(np.median(T))


def bank_response(bank, alpha, w):
    g0, cd, c = bank.coeffs(alpha)
    q = np.exp(-1j * w)
    return g0 + cd * q + (q[:, None] / (1.0 - bank.theta[None, :] * q[:, None])) @ c


def model_impedance(P, z, w, bank):
    M = len(P["gain_knots_z"])
    h = hat_basis(np.array([z]), np.array(P["gain_knots_z"]))[0]
    coef = np.array(P["coef"])
    gains = [h @ coef[k * M:(k + 1) * M] for k in range(len(coef) // M)]
    Z = gains[1] + 0j                                   # gains[0] is the offset c(z)
    q = np.exp(-1j * w)
    for tau, g in zip(P["tau"], gains[2:]):
        a = np.exp(-TS / tau)
        Z = Z + g * (1 - a) * q / (1 - a * q)
    if P["model"].startswith("RC+FO"):
        if P["model"] == "RC+FO const":
            beta = P["beta"]
        else:
            beta = float(hat_basis(np.array([z]), np.array(P["beta_knots_z"]))[0] @ np.array(P["beta_knots"]))
        # orders between grid points: interpolate the coefficients, as in the time domain
        j, t = frac_index(BETAS, np.array([beta]))
        H0, H1 = bank_response(bank, -float(BETAS[j[0]]), w), bank_response(bank, -float(BETAS[j[0] + 1]), w)
        Z = Z + gains[-1] * ((1 - t[0]) * H0 + t[0] * H1)
    return Z


def main():
    data = sys.argv[1] if len(sys.argv) > 1 else os.environ.get(
        "VOFRAC_DATA", os.path.expanduser("~/.cache/vofrac/panasonic18650pf"))
    e12 = json.load(open(os.path.join(OUT, "e12_battery.json")))
    _, bank = make_bank()
    docv = ocv_curve(os.path.join(data, "C20 OCV Test_C20_25dC.mat")).derivative()
    sweeps = []
    for path in sorted(glob.glob(os.path.join(data, "*EIS*.csv"))):
        r = read_eis(path)
        if r is None:
            continue
        f, Z, ah, Tc = r
        m = (f >= F_LO) & (f <= F_HI)
        if m.sum() < 15:
            continue
        T = min(SET_POINTS, key=lambda s: abs(s - Tc))
        g = e12["groups"].get(SET_POINTS[T])
        if not g or "all" not in g:
            continue
        z = 1.0 + ah / Q_REF
        zr = g["all"]["1RC"]["gain_knots_z"]
        w = 2 * np.pi * f[m] * TS
        Zocv = docv(np.clip(z, 0.0, 1.0)) / (Q_REF * 3600.0) / (1j * w / TS)
        err = {}
        for model in MODELS:
            Zm = model_impedance(g["all"][model], z, w, bank) + Zocv
            err[model] = float(np.sqrt(np.mean(np.abs(Zm - Z[m]) ** 2 / np.abs(Z[m]) ** 2)))
        sweeps.append({"file": os.path.basename(path), "T_set": T, "T_cell": Tc, "z": z,
                       "in_training_range": bool(zr[0] <= z <= zr[-1]), "n_freq": int(m.sum()), "rel_rms": err})
        print(f"{os.path.basename(path):20s} T {T:4d} z {z:.3f} " + " ".join(f"{k} {v:.3f}" for k, v in err.items()),
              flush=True)
    summary = {}
    for T in SET_POINTS:
        s = [x for x in sweeps if x["T_set"] == T and x["in_training_range"]]
        if s:
            summary[SET_POINTS[T]] = {"sweeps": len(s), **{k: float(np.mean([x["rel_rms"][k] for x in s])) for k in MODELS}}
            print(f"{SET_POINTS[T]:8s} ({len(s)} sweeps in range): "
                  + " ".join(f"{k} {summary[SET_POINTS[T]][k]:.3f}" for k in MODELS), flush=True)
    with open(os.path.join(OUT, "e12b_eis.json"), "w") as fh:
        json.dump({"band_hz": [F_LO, F_HI], "sweeps": sweeps, "summary": summary}, fh, indent=1)


if __name__ == "__main__":
    main()
