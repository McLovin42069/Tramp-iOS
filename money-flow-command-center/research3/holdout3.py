"""Run every round-3 candidate ONCE on hold-out data. Only the lead researcher runs this."""
import os, sys, json, glob, importlib.util
os.environ["MFCC_HOLDOUT"] = "1"
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, pandas as pd, lib3
D, L = lib3.load_stocks(), lib3.load_long(); out = []
for f in sorted(glob.glob(os.path.join(HERE, "candidates", "*.py"))):
    name = os.path.basename(f)[:-3]
    try:
        spec = importlib.util.spec_from_file_location(name, f); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        row = {"file": name, "name": m.NAME, "kind": m.KIND, "variants": getattr(m, "VARIANTS_TRIED", None)}
        if m.KIND == "xs":
            cols = getattr(m, "TICKERS", None) or lib3.tickers(D, **m.UNIVERSE); s = m.EXPECTED_SIGN; sig = m.signal(D)
            c = getattr(m, "COST_BPS", 5)
            ho = lib3.xs_eval(sig, D, m.H, cols=cols, start="2024-01-02", cost_bps=c)
            hn = lib3.xs_eval(lib3.size_neutral(sig, D), D, m.H, cols=cols, start="2024-01-02", cost_bps=c)
            full = lib3.xs_eval(sig, D, m.H, cols=cols, cost_bps=c)
            row.update({"h": m.H, "disc_t": m.DISCOVERY.get("t", np.nan) * s, "disc_spread": m.DISCOVERY.get("spread_pct", np.nan) * s,
                        "ho_t": ho.get("t", np.nan) * s, "ho_spread": ho.get("spread_pct", np.nan) * s, "ho_n": ho.get("n_eff"),
                        "ho_net": (ho.get("net_spread_pct", np.nan) if s > 0 else -ho.get("spread_pct", np.nan) - (ho.get("spread_pct", 0) - ho.get("net_spread_pct", 0))),
                        "ho_size_neutral_t": hn.get("t", np.nan) * s, "ho_by_year": {k: round(v * s, 2) for k, v in ho.get("by_year_pct", {}).items()},
                        "full_t": full.get("t", np.nan) * s, "turnover": ho.get("turnover")})
        else:
            Lu = lib3.us_calendar(L); ret = m.strategy(L)
            bench = Lu["C"][m.BENCH].pct_change(fill_method=None) if getattr(m, "BENCH", None) else None
            ho, full = lib3.ts_eval(ret, bench, start="2019-01-01"), lib3.ts_eval(ret, bench)
            keep = ("days", "ann_return_pct", "ann_vol_pct", "sharpe", "t", "max_drawdown_pct", "positive_years", "alpha_ann_pct", "alpha_t", "bench_ann_pct", "bench_sharpe", "bench_max_drawdown_pct", "by_year_pct")
            row.update({"discovery": {k: m.DISCOVERY.get(k) for k in ("t", "sharpe", "ann_return_pct", "alpha_t", "max_drawdown_pct")},
                        "holdout": {k: ho.get(k) for k in keep}, "full_t": full.get("t"), "full_alpha_t": full.get("alpha_t")})
        out.append(row)
    except Exception as e:
        out.append({"file": name, "error": f"{type(e).__name__}: {e}"})
json.dump(out, open(os.path.join(HERE, "holdout3_results.json"), "w"), indent=1, default=str)
for r in out: print(json.dumps(r, default=str))
