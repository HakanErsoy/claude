"""Multi-scenario tuning cost: weighted ITAE over the six DOF plus electrical energy.

    J(x) = sum_s [ sum_d w_d ITAE_{s,d} + rho E_s ] + penalty,

with w_d = scenarios.W_DOF, rho in 1/J and a penalty of 1e4 (1 + lost fraction)
for runs that diverge. `mirror=True` evaluates the parameters reflected in the
box (x -> lb + ub - x); an optimizer without positional bias is unaffected by
this change of coordinates.
"""

import numpy as np

from . import scenarios, sim
from .sim import I_E, I_FAIL, I_ITAE

RHO = 2e-4          # 1/J (5 kJ of electrical energy ~ 1 unit of weighted ITAE)
PENALTY = 1e4


def cost(metrics, rho=RHO):
    """J of one scenario from the metric matrix [P, NM]."""
    J = metrics[:, I_ITAE:I_ITAE + 6] @ scenarios.W_DOF + rho * metrics[:, I_E]
    fail = metrics[:, I_FAIL]
    return np.where(fail > 0, PENALTY * (1.0 + fail), J)


class Objective:
    def __init__(self, struct, cases=None, rho=RHO, mirror=False):
        self.struct, self.rho, self.mirror = struct, rho, mirror
        self.cases = scenarios.training() if cases is None else cases

    def params(self, X):
        X = np.atleast_2d(X)
        return self.struct.lb + self.struct.ub - X if self.mirror else X

    def __call__(self, X):
        P = self.params(X)
        return sum(cost(sim.run(self.struct, P, sc), self.rho) for sc in self.cases)
