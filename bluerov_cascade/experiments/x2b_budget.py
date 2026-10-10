"""X2b: all seven structures tuned by PSO with a 3.3 times larger budget (10 030 evaluations, 10 runs).

Answers whether the higher nominal cost of the 22-parameter FOPID-(1+TFOID) against the
8-parameter P-PID in X2 is a search limitation.

    python3 -I experiments/x2b_budget.py         # ~2.5 h on 4 cores, results/x2b_budget.json
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _tune import RES, run_all  # noqa: E402

from rovc.controllers import STRUCTURES  # noqa: E402

NFE = 10030
RUNS = 10

if __name__ == "__main__":
    # cheapest structures first, so partial results are useful early
    order = sorted(STRUCTURES, key=lambda s: STRUCTURES[s].dim)
    jobs = [(f"{s}|PSO|{seed}", s, "PSO", seed, False, NFE) for seed in range(RUNS) for s in order]
    run_all(os.path.join(RES, "x2b_budget.json"), jobs)
