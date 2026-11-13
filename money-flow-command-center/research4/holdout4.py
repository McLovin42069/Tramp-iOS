"""Run every round-4 candidate ONCE on hold-out data. Only the lead researcher runs this."""
import os, sys, json, glob, importlib.util
os.environ["MFCC_HOLDOUT"] = "1"
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, pandas as pd, lib4
DATA = {"long": lib4.load_long(), "fut": lib4.load_fut(), "crypto": lib4.load_crypto()}
START = {"long": lib4.CUTS["LCUT"], "fut": lib4.CUTS["HCUT"], "crypto": lib4.CUTS["CCUT"]}; out = []
for f in sorted(glob.glob(os.path.join(HERE, "candidates", "*.py"))):
    name = os.path.basename(f)[:-3]
    try:
        spec = importlib.util.spec_from_file_location(name, f); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        D = DATA[m.DATA]; start = START[m.DATA] + pd.Timedelta(days=1); ret = m.strategy(D); bench = None
        if getattr(m, "BENCH", None):
            b = D["C"][m.BENCH].dropna()
            bench = b.pct_change(fill_method=None) if m.DATA != "fut" else b.groupby((b.index + pd.Timedelta(hours=6)).normalize()).last().pct_change(fill_method=None)
        ho, full = lib4.ts_eval(ret, bench, start=start), lib4.ts_eval(ret, bench)
        r = ret[ret.index >= start]
        keep = ("days", "active_days_pct", "ann_return_pct", "ann_vol_pct", "sharpe", "t", "max_drawdown_pct", "positive_years", "alpha_ann_pct", "alpha_t", "bench_ann_pct", "bench_sharpe", "bench_max_drawdown_pct", "by_year_pct", "from", "to")
        out.append({"file": name, "name": m.NAME, "data": m.DATA, "variants": getattr(m, "VARIANTS_TRIED", None),
                    "discovery": {k: m.DISCOVERY.get(k) for k in ("t", "sharpe", "ann_return_pct", "alpha_t", "max_drawdown_pct")},
                    "holdout": {k: ho.get(k) for k in keep}, "ho_worst_day_pct": float(r.min() * 100) if len(r) else None,
                    "full_t": full.get("t"), "full_alpha_t": full.get("alpha_t")})
    except Exception as e:
        out.append({"file": name, "error": f"{type(e).__name__}: {e}"})
json.dump(out, open(os.path.join(HERE, "holdout4_results.json"), "w"), indent=1, default=str)
for r in out: print(json.dumps(r, default=str))
