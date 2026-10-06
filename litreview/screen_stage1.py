"""Stage 1 of the screening: a documented, rule-based relevance filter.

A record of candidates.csv passes when its title or abstract
  * concerns fractional calculus or multifractional processes (FRAC), and
  * is not an erratum, correction or front matter (ERR), and
  * matches at least one topic:
      - variable or time-varying order (VO) together with a realization,
        approximation, implementation or definition term (IMPL or DEF), or
      - an order-independent-pole / kernel-compression family (FP), or
      - multifractional processes (MBM).
The tags are written to stage1.csv so that stage 2 (manual screening,
screening.csv) can be audited against them.
"""

import csv
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

TAGS = {
    "FRAC": r"fraction|multifractional|brownian|hurst|fractal",
    "VO": (r"variable[- ]order|variable[- ]fractional[- ]order|time[- ]varying (fractional[- ])?order|order[- ]varying"
           r"|varying[- ]order|switched[- ]order|switching (fractional )?order|tunable[- ]order|variable fractional"),
    "IMPL": (r"reali[sz]|implement|circuit|analog|fpga|hardware|digital filter|differentiator|integrator|approximat"
             r"|discreti[sz]|electronic|vlsi|\bdsp\b|microcontroller|emulat"),
    "FP": (r"fixed[- ]pole|diffusive|sum[- ]of[- ]exponential|exponential[- ]sum|kernel compression|infinite[- ]state"
           r"|frequency[- ]distributed|continuous[- ]frequency|\bsoe\b"),
    "MBM": r"multifractional|\bmbm\b|\bmgn\b|local hurst|hurst function|time[- ]varying hurst|variable hurst",
    "DEF": r"definition|duality|dual |switching scheme|switching strateg|recursive|order memory",
    "HW": r"fpga|circuit|analog|hardware|electronic|vlsi|asic",
}
ERR = r"^(erratum|corrigendum|correction|retraction|front matter|editorial)"


def tags_of(row):
    text = (row["title"] + " " + row["abstract"]).lower()
    tg = {k for k, p in TAGS.items() if re.search(p, text)}
    if re.search(ERR, row["title"].lower()):
        tg.add("ERR")
    return tg


def passes(tg):
    return ("FRAC" in tg and "ERR" not in tg
            and (("VO" in tg and ("IMPL" in tg or "DEF" in tg)) or "FP" in tg or "MBM" in tg))


def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, "candidates.csv"))))
    out = []
    for r in rows:
        tg = tags_of(r)
        if passes(tg):
            out.append(dict(r, tags=" ".join(sorted(tg))))
    fields = list(rows[0].keys()) + ["tags"]
    with open(os.path.join(HERE, "stage1.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    print(f"stage 1: {len(out)} of {len(rows)} records pass")


if __name__ == "__main__":
    main()
