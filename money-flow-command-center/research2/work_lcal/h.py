import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research2"); import lib2
import numpy as np, pandas as pd
L = lib2.load_long(); C = L["C"]
def px(t): return C[t].dropna()
def bh(t): return px(t).pct_change()
def run(pos, t, exec="same_close", cost=2.0):
    """pos indexed on px(t).index (the ETF's own trading days)"""
    Ls = {"C": C[[t]].dropna()}
    return lib2.daily_strategy(pos.rename(t), Ls, cost_bps=cost, exec=exec)
def ev(pos, t, exec="same_close", start=None, end=None, show=True, label="", cost=2.0):
    r = run(pos, t, exec, cost)
    e = lib2.ts_eval(r, bench=bh(t), start=start, end=end)
    p = pos.reindex(r.index)
    tr = p.diff().abs().sum()/2/(len(p)/252)
    e["trades_per_year"] = float(tr)
    if show: print(f"{label:34s} {t:5s} t={e['t']:5.2f} at={e['alpha_t']:5.2f} ann={e['ann_return_pct']:6.2f} a={e['alpha_ann_pct']:6.2f} sh={e['sharpe']:5.2f} bsh={e['bench_sharpe']:5.2f} dd={e['max_drawdown_pct']:6.1f} act={e['active_days_pct']:3.0f}% py={e['positive_years']} h1={e['first_half_ann_pct']:5.1f} h2={e['second_half_ann_pct']:5.1f} tr/y={tr:4.1f} mde={e['mde_ann_pct']:.1f}")
    return r, e
def dec(r, n=5):
    g = r.groupby((r.index.year//n)*n)
    return " ".join(f"{k}:{v.mean()*252*100:5.1f}({v.mean()/v.std()*np.sqrt(len(v)):4.1f})" for k,v in g)
def tdm(idx):
    """trading day of month (1..) and trading days remaining (-1 = last day) for an index of trading days.
    NOTE: 'days remaining' is known in advance from the exchange calendar."""
    s = pd.Series(1, index=idx); ym = [idx.year, idx.month]
    fwd = s.groupby(ym).cumsum(); bwd = -(s[::-1].groupby([idx[::-1].year, idx[::-1].month]).cumsum()[::-1])
    return fwd, bwd
