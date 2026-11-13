from base import *
F=pd.DataFrame({t:flows(L,t)[0] for t in SEC}); T=pd.DataFrame({t:flows(L,t)[1] for t in SEC})
F=F.loc["2006-06-05":]; T=T.loc["2006-06-05":]
rel=F/T
print("daily flow/tna abs median", rel.abs().median().round(4).to_dict()); print("max",rel.abs().max().round(2).to_dict())
rel=rel.clip(-0.2,0.2)
R=C[SEC].pct_change()
# 1-3 contrarian flow N
for N in (5,20,60):
    s=-rel.rolling(N).sum()
    rep(f"sec contrarian flow{N}", run(xs_pos(s)))
# 4 z-scored
z=rel.rolling(20).sum()/ (rel.rolling(250,min_periods=120).std()*np.sqrt(20))
rep("sec contrarian flow20 z(own vol)", run(xs_pos(-z)))
# 5-7 price momentum full history
for N in (20,60,250):
    m=C[SEC].pct_change(N).loc["1999-01-01":]
    r=run(xs_pos(m)); rep(f"sec mom{N} 1999+", r); rep(f"sec mom{N} 2006.5+", r, start="2007-07-01")
# 8 momentum + outflow combined rank
m=C[SEC].pct_change(60).reindex(rel.index); f=rel.rolling(60).sum()
rep("mom60 rank + outflow60 rank", run(xs_pos((m.rank(axis=1)-f.rank(axis=1)).where(f.notna()))))
rep("mom60 rank + inflow60 rank", run(xs_pos((m.rank(axis=1)+f.rank(axis=1)).where(f.notna()))))
# 10 flow residual to return (flow not explained by chasing)
m20=C[SEC].pct_change(20).reindex(rel.index); f20=rel.rolling(20).sum()
rep("mom20 rank - flow20 rank", run(xs_pos((m20.rank(axis=1)-f20.rank(axis=1)).where(f20.notna()))))
