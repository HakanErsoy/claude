"""Controller structures for the six degrees of freedom.

Every structure is a position stage acting on the error e1 = r - eta (body frame
for translation) and, for the cascades, a velocity stage acting on
e2 = u1 - nu, where u1 is the output of the first stage (a velocity reference)
and nu the measured body velocity. This is the mechanical counterpart of the
FOPID-(1+TFOID) of Nour, Magdy and Jurado (Sci. Rep. 16 (2026) 30699), where
the second stage acts on u1 - Delta f. The output is an acceleration demand a,
and tau = M_nom a with the nominal diagonal inertia.

One parameter set is shared by the translational DOFs (x, y, z) and one by the
rotational DOFs (phi, theta, psi), so a structure with p parameters has 2p
decision variables.
"""

import numpy as np

from .fractional import NSEC, slot_sections, tustin

NOP = 5            # operator slots per DOF
GAIN = (0.0, 50.0)
LAM = (0.0, 1.5)   # integral orders
MU = (0.0, 1.0)    # derivative orders
TILT_N = (1.0, 10.0)


def _b(names):
    lo, hi = [], []
    for n in names:
        r = TILT_N if n == "n" else LAM if n.startswith("lam") else MU if n.startswith("mu") else GAIN
        lo.append(r[0])
        hi.append(r[1])
    return np.array(lo), np.array(hi)


class Structure:
    """name, parameter names of one group, cascade flag and a map to (kp1, kp2, slots)."""

    def __init__(self, name, names, cascade, fn):
        self.name, self.names, self.cascade, self._fn = name, tuple(names), cascade, fn
        lo, hi = _b(names)
        self.lb = np.concatenate([lo, lo])
        self.ub = np.concatenate([hi, hi])
        self.dim = 2 * len(names)

    def labels(self):
        return [f"{n}_{g}" for g in ("t", "r") for n in self.names]

    def group(self, x):
        """kp1, kp2, [(stage, kind, gain, alpha)] for one group's parameter vector."""
        return self._fn(dict(zip(self.names, x)))


def _proposed(p):
    return p["Kp"], 1.0, [
        (0, "fo", p["Ki1"], -p["lam1"]), (0, "fo", p["Kd1"], p["mu1"]),
        (1, "fo", p["Kt"], -1.0 / p["n"]), (1, "fo", p["Ki2"], -p["lam2"]), (1, "fo", p["Kd2"], p["mu2"])]


def _fopid(p):
    return p["Kp"], 0.0, [(0, "fo", p["Ki"], -p["lam"]), (0, "fo", p["Kd"], p["mu"])]


def _pid(p):
    return p["Kp"], 0.0, [(0, "int", p["Ki"], -1.0), (0, "dfilt", p["Kd"], 1.0)]


def _p_pid(p):
    return p["Kp1"], p["Kp2"], [(1, "int", p["Ki2"], -1.0), (1, "dfilt", p["Kd2"], 1.0)]


def _pi_1fopid(p):
    return p["Kp1"], 1.0 + p["Kp2"], [
        (0, "int", p["Ki1"], -1.0), (1, "fo", p["Ki2"], -p["lam"]), (1, "fo", p["Kd"], p["mu"])]


def _fopid_fopi(p):
    return p["Kp1"], p["Kp2"], [
        (0, "fo", p["Ki1"], -p["lam1"]), (0, "fo", p["Kd"], p["mu"]), (1, "fo", p["Ki2"], -p["lam2"])]


def _fopi_fopd(p):
    return p["Kp1"], p["Kp2"], [(0, "fo", p["Ki"], -p["lam"]), (1, "fo", p["Kd"], p["mu"])]


STRUCTURES = {s.name: s for s in [
    Structure("FOPID-(1+TFOID)", ["Kp", "Ki1", "lam1", "Kd1", "mu1", "Kt", "n", "Ki2", "lam2", "Kd2", "mu2"],
              True, _proposed),
    Structure("FOPID", ["Kp", "Ki", "lam", "Kd", "mu"], False, _fopid),
    Structure("PID", ["Kp", "Ki", "Kd"], False, _pid),
    Structure("P-PID", ["Kp1", "Kp2", "Ki2", "Kd2"], True, _p_pid),
    Structure("PI-(1+FOPID)", ["Kp1", "Ki1", "Kp2", "Ki2", "lam", "Kd", "mu"], True, _pi_1fopid),
    Structure("FOPID-FOPI", ["Kp1", "Ki1", "lam1", "Kd", "mu", "Kp2", "Ki2", "lam2"], True, _fopid_fopi),
    Structure("FOPI-FOPD", ["Kp1", "Ki", "lam", "Kp2", "Kd", "mu"], True, _fopi_fopd),
]}


def build(struct, X, dt):
    """Simulator arrays for a batch X[P, dim] of one structure.

    Returns kp1[P,6], kp2[P,6], sec[P,6,NOP,NSEC,3], gain[P,6,NOP], integ[P,6,NOP], stage[NOP], cascade.
    Slots are placed in a fixed order per structure, so `stage` is shared by the batch.
    """
    X = np.atleast_2d(np.asarray(X, float))
    P = X.shape[0]
    half = len(struct.names)
    kp1 = np.zeros((P, 6))
    kp2 = np.zeros((P, 6))
    sec = np.zeros((P, 6, NOP, NSEC, 3))
    sec[..., 0] = 1.0
    gain = np.zeros((P, 6, NOP))
    integ = np.zeros((P, 6, NOP), dtype=np.int64)
    stage = np.zeros(NOP, dtype=np.int64)
    for i in range(P):
        for g in range(2):
            k1, k2, slots = struct.group(X[i, g * half:(g + 1) * half])
            for j, (st, kind, gn, al) in enumerate(slots):
                zs, ps, k, it = slot_sections(kind, gn, al)
                c = tustin(zs, ps, dt)
                for d in range(3 * g, 3 * g + 3):
                    sec[i, d, j] = c
                    gain[i, d, j] = k
                    integ[i, d, j] = it
                stage[j] = st
            kp1[i, 3 * g:3 * g + 3] = k1
            kp2[i, 3 * g:3 * g + 3] = k2
    return kp1, kp2, sec, gain, integ, stage, int(struct.cascade)
