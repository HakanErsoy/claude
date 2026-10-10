"""Population-based optimizers with a common batched interface and an equal evaluation budget.

    minimize(name, f, lb, ub, nfe, pop=30, seed=0) -> dict(x, f, curve, nfe)

`f` maps a batch X[P, D] to costs[P]. Every method stops once `nfe` evaluations
(including the initial population) have been spent, so methods that evaluate
twice per iteration (SOO) get half as many iterations. Bounds are handled by
clipping, as in the released SOO code.

SOO follows the equations of Rodan et al., Cluster Comput. 28 (2025) 362, in the
reading of the mealpy reimplementation (single population, both movements in
every iteration, greedy survivor selection, P0 = 3, Delta P = 0.001 per
iteration); see docs/PLAN.md for the known paper/code inconsistencies.
"""

import math

import numpy as np


class _Budget:
    def __init__(self, f, nfe):
        self.f, self.nfe, self.used = f, nfe, 0
        self.best_f, self.best_x = np.inf, None
        self.curve = []          # (evaluations used, best-so-far)

    def left(self):
        return self.nfe - self.used

    def __call__(self, X):
        X = X[:max(self.left(), 0)]
        if X.shape[0] == 0:
            return np.zeros(0)
        y = np.asarray(self.f(X), float)
        y = np.where(np.isfinite(y), y, np.inf)
        self.used += X.shape[0]
        i = int(np.argmin(y))
        if y[i] < self.best_f:
            self.best_f, self.best_x = float(y[i]), X[i].copy()
        self.curve.append((self.used, self.best_f))
        return y


def _greedy(X, F, Xn, Fn):
    k = Fn.size
    better = Fn < F[:k]
    X[:k][better] = Xn[:k][better]
    F[:k][better] = Fn[better]


def soo(B, lb, ub, pop, rng, centred=False):
    """SOO; centred=True is BC-SOO: the first movement written in coordinates relative to x_best.

    In BC-SOO the substitution x -> x - x_best (so x_best -> 0) is applied to the
    first movement, which removes every reference to the coordinate origin:
        pos_k = x_best - r_k r3 S (caf r1 - 1)(x_i - x_best),   k = 1, 2,
        x_new = x_best + r3 ((pos_1 + pos_2)/2 - x_best).
    The second movement (top-3 mean plus differences) is already translation invariant.
    """
    D = lb.size
    X = lb + rng.random((pop, D)) * (ub - lb)
    F = B(X)
    T = max(1, (B.nfe - pop) // (2 * pop))
    for t in range(1, T + 1):
        if B.left() <= 0:
            break
        caf = 2 * math.pi / (3.0 + 0.001 * t)
        S = 2.0 * (1.0 - t / T)
        xb = X[np.argmin(F)]
        r1, r2, r3 = rng.random((3, pop, D))
        base = S * (caf * r1 - 1.0)
        if centred:
            pos1 = xb - r1 * r3 * base * (X - xb)
            pos2 = xb - r2 * r3 * base * (X - xb)
            Xn = np.clip(xb + r3 * ((pos1 + pos2) / 2.0 - xb), lb, ub)
        else:
            pos1 = xb - r1 * r3 * base * (X - np.abs(r1 * np.sin(r2) * np.abs(r3 * xb)))
            pos2 = xb - r2 * r3 * base * (X - np.abs(r1 * np.cos(r2) * np.abs(r3 * xb)))
            Xn = np.clip(r3 * (pos1 + pos2) / 2.0, lb, ub)
        _greedy(X, F, Xn, B(Xn))
        if B.left() <= 0:
            break
        avg3 = X[np.argsort(F)[:3]].mean(0)
        Xn = np.empty_like(X)
        for i in range(pop):
            a, b, c = rng.choice(np.delete(np.arange(pop), i), 3, replace=False)
            rf = rng.random()
            cand = avg3 + 0.5 * (math.sin(rf * math.pi) * (X[a] - X[b]) + math.cos((1 - rf) * math.pi) * (X[a] - X[c]))
            Xn[i] = np.where(rng.random(D) <= 0.5, cand, X[i])
        Xn = np.clip(Xn, lb, ub)
        _greedy(X, F, Xn, B(Xn))


def pso(B, lb, ub, pop, rng, w=0.7298, c1=1.49618, c2=1.49618):
    D = lb.size
    X = lb + rng.random((pop, D)) * (ub - lb)
    V = np.zeros_like(X)
    vmax = 0.2 * (ub - lb)
    F = B(X)
    P, PF = X.copy(), F.copy()
    while B.left() > 0:
        g = P[np.argmin(PF)]
        r1, r2 = rng.random((2, pop, D))
        V = np.clip(w * V + c1 * r1 * (P - X) + c2 * r2 * (g - X), -vmax, vmax)
        X = np.clip(X + V, lb, ub)
        F = B(X)
        k = F.size
        imp = F < PF[:k]
        P[:k][imp], PF[:k][imp] = X[:k][imp], F[imp]


def de(B, lb, ub, pop, rng, Fw=0.5, CR=0.9):
    D = lb.size
    X = lb + rng.random((pop, D)) * (ub - lb)
    F = B(X)
    while B.left() > 0:
        U = np.empty_like(X)
        for i in range(pop):
            a, b, c = rng.choice(np.delete(np.arange(pop), i), 3, replace=False)
            v = X[a] + Fw * (X[b] - X[c])
            m = rng.random(D) < CR
            m[rng.integers(D)] = True
            U[i] = np.where(m, v, X[i])
        U = np.clip(U, lb, ub)
        _greedy(X, F, U, B(U))


def gwo(B, lb, ub, pop, rng):
    D = lb.size
    X = lb + rng.random((pop, D)) * (ub - lb)
    F = B(X)
    T = max(1, (B.nfe - pop) // pop)
    t = 0
    while B.left() > 0:
        a = 2.0 * (1.0 - t / T)
        idx = np.argsort(F)[:3]
        Xn = np.zeros_like(X)
        for leader in X[idx]:
            r1, r2 = rng.random((2, pop, D))
            A, C = 2 * a * r1 - a, 2 * r2
            Xn += leader - A * np.abs(C * leader - X)
        X = np.clip(Xn / 3.0, lb, ub)
        Fn = B(X)
        F = np.concatenate([Fn, F[Fn.size:]])     # GWO replaces the pack (no greedy step)
        t += 1


def _levy(rng, shape, beta=1.5):
    s = (math.gamma(1 + beta) * math.sin(math.pi * beta / 2)
         / (math.gamma((1 + beta) / 2) * beta * 2 ** ((beta - 1) / 2))) ** (1 / beta)
    return 0.01 * rng.standard_normal(shape) * s / np.abs(rng.standard_normal(shape)) ** (1 / beta)


def gjo(B, lb, ub, pop, rng, c1=1.5):
    """Golden jackal optimization (Chopra and Ansari, Expert Syst. Appl. 198 (2022) 116924)."""
    D = lb.size
    X = lb + rng.random((pop, D)) * (ub - lb)
    F = B(X)
    T = max(1, (B.nfe - pop) // pop)
    t = 0
    while B.left() > 0:
        o = np.argsort(F)
        male, female = X[o[0]].copy(), X[o[1]].copy()
        E1 = c1 * (1.0 - t / T)
        E = E1 * (2 * rng.random((pop, D)) - 1)
        rl = 0.05 * _levy(rng, (pop, D))
        explore = np.abs(E) >= 1
        y1 = np.where(explore, male - E * np.abs(male - rl * X), male - E * np.abs(rl * male - X))
        y2 = np.where(explore, female - E * np.abs(female - rl * X), female - E * np.abs(rl * female - X))
        X = np.clip((y1 + y2) / 2.0, lb, ub)
        Fn = B(X)
        F = np.concatenate([Fn, F[Fn.size:]])     # positions are replaced, as in the original
        t += 1


def rs(B, lb, ub, pop, rng):
    """Uniform random search (sanity baseline)."""
    while B.left() > 0:
        B(lb + rng.random((pop, lb.size)) * (ub - lb))


METHODS = {"SOO": soo, "BC-SOO": lambda *a: soo(*a, centred=True), "PSO": pso, "DE": de, "GWO": gwo, "GJO": gjo,
           "RS": rs}


def minimize(name, f, lb, ub, nfe, pop=30, seed=0):
    lb, ub = np.asarray(lb, float), np.asarray(ub, float)
    B = _Budget(f, nfe)
    METHODS[name](B, lb, ub, pop, np.random.default_rng(seed))
    return dict(x=B.best_x, f=B.best_f, curve=np.array(B.curve), nfe=B.used)
