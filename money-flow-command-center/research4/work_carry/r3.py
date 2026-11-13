from core import *
X = lib4.load_crypto(); earn, known = daily_funding(X); C=X["C"]; O=X["O"]
print("=== CME basis")
for fu,sp,pc in [("BTC=F","BTC-USD","BTCUSDT"),("ETH=F","ETH-USD","ETHUSDT")]:
    d=pd.DataFrame({"F":C[fu],"S":C[sp]}).dropna()["2018":]
    d["prem"]=d.F/d.S-1
    # last Friday of month expiry
    def lastfri(y,m):
        me=pd.Timestamp(y,m,1)+pd.offsets.MonthEnd(0); return me-pd.Timedelta(days=(me.dayofweek-4)%7)
    def exp(t):
        lf=lastfri(t.year,t.month)
        if t>lf:
            n=t+pd.offsets.MonthBegin(1); lf=lastfri(n.year,n.month)
        return lf
    d["exp"]=[exp(t) for t in d.index]; d["dte"]=(d.exp-d.index).dt.days.values
    d["ann"]=d.prem*365/d.dte.clip(lower=5)
    print(fu, "n",len(d), "mean prem %",round(d.prem.mean()*100,3))
    print(" prem% by dte bucket:", d.groupby(pd.cut(d.dte,[-1,3,7,14,21,28,40])).prem.agg(["mean","median","count"]).mul([100,100,1]).round(3).to_dict("index"))
    print(" by year: mean prem%, annualised basis % (dte>=7), perp funding ann %")
    for y,g in d.groupby(d.index.year):
        gg=g[g.dte>=7]
        # regression slope of prem on dte -> per-day decay
        sl=np.polyfit(g.dte,g.prem,1)[0]*365*100
        pf=earn[pc][str(y)].mean()*36500 if str(y) in earn.index.year.astype(str) else np.nan
        print("  ",y, round(g.prem.mean()*100,3), "ann(mean of prem*365/dte):",round(gg.ann.mean()*100,2), "median:",round(gg.ann.median()*100,2),"slope-ann:",round(sl,2), "perp:",round(pf,2))
    # hedged P&L: long spot, short future, weekday closes; remove roll-day splice (first day of new contract)
    r=(d.S.pct_change()-d.F.pct_change()); roll=d.exp!=d.exp.shift(1); r_nr=r.where(~roll)
    # add true roll-day pnl approx: assume zero spread pnl on roll day
    rr=r_nr.fillna(0)["2020":]
    print("  hedged (spot - fut, splice removed) 2020-23: ann% per unit notional",round(rr.mean()*252*100,2),"daily sd% (asynchronous closes!)",round(rr.std()*100,2), "by yr", (rr.groupby(rr.index.year).sum()*100).round(1).to_dict(), "t",round(rr.mean()/rr.std()*np.sqrt(len(rr)),2))
    print("  roll-day raw splice jumps mean %", round((d.F.pct_change()-d.S.pct_change())[roll]["2020":].mean()*100,2), "n", int(roll["2020":].sum()))
