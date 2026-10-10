"""X2r: robust tuning of the cascades: training also on a severe-noise case and a weak-actuator corner case.

X6 showed that, for every cascade, a lower nominal training cost goes with more divergences in
the Monte Carlo study. Here the robustness requirement is part of the cost
(rovc.scenarios.training(robust=True)). PSO, 10 030 evaluations, 10 runs.

    python3 -I experiments/x2r_robust.py         # ~3 h on 4 cores, results/x2r_robust.json
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _tune import RES, run_all  # noqa: E402

from rovc import scenarios  # noqa: E402

NFE = 10030
RUNS = 10
ORDER = ("FOPID-(1+TFOID)", "P-PID", "PI-(1+FOPID)", "FOPI-FOPD", "FOPID", "PID", "FOPID-FOPI")
N_STRUCT = int(os.environ.get("X2R_STRUCTURES", "4"))     # the four cascades first; 7 for all

if __name__ == "__main__":
    jobs = [(f"{s}|PSO|{seed}", s, "PSO", seed, False, NFE) for seed in range(RUNS) for s in ORDER[:N_STRUCT]]
    run_all(os.path.join(RES, "x2r_robust.json"), jobs, cases=scenarios.training(robust=True))
