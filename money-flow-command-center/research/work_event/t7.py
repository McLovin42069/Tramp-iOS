from cal import *
D = lib.load(); C = D["C"]; V = D["V"]
US=lib.tickers(D,cls="US Stocks",core=False)
def W_shock(D, thr=-3.0, hold=20, side=-1):
    C, V = D["C"], D["V"]; US = lib.tickers(D, cls="US Stocks", core=False)
    ok = V[US] > 0
    RR = lib.residual(C[US].pct_change(fill_method=None).where(ok), D)
    z = RR / RR.rolling(60, min_periods=40).std().shift(1)
    ev = (z < thr) if side < 0 else (z > -thr)
    act = ev.astype(float).rolling(hold, min_periods=1).max() > 0
    act = act & C[US].notna()
    return act.div(act.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0), act.sum(axis=1)
def ev(W, bench, name, cost=10.0):
    ret = lib.weights_to_returns(W, D, cost).iloc[80:]; b = C[bench].pct_change(fill_method=None)
    e = lib.ts_eval(ret, b); half=len(ret)//2; a=ret-e['beta']*b.reindex(ret.index)
    ay={int(y):round(float(v.sum()*100),1) for y,v in a.groupby(a.index.year)}
    print(f"{name:34s} ann={e['ann_return_pct']:5.1f} sh={e['sharpe']:.2f} bsh={e['bench_sharpe']:.2f} beta={e['beta']:.2f} alpha={e['alpha_ann_pct']:.1f} alpha_t={e['alpha_t']:.2f} a_h1={a.iloc[:half].mean()*25200:.1f} a_h2={a.iloc[half:].mean()*25200:.1f} alpha_yrs={list(ay.values())}")
    return e
for thr,hold in [(-3,20),(-2.5,20),(-3.5,20),(-3,10),(-3,40),(-3,60)]:
    W,n=W_shock(D,thr,hold); print("avg names",round(n.iloc[80:].mean(),1),"min",n.iloc[80:].min(), end=" ")
    ev(W,"RSP",f"long shock thr={thr} hold={hold}")
W,n=W_shock(D,-3,20); ev(W,"SPY","thr=-3 hold=20 vs SPY"); ev(W,"RSP","thr=-3 hold=20 zero cost",cost=0)
W,n=W_shock(D,-3,20,side=1); ev(W,"RSP","UP shock thr=3 hold=20")
# equal-weight universe baseline vs RSP (does the basket alpha just reflect universe-vs-RSP?)
ok=C[US].notna(); Wu=ok.div(ok.sum(axis=1),axis=0); ev(Wu,"RSP","EW universe")
