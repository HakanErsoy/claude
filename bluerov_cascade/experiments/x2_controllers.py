"""X2: all seven controller structures, each tuned by DE, PSO and SOO (10 runs, 3030 evaluations).

    python3 -I experiments/x2_controllers.py     # ~80 min on 4 cores, results/x2_controllers.json
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _tune import NFE, RES, run_all  # noqa: E402

from rovc.controllers import STRUCTURES  # noqa: E402

TUNERS = ("DE", "PSO", "SOO")
RUNS = 10

if __name__ == "__main__":
    jobs = [(f"{s}|{m}|{seed}", s, m, seed, False, NFE)
            for seed in range(RUNS) for m in TUNERS for s in STRUCTURES]
    run_all(os.path.join(RES, "x2_controllers.json"), jobs)
