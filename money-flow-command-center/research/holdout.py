"""Run every candidate ONCE on the hold-out period (2024-01-02 onward). Only the lead researcher runs this."""
import os, sys, json, importlib.util, glob
os.environ["MFCC_HOLDOUT"] = "1"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, lib
D = lib.load(); START = "2024-01-02"; out = []
for f in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "candidates", "*.py"))):
    name = os.path.basename(f)[:-3]
    try:
        spec = importlib.util.spec_from_file_location(name, f); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        row = {"file": name, "name": m.NAME, "kind": m.KIND, "variants": getattr(m, "VARIANTS_TRIED", None)}
        if m.KIND == "xs":
            cols = getattr(m, "TICKERS", None) or lib.tickers(D, **m.UNIVERSE)
            sig = m.signal(D)
            ho = lib.xs_eval(sig, D, m.H, cols=cols, start=START)
            full = lib.xs_eval(sig, D, m.H, cols=cols)
            s = m.EXPECTED_SIGN
            row.update({"h": m.H, "disc_t": m.DISCOVERY.get("t", np.nan) * s, "disc_spread": m.DISCOVERY.get("spread_pct", np.nan) * s,
                        "ho_t": ho.get("t", np.nan) * s, "ho_spread": ho.get("spread_pct", np.nan) * s, "ho_net": ho.get("net_spread_pct", np.nan) if s > 0 else -ho.get("spread_pct", np.nan) - (ho.get("spread_pct", 0) - ho.get("net_spread_pct", 0)),
                        "ho_n": ho.get("n_eff"), "ho_hit": ho.get("hit_pct") if s > 0 else 100 - ho.get("hit_pct", 50), "ho_by_year": {k: round(v * s, 2) for k, v in ho.get("by_year_pct", {}).items()},
                        "full_t": full.get("t", np.nan) * s, "turnover": ho.get("turnover")})
        else:
            ret = lib.weights_to_returns(m.weights(D), D)
            bench = D["C"][m.BENCH].pct_change(fill_method=None) if getattr(m, "BENCH", None) else None
            ho = lib.ts_eval(ret, bench, start=START); full = lib.ts_eval(ret, bench)
            row.update({"disc_sharpe": m.DISCOVERY.get("sharpe"), "disc_alpha_t": m.DISCOVERY.get("alpha_t"), "ho_sharpe": ho.get("sharpe"), "ho_t": ho.get("t"),
                        "ho_alpha_t": ho.get("alpha_t"), "ho_alpha_ann": ho.get("alpha_ann_pct"), "ho_ann_ret": ho.get("ann_return_pct"), "ho_maxdd": ho.get("max_drawdown_pct"),
                        "ho_bench_sharpe": ho.get("bench_sharpe"), "ho_by_year": ho.get("by_year_pct"), "full_alpha_t": full.get("alpha_t"), "full_sharpe": full.get("sharpe")})
        out.append(row)
    except Exception as e:
        out.append({"file": name, "error": f"{type(e).__name__}: {e}"})
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "holdout_results.json"), "w"), indent=1, default=str)
for r in out: print(json.dumps(r, default=str))
