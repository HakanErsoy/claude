"""X1: tuners for the proposed FOPID-(1+TFOID) on the 6-DOF BlueROV2 Heavy.

Ten independent runs per method at an equal budget of 3030 evaluations, each in
the original and in the mirrored parameter box (x -> lb + ub - x). A method
without positional bias gives the same distribution in both. 'SOO-iter' is SOO
with as many iterations as the others (6030 evaluations), i.e. the
equal-iteration protocol of the earlier load-frequency study.

    python3 -I experiments/x1_optimizers.py      # ~60 min on 4 cores, results/x1_optimizers.json
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _tune import NFE, RES, run_all  # noqa: E402

METHODS = ("SOO", "BC-SOO", "PSO", "DE", "GWO", "GJO", "RS")
RUNS = 10
S = "FOPID-(1+TFOID)"

if __name__ == "__main__":
    jobs = []
    for seed in range(RUNS):
        for mirror in (False, True):
            for m in METHODS:
                jobs.append((f"{m}|{'mirror' if mirror else 'plain'}|{seed}", S, m, seed, mirror, NFE))
        jobs.append((f"SOO-iter|plain|{seed}", S, "SOO", seed, False, 2 * NFE - 30))
    run_all(os.path.join(RES, "x1_optimizers.json"), jobs)
