import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research3"); import lib3
import numpy as np, pandas as pd
L = lib3.us_calendar(lib3.load_long()); C = L["C"]
R = C.pct_change(fill_method=None)
N=[0]
def ev(name, pos, bench="SPY", exec="next_close", start=None, show=True, excl=None):
    N[0]+=1
    ret = lib3.daily_strategy(pos, L, exec=exec)
    if start: ret = ret[ret.index>=start]
    ret = ret[ret.index >= pos.dropna(how="all").index[0]]
    if excl is not None: ret = ret[~ret.index.isin(excl)]
    b = R[bench] if bench else None
    e = lib3.ts_eval(ret, bench=b)
    m = (1+ret).groupby([ret.index.year, ret.index.month]).prod()-1
    if show:
        print(f"{name:42s} {e['from']} ann {e['ann_return_pct']:6.2f} vol {e['ann_vol_pct']:5.1f} SR {e['sharpe']:.2f} t {e['t']:.2f} dd {e['max_drawdown_pct']:6.1f} wd {ret.min()*100:6.1f} wm {m.min()*100:6.1f} yrs {e['positive_years']} h1 {e['first_half_ann_pct']:.1f} h2 {e['second_half_ann_pct']:.1f}"
          + (f" | beta {e['beta']:.2f} a {e['alpha_ann_pct']:.2f} at {e['alpha_t']:.2f} bSR {e['bench_sharpe']:.2f} bdd {e['bench_max_drawdown_pct']:.0f}" if bench else ""))
    return ret, e
