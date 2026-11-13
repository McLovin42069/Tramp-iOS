from common import *
E_ = L["eia_weekly"]
tot = E_[["crude_stocks","gasoline_stocks","distillate_stocks"]].dropna().sum(axis=1)
n=0
def H(sig): return sig.reindex(IX).ffill().fillna(0)
for k in [3,5,10]:
    sg = rel(-np.sign(seas_surprise(tot,k)),"crude_stocks")
    r=ev(f"total surprise k={k} -> USO same_close", H(sg).rename("USO"), bench="USO"); n+=1
    if k==5: base=r; sg5=sg
ev("total surprise k=5 -> USO next_close", H(sg5).rename("USO"), bench="USO", exec="next_close"); n+=1
ev("raw total change sign -> USO", H(rel(-np.sign(tot.diff()),"crude_stocks")).rename("USO"), bench="USO"); n+=1
ev("total surprise k=5 long-only USO", H(sg5).clip(lower=0).rename("USO"), bench="USO"); n+=1
ev("total surprise k=5 short-only USO", H(sg5).clip(upper=0).rename("USO"), bench="USO"); n+=1
ev("total surprise k=5 -> XOP", H(sg5).rename("XOP"), bench="XOP"); n+=1
ev("total surprise k=5 -> CL=F (signal check, roll-contaminated)", H(sg5).rename("CL=F"), bench="CL=F"); n+=1
ev("  same, 2000-2006 only", H(sg5)[:'2006-04-10'].rename("CL=F"), bench="CL=F"); 
ev("total surprise k=5 -> BZ=F (check)", H(sg5).rename("BZ=F"), bench="BZ=F"); n+=1
print(base.groupby(base.index.year).apply(lambda g:(1+g).prod()-1).round(3).to_dict())
# by day since release
p = H(sg5); rel_days = pd.Series(0,index=IX); isrel = sg5.reindex(IX).notna()
dsr = isrel.groupby(isrel.cumsum()).cumcount()   # 0 on release day
g = (p.shift(1)*R["USO"]).dropna(); d = dsr.reindex(g.index)   # return day; d = days since release of the day earning
print(g.groupby(d).agg(['mean','std','count']).assign(t=lambda x:x['mean']/x['std']*np.sqrt(x['count'])).head(7))
# release-day reaction itself (not tradable): sign * USO ret on release day
rr = (sg5*R["USO"].reindex(sg5.index)).dropna(); print("release-day reaction t", rr.mean()/rr.std()*np.sqrt(len(rr)), rr.mean())
# worst month / episodes
m = base.resample('M').apply(lambda g:(1+g).prod()-1); print(m.sort_values().head(5), m.sort_values().tail(8))
print(n)
