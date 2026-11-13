import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research"); import lib
import pandas as pd, numpy as np
D = lib.load(); C=D["C"]; m=D["meta"]
def show(name, r):
    if r.get("n_eff",0)==0: print(name, r); return
    by=r["by_year_pct"]; pos=sum(v>0 for v in by.values())
    print(f"{name:42s} h={r['h']:3d} spr={r['spread_pct']:+.3f} t={r['t']:+.2f} ic_t={r['ic_t']:+.2f} net={r['net_spread_pct']:+.3f} H1={r['first_half_pct']:+.3f} H2={r['second_half_pct']:+.3f} yrs+={pos}/{len(by)} n={r['names_per_side']:.0f}")
n=0
SEC=['XLK','XLC','XLY','XLP','XLF','XLV','XLE','XLI','XLB','XLU','XLRE']
CTY=['EWG','EWU','EWQ','EWI','EWP','EWL','EWN','EWD','EWJ','EWA','EWH','EWS','EWY','EWT','FXI','INDA','EWZ','EWW','EZA','TUR','EIDO','SPY']
for nm,U,q,mn in [("sector",SEC,0.33,8),("country",CTY,0.25,15)]:
    for L,h in [(5,5),(20,5),(20,20),(120,20),(250,20)]:
        s=C[U].pct_change(L, fill_method=None)
        show(f"{nm} mom{L}", lib.xs_eval(s, D, h, cols=U, q=q, min_names=mn, resid=False)); n+=1
# US lead: country ETF gap vs SPY-beta implied move (underreaction to US), all US-listed so 1d
r1=C.pct_change(fill_method=None)
for L in [1,5]:
    beta=r1[CTY].rolling(250).cov(r1['SPY']).div(r1['SPY'].rolling(250).var(),axis=0)
    gap=beta.mul(C['SPY'].pct_change(L),axis=0)-C[CTY].pct_change(L)
    show(f"country beta*SPY{L}-own{L}", lib.xs_eval(gap, D, 5, cols=CTY, q=0.25, min_names=15, resid=False)); n+=1
# stocks in Europe/Asia: local-currency closes before US; signal = beta*SPY ret (US move on t) - own ret t.. with t+1 trade
for cls in ["Europe Stocks","Asia Stocks"]:
    cols=lib.tickers(D, cls=cls, core=False)
    spy=r1['SPY']
    # beta to previous-day SPY (lagged US), as stock sensitivity to US news
    for L in [1,5]:
        b=r1[cols].rolling(250).cov(spy.shift(1)).div(spy.rolling(250).var(),axis=0)
        sig=b.mul(C['SPY'].pct_change(L),axis=0)
        show(f"{cls} lagbeta*SPY{L} resid", lib.xs_eval(sig, D, 5, cols=cols)); n+=1
print("variants",n)
