import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research4"); import lib4, numpy as np, pandas as pd
exec(open('a1.py').read().split("on,day=")[0])
on,day=lib4.session_returns(L)
C,O,Hh,Ll=L["C"],L["O"],L["H"],L["L"]
vix=C["^VIX"]
def run(name,tk,sig,dsig=None,costs=(0.5,1.0),since=("2005","2010")):
    ix=C[tk].dropna().index
    p=sig.reindex(ix).fillna(0).astype(float).to_frame(tk)
    d=(dsig.reindex(ix).fillna(0).astype(float) if dsig is not None else pd.Series(0.0,index=ix)).to_frame(tk)
    bh=C[tk].pct_change().dropna()
    nights=on[tk].shift(-1).reindex(ix)[p[tk]>0]
    print(f"-- {name} {tk}: nights {int((p[tk]>0).sum())} ({(p[tk]>0).mean()*100:.0f}%), mean night {nights.mean()*1e4:.2f}bp; since2005 {nights['2005':].mean()*1e4:.2f}bp; since2010 {nights['2010':].mean()*1e4:.2f}")
    for c in costs:
        r=lib4.segment_strategy(p,d,L,cost_bps=c); r=r[r.index>=ix[0]]
        show(f"  c={c}",r,bh)
        for st in since: show(f"     since {st}",r[st:],bh)
if __name__=="__main__":
  for tk in ["SPY","QQQ"]:
    c=C[tk]; ret=c.pct_change(); clv=(c-Ll[tk])/(Hh[tk]-Ll[tk])
    run("down day",tk,ret<0)
    run("weak close clv<0.5",tk,clv<0.5)
    run("intraday down C<O",tk,c<O[tk])
    run("VIX>20",tk,vix>20)
    run("VIX>252d median",tk,vix>vix.rolling(252).median())
    run("Mon/Fri close",tk,pd.Series(c.index.dayofweek.isin([0,4]),index=c.index))
    run("below 5d MA",tk,c<c.rolling(5).mean())
    run("down day OR vix>20",tk,(ret<0)|(vix>20))
