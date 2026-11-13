import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research")
import lib, numpy as np, pandas as pd
D = lib.load()
C = D["C"]; idx = C.index
US = lib.tickers(D, cls="US Stocks"); EU = lib.tickers(D, cls="Europe Stocks"); AS = lib.tickers(D, cls="Asia Stocks")
def panel(col):
    s = D["short"]
    p = s.pivot_table(index="pub_date", columns="symbol", values=col, aggfunc="last").sort_index()
    return p
def daily(p, limit=25):
    # report-frequency panel -> daily grid, usable from pub_date
    u = idx.union(p.index)
    return p.reindex(u).ffill(limit=limit).reindex(idx)
SI, ADV, DTC = panel("si"), panel("adv"), panel("dtc")
N = 0
def ev(name, sig, h, cols=US, **k):
    global N; N += 1
    r = lib.xs_eval(sig, D, h, cols=cols, **k)
    if r.get("n_eff", 0) == 0: print(name, r); return r
    yrs = r["by_year_pct"]; pos = sum(v > 0 for v in yrs.values())
    print(f"{name:42s} h={h:3d} sp={r['spread_pct']:6.2f} t={r['t']:5.2f} net={r['net_spread_pct']:6.2f} ic_t={r['ic_t']:5.2f} H1={r['first_half_pct']:5.2f} H2={r['second_half_pct']:5.2f} yr+={pos}/{len(yrs)} n={r['names_per_side']:.0f} to={r['turnover']:.2f}")
    return r
