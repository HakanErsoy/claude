"""Stage 2 (manual title/abstract screening) and the included set.

The decisions below were made by reading every title of stage1.csv, and the
abstract where Crossref or arXiv provided one; borderline records were checked
in full text (see SENTEZ.md). Each stage-1 record gets a decision, a code and,
for included records, a short note. Records not listed explicitly receive
the default exclusion of their topic group, marked "(default)" so that the
rule is auditable. Snowball and full-text additions come from snowball.csv.

Inclusion criteria (any one):
  I1  realization or implementation of a variable-order (VO) operator or
      system: analog, digital filter, FPGA/ASIC, tunable-order element, or a
      rational / state-space approximation used for realization
  I2  VO definitions, their switching-scheme interpretation, duality,
      initialization, or definition-dependence of properties
  I3  order-independent nodes, sum-of-exponentials, kernel compression,
      diffusive or infinite-state representations (methods, not applications)
  I4  operator-level numerical approximation of VO operators
  I5  multifractional processes: definitions with different order memory,
      synthesis methods, local Hurst estimation used in this work
  BG  background needed by the manuscript (transients in time-varying
      recursive filters, fractional initialization, constant-order hardware)
Exclusion codes:
  PDE    numerical solver for a VO differential equation, no operator-level
         or realization contribution
  SPACE  space-fractional or variable-order fractional Laplacian
  VFD    variable fractional DELAY filters (fractional delay, not order)
  FPAPP  constant-order fast/diffusive scheme used inside an application
  THEORY existence, stability or analysis results not about definitions
  APP    application of a VO or fractional model, no realization contribution
  MBM    multifractional theory, estimation or application without a
         synthesis or definition contribution used here
  OFF    off topic
  DUP    duplicate of another record (preprint / published version)

Outputs: screening.csv (all stage-1 records), included.csv (included set,
search + snowball), prisma.json (flow counts).
"""

import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

INCLUDE = {
    # I1 realization / implementation
    "R0155": ("I1", "VO operator approximation by polynomial fitting (frequency domain); abstract not available"),
    "R0971": ("I1", "VO operator approximation by polynomial fitting (time domain); abstract not available"),
    "R0568": ("I1", "physical experiment with VO integrator/differentiator (electrochemical element)"),
    "R0641": ("I1", "analog and digital structures with tunable order"),
    "R0193": ("I1", "analog realization of a variable fractional-order integrator I^alpha(t)"),
    "R0096": ("I1", "analog D-type realization for a particular switching strategy (Sierociuk et al. 2020)"),
    "R0098": ("I1", "analog VO chaotic system; LTI (third) Lorenzo-Hartley definition, one transfer function"),
    "R0220": ("I1", "variable-order fractal-ladder fractor, order set by multiplying DACs"),
    "R0757": ("I1", "variable fractional order integrator, closed-form design (Tseng)"),
    "R0120": ("I1", "VO chaotic circuit, switching between orders"),
    "R0242": ("I1", "analog variable fractional order differentiator/integrator (Charef)"),
    "R0243": ("I1", "digital FIR variable fractional order integrator/differentiator (Charef)"),
    "R0855": ("I1", "variable fractional order differentiator, modular cascade structure (Tseng, Lee)"),
    "R0245": ("I1", "variable fractional order differentiator, infinite product expansion (Tseng, Lee)"),
    "R0249": ("I1", "digital circuit of a VO Hopfield network"),
    "R0883": ("I1", "discrete-time VO PID with GL VO differences"),
    "R0124": ("I1", "FPGA GL operator with run-time configurable order; VO chaotic oscillator (Tolba et al.)"),
    "R0998": ("I1", "FPGA VO operator with Mittag-Leffler kernel"),
    "R0072": ("I1", "VO PID with two discrete-time VO operators"),
    "R0038": ("I1", "analog realization of multiple order switching, recursive (D-type) derivative"),
    "R1478": ("I1", "realization of a VO model with symmetric property (Macias et al.)"),
    "R1527": ("I1", "variable fractional order integrator/differentiator by series expansion (Tseng)"),
    "R0591": ("I1", "variable fractional-order inductor (coaxial, NaCl-water)"),
    # I2 definitions, switching schemes, duality
    "R0057": ("I2", "alternative recursive VO derivative and analog validation"),
    "R0189": ("I2", "hidden-memory VO (order at the integration variable, B-type-like); numerics"),
    "R0666": ("I2", "additive switching scheme, analytical description and equivalence"),
    "R0017": ("I2", "1st/2nd/3rd type definitions; cascade switching scheme equivalent to 2nd (B) type"),
    "R0894": ("I2", "D/E duality used in UFOKF (Remark 2)"),
    "R0898": ("I2", "duality of VO difference operators (Sierociuk, Twardy)"),
    "R0068": ("I2", "equivalent switching strategy and analog validation"),
    "R0134": ("I2", "initial conditions of recursive constant- and variable-order derivatives"),
    "R0078": ("I2", "new VO derivative definition (recursive)"),
    "R0144": ("I2", "recursive VO derivative: switching strategy, duality, analog model (CSSP)"),
    "R0088": ("I2", "switching scheme and equivalence of the alternative VO definition"),
    "R1455": ("I2", "definition-dependence of Lyapunov estimates for VO derivatives"),
    # I3 order-independent nodes / kernel compression / diffusive
    "R0102": ("I3", "exponential-sum approximation for VO Caputo derivative, exponents independent of time level"),
    "R0022": ("I3", "fast second-order VO Caputo evaluation with exponential sums"),
    "R0395": ("I3", "robust fast VO method (integration by parts + exponential sums)"),
    "R0121": ("I3", "nearly optimal SOE by generalized Gaussian quadrature, small exponents"),
    "R0612": ("I3", "exponential-sum approximation of power-law kernels"),
    "R0634": ("I3", "fixed-pole approximation, constant order (Wei et al. 2016)"),
    "R0684": ("I3", "approximation and identification of diffusive interfaces"),
    "R0871": ("I3", "diffusive representation with adaptive partitioning"),
    "R0872": ("I3", "diffusive representation of N-th order fBm"),
    "R0873": ("I3", "diffusive representation of RL integrals and derivatives"),
    "R0248": ("I3", "diffusive representations for fractional integrals (Diethelm 2023)"),
    "R0964": ("I3", "fast Caputo algorithms for small fractional orders"),
    "R0968": ("I3", "SOE fast evaluation of the Caputo derivative (Jiang et al.)"),
    "R0992": ("I3", "fixed-pole modeling and simulation schemes (Wei et al. 2019)"),
    "R1131": ("I3", "adaptive kernel compression time stepping (Baffet, Hesthaven)"),
    "R1208": ("I3", "limited-band diffusive representation for nabla (discrete) fractional transfer functions"),
    "R1273": ("I3", "multiple fixed-pole rational approximation (Wei et al. 2021)"),
    "R0352": ("I3", "new variants of diffusive representation of fractional integrals"),
    "R1334": ("I3", "reformulated infinite state representation"),
    "R1463": ("I3", "rapidly convergent infinite state representation"),
    "R0394": ("I3", "revisiting diffusive representations"),
    "R1551": ("I3", "time-fractional ODE via rational approximation"),
    "R1629": ("I3", "infinite state representation survey, part 1"),
    "R1630": ("I3", "infinite state representation survey, part 2"),
    "R0429": ("I3", "sine and cosine diffusive representations"),
    "R1644": ("I3", "time-local discretization with Gaussian quadrature"),
    "R0162": ("I3", "Gauss-Jacobi kernel compression (Baffet)"),
    "R0510": ("I3", "kernel compression for distributed-order operators (shared nodes over orders)"),
    "R0511": ("I3", "kernel compression scheme (Baffet, Hesthaven 2017)"),
    "R0527": ("I3", "new diffusive representation, part I (Diethelm et al.)"),
    "R0170": ("I3", "new diffusive representation, part II"),
    "R0483": ("I3", "memoryless SOE method (Guglielmi, Hairer)"),
    "R0339": ("I3", "integral state space representation of fractional systems"),
    # I4 operator-level VO approximation
    "R0559": ("I4", "approximation of the VO fractional integral operator"),
    "R0190": ("I4", "expansion formula with integer-order derivatives for VO operators"),
    "R0002": ("I4", "series approximation of VO Caputo derivative with variable terminals"),
    "R0217": ("I4", "Caputo derivatives of variable order: numerical approximations"),
    "R0138": ("I4", "recurrence relations for VO operators on Laguerre polynomials"),
    "R0106": ("I4", "infinite series representation incl. variable order (Wei et al.)"),
    # I5 multifractional
    "R0180": ("I5", "VO-operator synthesis of multifractional Gaussian noise (Sheng et al. 2010)"),
    "R1610": ("I5", "VO-operator synthesis of mGn (Sheng et al. 2011)"),
    "R0279": ("I5", "RL-mBm (Lim 2001)"),
    "R0331": ("I5", "RL-mBm modeling (Muniandy, Lim 2001)"),
    "R0305": ("I5", "identification of mBm (Coeurjolly 2005)"),
    "R0426": ("I5", "generalized mBm (Ayache, Levy Vehel)"),
    "R1694": ("I5", "wavelet-based synthesis of a multifractional process"),
    "R0013": ("I5", "integrated fractional white noise as an alternative to mBm (Sly 2007)"),
    "R1018": ("I5", "fBm with variable Hurst parameter incl. jumps (Ryvkina)"),
    "R1241": ("I5", "incremental mBm: H changes act on new increments only (Slezak, Metzler)"),
    "R0137": ("I5", "mBm with telegraphic stochastically varying exponent"),
    "R1260": ("I5", "step fractional Brownian motion"),
    "R1262": ("I5", "modified multifractional Gaussian noise"),
    "R0350": ("I5", "nonparametric estimation of the local Hurst function"),
    "R1270": ("I5", "multifractional processes (Sheng, Chen, Qiu book chapter)"),
    "R1553": ("I5", "survey of fractional and multifractional Gaussian processes"),
}

EXCLUDE = {
    "VFD": "R0586 R0188 R0623 R0697 R0214 R0763 R0816 R0848 R0854 R0857 R0123 R1151 R1192 R1224 R1411 R1623 R1648 R1670",
    "SPACE": "R0484 R0156 R0176 R0628 R0114 R0063 R0228 R0266 R0275 R1371 R0370 R1488 R0405 R1635 R0442 R1226 R0874 "
             "R0969 R1296",
    "FPAPP": "R0482 R0485 R0486 R0487 R0488 R0494 R0506 R0513 R0515 R0537 R0565 R0585 R0657 R0665 R0708 R0742 R0852 "
             "R0247 R0980 R1141 R1222 R1254 R1256 R1261 R1321 R1391 R1406 R1407 R1515 R1596 R1664 R1668 R0443 R1691 "
             "R1692 R0178 R0549",
    "THEORY": "R0119 R0803 R0236 R0941 R0031 R0954 R1621 R0042 R0147 R1661 R0439 R0039 R1453 R0942 R0171",
    "APP": "R0158 R0592 R0198 R0200 R0705 R0224 R0229 R0237 R1016 R1067 R1417 R1521 R1552 R0403 R1619 R0044 R0437 "
           "R0438 R1682 R0441 R1686 R0916 R1685 R0148 R0965 R1066 R0014 R0108",
    "OFF": "R0110 R0265 R0281 R0316 R0367 R1376 R0446 R0215 R0797 R0939 R1020 R1169 R1206 R1301 R1327 R1456 R1462 "
           "R0972 R0974",
    "DUP": "R0526 R0967",
}
DUP_OF = {"R0526": "R0527", "R0967": "R0968"}

# full-text / snowball additions that are cited or used; S14 duplicates S30,
# S24 is already in the search set as a citation of the manuscript, S28 and
# S29 were wrong guesses and are dropped
SNOW_DROP = {"S14": "DUP of S30", "S28": "OFF (wrong target)", "S29": "OFF (no match)"}
SNOW_NOTES = {
    "S01": "experimental VO behaviour of ladders and nested ladders",
    "S02": "analytical solutions of VO equations using duality and switching schemes",
    "S03": "selection and meaning of VO operators",
    "S04": "Coimbra VO derivative",
    "S05": "constant- vs variable-order models of memory",
    "S06": "VO systems review",
    "S07": "variable and adaptive fractional order FIR differentiators (Tseng 2006)",
    "S08": "transient suppression in variable recursive digital filters",
    "S09": "elimination of transients in adaptive filters",
    "S10": "initialization of fractional operators",
    "S11": "fractional state-space description and its pitfalls",
    "S12": "state variables and transients of fractional systems",
    "S13": "electronically controlled fractional-order filters (tunable order)",
    "S15": "simulation of mBm",
    "S16": "non-equivalence of mBm definitions (moving-average vs harmonizable)",
    "S17": "switching fBm",
    "S18": "optimal VO PID",
    "S19": "VO GL backward difference properties",
    "S20": "extended algorithms for approximating VO derivatives",
    "S21": "FPGA fractional integrator/differentiator, two approaches (constant order)",
    "S22": "review of fractional-order element emulators",
    "S23": "VO operators in anomalous diffusion",
    "S24": "Lorenzo-Hartley VO definitions (already cited)",
    "S25": "VO discrete PID",
    "S26": "fBm with random Hurst exponent",
    "S27": "SOE fast Caputo evaluation (Jiang et al.)",
    "S30": "VO derivatives and numerical approximations (Valerio, Sa da Costa; already cited)",
    "S31": "parallel switching scheme for the B-type analog realization",
    "S32": "recursive variable-type and order difference",
    "S33": "differences of variable type and order",
    "S34": "output-additive switching strategy",
    "S35": "VO discrete-time systems and solutions",
    "S36": "fast method for hidden-memory (B-type-like) VO derivative, Taylor/hierarchical, O(N log N)",
    "S37": "memory-multi-FBM: exponent at increment time (B-type RL-mBm up to normalization)",
    "S38": "incremental mBm (journal version)",
    "S39": "unified fast memory-saving time stepping for constant and variable order (SOE)",
    "S40": "Charef fractional power pole approximation",
    "S41": "covariance structure of mBm",
    "S42": "analog modeling of switched-order derivatives, experimental",
}


def main():
    stage1 = list(csv.DictReader(open(os.path.join(HERE, "stage1.csv"))))
    n_all = sum(1 for _ in csv.DictReader(open(os.path.join(HERE, "candidates.csv"))))
    exc = {i: code for code, ids in EXCLUDE.items() for i in ids.split()}
    rows = []
    for r in stage1:
        i, tags = r["id"], set(r["tags"].split())
        if i in INCLUDE:
            crit, note = INCLUDE[i]
            dec, code = "include", crit
        elif i in exc:
            dec, code, note = "exclude", exc[i], f"duplicate of {DUP_OF[i]}" if i in DUP_OF else ""
        elif "MBM" in tags:
            dec, code, note = "exclude", "MBM", "(default)"
        elif "FP" in tags and "VO" not in tags:
            dec, code, note = "exclude", "FPAPP", "(default)"
        else:
            dec, code, note = "exclude", "PDE", "(default)"
        rows.append({"id": i, "decision": dec, "code": code, "note": note, "year": r["year"], "title": r["title"],
                     "authors": r["authors"], "venue": r["venue"], "doi": r["doi"], "arxiv": r["arxiv"], "tags": r["tags"]})
    overlap = set(INCLUDE) & set(exc)
    assert not overlap, overlap
    missing = set(INCLUDE) - {r["id"] for r in stage1}
    assert not missing, missing
    with open(os.path.join(HERE, "screening.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    inc = [dict(r, source="search") for r in rows if r["decision"] == "include"]
    snow = list(csv.DictReader(open(os.path.join(HERE, "snowball.csv"))))
    seen = {r["doi"] for r in inc if r["doi"]}
    snow_inc, snow_dup = [], 0
    for s in snow:
        if s["id"] in SNOW_DROP:
            continue
        if s["doi"] in seen:
            snow_dup += 1
            continue
        snow_inc.append({"id": s["id"], "decision": "include", "code": s["criterion"], "note": SNOW_NOTES.get(s["id"], ""),
                         "year": s["year"], "title": s["title"], "authors": s["authors"], "venue": s["venue"],
                         "doi": s["doi"], "arxiv": "", "tags": "", "source": "snowball"})
        seen.add(s["doi"])
    allinc = inc + snow_inc
    with open(os.path.join(HERE, "included.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(allinc[0].keys()))
        w.writeheader()
        w.writerows(sorted(allinc, key=lambda r: (r["code"], str(r["year"]))))
    by = {}
    for r in rows:
        by.setdefault(f"{r['decision']}:{r['code']}", 0)
        by[f"{r['decision']}:{r['code']}"] += 1
    prisma = {"records_identified": None, "unique_after_dedup": n_all, "stage1_pass": len(stage1),
              "stage1_excluded": n_all - len(stage1), "stage2": by,
              "included_from_search": len(inc), "snowball_targets": len(snow), "snowball_dropped": len(SNOW_DROP),
              "snowball_already_in_search": snow_dup, "included_from_snowball": len(snow_inc),
              "included_total": len(allinc),
              "included_by_criterion": {c: sum(1 for r in allinc if r["code"] == c) for c in sorted({r["code"] for r in allinc})}}
    log = list(csv.DictReader(open(os.path.join(HERE, "search_log.csv"))))
    prisma["records_identified"] = sum(int(r["records"]) for r in log)
    json.dump(prisma, open(os.path.join(HERE, "prisma.json"), "w"), indent=1)
    print(json.dumps(prisma, indent=1))


if __name__ == "__main__":
    main()
