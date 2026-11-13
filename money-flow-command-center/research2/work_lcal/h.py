import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research2"); import lib2
import numpy as np, pandas as pd
L = lib2.load_long(); C = L["C"]
def bh(t): return C[t].pct_change(fill_method=None)
def ev(pos, t, exec="same_close", start=None, show=True, label=""):
    pos = pos.rename(t).loc[C[t].first_valid_index():]
    r = lib2.daily_strategy(pos, L, exec=exec)
    e = lib2.ts_eval(r, bench=bh(t), start=start)
    tr = pos.diff().abs().sum()/2/ (len(pos)/252)
    if show: print(f"{label:38s} {t:5s} t={e['t']:5.2f} at={e['alpha_t']:5.2f} ann={e['ann_return_pct']:6.2f} a={e['alpha_ann_pct']:6.2f} sh={e['sharpe']:5.2f} bsh={e['bench_sharpe']:5.2f} dd={e['max_drawdown_pct']:6.1f} act={e['active_days_pct']:4.0f}% py={e['positive_years']} h1={e['first_half_ann_pct']:5.1f} h2={e['second_half_ann_pct']:5.1f} tr/y={tr:4.1f} mde={e['mde_ann_pct']:.1f}")
    return r, e
def dec(r):
    g = r.groupby((r.index.year//5)*5)
    return " ".join(f"{k}:{v.mean()*252*100:5.1f}({v.mean()/v.std()*np.sqrt(len(v)):4.1f})" for k,v in g)
