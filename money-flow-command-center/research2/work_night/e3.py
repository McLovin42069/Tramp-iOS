from base import *
H,Lo=L["H"],L["L"]
vix=C["^VIX"]
res=[]
def run(name,c,pon,pday,start=None):
    idx=C[c].dropna().index
    pon=pd.Series(pon,index=C.index).reindex(idx).fillna(0.).astype(float).rename(c)
    pday=pd.Series(pday,index=C.index).reindex(idx).fillna(0.).astype(float).rename(c)
    LL={"C":C.loc[idx],"O":O.loc[idx],"V":V.loc[idx]}
    row={"name":name,"tk":c}
    for cb in (1,2,5):
        r=lib2.segment_strategy(pon,pday,LL,cost_bps=cb)
        if start: r=r[start:]
        e=lib2.ts_eval(r)
        row[f"ann{cb}"]=e["ann_return_pct"]; row[f"t{cb}"]=e["t"]
        if cb==2: row.update(act=e["active_days_pct"],h1=e["first_half_ann_pct"],h2=e["second_half_ann_pct"],py=e["positive_years"],mdd=e["max_drawdown_pct"],mde=e["mde_ann_pct"])
    res.append(row)
Z=pd.Series(0.,index=C.index); ONE=Z+1
for c in ["SPY","QQQ","IWM","MDY","DIA","XLU","XLK","EEM","EWZ","EWW"]:
    run("plain ON",c,ONE,Z)
run("plain ON 2005+","SPY",ONE,Z,start="2005")
run("plain ON 2005+","QQQ",ONE,Z,start="2005")
for c in ["SPY","QQQ","IWM"]:
    cc=C[c].pct_change(fill_method=None); d=day[c]; g=on[c]
    clv=(C[c]-Lo[c])/(H[c]-Lo[c])
    v=vix.reindex(C.index).ffill()
    dow=pd.Series(C.index.dayofweek,index=C.index)
    run("ON if cc<0",c,cc<0,Z)
    run("ON if cc<-0.5%",c,cc<-0.005,Z)
    run("ON if clv<0.2",c,clv<0.2,Z)
    run("ON if clv<0.3",c,clv<0.3,Z)
    run("ON if cc<0&clv<0.3",c,(cc<0)&(clv<0.3),Z)
    run("ON if VIX 15-25",c,(v>=15)&(v<25),Z)
    run("ON if VIX up>5%",c,v.pct_change()>0.05,Z)
    run("ON if Mon/Fri close",c,dow.isin([0,4]),Z)
    run("ON if (cc<0|MonFri)&VIX15-25",c,((cc<0)|dow.isin([0,4]))&(v>=15)&(v<25),Z)
    run("DAY long if prevday<-1%",c,Z,d.shift(1)<-0.01)
    run("DAY short if prevday>1%",c,Z,-(d.shift(1)>0.01).astype(float))
    run("DAY long if gap<-1%",c,Z,g<-0.01)
    run("DAY short if gap in .3-1%",c,Z,-((g>0.003)&(g<0.01)).astype(float))
    run("B&H skip day if gap .3-1%",c,ONE,1-((g>0.003)&(g<0.01)).astype(float))
    run("B&H skip day if VIXprev 20-25",c,ONE,1-((v.shift(1)>=20)&(v.shift(1)<25)).astype(float))
df=pd.DataFrame(res).round(2); print(df.to_string()); print(len(df))
df.to_csv("e3.csv")
