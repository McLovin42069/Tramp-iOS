from base import *
spy=C["SPY"].pct_change()
def tim(name, w, start=None):
    """w in [0,1] SPY weight"""
    r=run(w.rename("SPY").to_frame()); 
    if start: r=r[r.index>=start]
    e=lib2.ts_eval(r,spy.reindex(r.index))
    x=r[(r.index.year!=2008)&(r.index.year!=2009)]; ex=lib2.ts_eval(x,spy.reindex(x.index))
    print(f"{name:40s} t={e['t']:5.2f} ann={e['ann_return_pct']:6.2f} sh={e['sharpe']:5.2f} (bench sh={e['bench_sharpe']:.2f}) beta={e['beta']:.2f} alpha={e['alpha_ann_pct']:6.2f} alpha_t={e['alpha_t']:5.2f} ex0809 alpha_t={ex['alpha_t']:5.2f} dd={e['max_drawdown_pct']:.0f} exposure={w.mean():.2f}")
f,t=flows(L,"SPY"); f=f.loc["2006-06-05":]; t=t.loc["2006-06-05":]; rel=(f/t).clip(-0.1,0.1)
sd=rel.rolling(250,min_periods=120).std()
for N in (20,60):
    z=rel.rolling(N).sum()/(sd*np.sqrt(N))
    tim(f"SPY long when flow{N} z<0", (z<0).astype(float).where(z.notna()).dropna())
z5=rel.rolling(5).sum()/(sd*np.sqrt(5))
cap=(z5<-1.5).astype(float).rolling(10).max().where(z5.notna()).dropna()
tim("SPY capitulation: 10d after z5<-1.5", cap)
eup=(z5>1.5).astype(float).rolling(10).max().where(z5.notna()).dropna()
tim("SPY 10d after z5>+1.5 (inflow)", eup)
# sector breadth
F=pd.DataFrame({s:flows(L,s)[0] for s in SEC}).loc["2006-06-05":]; T=pd.DataFrame({s:flows(L,s)[1] for s in SEC}).loc["2006-06-05":]
R=(F/T).clip(-0.2,0.2); SD=R.rolling(250,min_periods=120).std()
Z=R.rolling(20).sum()/(SD*np.sqrt(20))
br=(Z>0).sum(axis=1).where(Z.notna().all(axis=1)).dropna()
tim("long SPY when sector flow breadth<=4", (br<=4).astype(float))
dc=Z[["XLU","XLP","XLV"]].mean(axis=1)-Z[["XLY","XLI","XLF","XLK"]].mean(axis=1); dc=dc.dropna()
tim("long SPY when defensive-cyclical flow>0", (dc>0).astype(float))
# divergence
z20=(rel.rolling(20).sum()/(sd*np.sqrt(20))).dropna(); p20=C["SPY"].pct_change(20).reindex(z20.index)
tim("long SPY when price up & flow out", ((p20>0)&(z20<0)).astype(float))
tim("long SPY when price down & flow out", ((p20<0)&(z20<0)).astype(float))
tim("long SPY when price down & flow in", ((p20<0)&(z20>0)).astype(float))
# predictive regressions for reference (non-overlapping 20d)
fwd=C["SPY"].pct_change(20).shift(-21)
for nm,s in (("spy z20",z20),("breadth",br),("def-cyc",dc)):
    d=pd.concat([s,fwd],axis=1).dropna().iloc[::20]; print(nm,"corr with fwd20 (non-overlap) =",round(d.corr().iloc[0,1],3),"n=",len(d))
