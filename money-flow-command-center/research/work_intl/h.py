import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research"); import lib, numpy as np, pandas as pd
D = lib.load()
EU = lib.tickers(D, cls="Europe Stocks", core=False); AS = lib.tickers(D, cls="Asia Stocks", core=False); ALL = EU+AS
C = D["C"][ALL]; r = C.pct_change(fill_method=None)
res = lambda X: lib.residual(X, D)
rr = res(r)   # country-residual daily returns
def z(X):  # country-neutral signal
    return res(X)
def ev(name, sig, h, unis=("EU","AS","ALL"), **kw):
    out = {}
    for u in unis:
        cols = {"EU":EU,"AS":AS,"ALL":ALL}.get(u, u if isinstance(u, list) else None)
        e = lib.xs_eval(sig, D, h, cols=cols, **kw); out[u if isinstance(u,str) else "custom"] = e
        if e.get("n_eff",0)==0: print(name, u, "n/a"); continue
        by = e["by_year_pct"]; pos = sum(v>0 for v in by.values())
        print(f"{name:28s} h={h:3d} {str(u)[:6]:6s} sp={e['spread_pct']:+.2f} t={e['t']:+.2f} net={e['net_spread_pct']:+.2f} ic_t={e['ic_t']:+.2f} H1={e['first_half_pct']:+.2f} H2={e['second_half_pct']:+.2f} yrs+={pos}/{len(by)} to={e['turnover']:.2f} n={e['names_per_side']:.0f}")
    return out
