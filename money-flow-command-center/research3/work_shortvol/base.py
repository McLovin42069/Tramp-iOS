import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research3"); import lib3
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
D = lib3.load_stocks()
US = lib3.tickers(D, cls="US Stocks", core=False)
ix = D["C"].index
S = D["shortvol"]["short"].reindex(ix); T = D["shortvol"]["total"].reindex(ix)
cols = [c for c in US if c in S.columns]
S, T = S[cols], T[cols]
def ratio(n=1):
    return S.rolling(n, min_periods=max(1,n//2)).sum() / T.rolling(n, min_periods=max(1,n//2)).sum().replace(0,np.nan)
def ev(sig, h, name, cost=5):
    step = h+1 if h < 5 else 5
    a = lib3.xs_eval(sig, D, h, cols=cols, cost_bps=cost, step=step)
    b = lib3.xs_eval(lib3.size_neutral(sig, D), D, h, cols=cols, cost_bps=cost, step=step)
    if a.get("n_eff",0)==0: print(name, "too few"); return a,b
    yrs = a["by_year_pct"]; pos = sum(v>0 for v in yrs.values())
    print(f"{name:34s} h={h:2d} raw t={a['t']:+.2f} sp={a['spread_pct']:+.3f} net={a['net_spread_pct']:+.3f} | SN t={b['t']:+.2f} net={b['net_spread_pct']:+.3f} | halves {a['first_half_pct']:+.3f}/{a['second_half_pct']:+.3f} yrs+ {pos}/{len(yrs)} turn={a['turnover']:.2f} n={a['names_per_side']:.0f} neff={a['n_eff']}")
    return a,b
