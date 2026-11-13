"""ONE-SHOT hold-out run (2019-01-01 onward) of the scan-derived rules, each at the pre-fixed threshold 1.0 and 2 bps."""
import os, sys, json; os.environ["MFCC_HOLDOUT"] = "1"
sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research2"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, lib2, strat
L = strat.us(lib2.load_long()); START = "2019-01-01"; out = []
print(f"{'rule':46s} {'ann%':>6} {'vol%':>5} {'t':>6} {'shrp':>5} {'act%':>5} {'maxDD':>6} {'yrs+':>5} | at 5bps: ann%   t | full-sample t | by year")
for name, f in strat.RULES.items():
    r = f(L, 1.0, 2.0); e = lib2.ts_eval(r, start=START); e5 = lib2.ts_eval(f(L, 1.0, 5.0), start=START); full = lib2.ts_eval(r)
    out.append({"rule": name, **{k: e.get(k) for k in ("ann_return_pct", "ann_vol_pct", "t", "sharpe", "max_drawdown_pct", "positive_years", "by_year_pct", "active_days_pct")}, "t_5bps": e5.get("t"), "ann_5bps": e5.get("ann_return_pct"), "full_t": full.get("t")})
    print(f"{name:46s} {e['ann_return_pct']:6.2f} {e['ann_vol_pct']:5.1f} {e['t']:6.2f} {e['sharpe']:5.2f} {e['active_days_pct']:5.0f} {e['max_drawdown_pct']:6.1f} {e['positive_years']:>5} | {e5['ann_return_pct']:6.2f} {e5['t']:5.2f} | {full['t']:5.2f} | {e['by_year_pct']}")
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "holdout_scan_results.json"), "w"), indent=1, default=str)
