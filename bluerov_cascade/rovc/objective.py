"""Multi-scenario tuning cost with a phase-margin constraint.

    J(x) = sum_s [ sum_d w_d ITAE_{s,d} + rho E_s ] + K_pm sum_d max(0, PM_req - PM_d) / PM_req,

with w_d = scenarios.W_DOF, rho in 1/J, the phase margins PM_d of the
linearized per-DOF loops (rovc.margins, including the command delay) and a
penalty of 1e4 (1 + lost fraction) for runs that diverge. `mirror=True`
evaluates the parameters reflected in the box (x -> lb + ub - x); an optimizer
without positional bias is unaffected by this change of coordinates.
"""

import numpy as np

from . import margins, scenarios, sim
from .sim import I_E, I_FAIL, I_ITAE

RHO = 2e-4          # 1/J (5 kJ of electrical energy ~ 1 unit of weighted ITAE)
PENALTY = 1e4
PM_REQ = 45.0       # deg, required phase margin of every linearized DOF loop
K_PM = 200.0


def cost(metrics, rho=RHO):
    """J of one scenario from the metric matrix [P, NM]."""
    J = metrics[:, I_ITAE:I_ITAE + 6] @ scenarios.W_DOF + rho * metrics[:, I_E]
    fail = metrics[:, I_FAIL]
    return np.where(fail > 0, PENALTY * (1.0 + fail), J)


class Objective:
    def __init__(self, struct, cases=None, rho=RHO, mirror=False, pm_req=PM_REQ):
        self.struct, self.rho, self.mirror, self.pm_req = struct, rho, mirror, pm_req
        self.cases = scenarios.training() if cases is None else cases

    def params(self, X):
        """Controller parameters for search points X (after the optional mirror)."""
        X = np.atleast_2d(X)
        return self.struct.phys(self.struct.lb + self.struct.ub - X if self.mirror else X)

    def __call__(self, X):
        P = self.params(X)
        J = sum(cost(sim.run(self.struct, P, sc), self.rho) for sc in self.cases)
        if self.pm_req:
            pm = margins.phase_margins(self.struct, P, scenarios.DT, scenarios.DELAY)
            J = J + K_PM * np.sum(np.clip(self.pm_req - pm, 0, None), 1) / self.pm_req
        return J
