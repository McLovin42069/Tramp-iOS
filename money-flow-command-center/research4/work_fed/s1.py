from base import *
print(idx[0], idx[-1], len(F), F[0], F[-1])
print(pd.Series(1,index=F).groupby(F.year).sum().to_dict())
print("not trading days:", [d.date() for d in Fd if d not in idx])
print("weekday dist:", pd.Series(Fd.dayofweek).value_counts().to_dict())
# sanity: abs moves on fomc days vs others
for s in ["^VIX","^TNX","^IRX","^FVX"]:
    d = C[s].diff().abs() if s!="^VIX" else C[s].pct_change().abs()
    d=d[d.index>="2000"]
    m=pd.Series(d.index.isin(Fd),index=d.index)
    print(s, "abs move fomc", d[m].mean(), "other", d[~m].mean())
# intraday range of SPY
rng=(L["H"]["SPY"]/L["L"]["SPY"]-1)["2000":]
m=pd.Series(rng.index.isin(Fd),index=rng.index)
rel=rng/rng.rolling(20).median().shift(1)
print("rel range fomc",rel[m].mean(),"other",rel[~m].mean())
# flag fomc days with unusually small relative range and compare to neighbours
out=[]
for d in Fd:
    if d in idx:
        i=idx.get_loc(d)
        if i+1 < len(idx):
            w=rel.iloc[max(i-33,0)-0:0] 
            out.append((d.date(), round(rel.get(d,np.nan),2), round(rel.get(idx[i-1],np.nan),2), round(rel.get(idx[i+1],np.nan),2), round(abs(C["^FVX"].diff().get(d,np.nan)),3)))
df=pd.DataFrame(out,columns=["d","rel","prev","next","dFVX"])
print((df.rel>df.prev).mean(), (df.rel>df.next).mean())
print(df[(df.rel<0.8)&((df.prev>1.3)|(df.next>1.3))].to_string())
print([str(d.date()) for d in Fd])
