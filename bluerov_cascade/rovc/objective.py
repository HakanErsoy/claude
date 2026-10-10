"""Multi-scenario tuning cost with phase-margin constraints over the actuator uncertainty.

    J(x) = sum_s [ sum_d w_d ITAE_{s,d} + rho E_s ] + K_pm sum_a sum_d max(0, PM*_a - PM_{a,d}) / PM*_a,

with w_d = scenarios.W_DOF, rho in 1/J, and the phase margins PM_{a,d} of the
linearized per-DOF loops (rovc.margins) at three actuator points a (MARGIN_POINTS):
the nominal thruster (tau_m = 0.1 s, 30 ms latency, PM* = 45 deg) and the slow
(0.2 s, 60 ms) and fast (0.05 s, 10 ms) corners (PM* = 20 deg). The T200
dynamics are not known well (Blue Robotics estimates 25-40 ms of ESC latency when
the motor runs; ~0.11 s was measured from standstill), so the design must hold
over this range. Runs that diverge get 1e4 (1 + lost fraction). `mirror=True`
evaluates the parameters reflected in the box (x -> lb + ub - x); an optimizer
without positional bias is unaffected by this change of coordinates.
"""

import numpy as np

from . import margins, scenarios, sim
from .sim import I_E, I_FAIL, I_ITAE

RHO = 2e-4          # 1/J (5 kJ of electrical energy ~ 1 unit of weighted ITAE)
PENALTY = 1e4
PM_REQ = 45.0       # deg, nominal requirement
K_PM = 200.0
MARGIN_POINTS = ((0.1, 3, PM_REQ), (0.2, 6, 20.0), (0.05, 1, 20.0))   # (tau_m [s], delay [samples], PM* [deg])


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
            pm = margins.phase_margins_multi(self.struct, P, scenarios.DT, [(t, n) for t, n, _ in MARGIN_POINTS])
            req = np.array([r for _, _, r in MARGIN_POINTS])[None, :, None]
            J = J + K_PM * np.sum(np.clip(req - pm, 0, None) / req, (1, 2))
        return J
