from base import *
def st(x):
    x=x.dropna(); 
    return f"n={len(x):5d} mean={x.mean()*1e4:6.2f}bp t={x.mean()/x.std()*np.sqrt(len(x)):5.2f}" if len(x)>30 else "n<30"
# decades
for c in ["SPY","QQQ","IWM","MDY","DIA","XLU","EEM","EWZ","EWW","XLK","TLT","GLD","HYG","LQD","VTV"]:
    o=on[c].dropna(); d=day[c].reindex(o.index)
    per=pd.cut(o.index.year,[1990,1999,2004,2009,2014,2018])
    print(c, "ON bp/day:", o.groupby(per,observed=True).mean().mul(1e4).round(2).to_dict().values(), "DAY:", d.groupby(per,observed=True).mean().mul(1e4).round(2).to_dict().values())
vix=C["^VIX"]
for c in ["SPY","QQQ","IWM","MDY"]:
    print("=====",c)
    o=on[c]; d=day[c]; cc=C[c].pct_change(fill_method=None)
    nxt=o.shift(-1)  # overnight following close t
    ok=C[c].notna()
    print("all            ",st(nxt[ok]))
    print("day<0          ",st(nxt[d<0])); print("day>0          ",st(nxt[d>0]))
    print("day<-1%        ",st(nxt[d<-0.01])); print("day>1%         ",st(nxt[d>0.01]))
    print("cc<0           ",st(nxt[cc<0])); print("cc<-1%         ",st(nxt[cc<-0.01]))
    v=vix.reindex(o.index)
    for lo,hi in [(0,15),(15,20),(20,25),(25,35),(35,200)]:
        print(f"VIX {lo}-{hi}     ",st(nxt[(v>=lo)&(v<hi)&ok]))
    print("VIX up >5%     ",st(nxt[(v.pct_change()>0.05)&ok])); print("VIX dn         ",st(nxt[(v.pct_change()<0)&ok]))
    ma=C[c].rolling(200).mean()
    print("below 200d     ",st(nxt[C[c]<ma])); print("above 200d     ",st(nxt[C[c]>ma]))
    for w in range(5): print("weekday close",w,st(nxt[(o.index.dayofweek==w)&ok]))
    # close location in range
    clv=(C[c]-L["L"][c])/(L["H"][c]-L["L"][c])
    print("close in low 20% of range",st(nxt[clv<0.2])); print("close in top 20%",st(nxt[clv>0.8]))
    # day session conditional on gap
    print("-- day session | gap")
    for lo,hi in [(-1,-0.01),(-0.01,-0.003),(-0.003,0),(0,0.003),(0.003,0.01),(0.01,1)]:
        print(f"gap {lo}..{hi}",st(d[(o>=lo)&(o<hi)]))
    print("day | prev day<-1%",st(d[d.shift(1)<-0.01])); print("day | prev day>1%",st(d[d.shift(1)>0.01]))
    for lo,hi in [(0,15),(15,20),(20,25),(25,35),(35,200)]:
        print(f"day | VIX(prev) {lo}-{hi}",st(d[(v.shift(1)>=lo)&(v.shift(1)<hi)&ok]))
