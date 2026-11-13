from base import *
Z=pd.Series(0.,index=C.index)
res=[]
def run(name,cols,pday,cb=2,start=None,show=False):
    cols=list(cols)
    idx=C[cols].dropna(how="all").index
    if start: idx=idx[idx>=start]
    pd_=pday.reindex(idx).fillna(0.)
    LL={"C":C.loc[idx],"O":O.loc[idx],"V":V.loc[idx]}
    r=lib2.segment_strategy(pd_*0,pd_,LL,cost_bps=cb)
    e=lib2.ts_eval(r)
    sub=lambda a,bb: r[a:bb].mean()*252*100
    res.append(dict(name=name,tk="+".join(cols),cb=cb,ann=e["ann_return_pct"],t=e["t"],act=e["active_days_pct"],py=e["positive_years"],mdd=e["max_drawdown_pct"],h1=e["first_half_ann_pct"],h2=e["second_half_ann_pct"],p_08=sub("2000","2008"),p09_13=sub("2009","2013"),p14_18=sub("2014","2018"),mde=e["mde_ann_pct"]))
    if show: print(e["by_year_pct"])
    return r
def sig(c,th,long_only=False):
    g=on[c]
    s=(g>th).astype(float)-(0 if long_only else (g<-th).astype(float))
    return s.rename(c)
for c in ["FXI","EEM"]:
    for th in [0.005,0.01,0.015,0.02]:
        run(f"gap cont th={th}",[c],sig(c,th).to_frame())
    run("gap cont th=0.01 long only",[c],sig(c,0.01,True).to_frame())
    run("gap cont th=0.01 5bps",[c],sig(c,0.01).to_frame(),cb=5)
# other EM / Asia for generality
for c in ["EWJ","EWH","EWY","EWT","EWZ","EWW","EFA","SPY"]:
    run("gap cont th=0.01",[c],sig(c,0.01).to_frame())
# portfolio FXI+EEM half each
P=pd.concat([sig("FXI",0.01)*0.5,sig("EEM",0.01)*0.5],axis=1)
run("gap cont th=0.01 50/50",["FXI","EEM"],P,start="2004-10-08",show=True)
df=pd.DataFrame(res).round(2); print(df.to_string()); print(len(df))
# zero-gap / staleness check and gap vs SPY gap
for c in ["FXI","EEM"]:
    g=on[c].dropna(); print(c,"zero gaps by yr",(g==0).groupby(g.index.year).mean().round(3).to_dict())
    d=day[c]; sg=on["SPY"]; sd=day["SPY"]
    m=(g.abs()>0.01)
    print(" corr gap,day:",g.corr(d)," corr gap, SPYday:",g.corr(sd)," corr SPYgap, day:",sg.corr(d), "corr SPYgap,SPYday",sg.corr(sd))
    # hedged day: c day minus beta*SPY day when signal
    x=(np.sign(g)*(d-sd))[m].dropna(); print(" signed (day - SPYday) on |gap|>1%: mean bp",x.mean()*1e4,"t",x.mean()/x.std()*np.sqrt(len(x)),len(x))
    for a,b in [("2004","2008"),("2009","2013"),("2014","2018")]:
        y=(np.sign(g)*d)[m][a:b].dropna(); print("  ",a,b,"signed day bp",round(y.mean()*1e4,1),"t",round(y.mean()/y.std()*np.sqrt(len(y)),2),len(y))
