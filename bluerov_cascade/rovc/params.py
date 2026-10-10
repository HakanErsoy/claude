"""BlueROV2 Heavy: rigid-body, hydrodynamic and thruster-geometry parameters.

Hydrodynamic parameters: von Benzon et al., "An open-source benchmark simulator:
control of a BlueROV2 underwater robot", J. Mar. Sci. Eng. 10 (2022) 1898,
doi:10.3390/jmse10121898 (heavy configuration, from Wu 2018 and towing tests);
the same table is reproduced in arXiv:2405.10441, App. II.

Frames: NED earth frame, body frame x forward, y starboard, z down. The body
origin is the centre of gravity (r_g = 0), so the rigid-body mass matrix is
diagonal. Added masses and damping coefficients are stored as positive numbers.
"""

import numpy as np

RHO = 1000.0       # kg/m^3 (fresh water, as in the benchmark)
G = 9.81           # m/s^2

VEHICLE = dict(
    m=13.5, volume=0.0135,
    Ix=0.26, Iy=0.23, Iz=0.37,
    added=(6.357, 7.121, 18.69, 0.1858, 0.1348, 0.2215),       # X_udot, Y_vdot, Z_wdot, K_pdot, M_qdot, N_rdot
    lin=(13.7, 0.0, 33.0, 0.0, 0.8, 0.0),                       # X_u, Y_v, Z_w, K_p, M_q, N_r
    quad=(141.0, 217.0, 190.0, 1.192, 0.47, 1.5),               # X_u|u|, ..., N_r|r|
    rg=(0.0, 0.0, 0.0), rb=(0.0, 0.0, -0.01),
)

# Thruster layout of the heavy frame (ArduSub "vectored 6DOF"): four horizontal
# thrusters at 45 deg and four vertical thrusters. Positions [m] and the unit
# vector of positive thrust in the body frame; these reproduce the allocation
# matrix of von Benzon et al. (2022), Eq. (14).
_c = np.sqrt(0.5)
THR_POS = np.array([
    [0.156, 0.111, 0.085], [0.156, -0.111, 0.085], [-0.156, 0.111, 0.085], [-0.156, -0.111, 0.085],
    [0.120, 0.218, 0.0], [0.120, -0.218, 0.0], [-0.120, 0.218, 0.0], [-0.120, -0.218, 0.0],
])
THR_DIR = np.array([
    [_c, -_c, 0], [_c, _c, 0], [-_c, -_c, 0], [-_c, _c, 0],
    [0, 0, -1], [0, 0, 1], [0, 0, 1], [0, 0, -1],
], dtype=float)

DOF = ("x", "y", "z", "phi", "theta", "psi")


def allocation(pos=THR_POS, direc=THR_DIR):
    """6 x 8 matrix T with tau = T f (forces f along each thruster's positive direction)."""
    return np.vstack([direc.T, np.cross(pos, direc).T])


def mass_diag(v=VEHICLE):
    """Diagonal of M = M_RB + M_A (valid for r_g = 0)."""
    if any(v["rg"]):
        raise ValueError("the model assumes the body origin at the centre of gravity")
    return np.array([v["m"], v["m"], v["m"], v["Ix"], v["Iy"], v["Iz"]]) + np.array(v["added"])


def pack(v=VEHICLE, mass=1.0, added=1.0, damping=1.0, buoyancy=1.0):
    """Flat parameter vector for the simulator (layout in sim._rhs), with optional scale factors.

    `mass` scales m and the inertias, `added` the added masses, `damping` both
    damping sets and `buoyancy` the buoyancy force (W is fixed by the mass).
    """
    m = v["m"] * mass
    W = m * G
    B = RHO * G * v["volume"] * buoyancy * mass      # a heavier frame of the same density keeps W = B
    return np.array([
        m, v["Ix"] * mass, v["Iy"] * mass, v["Iz"] * mass,
        *(np.array(v["added"]) * added), *(np.array(v["lin"]) * damping), *(np.array(v["quad"]) * damping),
        W, B, *v["rg"], *v["rb"],
    ], dtype=float)
