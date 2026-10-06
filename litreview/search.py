"""Systematic literature search for the CSSP manuscript (reproducible part).

Runs a fixed list of queries against open bibliographic APIs, stores every
raw response under litreview/raw/ (with the query and the retrieval date),
merges the records, removes duplicates (DOI, then normalized title) and
writes litreview/candidates.csv for title/abstract screening.

Sources
  crossref   api.crossref.org/works, query.bibliographic, journal articles,
             proceedings papers and book chapters, published 2000 or later,
             top 100 by relevance per query
  arxiv      export.arxiv.org/api/query, boolean query, top 100 per query

Scopus and Web of Science are not reachable from this environment; the
same strings are listed in PROTOKOL.md for a manual run with institutional
access. OpenAlex and Semantic Scholar were rate-limited at the time of the
run.

Usage: python3 litreview/search.py [--refresh]
"""

import csv
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")

# (id, research question, crossref bibliographic query)
CROSSREF_QUERIES = [
    ("C01", "RQ1", "variable order fractional operator realization"),
    ("C02", "RQ1", "variable order fractional derivative analog realization"),
    ("C03", "RQ1", "variable order fractional circuit implementation"),
    ("C04", "RQ4", "variable order fractional FPGA implementation"),
    ("C05", "RQ4", "time-varying fractional order system FPGA"),
    ("C06", "RQ1", "variable order fractional digital filter"),
    ("C07", "RQ1", "variable fractional order differentiator design"),
    ("C08", "RQ2", "variable order fractional derivative switching scheme"),
    ("C09", "RQ2", "variable order fractional derivative duality recursive definition"),
    ("C10", "RQ2", "variable order fractional derivative definitions comparison"),
    ("C11", "RQ5", "variable order Grunwald-Letnikov numerical approximation"),
    ("C12", "RQ3", "fixed pole approximation fractional order system"),
    ("C13", "RQ3", "diffusive representation fractional integral numerical approximation"),
    ("C14", "RQ3", "sum of exponentials approximation variable order fractional derivative"),
    ("C15", "RQ3", "kernel compression fractional differential equations"),
    ("C16", "RQ3", "infinite state representation fractional system"),
    ("C17", "RQ1", "variable order fractional Oustaloup approximation"),
    ("C18", "RQ1", "variable order fractional PID controller implementation"),
    ("C19", "RQ1", "time-varying fractional order system approximation"),
    ("C20", "RQ6", "multifractional Brownian motion simulation"),
    ("C21", "RQ6", "multifractional Gaussian noise synthesis variable order"),
    ("C22", "RQ6", "Riemann-Liouville multifractional Brownian motion generation"),
    ("C23", "RQ5", "variable order fractional system stability"),
    ("C24", "RQ1", "variable order fractional chaotic system circuit"),
]

ARXIV_QUERIES = [
    ("A01", "RQ1", 'all:"variable order" AND all:fractional AND (all:realization OR all:implementation OR all:approximation)'),
    ("A02", "RQ1", 'all:"variable-order" AND all:fractional AND (all:realization OR all:implementation OR all:approximation)'),
    ("A03", "RQ2", '(all:"variable order" OR all:"variable-order") AND all:fractional AND (all:definition OR all:switching OR all:duality)'),
    ("A04", "RQ3", 'all:fractional AND (all:"sum of exponentials" OR all:"diffusive representation" OR all:"kernel compression")'),
    ("A05", "RQ6", 'all:"multifractional Brownian motion" AND (all:simulation OR all:synthesis OR all:generation)'),
    ("A06", "RQ4", 'all:fractional AND all:FPGA'),
]

UA = {"User-Agent": "vofrac-litreview/1.0 (research script)"}


def get(url, tries=5):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:                         # network or 429: back off
            if k == tries - 1:
                raise
            time.sleep(2 ** (k + 1))
            print(f"  retry {k + 1} after {type(e).__name__}: {e}", flush=True)


def cached(name, url, refresh):
    path = os.path.join(RAW, name)
    if os.path.exists(path) and not refresh:
        with open(path) as f:
            return json.load(f)
    body = get(url)
    rec = {"url": url, "retrieved": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
           "body": body.decode("utf-8")}
    with open(path, "w") as f:
        json.dump(rec, f)
    time.sleep(1.0)
    return rec


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(s or ""))).strip()


def crossref(qid, query, refresh):
    params = {"query.bibliographic": query, "rows": 100,
              "filter": "from-pub-date:2000-01-01,type:journal-article,type:proceedings-article,type:book-chapter",
              "select": "DOI,title,author,issued,container-title,type,abstract,is-referenced-by-count,volume,issue,page"}
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
    rec = cached(f"crossref_{qid}.json", url, refresh)
    items = json.loads(rec["body"])["message"]["items"]
    out = []
    for rank, it in enumerate(items, 1):
        year = (it.get("issued", {}).get("date-parts") or [[None]])[0][0]
        out.append({"doi": (it.get("DOI") or "").lower(), "title": strip_tags(" ".join(it.get("title") or [])),
                    "authors": "; ".join(f"{a.get('family', '')}, {a.get('given', '')}".strip(", ")
                                         for a in it.get("author", [])[:8]),
                    "year": year, "venue": " ".join(it.get("container-title") or []), "type": it.get("type"),
                    "volume": it.get("volume", ""), "issue": it.get("issue", ""), "pages": it.get("page", ""),
                    "cited_by": it.get("is-referenced-by-count", 0), "abstract": strip_tags(it.get("abstract")),
                    "arxiv": "", "hits": [f"{qid}#{rank}"]})
    return out


def arxiv(qid, query, refresh):
    params = {"search_query": query, "start": 0, "max_results": 100, "sortBy": "relevance"}
    url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
    rec = cached(f"arxiv_{qid}.json", url, refresh)
    ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(rec["body"])
    out = []
    for rank, e in enumerate(root.findall("a:entry", ns), 1):
        doi = e.find("x:doi", ns)
        jref = e.find("x:journal_ref", ns)
        out.append({"doi": (doi.text if doi is not None else "").lower(),
                    "title": strip_tags(e.findtext("a:title", "", ns)),
                    "authors": "; ".join(a.findtext("a:name", "", ns) for a in e.findall("a:author", ns)[:8]),
                    "year": int(e.findtext("a:published", "0000", ns)[:4]),
                    "venue": jref.text if jref is not None else "arXiv", "type": "preprint",
                    "volume": "", "issue": "", "pages": "", "cited_by": "",
                    "abstract": strip_tags(e.findtext("a:summary", "", ns)),
                    "arxiv": e.findtext("a:id", "", ns).rsplit("/", 1)[-1], "hits": [f"{qid}#{rank}"]})
    return out


def norm_title(t):
    return re.sub(r"[^a-z0-9]", "", t.lower())


def merge(records):
    by_key, order = {}, []
    for r in records:
        keys = [k for k in (("doi", r["doi"]) if r["doi"] else None, ("t", norm_title(r["title"]))) if k]
        hit = next((by_key[k] for k in keys if k in by_key), None)
        if hit is None:
            hit = dict(r, hits=list(r["hits"]))
            order.append(hit)
        else:
            hit["hits"] += r["hits"]
            for f in ("doi", "abstract", "arxiv", "volume", "issue", "pages"):
                if not hit[f] and r[f]:
                    hit[f] = r[f]
            if hit["type"] == "preprint" and r["type"] != "preprint":
                for f in ("venue", "type", "year", "cited_by"):
                    hit[f] = r[f]
        for k in keys:
            by_key[k] = hit
        if hit["doi"]:
            by_key[("doi", hit["doi"])] = hit
    return order


def main():
    refresh = "--refresh" in sys.argv
    os.makedirs(RAW, exist_ok=True)
    recs, log = [], []
    for qid, rq, q in CROSSREF_QUERIES:
        r = crossref(qid, q, refresh)
        log.append((qid, rq, "crossref", q, len(r)))
        print(f"{qid} {rq} crossref {len(r):4d}  {q}", flush=True)
        recs += r
    for qid, rq, q in ARXIV_QUERIES:
        r = arxiv(qid, q, refresh)
        log.append((qid, rq, "arxiv", q, len(r)))
        print(f"{qid} {rq} arxiv    {len(r):4d}  {q}", flush=True)
        recs += r
    merged = merge(recs)
    merged.sort(key=lambda r: (-len(r["hits"]), r["title"].lower()))
    fields = ["id", "title", "authors", "year", "venue", "type", "volume", "issue", "pages", "doi", "arxiv",
              "cited_by", "n_hits", "hits", "abstract"]
    with open(os.path.join(HERE, "candidates.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i, r in enumerate(merged, 1):
            w.writerow(dict({k: r.get(k, "") for k in fields}, id=f"R{i:04d}", n_hits=len(r["hits"]),
                            hits=" ".join(r["hits"])))
    with open(os.path.join(HERE, "search_log.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["query_id", "rq", "source", "query", "records"])
        w.writerows(log)
    print(f"records {len(recs)}, unique {len(merged)}")


if __name__ == "__main__":
    main()
