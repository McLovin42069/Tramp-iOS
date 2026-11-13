from base import *
F=pd.DataFrame({t:flows(L,t)[0] for t in SEC}).loc["2006-06-05":]; T=pd.DataFrame({t:flows(L,t)[1] for t in SEC}).loc["2006-06-05":]
rel=(F/T).clip(-0.2,0.2)
sd=rel.rolling(250,min_periods=120).std()
def zN(N): return rel.rolling(N).sum()/(sd*np.sqrt(N))
def xs_ph(sig,ph,k=3,rebal=5):
    sig=sig.dropna(how="all"); rk=sig.rank(axis=1); n=sig.notna().sum(axis=1)
    pos=((rk.gt(n-k,axis=0)).astype(float)-(rk.le(k)).astype(float))/(2*k); pos[n<9]=0
    keep=np.arange(len(pos))%rebal==ph
    return pos.where(pd.Series(keep,index=pos.index),axis=0).ffill().fillna(0)
for N in (15,20,25):
    rs=[]
    for ph in range(5):
        r=run(xs_ph(-zN(N),ph)); rs.append(r); e=lib2.ts_eval(r); print(N,ph,round(e['t'],2),round(e['ann_return_pct'],2))
    rep(f"z{N} avg of 5 phases", pd.concat(rs,axis=1).mean(axis=1))
