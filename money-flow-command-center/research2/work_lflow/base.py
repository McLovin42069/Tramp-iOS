import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research2"); import lib2
import numpy as np, pandas as pd
L = lib2.load_long()
C0=L["C"]; C=C0[C0["SPY"].notna()]; S=L["spdr"]
SEC=["XLK","XLF","XLE","XLV","XLI","XLY","XLP","XLU","XLB"]
def flows(L, tick):
    S=L["spdr"]; so=S["so"][tick]; nav=S["nav"][tick]
    f=(so.diff()*nav); tna=S["tna"][tick]
    return f.shift(1), tna.shift(1)   # public next day; index = US trading days
def ev(ret,bench=None,**k):
    e=lib2.ts_eval(ret,bench,**k); return e
def short(e): 
    return {k:(round(v,2) if isinstance(v,float) else v) for k,v in e.items() if k in("t","sharpe","ann_return_pct","positive_years","first_half_ann_pct","second_half_ann_pct","mde_ann_pct","alpha_t","max_drawdown_pct","from")}
def xs_pos(sig, k=3, rebal=5, need=None):
    """long top-k / short bottom-k of sig (higher = long), weights +-1/(2k), rebalanced every `rebal` days"""
    sig=sig.dropna(how="all"); need=need or sig.shape[1]
    rk=sig.rank(axis=1); n=sig.notna().sum(axis=1)
    pos=((rk.gt(n-k,axis=0)).astype(float)-(rk.le(k)).astype(float))/(2*k)
    pos[n<need]=0.0
    keep=np.arange(len(pos))%rebal==0
    pos=pos.where(pd.Series(keep,index=pos.index),axis=0).ffill().fillna(0)
    return pos
def run(pos, bench=None, ex="next_close", **k):
    r=lib2.daily_strategy(pos,L,cost_bps=2.0,exec=ex)
    return r
def rep(name, r, bench=None, start=None):
    if start: r=r[r.index>=start]
    e=lib2.ts_eval(r,bench); x=r[(r.index.year!=2008)&(r.index.year!=2009)]
    ex=lib2.ts_eval(x)
    print(f"{name:42s} t={e['t']:5.2f} ann={e['ann_return_pct']:6.2f} sh={e['sharpe']:5.2f} h1={e['first_half_ann_pct']:6.2f} h2={e['second_half_ann_pct']:6.2f} yrs={e['positive_years']:6s} ex0809_t={ex['t']:5.2f} mde={e['mde_ann_pct']:.2f}"+(f" alpha_t={e['alpha_t']:.2f} beta={e['beta']:.2f}" if bench is not None else ""))
    return e
