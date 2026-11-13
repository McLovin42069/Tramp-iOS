from base import *
def z(s,n): return (s-s.rolling(n,min_periods=n//2).mean())/s.rolling(n,min_periods=n//2).std()
def pred(x, tk, hs=(1,5,20), lag=1):
    r = C[tk].pct_change(fill_method=None)
    out=[]
    for h in hs:
        f = (C[tk].shift(-(lag+h))/C[tk].shift(-lag)-1)
        d = pd.concat([x,f],axis=1).dropna(); d.columns=["x","f"]
        if len(d)<300: out.append("na"); continue
        ic = d.x.corr(d.f,method="spearman"); n=len(d)/h
        # sub-period ICs
        sub=[d[(d.index.year>=a)&(d.index.year<=b)] for a,b in ((2000,2009),(2010,2013),(2014,2018))]
        ex = d[~d.index.year.isin([2008,2009])]
        out.append(f"h{h}: ic={ic:+.3f} t~{ic*np.sqrt(n):+.1f} ex0809={ex.x.corr(ex.f,method='spearman'):+.3f} sub="+"/".join(f"{s.x.corr(s.f,method='spearman'):+.2f}" if len(s)>100 else "na" for s in sub))
    return " | ".join(out)
if __name__=="__main__":
    print("== JNK premium -> JNK/HYG/SPY/LQD")
    for nm,x in [("raw",P.JNK),("z60",z(P.JNK,60)),("z250",z(P.JNK,250)),("d1",P.JNK.diff()),("d5",P.JNK.diff(5))]:
        for tk in ["JNK","HYG","SPY"]:
            print(nm,tk,pred(x,tk))
    print("== same-day lag0 (not tradable, diagnostic) JNK raw->JNK", pred(P.JNK,"JNK",lag=0))
    # NAV prediction: premium -> next-day NAV change
    nav=S["nav"]
    for f in ["JNK","SPDW","SPEM","FEZ","GXC","CWB","SPIB","SPAB","BWX","SPTL","SPMB"]:
        nr=nav[f].pct_change(fill_method=None).shift(-1); pr=(nav[f]*(1+P[f]/100)).pct_change(fill_method=None)
        d=pd.concat([P[f],nr,pr.shift(-1),pr.shift(-2)],axis=1).dropna(); d.columns=["p","nav1","px1","px2"]
        d=d[(d.nav1.abs()<.15)&(d.px1.abs()<.15)&(d.px2.abs()<.15)]
        print(f, "prem->nextNAV %.3f  prem->next px(t+1, untradable) %.3f  prem->px(t+2, tradable) %.3f"%(d.p.corr(d.nav1,method="spearman"),d.p.corr(d.px1,method="spearman"),d.p.corr(d.px2,method="spearman")))
