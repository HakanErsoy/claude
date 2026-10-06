"""Check every entry of a .bib file against Crossref.

For each entry the title (plus first author surname) is sent as a
bibliographic query; the best match by title similarity is compared with the
entry's year, volume, pages and DOI. Results: litreview/bib_check.csv and a
summary on stdout. Raw responses: litreview/raw/bib_<key>.json.

Usage: python3 litreview/verify_bib.py [paper/refs.bib] [--refresh]
"""

import csv
import difflib
import json
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from search import HERE, cached, strip_tags  # noqa: E402


def parse_bib(text):
    entries = []
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,]+),(.*?)\n\}", text, re.S):
        kind, key, body = m.group(1).lower(), m.group(2).strip(), m.group(3)
        fields = {}
        for f in re.finditer(r"(\w+)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|\"[^\"]*\"|\d+)", body):
            v = f.group(2).strip()
            if v[0] in "{\"":
                v = v[1:-1]
            fields[f.group(1).lower()] = v
        entries.append((kind, key, fields))
    return entries


def detex(s):
    s = re.sub(r"\\[`'^\"~=.uvHc]\{?\\?(\w)\}?", r"\1", s)
    s = re.sub(r"\\[a-zA-Z]+\s*", "", s)
    return re.sub(r"[{}$]", "", s)


def norm(t):
    return re.sub(r"[^a-z0-9]", "", detex(t).lower())


def main():
    bib = next((a for a in sys.argv[1:] if a.endswith(".bib")), os.path.join(HERE, "..", "paper", "refs.bib"))
    refresh = "--refresh" in sys.argv
    rows = []
    for kind, key, f in parse_bib(open(bib).read()):
        if kind in ("unpublished",):
            rows.append({"key": key, "status": "skip (unpublished)"})
            continue
        title = detex(f.get("title", ""))
        first = detex(f.get("author", "").split(" and ")[0].split(",")[0])
        params = {"query.bibliographic": f"{title} {first}", "rows": 5,
                  "select": "DOI,title,author,issued,container-title,volume,issue,page,type"}
        rec = cached(f"bib_{key}.json", "https://api.crossref.org/works?" + urllib.parse.urlencode(params), refresh)
        items = json.loads(rec["body"])["message"]["items"]
        best, score = None, 0.0
        for it in items:
            s = difflib.SequenceMatcher(None, norm(" ".join(it.get("title") or [])), norm(title)).ratio()
            if s > score:
                best, score = it, s
        row = {"key": key, "score": round(score, 3)}
        if best is None or score < 0.85:
            row["status"] = "NOT FOUND in Crossref (check manually)"
        else:
            cy = (best.get("issued", {}).get("date-parts") or [[None]])[0][0]
            cr = {"year": str(cy or ""), "volume": best.get("volume", ""), "pages": (best.get("page") or "").replace("-", "--"),
                  "doi": (best.get("DOI") or "").lower()}
            issues = []
            for k in ("year", "volume", "pages"):
                mine = f.get(k, "").replace(" ", "")
                if cr[k] and mine and mine != cr[k]:
                    issues.append(f"{k}: bib={mine} crossref={cr[k]}")
                if cr[k] and not mine:
                    issues.append(f"{k} missing (crossref={cr[k]})")
            if f.get("doi", "").lower() and f["doi"].lower() != cr["doi"]:
                issues.append(f"doi: bib={f['doi']} crossref={cr['doi']}")
            row.update(status="OK" if not issues else "CHECK", issues="; ".join(issues),
                       crossref_title=strip_tags(" ".join(best.get("title") or [])),
                       crossref_venue=" ".join(best.get("container-title") or []), **{f"cr_{k}": v for k, v in cr.items()})
        rows.append(row)
        print(f"{key:20s} {row['status']:8s} {row.get('score', '')} {row.get('issues', '')}", flush=True)
    fields = ["key", "status", "score", "issues", "crossref_title", "crossref_venue", "cr_year", "cr_volume", "cr_pages", "cr_doi"]
    with open(os.path.join(HERE, "bib_check.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


if __name__ == "__main__":
    main()
