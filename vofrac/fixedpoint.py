"""Bit-accurate fixed-point model of the discrete fixed-pole bank (RTL golden).

The bank runs in sample units (Ts = 1), where g0 = Ts^(-a) = 1 for every
order, so the recursive types need no divider: v = x - hist. Physical units
follow from one gain Ts^(-alpha_n): after the bank for A and E, before it
for B and D.

Number formats
  * signals x, v, y and the history sum: WS-bit two's complement with F
    fractional bits; I = WS - 1 - F integer bits cover the output bound
    V_max over the operating horizon n_max;
  * states: WST-bit words. Mode k stores its state scaled by 2^G_k (one
    gain per schedule) so that its own bound uses the full word: fast modes
    gain fractional bits, and the input-scheduled slow modes, whose
    per-sample increments c_k v are far below the signal LSB, become
    representable;
  * coefficients: mantissa/shift pairs c ~ M 2^-S, 2^(WM-2) <= |M| < 2^(WM-1).

Arithmetic (mirrored exactly by rtl/vo_bank_core.v), mulsh(a, M, S) =
(a M + 2^(S-1)) >> S for S > 0 and (a M) << -S otherwise:
  output schedule (A, D):
      hist = mulsh(dl, C_d) + sum_k mulsh(s_k, M_k, S_k + Go_k)
      s_k += (v << Go_k) - mulsh(s_k, U_k);   dl = v
  input schedule (B, E):
      hist = dl + sum_k mulsh(s_k, 1, Gi_k)
      s_k += mulsh(v, M_k, S_k - Gi_k) - mulsh(s_k, U_k);   dl = mulsh(v, C_d)
  A, B: v = x, y = x + hist.   D, E: v = x - hist, y = v.
D and E read the coefficient row of -alpha, i.e. the mirrored grid index.
"""

import math

import numpy as np

SBITS = 7          # shift field width (0..127)


def qcoef(c, WM, SMAX=(1 << SBITS) - 1):
    """Quantize c to (M, S), c ~ M 2^-S, floating mantissa of WM bits."""
    c = float(c)
    if c == 0.0:
        return 0, 0
    e = math.floor(math.log2(abs(c)))
    S = (WM - 2) - e
    if S < 0:
        raise ValueError(f"coefficient {c} too large for WM={WM}")
    if S > SMAX:
        return 0, 0
    M = int(round(c * 2.0 ** S))
    if abs(M) >= 2 ** (WM - 1):
        M //= 2
        S -= 1
    return M, S


def dq(MS):
    M, S = MS
    return M * 2.0 ** (-S)


def mulsh(a, M, S):
    p = a * M
    if S > 0:
        return (p + (1 << (S - 1))) >> S
    return p << (-S)


def alpha_grid(P, amax):
    """Symmetric order grid; index P-1-p holds -alpha_p."""
    return amax * np.linspace(-1.0, 1.0, P)


def output_bound(bank, n_max, amax, x_max=1.0, n_orders=9, types="AD"):
    """Bound on |v| and |y| for |x| <= x_max over n_max samples, all types.

    For A and B the bank input is x itself; for D and E it is the output.
    The l1 norm of each frozen-order impulse response bounds the output; the
    largest occurs at the integral end of the range.
    """
    d = np.zeros(n_max)
    d[0] = 1.0
    worst = 1.0
    for a in np.linspace(-amax, amax, n_orders):
        for T in types:
            worst = max(worst, np.abs(bank.simulate_type(d, np.full(n_max, a), T)).sum())
    return x_max * worst


def stress_bound(bank, n_max, amax, x_max=1.0, types="ABDE"):
    """Peak |v| and |y| over switching stress cases (DC input, all types).

    The frozen-order l1 bound does not cover order switching: a D-type
    operator that switches from an integral to a derivative order applies
    the new integral to an already grown history, so its output can exceed
    every frozen-order bound. Cases: constant +-amax, single switches
    between the extremes at n/4, n/2, 3n/4, and alternating extremes.
    """
    t = np.arange(n_max)
    profiles = [np.full(n_max, a) for a in (-amax, amax)]
    for frac in (0.25, 0.5, 0.75):
        for a1, a2 in ((-amax, amax), (amax, -amax), (-amax, 0.0), (0.0, -amax)):
            profiles.append(np.where(t < frac * n_max, a1, a2))
    profiles.append(np.where((t // max(1, n_max // 8)) % 2 == 0, -amax, amax))
    worst = 0.0
    x = np.full(n_max, x_max)
    for al in profiles:
        for T in types:
            worst = max(worst, float(np.abs(bank.simulate_type(x, al, T)).max()))
    return worst


class FixedPointBank:
    def __init__(self, bank, P=1024, amax=0.95, WS=32, WST=None, WM=25, n_max=4000,
                 x_max=1.0, dc_floor=True, V_max=None):
        if bank.Ts != 1.0:
            raise ValueError("build the bank in sample units (Ts = 1)")
        self.bank, self.P, self.amax, self.n_max = bank, P, amax, n_max
        self.K = bank.K
        self.WM = WM
        self.V_max = V_max if V_max is not None else output_bound(bank, n_max, amax, x_max)
        self.I = int(math.ceil(math.log2(1.25 * self.V_max))) + 1
        self.WS = WS
        self.F = WS - 1 - self.I
        if self.F < 1:
            raise ValueError("WS too small for the output bound")
        self.LOGN = int(math.ceil(math.log2(n_max))) + 1
        self.WST = WST if WST is not None else WS + self.LOGN
        self.grid = alpha_grid(P, amax)
        self.U = [qcoef(u, WM) for u in bank.one_minus_theta]
        raw = [bank.coeffs(float(a)) for a in self.grid]
        self.floor_hits = 0
        self.C = []
        for a, (g0, cd, c) in zip(self.grid, raw):
            row = [qcoef(ck, WM) for ck in c] + [qcoef(cd, WM)]
            if dc_floor and a > 0:
                row = self._quantized_dc_floor(row, bank.dc_gain(float(a)))
            self.C.append(row)
        # per-mode state gains from the state bounds (powers of two)
        mem = np.minimum(n_max, 1.0 / bank.one_minus_theta)
        cmax = np.max(np.abs(np.array([[dq(m) for m in row[:-1]] for row in self.C])), axis=0)
        head = (self.WST - 1 - self.F) - 1          # integer bits of a state word, 1 bit margin
        Bo = self.V_max * mem
        Bi = self.V_max * np.maximum(cmax, 1e-300) * mem
        self.Go = [max(0, int(math.floor(head - math.log2(b)))) for b in Bo]
        self.Gi = [max(0, int(math.floor(head - math.log2(b)))) for b in Bi]
        for g, s in zip(self.Go + self.Gi, [m[1] for m in self.U] * 2):
            if g >= (1 << SBITS):
                raise ValueError("state gain exceeds shift field")

    def _dc_gain(self, row):
        u = np.array([dq(x) for x in self.U])
        c = np.array([dq(x) for x in row[:-1]])
        return 1.0 + dq(row[-1]) + float(np.sum(c / u))

    def _quantized_dc_floor(self, row, target):
        """Inverse stability must hold for the *quantized* coefficients.
        Raise the delay coefficient, in mantissa LSBs, until the quantized
        DC gain is at least that of the floating-point bank (itself floored
        positive), so the inverse keeps the designed low-frequency gain."""
        M, S = row[-1]
        for _ in range(1 << 16):
            if self._dc_gain(row) > target:
                return row
            self.floor_hits += 1
            step = max(1, int(math.ceil((target - self._dc_gain(row)) * 2.0 ** S)))
            M += step
            if abs(M) >= 2 ** (self.WM - 1):
                M //= 2
                S -= 1
            row = row[:-1] + [(M, S)]
        raise RuntimeError("DC floor did not converge")

    # ------------------------------------------------------------------ I/O
    def to_int(self, x):
        return [int(round(v * 2.0 ** self.F)) for v in np.asarray(x, dtype=float)]

    def to_float(self, y):
        return np.asarray(y, dtype=float) * 2.0 ** (-self.F)

    def index(self, alpha):
        a = np.clip(np.asarray(alpha, dtype=float), -self.amax, self.amax)
        return np.rint((a / self.amax + 1.0) * 0.5 * (self.P - 1)).astype(int)

    # --------------------------------------------------------------- golden
    def run(self, x_int, aidx, vo_type, check=True):
        """Golden integer model; vo_type is one letter or a per-sample sequence."""
        K, P = self.K, self.P
        lim_s, lim_x = 1 << (self.WST - 1), 1 << (self.WS - 1)
        # Python ints throughout: numpy int64 inputs would overflow silently in
        # the wide products
        x_int = [int(v) for v in x_int]
        aidx = [int(v) for v in aidx]
        types = [vo_type] * len(x_int) if isinstance(vo_type, str) else list(vo_type)
        U, Go, Gi = self.U, self.Go, self.Gi
        s = [0] * K
        dl = 0
        y = [0] * len(x_int)
        self.peak_state = self.peak_signal = 0
        for n, (x, p, T) in enumerate(zip(x_int, aidx, types)):
            out_sched = T in ("A", "D")
            inv = T in ("D", "E")
            C = self.C[P - 1 - p if inv else p]
            if out_sched:
                hist = mulsh(dl, *C[K])
                for k in range(K):
                    hist += mulsh(s[k], C[k][0], C[k][1] + Go[k])
            else:
                hist = dl
                for k in range(K):
                    hist += mulsh(s[k], 1, Gi[k])
            if inv:
                v = x - hist
                y[n] = v
            else:
                v = x
                y[n] = x + hist
            if out_sched:
                for k in range(K):
                    s[k] = s[k] + (v << Go[k]) - mulsh(s[k], *U[k])
                dl = v
            else:
                for k in range(K):
                    s[k] = s[k] + mulsh(v, C[k][0], C[k][1] - Gi[k]) - mulsh(s[k], *U[k])
                dl = mulsh(v, *C[K])
            if check:
                ms = max(abs(t) for t in s)
                mx = max(abs(y[n]), abs(hist), abs(dl))
                self.peak_state = max(self.peak_state, ms)
                self.peak_signal = max(self.peak_signal, mx)
                if ms >= lim_s or mx >= lim_x:
                    raise OverflowError(f"overflow at sample {n}: state 2^{math.log2(ms + 1):.1f} "
                                        f"(WST={self.WST}), signal 2^{math.log2(mx + 1):.1f} (WS={self.WS})")
        return y

    # ---------------------------------------------------------------- export
    def pack(self, MS):
        """{M (WM bits, two's complement), S (SBITS bits)} as one integer."""
        M, S = MS
        return ((M & ((1 << self.WM) - 1)) << SBITS) | S

    def export_mem(self, outdir):
        import os
        os.makedirs(outdir, exist_ok=True)
        w = (self.WM + SBITS + 3) // 4
        with open(os.path.join(outdir, "coef.mem"), "w") as f:
            for row in self.C:
                for MS in row:
                    f.write(f"{self.pack(MS):0{w}x}\n")
        with open(os.path.join(outdir, "upole.mem"), "w") as f:
            for MS in self.U:
                f.write(f"{self.pack(MS):0{w}x}\n")
        with open(os.path.join(outdir, "gain.mem"), "w") as f:
            for go, gi in zip(self.Go, self.Gi):
                f.write(f"{(go << SBITS) | gi:04x}\n")
        return {"K": self.K, "P": self.P, "WS": self.WS, "WST": self.WST, "WM": self.WM,
                "F": self.F, "I": self.I, "SBITS": SBITS}
