"""Snowballing step: targeted look-ups of works found through the reference
lists and citations of the seed papers (or known to the authors), checked
against Crossref. Each target is a free-text query plus the expected title;
the best Crossref match is accepted only if its normalized title matches the
expected one closely (difflib ratio >= 0.85). Raw responses go to
litreview/raw/snow_<id>.json, results to litreview/snowball.csv.

Usage: python3 litreview/snowball.py [--refresh]
"""

import csv
import difflib
import json
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from search import RAW, HERE, cached, strip_tags  # noqa: E402

# (id, criterion, expected title, extra query words)
TARGETS = [
    ("S01", "I1", "Experimental evidence of variable-order behavior of ladders and nested ladders", "Sierociuk Podlubny Petras"),
    ("S02", "I2", "Analytical solution of fractional variable order differential equations", "Malesza Macias Sierociuk"),
    ("S03", "I2", "On the selection and meaning of variable order operators for dynamic modeling", "Ramirez Coimbra"),
    ("S04", "I2", "Mechanics with variable-order differential operators", "Coimbra"),
    ("S05", "I2", "A comparative study of constant-order and variable-order fractional models in characterizing memory property of systems", "Sun Chen Wei"),
    ("S06", "I2", "Variable order fractional systems", "Ortigueira Valerio Machado Communications in Nonlinear Science"),
    ("S07", "I1", "Design of variable and adaptive fractional order FIR differentiators", "Tseng Signal Processing"),
    ("S08", "BG", "Suppression of transients in variable recursive digital filters with a novel and efficient cancellation method", "Valimaki Laakso"),
    ("S09", "BG", "Elimination of transients in adaptive filters with application to speech coding", "Zetterberg Zhang"),
    ("S10", "BG", "Initialization of fractional-order operators and fractional differential equations", "Lorenzo Hartley"),
    ("S11", "BG", "Fractional systems state space description: some wrong ideas and proposed solutions", "Sabatier Farges Trigeassou"),
    ("S12", "BG", "State variables and transients of fractional order differential systems", "Trigeassou Maamri Oustaloup"),
    ("S13", "I1", "Fractional-order electronically controlled generalized filters", "Tsirimokou Psychalinos Elwakil"),
    ("S14", "I2", "Variable-order fractional derivatives and their numerical approximations I - real orders", "Valerio Vinagre Domingues Sa da Costa"),
    ("S15", "I5", "Simulation of multifractional Brownian motion", "Chan Wood COMPSTAT"),
    ("S16", "I5", "How rich is the class of multifractional Brownian motions?", "Stoev Taqqu"),
    ("S17", "I5", "Modelling intermittent anomalous diffusion with switching fractional Brownian motion", "Balcerek Wylomanska"),
    ("S18", "I1", "Optimal variable-order fractional PID controllers for dynamical systems", "Dabiri Moghaddam Machado"),
    ("S19", "I2", "Variable-, fractional-order Grunwald-Letnikov backward difference selected properties", "Mozyrska Ostalczyk"),
    ("S20", "I4", "Extended algorithms for approximating variable order fractional derivatives with applications", "Moghaddam Machado"),
    ("S21", "I1", "FPGA implementation of the fractional order integrator/differentiator: two approaches and applications", "Tolba AbdelAty Said Radwan"),
    ("S22", "I1", "History and progress of fractional-order element passive emulators: a review", "Kartci Herencsar Machado Brancik"),
    ("S23", "I2", "Variable-order fractional differential operators in anomalous diffusion modeling", "Sun Chen Chen Physica A"),
    ("S24", "I2", "Variable order and distributed order fractional operators", "Lorenzo Hartley Nonlinear Dynamics"),
    ("S25", "I1", "Variable-, fractional-order discrete PID controllers", "Ostalczyk MMAR"),
    ("S26", "I5", "Fractional Brownian motion with random Hurst exponent: accelerating diffusion and persistence transitions", "Balcerek Burnecki Thapa Wylomanska Chechkin"),
    ("S27", "I3", "Fast evaluation of the Caputo fractional derivative and its applications to fractional diffusion equations", "Jiang Zhang Zhang Zhang"),
    ("S28", "I3", "Approximating the Caputo fractional derivative through the Mittag-Leffler reproducing kernel Hilbert space and the kernelized Adams-Bashforth-Moulton method", ""),
    ("S29", "I1", "A fractional-order element (FOE) based on the variable-order concept", ""),
    ("S30", "I2", "Variable order fractional derivatives and their numerical approximations", "Valerio Sa da Costa Signal Processing"),
    # second round: reference lists of Sierociuk et al. (Electronics 2020), Arıcıoğlu (2025),
    # Jia et al. (JSC 2022) and Ślęzak and Metzler (2023), read in full text
    ("S31", "I1", "Analog realization of fractional variable-type and -order iterative operator", "Sierociuk Macias Malesza"),
    ("S32", "I2", "Recursive variable type and order difference, its definition and basic properties", "Malesza Sierociuk"),
    ("S33", "I2", "On the differences of variable type and variable fractional order", "Sierociuk Malesza European Control Conference"),
    ("S34", "I2", "On the output-additive switching strategy for a new variable type and order difference", "Sierociuk Malesza Macias"),
    ("S35", "I2", "Fractional variable order discrete-time systems, their solutions and properties", "Sierociuk Malesza"),
    ("S36", "I3", "Numerical analysis of a fast finite element method for a hidden-memory variable-order time-fractional diffusion equation", "Jia Wang Zheng"),
    ("S37", "I5", "Memory-multi-fractional Brownian motion with continuous correlations", "Wang Balcerek Metzler"),
    ("S38", "I5", "Minimal model of diffusion with time changing Hurst exponent", "Slezak Metzler"),
    ("S39", "I3", "A unified fast memory-saving time-stepping method for fractional operators and its applications", ""),
    ("S40", "I1", "Fractal system as represented by singularity function", "Charef Sun Tsao Onaral"),
    ("S41", "I5", "The covariance structure of multifractional Brownian motion, with application to long range dependence", "Ayache Cohen Levy Vehel"),
    ("S42", "I1", "Analog modeling of fractional switched-order derivatives: experimental approach", "Sierociuk Podlubny Petras"),
    # third round: found during the full-text checks (FULLTEXT.md)
    ("S43", "I2", "Time-varying fractionally integrated processes with nonstationary long memory", "Philippe Surgailis Viano"),
    ("S44", "I2", "Invariance principle for a class of non stationary processes with long memory", "Philippe Surgailis Viano"),
]


def norm(t):
    return re.sub(r"[^a-z0-9]", "", t.lower())


def main():
    refresh = "--refresh" in sys.argv
    out = []
    for sid, crit, title, extra in TARGETS:
        params = {"query.bibliographic": f"{title} {extra}".strip(), "rows": 5,
                  "select": "DOI,title,author,issued,container-title,type,volume,issue,page,is-referenced-by-count"}
        url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
        rec = cached(f"snow_{sid}.json", url, refresh)
        items = json.loads(rec["body"])["message"]["items"]
        best, score = None, 0.0
        for it in items:
            t = strip_tags(" ".join(it.get("title") or []))
            s = difflib.SequenceMatcher(None, norm(t), norm(title)).ratio()
            if s > score:
                best, score = it, s
        row = {"id": sid, "criterion": crit, "expected_title": title, "match": score >= 0.85, "score": round(score, 3)}
        if best is not None:
            row.update(title=strip_tags(" ".join(best.get("title") or [])),
                       authors="; ".join(f"{a.get('family', '')}, {a.get('given', '')}".strip(", ")
                                         for a in best.get("author", [])[:8]),
                       year=(best.get("issued", {}).get("date-parts") or [[None]])[0][0],
                       venue=" ".join(best.get("container-title") or []), volume=best.get("volume", ""),
                       issue=best.get("issue", ""), pages=best.get("page", ""), doi=best.get("DOI", "").lower(),
                       cited_by=best.get("is-referenced-by-count", 0), type=best.get("type"))
        out.append(row)
        print(f"{sid} {'OK ' if row['match'] else 'MISS'} {score:.2f} {row.get('year')} {row.get('title', '')[:90]} | {row.get('venue', '')[:40]}",
              flush=True)
    fields = ["id", "criterion", "expected_title", "match", "score", "title", "authors", "year", "venue", "volume",
              "issue", "pages", "doi", "cited_by", "type"]
    with open(os.path.join(HERE, "snowball.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in out:
            w.writerow({k: r.get(k, "") for k in fields})


if __name__ == "__main__":
    main()
