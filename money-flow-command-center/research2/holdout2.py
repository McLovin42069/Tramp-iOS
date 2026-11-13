"""Run every round-2 candidate ONCE on the hold-out period. Only the lead researcher runs this."""
import os, sys, json, glob, importlib.util
os.environ["MFCC_HOLDOUT"] = "1"
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, pandas as pd, lib2
L, I = lib2.load_long(), lib2.load_intra(); out = []
for f in sorted(glob.glob(os.path.join(HERE, "candidates", "*.py"))):
    name = os.path.basename(f)[:-3]
    try:
        spec = importlib.util.spec_from_file_location(name, f); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        D = L if m.DATA == "long" else I
        start = (lib2.CUTS["LCUT"] if m.DATA == "long" else lib2.CUTS["ICUT"]) + pd.Timedelta(days=1)
        ret = m.strategy(D)
        bench = None
        if getattr(m, "BENCH", None):
            b = D["C"][m.BENCH]
            bench = b.pct_change(fill_method=None) if m.DATA == "long" else b.groupby(b.index.normalize()).last().pct_change(fill_method=None)
        ho, full = lib2.ts_eval(ret, bench, start=start), lib2.ts_eval(ret, bench)
        keep = ("days", "ann_return_pct", "ann_vol_pct", "sharpe", "t", "max_drawdown_pct", "positive_years", "alpha_ann_pct", "alpha_t", "bench_ann_pct", "bench_sharpe", "bench_max_drawdown_pct", "by_year_pct", "from", "to")
        out.append({"file": name, "name": m.NAME, "data": m.DATA, "variants": getattr(m, "VARIANTS_TRIED", None),
                    "discovery": {k: m.DISCOVERY.get(k) for k in ("t", "sharpe", "ann_return_pct", "alpha_t", "max_drawdown_pct")},
                    "holdout": {k: ho.get(k) for k in keep}, "full_t": full.get("t"), "full_alpha_t": full.get("alpha_t")})
    except Exception as e:
        out.append({"file": name, "error": f"{type(e).__name__}: {e}"})
json.dump(out, open(os.path.join(HERE, "holdout2_results.json"), "w"), indent=1, default=str)
for r in out: print(json.dumps(r, default=str))
