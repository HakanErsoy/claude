"""X0: positional (centre/origin) bias of the tuners on shifted benchmark functions.

D = 22 (the dimension of the proposed controller), box [-100, 100]^D, optimum
at the origin or at a random point o in [-60, 60]^D. 15 runs, 3030 evaluations.

    python3 -I experiments/x0_center_bias.py     # ~3 min, results/x0_center_bias.json
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rovc import optim  # noqa: E402

D, LO, HI, NFE, RUNS = 22, -100.0, 100.0, 3030, 15


def sphere(z):
    return np.sum(z ** 2, 1)


def rastrigin(z):
    return 10 * z.shape[1] + np.sum(z ** 2 - 10 * np.cos(2 * np.pi * z), 1)


def rosenbrock(z):
    y = z / 25.0 + 1.0                 # optimum at z = 0, scaled to the box
    return np.sum(100 * (y[:, 1:] - y[:, :-1] ** 2) ** 2 + (1 - y[:, :-1]) ** 2, 1)


def ackley(z):
    y = z / 3.0
    return (-20 * np.exp(-0.2 * np.sqrt(np.mean(y ** 2, 1))) - np.exp(np.mean(np.cos(2 * np.pi * y), 1))
            + 20 + np.e)


FUNCS = dict(sphere=sphere, rastrigin=rastrigin, rosenbrock=rosenbrock, ackley=ackley)

if __name__ == "__main__":
    out = {}
    lb, ub = LO * np.ones(D), HI * np.ones(D)
    for fi, (fname, f) in enumerate(FUNCS.items()):
        for shifted in (False, True):
            o = np.random.default_rng(1000 + fi).uniform(-60, 60, D) if shifted else np.zeros(D)
            for m in optim.METHODS:
                vals = [optim.minimize(m, lambda X: f(X - o), lb, ub, NFE, seed=s)["f"] for s in range(RUNS)]
                key = f"{fname}|{'shifted' if shifted else 'origin'}|{m}"
                out[key] = vals
                print(f"{key:32s} median {np.median(vals):.3g}  IQR [{np.percentile(vals, 25):.3g}, "
                      f"{np.percentile(vals, 75):.3g}]", flush=True)
    json.dump(out, open(os.path.join(os.path.dirname(__file__), "..", "results", "x0_center_bias.json"), "w"),
              indent=1)
