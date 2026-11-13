from base import *
on,dy=lib4.session_returns(L)
me=pd.Series(idx.month,index=idx); last=(me!=me.shift(-1)); last.iloc[-1]=True  # 2018-12-31 is a month end
def off(k): return last.shift(k,fill_value=False)
print("TLT by day relative to last trading day of month (0 = last day)")
for tk in ["TLT","IEF","SHY","LQD","HYG","AGG","ZB=F","ZN=F"]:
    if tk not in C: print(tk,"missing"); continue
    r=R[tk]["2000":].dropna(); row=[]
    for k in range(-5,4):
        c=cmp(r,off(k).reindex(r.index)); row.append(f"{k:+d}:{c['mean_in_bp']:5.1f}({c['t_diff']:4.1f})")
    print(tk,r.index[0].date()," ".join(row))
r=R["TLT"].dropna()
print("TLT last day: overnight", cmp(on["TLT"].dropna(),last.reindex(on["TLT"].dropna().index)), "day", cmp(dy["TLT"].dropna(),last.reindex(dy["TLT"].dropna().index)))
print("^TNX change on last day (bp of yield):", (C["^TNX"].diff()["2002-08":][last["2002-08":]]*100).mean(), tt(C["^TNX"].diff()["2002-08":][last["2002-08":]]), " pre-2002 (1993-2002):", (C["^TNX"].diff()["1993":"2002-07"][last["1993":"2002-07"]]*100).mean(), tt(C["^TNX"].diff()["1993":"2002-07"][last["1993":"2002-07"]]))
print("^TYX:", (C["^TYX"].diff()["2002-08":][last["2002-08":]]*100).mean(), " pre:", (C["^TYX"].diff()["1993":"2002-07"][last["1993":"2002-07"]]*100).mean(), tt(C["^TYX"].diff()["1993":"2002-07"][last["1993":"2002-07"]]))
def strat(tk,mask,c=2.0):
    pos=mask.shift(-1,fill_value=False).astype(float).rename(tk)
    return lib4.daily_strategy(pos,L,c,exec="same_close").loc[R[tk].dropna().index[0]:]
for nm,m in [("last day",last),("last 2 days",last|off(-1)),("last 3 days",last|off(-1)|off(-2)),("day -1 only",off(-1)),("last day + first day short?",None)]:
    if m is None: continue
    for tk in ["TLT","IEF"]:
        for c in (2.0,1.0):
            x=strat(tk,m,c); e=lib4.ts_eval(x,R[tk])
            print(nm,tk,c,ev(x,R[tk]), "worst day",round(x.min()*100,2),"worst month",round(x.resample("ME").sum().min()*100,2))
x=strat("TLT",last); e=lib4.ts_eval(x,R["TLT"]); print(e["by_year_pct"])
ev_=R["TLT"][last.reindex(R["TLT"].index)].dropna(); print("hit rate",(ev_>0).mean(), "n",len(ev_), "top5",ev_.nlargest(5).round(4).to_dict(), "sum top5 share", ev_.nlargest(5).sum()/ev_.sum())
print("by month-of-year bp:", (ev_.groupby(ev_.index.month).mean()*1e4).round(0).to_dict())
