"""Blue Robotics T200 thruster: static thrust and electrical power from the measured curves.

COEF is the output of experiments/fetch_t200.py (least-squares fit to the
public performance data, 10-20 V). With u = (PWM - 1500)/400 in [-1, 1],

    F(u) =  a1 z + a2 z^2 + a3 z^3,  z = u - d+   (u > d+)
    F(u) = -(b1 z + b2 z^2 + b3 z^3), z = -u - d-  (u < -d-),   F = 0 in the dead band,

and the power P(u) the same way with (pa, pb). Fit error at 16 V: 0.24 N RMS,
1.3 N max (of 51 N). The flat layout of `coef_array` is what the simulator uses.
"""

import numpy as np

COEF = {
    10: {'dp': 0.0925, 'dn': 0.0925, 'a': [14.045, 29.243, -10.1274], 'b': [11.6072, 21.8268, -7.2311], 'pdp': 0.105, 'pdn': 0.1025, 'pa': [0.339, 165.985, 9.54], 'pb': [0.076, 155.748, 20.774]},
    12: {'dp': 0.08, 'dn': 0.0825, 'a': [16.9461, 35.376, -10.6931], 'b': [14.3121, 26.9028, -8.7337], 'pdp': 0.0925, 'pdn': 0.095, 'pa': [-0.468, 231.07, 25.616], 'pb': [0.269, 220.641, 41.389]},
    14: {'dp': 0.0725, 'dn': 0.0725, 'a': [20.1818, 41.5328, -11.2836], 'b': [16.1944, 33.7439, -11.0521], 'pdp': 0.075, 'pdn': 0.08, 'pa': [0.249, 273.789, 73.01], 'pb': [0.018, 269.807, 89.553]},
    16: {'dp': 0.0675, 'dn': 0.06, 'a': [23.3704, 47.2246, -12.4999], 'b': [16.6306, 41.3957, -13.5868], 'pdp': 0.06, 'pdn': 0.0525, 'pa': [-0.53, 310.85, 141.325], 'pb': [-0.177, 261.927, 193.527]},
    18: {'dp': 0.0575, 'dn': 0.0525, 'a': [22.6767, 44.368, -0.1986], 'b': [17.4199, 42.2243, -9.6172], 'pdp': 0.0475, 'pdn': 0.075, 'pa': [-0.504, 288.378, 284.627], 'pb': [23.571, 281.599, 324.627]},
    20: {'dp': 0.04, 'dn': 0.04, 'a': [17.2834, 48.1439, 7.5952], 'b': [14.9497, 41.9476, -2.787], 'pdp': 0.0825, 'pdn': 0.0625, 'pa': [-0.794, 450.261, 321.447], 'pb': [0.69, 359.391, 399.568]},
}

NOMINAL_VOLT = 16
TAU_MOTOR = 0.1        # s, first-order thrust lag (assumed; replace by the identified T200 model)


def coef_array(volt=NOMINAL_VOLT, linear=False):
    """[dp, dn, a1, a2, a3, b1, b2, b3, pdp, pdn, pa1..3, pb1..3, Fmax, Fmin].

    linear=True gives an idealized thruster with the same limits, no dead band
    and a linear curve (used to separate the effect of the actuator nonlinearity).
    """
    c = COEF[volt]
    fmax = _poly(1.0 - c["dp"], c["a"])
    fmin = -_poly(1.0 - c["dn"], c["b"])
    if linear:
        a, b, dp, dn = [fmax, 0.0, 0.0], [-fmin, 0.0, 0.0], 0.0, 0.0
    else:
        a, b, dp, dn = c["a"], c["b"], c["dp"], c["dn"]
    return np.array([dp, dn, *a, *b, c["pdp"], c["pdn"], *c["pa"], *c["pb"], fmax, fmin], dtype=float)


def _poly(z, k):
    return sum(k[i] * z ** (i + 1) for i in range(len(k)))


def force(u, ca):
    """Static thrust [N] for normalized command u (vectorized, numpy)."""
    u = np.asarray(u, float)
    zp = np.clip(u - ca[0], 0, None)
    zn = np.clip(-u - ca[1], 0, None)
    return (ca[2] * zp + ca[3] * zp ** 2 + ca[4] * zp ** 3) - (ca[5] * zn + ca[6] * zn ** 2 + ca[7] * zn ** 3)


def power(u, ca):
    """Electrical power [W] for normalized command u (vectorized, numpy)."""
    u = np.asarray(u, float)
    zp = np.clip(u - ca[8], 0, None)
    zn = np.clip(-u - ca[9], 0, None)
    pp = ca[10] * zp + ca[11] * zp ** 2 + ca[12] * zp ** 3
    pn = ca[13] * zn + ca[14] * zn ** 2 + ca[15] * zn ** 3
    return np.clip(pp + pn, 0, None)
