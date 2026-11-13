from core import *
N[0]=73
r["lpt"]=np.log(r.currentPriceTarget.where(r.currentPriceTarget>0))
def consensus(col,fn,life=250,minf=3):
    out=pd.DataFrame(np.nan,index=IDX,columns=US)
    for tk,g in r.dropna(subset=[col]).groupby("ticker"):
        p=g.pivot_table(index="usable_date",columns="Firm",values=col,aggfunc="last").reindex(IDX).ffill(limit=life)
        out[tk]=fn(p).where(p.notna().sum(axis=1)>=minf)
    return out.where(C.notna())
f=lambda p:p.sub(p.median(axis=1),axis=0).clip(-0.5,0.5).std(axis=1)
vol=C.pct_change().rolling(60).std()
ev("BENCH realised vol 60d",vol,20)
for life in (60,120,250):
    d=consensus("lpt",f,life=life)
    ev(f"dispersion life{life}",d,20)
    # residual on vol rank and 250d return rank
    S=d.values; res=np.full(S.shape,np.nan); X1=(vol.rank(axis=1,pct=True)-.5).values; X2=((C/C.shift(250)-1).rank(axis=1,pct=True)-.5).values
    for i in range(len(IDX)):
        xs=np.column_stack([X1[i],X2[i],np.ones(len(US))]); m=np.isfinite(S[i])&np.isfinite(xs).all(1)
        if m.sum()<50: continue
        b=np.linalg.lstsq(xs[m],S[i][m],rcond=None)[0]; res[i,m]=S[i][m]-xs[m]@b
    ev(f"dispersion life{life} resid vol+mom",pd.DataFrame(res,index=IDX,columns=US),20)
print("variants",N[0])
