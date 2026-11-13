from base import *
vix=C["^VIX"].reindex(C.index).ffill()
dow=pd.Series(C.index.dayofweek,index=C.index)
Z=pd.Series(0.,index=C.index)
res=[]
def run(name,c,pon,pday=Z,cb=2,bench=False):
    idx=C[c].dropna().index
    pon=pd.Series(pon,index=C.index).reindex(idx).fillna(0.).astype(float).rename(c)
    pday=pd.Series(pday,index=C.index).reindex(idx).fillna(0.).astype(float).rename(c)
    LL={"C":C.loc[idx],"O":O.loc[idx],"V":V.loc[idx]}
    r=lib2.segment_strategy(pon,pday,LL,cost_bps=cb)
    b=C[c].pct_change(fill_method=None) if bench else None
    e=lib2.ts_eval(r,bench=b)
    sub=lambda a,bb: r[a:bb].mean()*252*100
    row=dict(name=name,tk=c,cb=cb,ann=e["ann_return_pct"],t=e["t"],act=e["active_days_pct"],py=e["positive_years"],mdd=e["max_drawdown_pct"],p00_08=sub("2000","2008"),p09_13=sub("2009","2013"),p14_18=sub("2014","2018"))
    if bench: row.update(alpha=e["alpha_ann_pct"],alpha_t=e["alpha_t"],beta=e["beta"])
    res.append(row); return r,e
for c in ["SPY","QQQ","IWM"]:
    cc=C[c].pct_change(fill_method=None)
    A=(cc<0)|dow.isin([0,4])
    med=vix.rolling(252).median()
    run("A & VIX15-25",c,A&(vix>=15)&(vix<25))
    run("A & VIX>=15",c,A&(vix>=15))
    run("A & VIX14-28",c,A&(vix>=14)&(vix<28))
    run("A & VIX17-23",c,A&(vix>=17)&(vix<23))
    run("A & VIX>median252",c,A&(vix>med))
    run("A only",c,A)
    run("cc<0 & VIX15-25",c,(cc<0)&(vix>=15)&(vix<25))
    run("cc<0 & VIX>=15",c,(cc<0)&(vix>=15))
    run("MonFri & VIX15-25",c,dow.isin([0,4])&(vix>=15)&(vix<25))
    run("TueWedThu&cc>=0 & VIX15-25 (complement)",c,(~A)&(vix>=15)&(vix<25))
    v1=vix.shift(1)
    run("B&H skip day VIXprev20-25",c,Z+1,1-((v1>=20)&(v1<25)).astype(float),bench=True)
    run("B&H skip day VIXprev18-28",c,Z+1,1-((v1>=18)&(v1<28)).astype(float),bench=True)
df=pd.DataFrame(res).round(2); print(df.to_string()); print(len(df))
# country/bond/gold gaps: day return by gap bucket
print("\nday-session mean (bp) by own-gap bucket; and corr(gap,day)")
for c in ["EWJ","EWG","EWU","FXI","EEM","EFA","EWZ","EWW","EWH","EWY","TLT","IEF","GLD","XLE","XLF","XLK"]:
    g=on[c]["2001":]; d=day[c]["2001":]
    out=[]
    for lo,hi in [(-1,-0.015),(-0.015,-0.005),(-0.005,0),(0,0.005),(0.005,0.015),(0.015,1)]:
        x=d[(g>=lo)&(g<hi)].dropna(); out.append(f"{x.mean()*1e4:6.1f}({x.mean()/x.std()*np.sqrt(len(x)):4.1f},{len(x)})")
    print(f"{c:4s} corr={g.corr(d):5.2f} "," ".join(out))
