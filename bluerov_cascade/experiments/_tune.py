"""Shared driver: independent tuning runs with incremental JSON output (resumable)."""

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rovc import objective, optim  # noqa: E402
from rovc.controllers import STRUCTURES  # noqa: E402

RES = os.path.join(os.path.dirname(__file__), "..", "results")
NFE = 3030          # 30 initial + 100 iterations of 30 (50 for SOO, which evaluates twice per iteration)
POP = 30


def _curve(c, nfe):
    """Best-so-far on a grid of 101 evaluation counts."""
    grid = np.linspace(POP, nfe, 101)
    idx = np.searchsorted(c[:, 0], grid, side="right") - 1
    return np.where(idx >= 0, c[np.clip(idx, 0, None), 1], np.nan).tolist()


def run_all(path, jobs):
    """jobs: list of (key, structure name, method, seed, mirror, nfe)."""
    out = json.load(open(path)) if os.path.exists(path) else {}
    for key, sname, method, seed, mirror, nfe in jobs:
        if key in out:
            continue
        s = STRUCTURES[sname]
        ob = objective.Objective(s, mirror=mirror)
        t0 = time.time()
        r = optim.minimize(method, ob, s.lb, s.ub, nfe, pop=POP, seed=seed)
        x = ob.params(r["x"])[0]
        out[key] = dict(structure=sname, method=method, seed=seed, mirror=mirror, nfe=r["nfe"], f=r["f"],
                        x=x.tolist(), curve=_curve(r["curve"], nfe), seconds=time.time() - t0)
        print(f"{key:40s} J={r['f']:.4f} ({out[key]['seconds']:.0f} s)", flush=True)
        tmp = path + ".tmp"
        json.dump(out, open(tmp, "w"))
        os.replace(tmp, path)
    return out
