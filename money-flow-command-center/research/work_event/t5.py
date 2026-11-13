from cal import *
D = lib.load(); C = D["C"]; V = D["V"]; O=D["O"]
US=lib.tickers(D,cls="US Stocks",core=False); ALL=lib.tickers(D,cls=["US Stocks","Europe Stocks","Asia Stocks"],core=False)
ok=V[ALL]>0
R=C[ALL].pct_change(fill_method=None).where(ok); RR=lib.residual(R,D)
vol=RR.rolling(60,min_periods=40).std().shift(1); z=RR/vol
Vp=V[ALL].where(ok); relv=Vp/Vp.rolling(60,min_periods=40).median().shift(1)
N=[0]
def x(name,sig,h,cols=US,**k):
    N[0]+=1; e=lib.xs_eval(sig,D,h,cols=cols,**k)
    print(f"{name:38s} h={h:2d} spread={e['spread_pct']:6.3f} t={e['t']:5.2f} n={e['n_eff']} ic_t={e['ic_t']:5.2f} net={e['net_spread_pct']:6.3f} turn={e['turnover']:.2f} h1={e['first_half_pct']:.3f} h2={e['second_half_pct']:.3f} nps={e['names_per_side']:.0f} yrs={list(e['by_year_pct'].values())}")
    return e
print("== event study (US): mean fwd residual return after shock, date-clustered t (monthly buckets)")
for nm,m in [("z<-4 & rv>2",(z<-4)&(relv>2)),("z>4 & rv>2",(z>4)&(relv>2)),("z<-3",(z<-3)),("z>3",(z>3)),("z<-3 & rv<1.5",(z<-3)&(relv<1.5)),("z>3 & rv<1.5",(z>3)&(relv<1.5))]:
    out=[]
    for h in [1,5,20,60]:
        f=lib.fwd_return(D,h,True,US); e=f.where(m[US]).stack()
        bm=e.groupby(e.index.get_level_values(0).to_period("M")).mean()
        by=e.groupby(e.index.get_level_values(0).year).mean()
        out.append(f"h{h}: {e.mean()*100:5.2f}% n={len(e)} t_m={bm.mean()/bm.std()*np.sqrt(len(bm)):.2f} pos_yrs={(by>0).sum()}/{len(by)}")
    print(f"{nm:16s}"," | ".join(out)); N[0]+=4
for un,cols in [("US",US),("ALL",ALL)]:
    print("=====",un)
    x("relvol 1d",relv,20,cols); x("relvol 5d avg",relv.rolling(5).mean(),20,cols); x("relvol 5d avg",relv.rolling(5).mean(),5,cols)
    on=(O[ALL]/C[ALL].shift(1)-1).where(ok); intr=(C[ALL]/O[ALL]-1).where(ok)
    x("overnight 20d sum",on.rolling(20,min_periods=15).sum(),20,cols); x("intraday 20d sum",intr.rolling(20,min_periods=15).sum(),20,cols)
    x("overnight-intraday 20d",(on-intr).rolling(20,min_periods=15).sum(),20,cols)
    x("overnight gap 1d z",lib.residual(on,D)/vol,5,cols)
    # PEAD proxy: sign & size of most recent |z|>3 high-volume day within 60d, else 0 (plus tiny tiebreak)
    evz=z.where((z.abs()>3)&(relv>1.5)).ffill(limit=60).fillna(0)+1e-6*z.rolling(60).sum().fillna(0)
    x("last shock (|z|>3,rv>1.5) 60d",evz,20,cols)
print("N",N[0])
