import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research"); import lib
import pandas as pd, numpy as np
D = lib.load(); C=D["C"]; m=D["meta"]
def show(name, r):
    if r.get("n_eff",0)==0: print(name, r); return
    by=r["by_year_pct"]; pos=sum(v>0 for v in by.values())
    print(f"{name:42s} h={r['h']:3d} spr={r['spread_pct']:+.3f} t={r['t']:+.2f} ic_t={r['ic_t']:+.2f} net={r['net_spread_pct']:+.3f} H1={r['first_half_pct']:+.3f} H2={r['second_half_pct']:+.3f} yrs+={pos}/{len(by)} n={r['names_per_side']:.0f}")
def grp_mean(X, cols):
    g=m["group"].reindex(cols).values
    s=X[cols].T.groupby(g).transform("sum").T; n=X[cols].notna().T.groupby(g).transform("sum").T
    return (s - X[cols].fillna(0))/(n-1).where(n>1)   # leave-one-out
n=0
for cls in ["US Stocks","Europe Stocks","Asia Stocks"]:
    cols=lib.tickers(D, cls=cls, core=False)
    print("==",cls,len(cols))
    for L in [5,20,60]:
        r=C[cols].pct_change(L, fill_method=None)
        peer=grp_mean(r, cols)
        for h in ([5,20] if L<60 else [20]):
            show(f"plain reversal -ret{L}", lib.xs_eval(-r, D, h, cols=cols)); 
            show(f"gap peer{L}-own{L}", lib.xs_eval(peer-r, D, h, cols=cols)); n+=2
    # peer momentum on raw returns (industry/country momentum via stocks)
    for L in [1,5,20]:
        r=C[cols].pct_change(L, fill_method=None); peer=grp_mean(r, cols)
        show(f"peer ret{L} RAW fwd", lib.xs_eval(peer, D, 5, cols=cols, resid=False)); n+=1
print("variants",n)
