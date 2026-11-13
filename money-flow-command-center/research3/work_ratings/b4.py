from core import *
N[0]=58
x=r[r.currentPriceTarget>0].copy(); x["px"]=pd.MultiIndex.from_arrays([x.usable_date,x.ticker]).map(C.stack().to_dict()); x["up"]=x.currentPriceTarget/x.px
print("median target/price by year:",x.groupby(x.usable_date.dt.year).up.median().round(2).to_dict(), "share >2:",(x.up>2).mean().round(3))
# stale: trading days since last PT/rating event
anyev=panel(r,"one").notna()
rows=pd.DataFrame(np.arange(len(IDX))[:,None]*np.ones(len(US)),index=IDX,columns=US)
last=rows.where(anyev).ffill(); stale=(rows-last).where(C.notna())
for h in (5,20): ev("staleness (days since last event)",stale,h)
# event intensity (attention)
ev("event count W60",rsum(r,"one",60),20)
# latest-per-firm consensus: grade level, dispersion of targets, change in implied upside
G={"Strong Buy":2,"Buy":1,"Overweight":1,"Outperform":1,"Positive":1,"Market Outperform":1,"Sector Outperform":1,"Accumulate":1,"Top Pick":2,"Conviction Buy":2,"Outperformer":1,
   "Sell":-1,"Underweight":-1,"Underperform":-1,"Reduce":-1,"Negative":-1,"Strong Sell":-2,"Sector Underperform":-1,"Market Underperform":-1}
r["grade"]=r.ToGrade.map(G).fillna(0.0).where(r.ToGrade.notna()&(r.ToGrade!=""))
r["lpt"]=np.log(r.currentPriceTarget.where(r.currentPriceTarget>0))
def consensus(col,fn,life=250,minf=3):
    out=pd.DataFrame(np.nan,index=IDX,columns=US)
    for tk,g in r.dropna(subset=[col]).groupby("ticker"):
        p=g.pivot_table(index="usable_date",columns="Firm",values=col,aggfunc="last").reindex(IDX).ffill(limit=life)
        v=fn(p); out[tk]=v.where(p.notna().sum(axis=1)>=minf)
    return out.where(C.notna())
cg=consensus("grade",lambda p:p.mean(axis=1))
disp=consensus("lpt",lambda p:p.sub(p.median(axis=1),axis=0).clip(-0.5,0.5).std(axis=1),life=120)
for h in (5,20):
    ev("consensus grade level",cg,h); ev("target dispersion",disp,h)
ev("consensus grade change 60d",cg-cg.shift(60),20)
# change in implied upside: PT revision minus the stock's own return since that firm's previous target (split-safe)
r=r.sort_values(["ticker","Firm","ts"]); 
pc=C.stack().rename("px"); r["px"]=pd.MultiIndex.from_arrays([r.usable_date,r.ticker]).map(pc.to_dict())
r["px_prev"]=r.groupby(["ticker","Firm"]).px.shift(1); r["gap"]=(IDX.get_indexer(r.usable_date)-pd.Series(IDX.get_indexer(r.groupby(["ticker","Firm"]).usable_date.shift(1).fillna(IDX[0])),index=r.index))
r["ups_chg"]=(r.ptrev-np.log(r.px/r.px_prev)).where(r.gap.between(1,250)).clip(-0.5,0.5)
for W,h in ((20,5),(20,20),(60,20)): ev(f"implied-upside change W{W}",rmean(r,"ups_chg",W),h)
# rolling firm skill: past hit-rate of firm's PT direction on 20d sector-rel fwd return, known only after 22 rows
f20=lib3.fwd_return(D,20,True,US).stack().to_dict()
r["f20"]=pd.MultiIndex.from_arrays([r.usable_date,r.ticker]).map(f20)
r["hit"]=(np.sign(r.ptdir)*r.f20)
rr=r.dropna(subset=["ptdir"]).sort_values("usable_date").copy(); rr=rr[rr.ptdir!=0]
# per-firm expanding mean of hit using only events at least 30 trading rows old
rr["row"]=IDX.get_indexer(rr.usable_date)
sk=np.full(len(rr),np.nan)
for f,g in rr.groupby("Firm"):
    rows_=g.row.values; h_=np.nan_to_num(g.hit.values); cs=np.cumsum(h_); cn=np.arange(1,len(g)+1)
    j=np.searchsorted(rows_,rows_-30,side="right")-1   # last event with row <= row-30
    val=np.where(j>=49,cs[np.clip(j,0,None)]/cn[np.clip(j,0,None)],np.nan)   # need >=50 past calls
    sk[rr.index.get_indexer(g.index)]=val
rr["skill"]=sk
med=rr.groupby("row").skill.transform("median")
rr["skw"]=rr.ptdir*(rr.skill-rr.skill.expanding().median())   # direction weighted by firm's past skill relative to typical
good=rr[rr.skill>rr.skill.expanding().quantile(0.67)]; bad=rr[rr.skill<rr.skill.expanding().quantile(0.33)]
print("skill events",rr.skill.notna().sum(),len(good),len(bad))
for h in (5,20):
    ev("PT dir of top-third-skill firms W20",rsum(good,"ptdir",20),h)
    ev("PT dir of bottom-third-skill firms W20",rsum(bad,"ptdir",20),h)
print("variants",N[0])
