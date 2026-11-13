import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research")
import lib, numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
D = lib.load()
U = lib.tickers(D, cls="US Stocks", core=False)
O,H,L,C,V = [D[k][U] for k in "OHLCV"]
r = C.pct_change(fill_method=None)
rr = lib.residual(r, D)            # sector-relative daily return
on = O/C.shift(1)-1; intr = C/O-1
def ev(name, sig, h, **kw):
    step = kw.pop("step", min(5, h+1))
    e = lib.xs_eval(sig, D, h, cols=U, step=step, **kw)
    yrs = e["by_year_pct"]; 
    print(f"{name:42s} h={h:3d} t={e['t']:6.2f} sp={e['spread_pct']:6.3f} net={e['net_spread_pct']:6.3f} turn={e['turnover']:.2f} H1={e['first_half_pct']:6.3f} H2={e['second_half_pct']:6.3f} ic_t={e['ic_t']:5.2f} n={e['names_per_side']:.0f} yrs={list(yrs.values())}")
    return e
