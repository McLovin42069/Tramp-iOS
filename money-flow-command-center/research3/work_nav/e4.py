import warnings; warnings.filterwarnings("ignore")
from base import *; from e2 import z, pred
credit=["JNK","SJNK","CWB","SPIB","SPSB"]
cz=pd.concat([z(P[f],250) for f in credit],axis=1).mean(axis=1,skipna=True)
def show(nm,ret,b):
    e=lib3.ts_eval(ret,bench=C[b].pct_change()); x=lib3.ts_eval(ret[~ret.index.year.isin([2008,2009])],bench=C[b].pct_change())
    print(f"{nm}: t={e['t']:.2f} a_t={e['alpha_t']:.2f} ann={e['ann_return_pct']:.2f} sh={e['sharpe']:.2f} act={e['active_days_pct']:.0f}% yrs={e['positive_years']} halves={e['first_half_ann_pct']:.1f}/{e['second_half_ann_pct']:.1f} | ex0809 t={x['t']:.2f} a_t={x['alpha_t']:.2f}")
for tk in ["HYG","SPY"]:
    f20=(C[tk].shift(-21)/C[tk].shift(-1)-1)
    d=pd.concat([cz,f20,C[tk].pct_change(20)],axis=1).dropna(); d.columns=["z","f","past"]
    print(tk,"fwd20 by z quintile:",(d.groupby(pd.qcut(d.z,5)).f.mean()*100).round(2).values, " ex0809:",(d[~d.index.year.isin([2008,2009])].pipe(lambda q:q.groupby(pd.qcut(q.z,5)).f.mean())*100).round(2).values)
    # control for past 20d return (partial rank corr)
    r=d.rank(); import numpy.linalg as la
    X=np.c_[np.ones(len(r)),r.z,r.past]; b=la.lstsq(X,r.f.values,rcond=None)[0]; print("  partial rank beta z, past:",b[1].round(3),b[2].round(3))
    for thr in (-0.5,-1.0):
        pos=(cz<thr).astype(float).where(cz.notna()).rolling(10,min_periods=1).max()   # hold >=10d after signal
        show(f"long {tk} if creditz250<{thr} (10d hold)", lib3.daily_strategy(pos.rename(tk),L), tk)
    pos=(cz<0.5).astype(float).where(cz.notna()); show(f"long {tk} unless creditz250>0.5", lib3.daily_strategy(pos.rename(tk),L), tk)
# equity sector cross-section on closing premium
sec=[t for t in ['XLK','XLY','XLP','XLF','XLV','XLE','XLI','XLB','XLU','XBI','XOP','XHB','XRT','KRE'] if t in tr]
X=P[sec]; rk=X.rank(axis=1,pct=True); n=X.notna().sum(axis=1)
w=(-(rk-0.5)).where(n>=8); w=w.div(w.abs().sum(axis=1),axis=0)
ret=lib3.daily_strategy(w,L); e=lib3.ts_eval(ret); print("sector XS short-premium daily next_close: t=%.2f ann=%.2f"%(e['t'],e['ann_return_pct']))
ret=lib3.daily_strategy(w,L,cost_bps=0); e=lib3.ts_eval(ret); print("  gross t=%.2f"%e['t'])
X5=X.rolling(5).mean(); rk=X5.rank(axis=1,pct=True); w=(-(rk-0.5)).where(n>=8); w=w.div(w.abs().sum(axis=1),axis=0)[::5]
e=lib3.ts_eval(lib3.daily_strategy(w,L)); print("sector XS 5d-avg premium weekly: t=%.2f ann=%.2f"%(e['t'],e['ann_return_pct']))
print("SPY own prem", pred(P.SPY,"SPY",hs=(1,5)))
# flows combo JNK: discount + redemptions vs discount + creations
flow=(S["so"]["JNK"].diff()*S["nav"]["JNK"]/S["tna"]["JNK"]).shift(1).rolling(5).sum()
zz=z(P.JNK,250); f5=(C.HYG.shift(-6)/C.HYG.shift(-1)-1); f20=(C.HYG.shift(-21)/C.HYG.shift(-1)-1)
d=pd.concat([zz,flow,f5,f20],axis=1).dropna(); d.columns=["z","fl","f5","f20"]
for nm,m in [("disc&redeem",(d.z<-1)&(d.fl<0)),("disc&create",(d.z<-1)&(d.fl>=0)),("prem&redeem",(d.z>1)&(d.fl<0)),("prem&create",(d.z>1)&(d.fl>=0)),("all",d.z==d.z)]:
    s=d[m]; print(nm,len(s),"f5 %.3f%% f20 %.3f%%"%(s.f5.mean()*100,s.f20.mean()*100), "ex0809 f20 %.3f%%"%(s[~s.index.year.isin([2008,2009])].f20.mean()*100))
