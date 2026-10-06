"""Data extraction for the core comparison (RQ1-RQ3, RQ6).

One row per work that realizes, approximates or defines a VO operator in a
way that bears on the manuscript's claims. Fields are filled only from text
that was read (full text, abstract, or a statement in another paper's full
text); the 'evidence' column says which. 'inferred' marks entries derived by
applying the manuscript's Proposition 2 / Theorem 5 to the described structure.

Output: litreview/extraction.csv
"""

import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))

FIELDS = ["key", "work", "domain", "structure", "definition", "poles", "order_variation", "types", "cost",
          "design_rule", "evidence"]

ROWS = [
    ("sierociuk2015amm", "Sierociuk, Malesza, Macias, Appl. Math. Model. 2015", "analog + numerical",
     "serial cascade: a complementary-order block (order alpha_j - alpha_{j-1}) is pre-connected at each switch",
     "2nd type (= B), proved equivalent (Thm. 1); 1st and 3rd types also defined", "each block constant order",
     "any number of switches; one extra block per switch", "B", "grows with the number of switches",
     "none", "full text (arXiv:1304.5072)"),
    ("sierociuk2015cssp", "Sierociuk, Malesza, Macias, CSSP 2015", "analog + numerical",
     "switching strategy for the recursive (D-type) derivative, based on duality", "D, duality with A",
     "constant-order blocks", "switching", "D", "n/a", "none", "title + statements in Electronics 2020 (full text)"),
    ("sierociuk2018amc", "Sierociuk, Macias, Malesza, Appl. Math. Comput. 2018", "analog",
     "parallel switching scheme (the serial scheme could not be realized in practice)",
     "iterative variable-type and order operator (B-type family)", "constant-order blocks",
     "switching between types/orders", "B (variable type)", "n/a", "none", "abstract"),
    ("sierociuk2020", "Sierociuk, Macias, Malesza, Wiraszka, Electronics 2020", "analog",
     "conceptual scheme from equivalent forms of B- and D-type; analog model for one switch (order 1 -> 0.5)",
     "switching between B- and D-type", "domino ladders, constant order",
     "particular switching strategy", "B/D", "n/a", "none",
     "full text: 'a realization of D-type difference is practically impossible because of the duality'"),
    ("aricioglu2025", "Arıcıoğlu, Axioms 2025", "analog",
     "one transfer-function approximation (op-amps, RC) for a smoothly varying order",
     "third Lorenzo-Hartley definition (the only LTI one)", "fixed (LTI)",
     "smooth alpha(t), Laplace-transformable", "3rd (LTI) type", "n/a",
     "slope between -20 and 0 dB/dec", "full text; also states prior work switches between 2-3 orders"),
    ("zhou2019", "Zhou, Li, Xie, Eur. Phys. J. Plus 2019", "analog", "switches between constant orders",
     "not stated", "constant-order approximations per order", "two or three orders", "n/a", "n/a", "none",
     "statement in Arıcıoğlu 2025 (full text)"),
    ("macias2019", "Macias, Sierociuk, Malesza, LNEE 2019", "analog", "switching of constant-order ladders",
     "VO model with symmetric property", "constant-order blocks", "two or three orders", "n/a", "n/a", "none",
     "title + statement in Arıcıoğlu 2025"),
    ("tolba2020", "Tolba et al., Nonlinear Dyn. 2020", "FPGA",
     "direct GL convolution with run-time configurable order; PWL/PWQ weight approximations",
     "not stated; if weights are recomputed for the current order: A-type (inferred)",
     "none (FIR / finite memory)", "orders varying in time (VO chaotic oscillator)", "A (inferred)",
     "O(L) per sample, L = memory length", "none", "abstract (web); full text not accessible"),
    ("tsirimokou2016", "Tsirimokou, Psychalinos, Elwakil, Int. J. Circ. Theor. Appl. 2016", "analog (OTA)",
     "fractional-order filters with electronically adjustable order", "constant order, adjustable",
     "order-dependent approximation (moving poles)", "re-tuning", "n/a", "n/a", "none", "abstract"),
    ("charef2012", "Charef, Idiou, Nonlinear Dyn. 2012", "analog",
     "variable fractional order differentiator/integrator in a band, re-tunable without redesign",
     "constant order, adjustable", "not verified", "re-tuning", "n/a", "n/a", "band design",
     "web abstract snippet; full text not accessible"),
    ("charef2024", "Charef, Ladaci, IFAC-PapersOnLine 2024", "analog", "variable fractional-order integrator I^alpha(t)",
     "not verifiable", "not verifiable", "not verifiable", "n/a", "n/a", "n/a",
     "title only; open access but not reachable from this environment"),
    ("sierociuk2013tcst", "Sierociuk, Podlubny, Petras, IEEE TCST 2013", "analog (passive)",
     "fixed domino and nested ladders (no switching)", "time-domain behaviour of variable order (0.5 -> ~1)",
     "fixed passive network", "intrinsic", "n/a", "n/a", "n/a", "full text (arXiv:1107.2575)"),
    ("yu2022", "Yu, Pu, He, Yuan, Fractal Fract. 2022", "analog",
     "scaling fractal-ladder fractor with programmable R/C (multiplying DACs, microcontroller)",
     "compared with a B-type GL reference (weights at mu(t-jh), scale 1/F at mu(t))",
     "element values depend on order (moving poles)", "jumps -0.33 <-> -0.66 at 50 Hz; continuous -0.3 -> -0.7",
     "B (approximate; Thm. 5)", "fixed circuit", "none", "full text (MDPI)"),
    ("tseng2006/2008, charef2011", "Tseng 2006, 2008; Charef, Bensouici 2011", "digital (FIR/IIR)",
     "variable fractional order differentiators/integrators: one filter whose order is a parameter",
     "constant order, adjustable; an FIR updated with current-order coefficients is A-type with finite memory (inferred)",
     "FIR: all poles at z = 0 (fixed)", "parameter change", "A (inferred, FIR)", "O(L)", "design specific",
     "titles + inferred"),
    ("zhang2021esa", "Zhang, Fang, Sun, J. Appl. Math. Comput. 2021 (and NMTMA 2022, AMC 2022)", "numerical (PDE solver)",
     "exponential-sum approximation of the VO Caputo kernel; exponents and their number independent of the time level, weights depend on t",
     "VO Caputo with alpha(t) at the current time (A-type, continuous time)", "fixed exponents",
     "any alpha(t) in (0,1)", "A (Caputo)", "O(log^2 n) memory", "error bound for the ESA", "full text (arXiv:2101.08125)"),
    ("huang2022", "Huang et al., NMTMA 2022", "numerical", "improved SOE; SOE for VO kernels; unified fast time stepping",
     "constant and variable order (definition and node dependence not verifiable)", "SOE nodes", "VO", "n/a", "n/a",
     "error analysis", "abstract only; full text not accessible"),
    ("jia2022", "Jia, Wang, Zheng, J. Sci. Comput. 2022", "numerical (PDE solver)",
     "fast approximation of the hidden-memory VO derivative via Taylor expansions / hierarchical matrices",
     "hidden memory: order at the integration variable s (B-type-like)", "none (not an SOE recursion)",
     "alpha(t)", "B-like (Caputo)", "O(N log N) total for coefficients", "error estimates", "full text (first pages)"),
    ("wei2016/2019/2021", "Wei et al., ISA Trans. 2016, 2019; J. Dyn. Syst. Meas. Control 2021", "numerical / rational",
     "fixed-pole rational approximation; poles constant for different alpha", "constant order", "fixed",
     "not addressed", "n/a", "O(K)", "design by fitting", "abstracts / web"),
    ("valerio2011", "Valério, Sá da Costa, Signal Process. 2011", "numerical",
     "VO definitions and numerical approximations; discretized Crone approximations combined with fuzzy logic / interpolation",
     "several GL/RL types", "order-dependent (Crone)", "VO", "several", "n/a", "none", "web snippet"),
    ("oziablo2020", "Oziablo, Mozyrska, Wyrwas, Entropy 2020 (and Mozyrska et al. 2019)", "discrete-time control",
     "VO PID from the FVOGLD: coefficients a_i^{nu_k} at the current order", "A-type (stated by the authors)",
     "none (GL sums)", "order changes every step", "A", "O(k) at step k; buffer bound is an open problem", "tuning",
     "full text (MDPI)"),
    ("philippe2006/2008", "Philippe, Surgailis, Viano, CRAS 2006; TVP 2008", "time series",
     "time-varying fractional filters A(d), B(d); coefficients are products of d_u over intermediate times",
     "own family (not GL A/B); constant d gives (I-L)^-d", "n/a", "any d_t", "A(d), B(d)", "O(n)", "n/a",
     "full text (CRAS 2006)"),
    ("ryvkina2015", "Ryvkina, J. Theor. Probab. 2015", "stochastic process",
     "fBm with variable Hurst parameter via covariance; kernel uses H(t)", "A-like: paths discontinuous at jumps of H",
     "n/a", "H(t) in (1/2,1)", "A-like", "n/a", "n/a", "full text (arXiv:1306.2870)"),
    ("lim2001", "Lim, J. Phys. A 2001", "stochastic process", "RL-mBm: order H(t)+1/2 applied to the whole past",
     "A-type", "n/a", "H(t)", "A", "n/a", "n/a", "known definition"),
    ("wang2023mmfbm", "Wang et al., Phys. Rev. Research 2023", "stochastic process",
     "memory-multi-FBM: X(t) = int sqrt(alpha(s)) (t-s)^((alpha(s)-1)/2) dB(s)",
     "B-type RL integral of white noise (up to a per-increment normalization)", "n/a", "alpha(t)", "B", "n/a", "n/a",
     "full text (arXiv:2303.01551)"),
    ("slezak2023", "Ślęzak, Metzler, J. Phys. A 2023", "stochastic process",
     "incremental mBm defined through the covariance of increments", "H changes act on new increments only",
     "n/a", "H(t)", "B-like (not identical)", "n/a", "n/a", "full text (arXiv:2307.13980)"),
    ("this work", "fixed-pole bank (this manuscript)", "DT digital, fixed-point RTL",
     "Beta-integral fixed-pole bank; order in output weights (A), input weights (B); exact inversion (D, E)",
     "A, B, D, E exactly up to frozen-order quadrature", "fixed (order-independent)", "every sample, any sequence",
     "A, B, D, E", "O(K), K = 20-50", "analytic, fit-free; sealed holdout", "this work"),
]


def main():
    with open(os.path.join(HERE, "extraction.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(FIELDS)
        w.writerows(ROWS)
    print(f"{len(ROWS)} rows")


if __name__ == "__main__":
    main()
