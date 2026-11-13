import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research3"); import lib3
import pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
D=lib3.load_stocks(); US=lib3.tickers(D,cls="US Stocks",core=False)
C=D["C"][US]; IDX=C.index
r=D["ratings"].dropna(subset=["usable_date"]).copy()
r=r[r.ticker.isin(US)&r.usable_date.isin(IDX)]
r["ud"]=np.where(r.Action=="up",1.0,np.where(r.Action=="down",-1.0,0.0))
ok=(r.currentPriceTarget>0)&(r.priorPriceTarget>0)
r["ptrev"]=np.where(ok,np.log(r.currentPriceTarget.where(ok,1)/r.priorPriceTarget.where(ok,1)),np.nan)
r.loc[r.ptrev.abs()>0.7,"ptrev"]=np.nan   # split artefacts / typos
r["ptdir"]=np.sign(r.ptrev)
r["one"]=1.0
# earnings flag: usable_date within +-2 trading rows of an earnings usable_date
e=D["earnings"].dropna(subset=["usable_date"]); e=e[e.ticker.isin(US)&e.usable_date.isin(IDX)]
EP=pd.DataFrame(0.0,index=IDX,columns=US)
pos=IDX.get_indexer(e.usable_date); cp={t:i for i,t in enumerate(US)}
A=np.zeros(EP.shape,bool)
for p,t in zip(pos,e.ticker):
    A[max(p-2,0):p+3,cp[t]]=True
EARN=pd.DataFrame(A,index=IDX,columns=US)
r["near_earn"]=A[IDX.get_indexer(r.usable_date),[cp[t] for t in r.ticker]]
def panel(ev,col,agg="sum"):
    p=ev.dropna(subset=[col]).pivot_table(index="usable_date",columns="ticker",values=col,aggfunc=agg)
    return p.reindex(index=IDX,columns=US)
def rsum(ev,col,W):  return panel(ev,col).fillna(0).rolling(W,min_periods=1).sum().where(C.notna())
def rmean(ev,col,W):
    s=panel(ev,col).fillna(0).rolling(W,min_periods=1).sum(); n=panel(ev.dropna(subset=[col]),"one").fillna(0).rolling(W,min_periods=1).sum()
    return (s/n.where(n>0)).fillna(0).where(C.notna())
def mom_resid(sig,looks=(20,)):
    """cross-sectional residual of sig on past-return ranks"""
    out=sig.copy()
    X=[ (C/C.shift(L)-1).rank(axis=1,pct=True)-0.5 for L in looks]
    S=sig.values; res=np.full(S.shape,np.nan)
    for i in range(len(IDX)):
        y=S[i]; xs=np.column_stack([x.values[i] for x in X]+[np.ones(len(US))])
        m=np.isfinite(y)&np.isfinite(xs).all(1)
        if m.sum()<50: continue
        b=np.linalg.lstsq(xs[m],y[m],rcond=None)[0]; res[i,m]=y[m]-xs[m]@b
    return pd.DataFrame(res,index=IDX,columns=US)
N=[0]
rng=np.random.default_rng(0); NOISE=pd.DataFrame(rng.normal(0,1e-6,C.shape),index=IDX,columns=US)
def ev(name,sig,h,step=None,sn=True,quiet=False,**kw):
    N[0]+=1
    step=step if step is not None else (h+1 if h<5 else 5)
    a=lib3.xs_eval(sig,D,h,cols=US,cost_bps=5,step=step,**kw)
    b=lib3.xs_eval(lib3.size_neutral(sig,D),D,h,cols=US,cost_bps=5,step=step,**kw) if sn else {}
    if 't' not in a or (sn and 't' not in b): print(name,h,'too few dates'); return a,b
    if not quiet:
        yrs=a.get("by_year_pct",{}); 
        print(f"{name:42s} H={h:2d} t={a['t']:5.2f} sn_t={b.get('t',np.nan):5.2f} spr={a['spread_pct']:6.3f} net={a['net_spread_pct']:6.3f} sn_net={b.get('net_spread_pct',np.nan):6.3f} h1={a['first_half_pct']:6.3f} h2={a['second_half_pct']:6.3f} n={a['names_per_side']:4.0f} yrs+={sum(v>0 for v in yrs.values())}/{len(yrs)} {list(yrs.values())}")
    return a,b
