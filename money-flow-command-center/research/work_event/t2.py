from cal import *
D = lib.load(); C = D["C"]; V = D["V"]
cal = calendar(C.index); N=[0]
def run(name, f, tk="SPY", bench=None, cost=10.0, show=True):
    N[0]+=1
    W = cal_weights(C.index, f, tk); ret = lib.weights_to_returns(W, D, cost)
    b = C[bench or tk].pct_change(fill_method=None)
    e = lib.ts_eval(ret, b)
    tim = (W[tk].shift(2) > 0).mean()
    r = C[tk].pct_change(); tr = cal.trading.reindex(C.index); m = f(cal).reindex(C.index).fillna(False) & tr
    a, o = r[m], r[tr & ~m]
    dt = (a.mean()-o.mean())/np.sqrt(a.var()/len(a)+o.var()/len(o))
    half = len(ret)//2; h1 = ret.iloc[:half].mean()*252*100; h2 = ret.iloc[half:].mean()*252*100
    if show: print(f"{name:34s} {tk:5s} tim={tim:.2f} in={a.mean()*1e4:6.1f}bp out={o.mean()*1e4:5.1f}bp diff_t={dt:5.2f} | net ann={e['ann_return_pct']:5.1f} sh={e['sharpe']:.2f} t={e['t']:.2f} beta={e['beta']:.2f} alpha_t={e['alpha_t']:.2f} bsh={e['bench_sharpe']:.2f} h1={h1:.1f} h2={h2:.1f} yrs={list(e['by_year_pct'].values())}")
    return e
print("== turn of month")
for tk in ["SPY","QQQ","IWM"]:
    run("TOM -1..+3", lambda c: (c.tdm_rev==-1)|(c.tdm<=3), tk)
for nm,f in [("TOM -1..+2", lambda c: (c.tdm_rev==-1)|(c.tdm<=2)), ("TOM -2..+3", lambda c: (c.tdm_rev>=-2)|(c.tdm<=3)), ("TOM -1..+4", lambda c: (c.tdm_rev==-1)|(c.tdm<=4)),("TOM +1..+3", lambda c: (c.tdm<=3)),("TOM -4..-1", lambda c: (c.tdm_rev>=-4))]:
    run(nm,f)
print("== by trading day of month (SPY mean bp, t)")
r=C["SPY"].pct_change(); x=pd.DataFrame({"r":r,"tdm":cal.tdm.reindex(C.index),"rev":cal.tdm_rev.reindex(C.index)}).dropna()
g=x.groupby("tdm").r.agg(["mean","std","count"]); g["t"]=g["mean"]/g["std"]*np.sqrt(g["count"]); g["mean"]*=1e4; print(g.round(2).T.to_string())
g=x.groupby("rev").r.agg(["mean","std","count"]); g["t"]=g["mean"]/g["std"]*np.sqrt(g["count"]); g["mean"]*=1e4; print(g.tail(8).round(2).T.to_string())
for tk in ["TLT","IEF","LQD","HYG"]:
    r=C[tk].pct_change(); x=pd.DataFrame({"r":r,"tdm":cal.tdm.reindex(C.index),"rev":cal.tdm_rev.reindex(C.index)}).dropna()
    g=x.groupby("rev").r.agg(["mean","std","count"]); g["t"]=g["mean"]/g["std"]*np.sqrt(g["count"]); print(tk,"rev",(g["mean"].tail(6)*1e4).round(1).tolist(), g.t.tail(6).round(2).tolist())
    g=x.groupby("tdm").r.agg(["mean","std","count"]); g["t"]=g["mean"]/g["std"]*np.sqrt(g["count"]); print(tk,"tdm",(g["mean"].head(6)*1e4).round(1).tolist(), g.t.head(6).round(2).tolist())
print("== day of week")
for d in range(5): run(f"DOW {d}", lambda c,d=d: c.dow==d)
print("== holiday")
run("pre-holiday", lambda c: c.pre_hol==True); run("post-holiday", lambda c: c.post_hol==True)
print("== halves / opex / months")
run("first half (tdm<=10)", lambda c: c.tdm<=10); run("second half", lambda c: c.tdm>10)
run("opex week", lambda c: c.opex_week==True); run("Nov-Apr", lambda c: c.month.isin([11,12,1,2,3,4]))
print("== bonds month end")
for tk in ["TLT","IEF"]:
    run("last 3 days", lambda c: c.tdm_rev>=-3, tk); run("last 5 days", lambda c: c.tdm_rev>=-5, tk)
print("N",N[0])
