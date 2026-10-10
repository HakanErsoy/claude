"""Download the Blue Robotics T200 performance data and fit the thruster model.

Source: Blue Robotics, "T200 Public Performance Data 10-20V (September 2019)",
https://cad.bluerobotics.com/T200-Public-Performance-Data-10-20V-September-2019.xlsx
The spreadsheet is not stored in this repository; it is fetched into a data
directory (argument, or $ROVC_DATA, default ~/.cache/rovc) and checked by SHA-256.

The fit gives the coefficients in rovc/thruster.py (COEF). With u = (PWM - 1500)/400,

    F(u) = sum_k a_k (u - d+)^k   for u >  d+,
    F(u) = -sum_k b_k (-u - d-)^k for u < -d-,   F = 0 in between,

and the electrical power P(u) the same way (degree 3, no constant term). The
simulator uses the power as a function of the actual thrust,
P(F) = sum_k q_k |F|^k (k = 1..3, separate coefficients qa for F > 0, qb for F < 0).

    python3 -I experiments/fetch_t200.py [DATA_DIR]      # prints COEF and the fit errors
"""

import hashlib
import json
import os
import sys
import urllib.request

import numpy as np

URL = "https://cad.bluerobotics.com/T200-Public-Performance-Data-10-20V-September-2019.xlsx"
SHA256 = "1399b76df7a176cfbb08760c11731199053336e7d92182dece11824c73285085"
VOLTS = (10, 12, 14, 16, 18, 20)
KGF = 9.80665
DEG = 3


def fetch(out):
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, os.path.basename(URL))
    if not (os.path.exists(path) and hashlib.sha256(open(path, "rb").read()).hexdigest() == SHA256):
        req = urllib.request.Request(URL, headers={"User-Agent": "rovc-fetch/1.0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            blob = r.read()
        if hashlib.sha256(blob).hexdigest() != SHA256:
            raise RuntimeError("SHA-256 mismatch for " + URL)
        open(path, "wb").write(blob)
    return path


def read(path):
    """{volt: (pwm, force [N], power [W])} from the spreadsheet."""
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    out = {}
    for v in VOLTS:
        rows = [r[:7] for r in wb[f"{v} V"].iter_rows(min_row=2, values_only=True) if r[0] is not None]
        a = np.array(rows, float)
        out[v] = (a[:, 0], a[:, 5] * KGF, a[:, 4])
    return out


def _side(x, y, dgrid):
    """Least-squares polynomial in (x - d), no constant, best d on a grid; x >= 0 is the distance from 0."""
    best = None
    for d in dgrid:
        m = x > d
        X = np.stack([(x[m] - d) ** k for k in range(1, DEG + 1)], 1)
        c, *_ = np.linalg.lstsq(X, y[m], rcond=None)
        pred = np.where(x > d, sum(c[k - 1] * np.clip(x - d, 0, None) ** k for k in range(1, DEG + 1)), 0.0)
        sse = np.sum((pred - y) ** 2)
        if best is None or sse < best[0]:
            best = (sse, d, c)
    return best[1], best[2]


def _lsq(x, y):
    X = np.stack([x ** k for k in range(1, DEG + 1)], 1)
    return np.linalg.lstsq(X, y, rcond=None)[0]


def fit(data):
    dgrid = np.arange(0.04, 0.11, 0.0025)
    coef, err = {}, {}
    for v, (pwm, F, P) in data.items():
        u = (pwm - 1500.0) / 400.0
        pos, neg = u > 0, u < 0
        dp, a = _side(u[pos], F[pos], dgrid)
        dn, b = _side(-u[neg], -F[neg], dgrid)
        dpp, ap = _side(u[pos], P[pos], dgrid)
        dpn, bp = _side(-u[neg], P[neg], dgrid)
        qa = _lsq(F[F > 0], P[F > 0])
        qb = _lsq(-F[F < 0], P[F < 0])
        r = lambda x, n: round(float(x), n)
        coef[v] = dict(dp=r(dp, 4), dn=r(dn, 4), a=[r(x, 4) for x in a], b=[r(x, 4) for x in b],
                       pdp=r(dpp, 4), pdn=r(dpn, 4), pa=[r(x, 3) for x in ap], pb=[r(x, 3) for x in bp],
                       qa=[r(x, 6) for x in qa], qb=[r(x, 6) for x in qb])
        from_model = _eval(coef[v], u)
        PF = np.where(F > 0, sum(qa[k] * np.abs(F) ** (k + 1) for k in range(3)),
                      sum(qb[k] * np.abs(F) ** (k + 1) for k in range(3)))
        err[v] = dict(power_of_thrust_rms=float(np.sqrt(np.mean((PF - P)[F != 0] ** 2))),
                      force_rms=float(np.sqrt(np.mean((from_model[0] - F) ** 2))),
                      force_max=float(np.max(np.abs(from_model[0] - F))),
                      power_rms=float(np.sqrt(np.mean((from_model[1] - P) ** 2))),
                      F_min=float(F.min()), F_max=float(F.max()), P_max=float(P.max()))
    return coef, err


def _eval(c, u):
    def poly(x, d, k):
        z = np.clip(x - d, 0, None)
        return sum(k[i] * z ** (i + 1) for i in range(len(k)))
    F = np.where(u > 0, poly(u, c["dp"], c["a"]), -poly(-u, c["dn"], c["b"]))
    P = np.where(u > 0, poly(u, c["pdp"], c["pa"]), poly(-u, c["pdn"], c["pb"]))
    return F, P


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ROVC_DATA", os.path.expanduser("~/.cache/rovc"))
    coef, err = fit(read(fetch(out)))
    print("COEF = {")
    for v in VOLTS:
        print(f"    {v}: {coef[v]},")
    print("}")
    print(json.dumps(err, indent=1))


if __name__ == "__main__":
    main()
