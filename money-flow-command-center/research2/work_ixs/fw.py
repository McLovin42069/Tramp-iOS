import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research2"); import lib2
import numpy as np, pandas as pd
I = lib2.load_intra()
ETF = ['SPY','QQQ','IWM','DIA','XLK','XLF','XLE','XLV','XLI','XLY','XLP','XLU','XLB','XLRE','XLC','SMH','XBI','KRE','GDX','XOP','TLT','IEF','HYG','LQD','GLD','SLV','USO','UUP','EEM','EFA','FXI','EWJ','EWZ','VNQ','RSP']
STK = [c for c in I['C'].columns if c not in ETF]
C = I['C'][STK]; O = I['O'][STK]; V = I['V'][STK]
idx = C.index; day = idx.normalize()
k = pd.Series(np.arange(len(idx)), index=idx).groupby(day).cumcount().values   # bar number in session
nb = pd.Series(1, index=idx).groupby(day).transform('count').values
last = (k == nb - 1)
days = pd.DatetimeIndex(sorted(set(day)))
# daily tables
Cl = C[last]; Cl.index = Cl.index.normalize()                    # session close
Op = O[k == 0]; Op.index = Op.index.normalize()                  # session open
C1 = C[k == 0]; C1.index = C1.index.normalize()                  # close of first bar (10:30)
def Ck(j):
    x = C[k == j]; x.index = x.index.normalize(); return x.reindex(days)
gap = Op / Cl.shift(1) - 1
on1 = C1 / Cl.shift(1) - 1          # prev close -> 10:30
fh = C1 / Op - 1                    # first hour
intr = Cl / Op - 1
rod = Cl / C1 - 1                   # 10:30 -> close
rc = C.pct_change(fill_method=None)
vol20 = (Cl.pct_change(fill_method=None)).rolling(20).std()

def xw(sig, mode='q', q=0.2, long_only=False):
    """cross-sectional weights from daily signal (high = long). sum|w| = 1."""
    s = sig.sub(sig.mean(axis=1), axis=0)
    if mode == 'rank':
        r = sig.rank(axis=1); r = r.sub(r.mean(axis=1), axis=0); w = r
    else:
        p = sig.rank(axis=1, pct=True)
        w = (p > 1 - q).astype(float) - (p <= q).astype(float)
        w = w.where(sig.notna(), 0.0)
    if long_only:
        w = w.clip(lower=0); return w.div(w.abs().sum(axis=1), axis=0).fillna(0)
    lp = w.clip(lower=0); sp = (-w).clip(lower=0)
    return (0.5 * lp.div(lp.sum(axis=1), axis=0) - 0.5 * sp.div(sp.sum(axis=1), axis=0)).fillna(0)

def sched(w, enter, exit):
    """w: daily weights [day x stk], decided using info up to close of bar `enter` of that day.
    enter/exit: bar numbers; 'L' = last bar of session. exit: bar at whose close we are flat;
    exit <= enter (or 'N<j>') means held overnight and flat at close of bar j next session."""
    P = pd.DataFrame(0.0, index=idx, columns=w.columns)
    W = w.reindex(days).fillna(0)
    Wb = pd.DataFrame(W.values[np.searchsorted(days, day)], index=idx, columns=w.columns)
    Wprev = pd.DataFrame(W.shift(1).fillna(0).values[np.searchsorted(days, day)], index=idx, columns=w.columns)
    e = (nb - 1) if enter == 'L' else np.minimum(enter, nb - 1)
    if isinstance(exit, str) and exit.startswith('N'):
        j = int(exit[1:])
        m_today = (k >= e)                 # from enter bar to session end
        m_next = (k < j)                   # next session bars before exit
        P = Wb.where(pd.Series(m_today, index=idx), 0.0, axis=0) + Wprev.where(pd.Series(m_next, index=idx), 0.0, axis=0)
    else:
        x = (nb - 1) if exit == 'L' else np.minimum(exit, nb - 1)
        m = (k >= e) & (k < x)
        P = Wb.where(pd.Series(m, index=idx), 0.0, axis=0)
    return P

def run(P, cost=5.0, bench=None):
    r = lib2.bar_strategy(P, I, cost_bps=cost)
    return r

def turn(P):
    Ps = P.shift(1).fillna(0)
    return Ps.diff().abs().sum(axis=1).sum() / len(days)

def qtrs(r):
    q = r.groupby(r.index.to_period('Q')).sum()
    return f"{int((q>0).sum())}/{len(q)}"

N = [0]
def rep(name, P, costs=(2, 5, 10), full=False):
    N[0] += 1
    out = []
    for c in costs:
        e = lib2.ts_eval(run(P, c)); out.append(f"{c}bp: ann {e['ann_return_pct']:6.2f} t {e['t']:5.2f}")
    r = run(P, 5); e = lib2.ts_eval(r)
    g = lib2.ts_eval(run(P, 0))
    print(f"{name:42s} gross {g['ann_return_pct']:6.2f} t {g['t']:5.2f} | " + " | ".join(out) + f" | to/d {turn(P):.2f} h1 {e['first_half_ann_pct']:.1f} h2 {e['second_half_ann_pct']:.1f} q {qtrs(r)} mde {e['mde_ann_pct']:.1f}")
    return r
