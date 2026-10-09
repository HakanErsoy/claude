"""Download the Panasonic 18650PF files used by E12, with SHA-256 checks.

Source: P. Kollmeyer, "Panasonic 18650PF Li-ion Battery Data", Mendeley Data,
v1, 2018, doi:10.17632/wykht8y7tg.1, licence CC BY 4.0. The data are not
stored in this repository; they are fetched into a data directory
(argument, or $VOFRAC_DATA, default ~/.cache/vofrac/panasonic18650pf).

    python3 experiments/fetch_panasonic.py [DATA_DIR] [--all-temps] [--eis]
"""

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://data.mendeley.com/public-api/datasets/wykht8y7tg"
UA = {"User-Agent": "vofrac-fetch/1.0 (+https://github.com/HakanErsoy/claude)"}   # the default urllib agent is refused
TEMPS = ("25degC", "10degC", "0degC", "n10degC", "n20degC")
CYCLES = ("UDDS", "LA92", "US06", "HWFET", "HWFTa", "NN")


def wanted(name, all_temps, eis):
    base = name.split(" ", 1)[1] if " " in name else name
    if base == "C20 OCV Test_C20_25dC.mat":
        return base
    if eis and base.endswith(".csv") and "EIS" in base:
        return base
    for T in (TEMPS if all_temps else TEMPS[:1]):
        if base.startswith(T + "_") and base.endswith("_Pan18650PF.mat"):
            mid = base[len(T) + 1:-len("_Pan18650PF.mat")]
            if mid in CYCLES or mid.lower().endswith("pulse_hppc") or mid.startswith("trise"):
                return base
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = args[0] if args else os.environ.get("VOFRAC_DATA",
                                               os.path.expanduser("~/.cache/vofrac/panasonic18650pf"))
    os.makedirs(out, exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(API, headers=UA), timeout=60) as r:
        meta = json.load(r)
    files = []
    for f in meta["files"]:
        base = wanted(f["filename"], "--all-temps" in sys.argv, "--eis" in sys.argv)
        if base:
            c = f["content_details"]
            files.append((base, c["download_url"], c["sha256_hash"], c["size"]))
    manifest = {}
    for base, url, sha, size in sorted(files):
        path = os.path.join(out, base)
        if not (os.path.exists(path) and hashlib.sha256(open(path, "rb").read()).hexdigest() == sha):
            blob = None
            for attempt in range(4):              # the host returns transient 404s under load
                try:
                    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
                        blob = r.read()
                    break
                except urllib.error.HTTPError as e:
                    err = e.code
                    time.sleep(15 * (attempt + 1))
            if blob is None:
                print(f"MISSING {base}: HTTP {err}", flush=True)
                manifest[base] = {"sha256": sha, "bytes": size, "missing": f"HTTP {err}"}
                continue
            with open(path, "wb") as fh:
                fh.write(blob)
        got = hashlib.sha256(open(path, "rb").read()).hexdigest()
        if got != sha:
            raise RuntimeError(f"SHA-256 mismatch for {base}")
        manifest[base] = {"sha256": sha, "bytes": size}
        print(f"ok {base} ({size / 1e6:.1f} MB)", flush=True)
    with open(os.path.join(out, "manifest.json"), "w") as fh:
        json.dump({"source": "doi:10.17632/wykht8y7tg.1 (CC BY 4.0)", "files": manifest}, fh, indent=1)


if __name__ == "__main__":
    main()
