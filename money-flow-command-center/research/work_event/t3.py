from cal import *
D = lib.load(); C = D["C"]; V = D["V"]; O=D["O"]
cal = calendar(C.index).reindex(C.index); tr=cal.trading
def ev(W, bench, name, cost=10.0):
    ret = lib.weights_to_returns(W, D, cost); b = C[bench].pct_change(fill_method=None) if bench else None
    e = lib.ts_eval(ret, b); half=len(ret)//2
    print(f"{name:40s} ann={e['ann_return_pct']:5.1f} sh={e['sharpe']:.2f} t={e['t']:.2f} alpha_t={e.get('alpha_t',np.nan):.2f} beta={e.get('beta',np.nan):.2f} h1={ret.iloc[:half].mean()*25200:.1f} h2={ret.iloc[half:].mean()*25200:.1f} yrs={list(e['by_year_pct'].values())}")
    return e
print("== overnight vs intraday (NOT testable in runner)")
for tk in ["SPY","QQQ","IWM"]:
    c,o=C[tk][tr],O[tk][tr]; on=o/c.shift(1)-1; intr=c/o-1
    for nm,x in [("overnight",on),("intraday",intr)]:
        x=x.dropna(); print(tk,nm,f"mean={x.mean()*1e4:.2f}bp ann={x.mean()*25200:.1f}% t={x.mean()/x.std()*np.sqrt(len(x)):.2f} net of 2x1bp={ (x.mean()-2e-4)*25200:.1f}%", {y:round(float(v.sum()*100),1) for y,v in x.groupby(x.index.year)})
print("== month-end rebalancing: last-k-day SPY-TLT vs MTD relative return")
rs=C["SPY"].pct_change(); rb=C["TLT"].pct_change(); rel=np.log1p(rs)-np.log1p(rb)
ym=C.index.to_period("M")
for k in [3,5]:
    pre=rel[cal.tdm_rev< -k-1].groupby(ym[cal.tdm_rev< -k-1]).sum()   # info up to day -(k+2): tradable at -(k+1) close
    post=rel[cal.tdm_rev>= -k].groupby(ym[cal.tdm_rev>= -k]).sum()
    nxt=rel[cal.tdm<=3].groupby(ym[cal.tdm<=3]).sum().shift(-1)
    df=pd.DataFrame({"pre":pre,"post":post,"nxt":nxt}).dropna()
    import scipy.stats as ss
    print(k, "n",len(df),"corr pre/post",ss.pearsonr(df.pre,df.post), "spearman",ss.spearmanr(df.pre,df.post)[:2], "corr pre/next3", ss.pearsonr(df.pre,df.nxt))
    s=-np.sign(df.pre)*df.post; print("  sign strat mean %.2f%% t=%.2f"%(s.mean()*100, s.mean()/s.std()*np.sqrt(len(s))), {y:round(float(v.sum()*100),1) for y,v in s.groupby(s.index.year)})
# as ts strategy: at row t (tdm_rev==-(k+2)), set w = -sign(MTD rel)*0.5 SPY, +sign*0.5 TLT, held on days -k..-1
for k in [3,5]:
    mtd=rel.groupby(ym).cumsum()
    sig=(-np.sign(mtd)).where(cal.tdm_rev==-(k+2))
    # hold from row t through the row two before month end -> returns earned days -k..-1
    hold=(cal.tdm_rev>=-(k+2))&(cal.tdm_rev<=-3)
    s=sig.groupby(ym).ffill().where(hold,0).fillna(0)
    s=s.where(tr).ffill().fillna(0)
    W=pd.DataFrame({"SPY":0.5*s,"TLT":-0.5*s}); ev(W,None,f"rebal last {k}d SPY/TLT L/S")
print("== post-shock SPY")
r=rs[tr]; vol=r.rolling(60).std().shift(1); z=r/vol
for nm,m in [("ret<-2%",r<-0.02),("z<-2",z<-2),("z<-1.5",z<-1.5),("ret>2%",r>0.02),("z>2",z>2)]:
    out=[]
    for h in [1,5,20]:
        f=C["SPY"][tr].shift(-h-1)/C["SPY"][tr].shift(-1)-1; unc=f.mean()
        x=f[m].dropna(); out.append(f"h{h}: {x.mean()*100:.2f}% (unc {unc*100:.2f}%) n={len(x)} t~{(x.mean()-unc)/x.std()*np.sqrt(len(x)/ (1 if h==1 else 2)):.2f}")
    print(nm, " | ".join(out))
