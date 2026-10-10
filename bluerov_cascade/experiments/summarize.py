"""Tables for X0-X3: statistics of the tuning runs and the test results.

    python3 -I experiments/summarize.py          # prints the tables, writes results/summary.json
"""

import json
import os

import numpy as np
from scipy.stats import kruskal, mannwhitneyu

RES = os.path.join(os.path.dirname(__file__), "..", "results")


def stats(v):
    v = np.asarray(v, float)
    return dict(n=int(v.size), best=float(v.min()), median=float(np.median(v)), mean=float(v.mean()),
                std=float(v.std(ddof=1)) if v.size > 1 else 0.0, worst=float(v.max()),
                q25=float(np.percentile(v, 25)), q75=float(np.percentile(v, 75)))


def x1(path):
    runs = json.load(open(path))
    groups = {}
    for k, r in runs.items():
        m, box, _ = k.split("|")
        groups.setdefault((m, box), []).append(r["f"])
    out = {f"{m}|{b}": stats(v) for (m, b), v in groups.items()}
    plain = {m: v for (m, b), v in groups.items() if b == "plain" and m != "SOO-iter"}
    ref = min(plain, key=lambda m: np.median(plain[m]))
    print(f"\nX1 tuners, proposed FOPID-(1+TFOID), training cost J (reference: {ref})")
    print(f"{'method':10s} {'box':7s} {'best':>8s} {'median':>8s} {'mean':>8s} {'std':>7s} {'worst':>8s}"
          f" {'p vs ref':>9s} {'p plain/mirror':>15s}")
    for (m, b), v in sorted(groups.items()):
        s = stats(v)
        p_ref = mannwhitneyu(v, plain[ref]).pvalue if (b == "plain" and m != ref) else np.nan
        p_mir = (mannwhitneyu(groups[(m, "plain")], groups[(m, "mirror")]).pvalue
                 if b == "mirror" and (m, "plain") in groups else np.nan)
        out[f"{m}|{b}"].update(p_vs_ref=p_ref, p_plain_mirror=p_mir)
        print(f"{m:10s} {b:7s} {s['best']:8.3f} {s['median']:8.3f} {s['mean']:8.3f} {s['std']:7.3f} "
              f"{s['worst']:8.3f} {p_ref:9.2g} {p_mir:15.2g}")
    out["kruskal_plain"] = float(kruskal(*plain.values()).pvalue)
    out["reference"] = ref
    return out


def x2(path):
    runs = json.load(open(path))
    groups = {}
    for r in runs.values():
        groups.setdefault((r["structure"], r["method"]), []).append(r["f"])
    print("\nX2 structures, training cost J over the runs")
    print(f"{'structure':18s} {'tuner':6s} {'best':>8s} {'median':>8s} {'std':>7s} {'worst':>8s}")
    out = {}
    for (s, m), v in sorted(groups.items(), key=lambda kv: np.median(kv[1])):
        st = stats(v)
        out[f"{s}|{m}"] = st
        print(f"{s:18s} {m:6s} {st['best']:8.3f} {st['median']:8.3f} {st['std']:7.3f} {st['worst']:8.3f}")
    return out


def x3(path):
    res = json.load(open(path))
    print("\nX3 test cases, weighted ITAE (energy in kJ), best run of each structure")
    names = list(next(iter(res.values()))["tests"])
    print(f"{'structure|tuner':28s} " + " ".join(f"{n:>18s}" for n in names) + f" {'MC med':>8s} {'MC p90':>8s}")
    out = {}
    for k, e in sorted(res.items(), key=lambda kv: kv[1]["tests"][names[-1]]["wITAE"]):
        t = e["tests"]
        mc = np.array(e["monte_carlo"]["wITAE"])
        print(f"{k:28s} " + " ".join(f"{t[n]['wITAE']:9.3f} ({t[n]['energy'] / 1e3:5.2f})" for n in names)
              + f" {np.median(mc):8.3f} {np.percentile(mc, 90):8.3f}")
        out[k] = dict(tests={n: t[n]["wITAE"] for n in names}, energy={n: t[n]["energy"] for n in names},
                      mc_median=float(np.median(mc)), mc_p90=float(np.percentile(mc, 90)),
                      mc_fail=e["monte_carlo"]["failures"])
    return out


def x0(path):
    d = json.load(open(path))
    print("\nX0 positional bias: median final error, optimum at the origin -> shifted")
    funcs = sorted({k.split("|")[0] for k in d})
    methods = list(dict.fromkeys(k.split("|")[2] for k in d))
    print(f"{'method':8s} " + " ".join(f"{f:>22s}" for f in funcs))
    for m in methods:
        print(f"{m:8s} " + " ".join(f"{np.median(d[f'{f}|origin|{m}']):10.3g}->{np.median(d[f'{f}|shifted|{m}']):<10.3g}"
                                    for f in funcs))
    return {k: stats(v) for k, v in d.items()}


def main():
    out = {}
    for name, fn in (("x0", x0), ("x1", x1), ("x2", x2), ("x3", x3)):
        p = os.path.join(RES, {"x0": "x0_center_bias.json", "x1": "x1_optimizers.json",
                               "x2": "x2_controllers.json", "x3": "x3_evaluate.json"}[name])
        if os.path.exists(p):
            out[name] = fn(p)
    json.dump(out, open(os.path.join(RES, "summary.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
