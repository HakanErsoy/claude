"""Full-text access step for the works whose classification rests on an
abstract, a web snippet or another paper's statement.

For each target: Unpaywall (open-access locations) and an arXiv title search.
Raw responses are cached in litreview/raw/ (ft_*.json). PDFs are downloaded to
a scratch directory outside the repository (FT_DIR, default: $TMPDIR or
/tmp) and are not committed; only the access log and the reading notes
(FULLTEXT.md) are. The access log is written to litreview/fulltext_log.csv.

Usage: python3 litreview/fulltext.py [--refresh] [--download]
"""

import csv
import difflib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from search import HERE, cached  # noqa: E402

FT_DIR = os.environ.get("FT_DIR", os.path.join(os.environ.get("TMPDIR", "/tmp"), "vofrac_fulltext"))
EMAIL = "vofrac-litreview@example.org"   # Unpaywall requires a contact address; not a personal one

# key, DOI, title (for the arXiv search), what has to be checked
TARGETS = [
    ("huang2022unified", "10.4208/nmtma.oa-2022-0023",
     "A unified fast memory-saving time-stepping method for fractional operators and its applications",
     "are the SOE nodes for variable order independent of the order; which VO definition"),
    ("valerio2011", "10.1016/j.sigpro.2010.04.006", "Variable-order fractional derivatives and their numerical approximations",
     "which definitions; how the Crone/fuzzy approximations treat a varying order"),
    ("tseng2006", "10.1016/j.sigpro.2006.02.004", "Design of variable and adaptive fractional order FIR differentiators",
     "structure (Farrow? order as a polynomial variable?)"),
    ("tseng2008", "10.1016/j.sigpro.2008.03.012",
     "Series expansion design of variable fractional order integrator and differentiator using logarithm", "structure"),
    ("charef2012sivp", "10.1007/s11760-010-0197-1", "Design of digital FIR variable fractional order integrator and differentiator",
     "structure"),
    ("charef2012", "10.1007/s11071-012-0370-x", "Design of analog variable fractional order differentiator and integrator",
     "how the order is varied (element values / switches)"),
    ("charef2024", "10.1016/j.ifacol.2024.08.158",
     "Analog realization and numerical evaluation of the variable fractional-order integrator", "definition and structure"),
    ("huang2018a", "10.23919/chicc.2018.8483651",
     "A fast frequency domain approximation method for variable order fractional calculus operator based on polynomial fitting",
     "structure: order-dependent poles?"),
    ("huang2018b", "10.23919/chicc.2018.8482866",
     "Fast numerical implementation for variable order fractional calculus operator based on polynomial fitting method in time domain",
     "structure and definition"),
    ("tolba2020", "10.1007/s11071-019-05449-w",
     "Enhanced FPGA realization of the fractional-order derivative and application to a variable-order chaotic system",
     "which VO definition; memory length; how the order changes"),
    ("tsirimokou2017", "10.1002/cta.2250", "Fractional-order electronically controlled generalized filters",
     "order adjustment mechanism; behaviour while the order changes"),
    ("yu2022", "10.3390/fractalfract6070388",
     "Circuit implementation of variable-order scaling fractal-ladder fractor with high resolution",
     "order adjustment; time-varying operation"),
    ("oziablo2020", "10.3390/e22070771", "Discrete-time fractional, variable-order PID controller for a plant with delay",
     "which GL VO differences"),
    ("mozyrska2019", "10.1109/iccma46720.2019.8988684",
     "Fractional-, variable-order PID controller implementation based on two discrete-time fractional order operators",
     "which operators"),
    ("sheng2011", "10.1016/j.sigpro.2011.01.010",
     "Synthesis of multifractional Gaussian noises based on variable-order fractional operators", "which VO definition"),
    ("sheng2010", "10.1109/mesa.2010.5552002",
     "A variable-order fractional operator based synthesis method for multifractional Gaussian noise", "which VO definition"),
    ("wei2016", "10.1016/j.isatra.2016.01.010", "An innovative fixed-pole numerical approximation for fractional order systems",
     "poles independent of the order; any variable-order use"),
    ("wei2019", "10.1016/j.isatra.2018.10.001", "Fixed pole based modeling and simulation schemes for fractional order systems",
     "poles independent of the order; any variable-order use"),
    ("wei2021", "10.1115/1.4049557", "Multiple fixed pole-based rational approximation for fractional order systems",
     "any variable-order use"),
    ("sierociuk2015cssp", "10.1007/s00034-014-9895-1",
     "On the recursive fractional variable-order derivative: equivalent switching strategy, duality, and analog modeling",
     "D-type switching structure"),
    ("sierociuk2013tcst", "10.1109/tcst.2012.2185932",
     "Experimental evidence of variable-order behavior of ladders and nested ladders",
     "is it a switching realization (cited as such)?"),
    ("zhou2019", "10.1140/epjp/i2019-12434-4",
     "Coexisting attractors, crisis route to chaos in a novel 4D fractional-order system and variable-order circuit implementation",
     "switching between orders"),
    ("surgailis2008", "10.1016/j.spa.2007.04.003", "Nonhomogeneous fractional integration and multifractional processes",
     "is the order applied at the increment time (B-type)?"),
    ("sly2007", "10.1017/s0021900200003041", "Integrated fractional white noise as an alternative to multifractional Brownian motion",
     "definition; does a change of H act only on new increments?"),
    ("ryvkina2015", "10.1007/s10959-013-0502-3", "Fractional Brownian motion with variable Hurst parameter: definition and properties",
     "definition; does a change of H act only on new increments?"),
    ("lim2001", "10.1088/0305-4470/34/7/306",
     "Fractional Brownian motion and multifractional Brownian motion of Riemann-Liouville type", "A-type definition"),
]


def norm(t):
    return re.sub(r"[^a-z0-9]", "", t.lower())


def unpaywall(key, doi, refresh):
    url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={EMAIL}"
    try:
        rec = cached(f"ft_unpaywall_{key}.json", url, refresh)
        return json.loads(rec["body"])
    except Exception as e:                          # 404 for DOIs Unpaywall does not know
        return {"error": str(e)}


def arxiv(key, title, refresh):
    words = [w for w in re.findall(r"[A-Za-z]+", title) if len(w) > 3][:8]
    q = " AND ".join(f"ti:{w}" for w in words)
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode({"search_query": q, "max_results": 5})
    rec = cached(f"ft_arxiv_{key}.json", url, refresh)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    best, score = None, 0.0
    for e in ET.fromstring(rec["body"]).findall("a:entry", ns):
        t = e.findtext("a:title", "", ns)
        s = difflib.SequenceMatcher(None, norm(t), norm(title)).ratio()
        if s > score:
            best, score = e.findtext("a:id", "", ns), s
    return best if score >= 0.85 else None


def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research script)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    if not data.startswith(b"%PDF"):
        return False
    with open(path, "wb") as f:
        f.write(data)
    return True


def main():
    refresh, dl = "--refresh" in sys.argv, "--download" in sys.argv
    os.makedirs(FT_DIR, exist_ok=True)
    rows = []
    for key, doi, title, check in TARGETS:
        up = unpaywall(key, doi, refresh)
        locs = [l for l in (up.get("oa_locations") or []) if l.get("url_for_pdf") or l.get("url")]
        ax = arxiv(key, title, refresh)
        cands = [(l.get("url_for_pdf") or l.get("url"), f"unpaywall:{l.get('host_type')}:{l.get('version')}") for l in locs]
        if ax:
            cands.append((ax.replace("/abs/", "/pdf/"), "arxiv"))
        got, used = False, ""
        if dl:
            for url, src in cands:
                try:
                    if download(url, os.path.join(FT_DIR, f"{key}.pdf")):
                        got, used = True, f"{src} {url}"
                        break
                except Exception as e:
                    print(f"  {key}: {src} failed ({type(e).__name__})", flush=True)
        rows.append({"key": key, "doi": doi, "oa_status": up.get("oa_status", up.get("error", "")), "arxiv": ax or "",
                     "candidates": " | ".join(f"{s} {u}" for u, s in cands), "downloaded": got, "source": used,
                     "check": check})
        print(f"{key:18s} {str(up.get('oa_status', 'n/a')):8s} arxiv={'yes' if ax else 'no '} cands={len(cands)} "
              f"{'GOT' if got else ''}", flush=True)
    with open(os.path.join(HERE, "fulltext_log.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
