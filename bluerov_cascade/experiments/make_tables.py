"""LaTeX tables for the manuscript, built only from results/*.json (paper/tables/*.tex).

    python3 -I experiments/make_tables.py
"""

import json
import os

import numpy as np
from scipy.stats import mannwhitneyu

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
OUT = os.path.join(HERE, "..", "paper", "tables")
PROPOSED = "FOPID-(1+TFOID)"


def load(name):
    return json.load(open(os.path.join(RES, name)))


def write(name, lines):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w") as f:
        f.write("\n".join(lines) + "\n")


def fmt_p(p):
    return "--" if not np.isfinite(p) else (f"{p:.3f}" if p >= 0.001 else r"$<0.001$")


def x1_table():
    runs = load("x1_optimizers.json")
    g = {}
    for k, r in runs.items():
        m, box, _ = k.split("|")
        g.setdefault((m, box), []).append(r["f"])
    order = ["PSO", "DE", "GWO", "SOO", "SOO-iter", "GJO", "BC-SOO", "RS"]
    ref = g[("PSO", "plain")]
    rows = []
    for m in order:
        p = np.array(g[(m, "plain")])
        mir = g.get((m, "mirror"))
        q = lambda v: f"{np.median(v):.1f} [{np.percentile(v, 25):.1f}, {np.percentile(v, 75):.1f}]"
        p_ref = mannwhitneyu(p, ref).pvalue if m != "PSO" else np.nan
        p_mir = mannwhitneyu(p, mir).pvalue if mir else np.nan
        name = "SOO, 6030 eval." if m == "SOO-iter" else m
        rows.append(f"{name} & {p.min():.1f} & {q(p)} & {q(mir) if mir else '--'} & {fmt_p(p_ref)} & {fmt_p(p_mir)} \\\\")
    write("x1.tex", [
        r"\begin{tabular}{lrllrr}", r"\toprule",
        r"tuner & best & median [IQR], original box & median [IQR], mirrored box & $p$ vs PSO & $p$ boxes \\",
        r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])


X3 = "x3r_evaluate.json" if os.path.exists(os.path.join(RES, "x3r_evaluate.json")) else "x3_evaluate.json"
X4 = "x4r_margins.json" if os.path.exists(os.path.join(RES, "x4r_margins.json")) else "x4_margins.json"


def best_per_structure():
    x3 = load(X3)
    best = {}
    for e in x3.values():
        s = e["structure"]
        if s not in best or e["train_J"] < best[s]["train_J"]:
            best[s] = e
    return best


def x2_table():
    """Nominal tuning at two budgets and robust tuning (PSO): training cost and Monte Carlo divergences."""
    x6 = load("x6_tradeoff.json")
    rob = load("x2r_robust.json")
    nom = {b: {} for b in ("3030", "10030")}
    for e in x6.values():
        if e["budget"] in nom and e["method"] == "PSO":
            nom[e["budget"]].setdefault(e["structure"], []).append(e)
    rr = {}
    for e in x6.values():
        if e["budget"] == "robust":
            rr.setdefault(e["structure"], []).append(e)
    tr = {}
    for r in rob.values():
        tr.setdefault(r["structure"], []).append(r["f"])
    rows = []
    for s in sorted(tr, key=lambda s: np.median(tr[s])):
        cells = []
        for b in ("3030", "10030"):
            v = nom[b][s]
            cells.append(f"{np.median([e['train_J'] for e in v]):.1f} & {sum(e['mc_fail'] == 0 for e in v)}/{len(v)}")
        v = np.array(tr[s])
        cells.append(f"{v.min():.1f} & {np.median(v):.1f} & {sum(e['mc_fail'] == 0 for e in rr[s])}/{len(rr[s])}")
        p = "--" if s == PROPOSED else fmt_p(mannwhitneyu(tr[PROPOSED], v).pvalue)
        rows.append(f"{s} & " + " & ".join(cells) + f" & {p} \\\\")
    write("x2.tex", [
        r"\begin{tabular}{lrrrrrrrr}", r"\toprule",
        r" & \multicolumn{2}{c}{nominal, 3030} & \multicolumn{2}{c}{nominal, 10\,030} &"
        r" \multicolumn{4}{c}{robust, 10\,030} \\ \cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(lr){6-9}",
        r"structure & median $J$ & no div. & median $J$ & no div. & best $J$ & median $J$ & no div. & $p$ \\",
        r"\midrule", *rows, r"\bottomrule", r"\end{tabular}"])


def x3_table():
    best = best_per_structure()
    tests = list(next(iter(best.values()))["tests"])
    order = sorted(best, key=lambda s: best[s]["tests"][tests[-1]]["wITAE"])
    rows = []
    for s in order:
        e = best[s]
        t = e["tests"]
        mc = np.array(e["monte_carlo"]["wITAE"])
        cells = [f"{t[n]['wITAE']:.1f}" for n in tests]
        rows.append(f"{s} ({e['tuner']}) & " + " & ".join(cells)
                    + f" & {t[tests[-1]]['energy'] / 1e3:.1f} & {np.median(mc):.0f} & {np.percentile(mc, 90):.0f}"
                    + f" & {e['monte_carlo']['failures']} \\\\")
    write("x3.tex", [
        r"\begin{tabular}{lrrrrrrrr}", r"\toprule",
        r" & \multicolumn{4}{c}{weighted ITAE} & $E$ T4 & \multicolumn{3}{c}{Monte Carlo, T4 (100)} \\"
        r" \cmidrule(lr){2-5}\cmidrule(lr){7-9}",
        r"structure (tuner) & T1 & T2 & T3 & T4 & [kJ] & median & p90 & diverged \\", r"\midrule",
        *rows, r"\bottomrule", r"\end{tabular}"])


def x45_numbers():
    """Key numbers of X4/X5 as LaTeX macros."""
    x4 = load(X4)
    x5 = load("x5_unconstrained.json")
    best = best_per_structure()
    key = f"{PROPOSED}|{best[PROPOSED]['tuner']}"
    pts = list(x4[key])
    nom = x4[key][pts[0]]
    pm = [nom[d]["oustaloup"]["pm_deg"] for d in nom]
    dm = [1e3 * nom[d]["oustaloup"]["delay_margin"] for d in nom]
    slow = min(x4[key][pts[1]][d]["oustaloup"]["pm_deg"] for d in nom)
    unc = [v for k, v in x5.items() if k.startswith("unconstrained")]
    pm_unc = [min(v["pm_delay0"]) for v in unc]
    J0 = [v["sweep"][0]["J"] for v in unc]
    J3 = [next(s["J"] for s in v["sweep"] if s["delay"] == 3) for v in unc]
    J6 = [next(s["J"] for s in v["sweep"] if s["delay"] == 6) for v in unc]
    con = x5["constrained|best"]["sweep"]
    lines = [
        f"\\newcommand{{\\pmNomMin}}{{{min(pm):.1f}}}", f"\\newcommand{{\\pmNomMax}}{{{max(pm):.1f}}}",
        f"\\newcommand{{\\dmNomMin}}{{{min(dm):.0f}}}", f"\\newcommand{{\\dmNomMax}}{{{max(dm):.0f}}}",
        f"\\newcommand{{\\pmSlowMin}}{{{slow:.1f}}}",
        f"\\newcommand{{\\pmUncMin}}{{{min(pm_unc):.1f}}}", f"\\newcommand{{\\pmUncMax}}{{{max(pm_unc):.1f}}}",
        f"\\newcommand{{\\JuncZeroMin}}{{{min(J0):.0f}}}", f"\\newcommand{{\\JuncZeroMax}}{{{max(J0):.0f}}}",
        f"\\newcommand{{\\JuncThreeMin}}{{{min(J3):.0f}}}", f"\\newcommand{{\\JuncThreeMax}}{{{max(J3):.0f}}}",
        f"\\newcommand{{\\JuncSixMin}}{{{min(J6):.0f}}}", f"\\newcommand{{\\JuncSixMax}}{{{max(J6):.0f}}}",
        f"\\newcommand{{\\JconZero}}{{{con[0]['J']:.1f}}}", f"\\newcommand{{\\JconSix}}{{{con[-1]['J']:.1f}}}",
    ]
    write("numbers.tex", lines)


if __name__ == "__main__":
    x1_table()
    x2_table()
    x3_table()
    x45_numbers()
    print("tables written to", OUT)
