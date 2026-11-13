from base import *
F=pd.DataFrame({t:flows(L,t)[0] for t in SEC}).loc["2006-06-05":]; T=pd.DataFrame({t:flows(L,t)[1] for t in SEC}).loc["2006-06-05":]
rel=(F/T).clip(-0.2,0.2)
sd=rel.rolling(250,min_periods=120).std()
def zN(N): return rel.rolling(N).sum()/(sd*np.sqrt(N))
for N in (10,30,40):
    rep(f"contr z flow{N}", run(xs_pos(-zN(N))))
z=zN(20)
for k in (2,4): rep(f"contr z20 k={k}", run(xs_pos(-z,k=k)))
for rb in (1,10,20): rep(f"contr z20 rebal={rb}", run(xs_pos(-z,rebal=rb)))
# rebal phase (not new variants: same rule, different start day)
for ph in range(1,5):
    rep(f"contr z20 phase{ph}", run(xs_pos(-z.iloc[ph:])))
rep("contr z20 same_close", run(xs_pos(-z),ex="same_close"))
# independence from price reversal
m=C[SEC].pct_change(20).reindex(rel.index)
rep("reversal20 same window", run(xs_pos(-m.where(z.notna()))))
rep("rev20 rank + outflow z20 rank", run(xs_pos((-m.rank(axis=1)-z.rank(axis=1)))))
# flow residual after cross-sectional regression on return
zr=z.sub(z.mean(axis=1),axis=0); mr=m.sub(m.mean(axis=1),axis=0)
b=(zr*mr).sum(axis=1).rolling(250).sum()/(mr**2).sum(axis=1).rolling(250).sum()
print("xs beta of flow z on ret20:", b.describe()[["mean","min","max"]].round(2).to_dict(), "corr", zr.stack().corr(mr.stack()).round(3))
r1=run(xs_pos(-z)); r2=run(xs_pos(-m.where(z.notna())))
print("corr flow-contr vs price-reversal returns", r1.corr(r2).round(3))
# leg decomposition
p=xs_pos(-z); rep("long leg (outflow) minus eqw", run(p.clip(lower=0)- (1/6)*3/9*0+ -1/18+0*p))  # long outflow 3 vs short all 9 equally
rep("eqw minus short leg (inflow)", run(p.clip(upper=0)+1/18+0*p))
