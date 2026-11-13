import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research4"); import lib4
import numpy as np, pandas as pd
L = lib4.us_calendar(lib4.load_long())
C = L["C"]; ix = C["SPY"].dropna().index
def ev(ret, bench=None, start=None, end=None):
    return lib4.ts_eval(ret, bench, start, end)
def bh(t): return C[t].pct_change(fill_method=None)
def line(name, ret, bench=None, start=None):
    e = ev(ret, bench, start)
    if "t" not in e: return name+" short"
    x2 = ret[(ret.index.year!=2008)&(ret.index.year!=2009)]
    e2 = ev(x2, bench)
    return f"{name:34s} t={e['t']:5.2f} ann={e['ann_return_pct']:6.2f} a_t={e.get('alpha_t',float('nan')):5.2f} beta={e.get('beta',float('nan')):4.2f} h1={e['first_half_ann_pct']:6.2f} h2={e['second_half_ann_pct']:6.2f} yrs={e['positive_years']} mde={e['mde_ann_pct']:5.2f} | ex0809 t={e2['t']:5.2f} a_t={e2.get('alpha_t',float('nan')):5.2f}"
