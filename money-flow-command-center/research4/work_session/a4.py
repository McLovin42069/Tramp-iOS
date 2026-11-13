exec(open('a2.py').read().split('if __name__')[0])
def basket(tks,rule,c):
    P=pd.DataFrame({t:rule(t) for t in tks}).reindex(C["SPY"].dropna().index)
    avail=C[tks].reindex(P.index).notna()
    W=(P.fillna(False).astype(float)*avail).div(avail.sum(axis=1).clip(lower=1),axis=0)
    r=lib4.segment_strategy(W,W*0,L,cost_bps=c); return r[r.index>=P.index[0]]
down=lambda t:(C[t].pct_change()<0)
ma5=lambda t:(C[t]<C[t].rolling(5).mean())
both=lambda t:down(t)|ma5(t)
band=lambda t:down(t)&ma5(t)
bh=C["SPY"].pct_change().dropna()
for nm,tks,rule in [("B4 down",["SPY","QQQ","IWM","DIA"],down),("B2 down SPY+QQQ",["SPY","QQQ"],down),("B4 down|ma5",["SPY","QQQ","IWM","DIA"],both),("B4 down&ma5",["SPY","QQQ","IWM","DIA"],band),("B4 always",["SPY","QQQ","IWM","DIA"],lambda t:C[t].notna())]:
    for c in [0.5,1.0,2.0]:
        r=basket(tks,rule,c); e=show(f"{nm} c={c}",r,bh)
        for st in ["2005","2010"]: show(f"    since {st}",r[st:],bh)
        if c==0.5: print("    ",e["by_year_pct"])
