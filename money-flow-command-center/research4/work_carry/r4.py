from core import *
X = lib4.load_crypto(); earn, known = daily_funding(X); C=X["C"]; N=0
cols=list(known.columns)
P = C[[SPOT[c] for c in cols]].set_axis(cols,axis=1).reindex(known.index)
R = P.pct_change(fill_method=None)
print("=== funding as sentiment: forward spot returns by trailing-funding bucket (signal known at close D, return from close D)")
for c in ["BTCUSDT","ETHUSDT"]:
  for k in [1,3,7]:
    sig=known[c].rolling(k).mean()*36500
    q=pd.cut(sig,[-1e9,0,5,10,20,40,1e9])
    out={}
    for h in [1,3,7]:
        fwd=P[c].shift(-h)/P[c]-1
        out[h]=fwd.groupby(q,observed=True).mean().mul(100).round(2)
    df=pd.DataFrame(out); df["n"]=q.value_counts()
    print(c,"k=",k); print(df.T.to_string())
    for h in [1,7]:
        fwd=P[c].shift(-h)/P[c]-1; d=pd.concat([sig,fwd],axis=1).dropna()
        print("   rank corr h=",h, round(d.corr(method="spearman").iloc[0,1],3))
print("=== timing rule BTC: hold spot unless trailing funding > hi (crowded longs); 5 bps per trade; vs buy&hold")
bh=R["BTCUSDT"].iloc[1:]
def timing(pos,c="BTCUSDT"):
    p=pos.shift(1).fillna(0); return (p*R[c]-pos.diff().abs().shift(1).fillna(0)*5e-4).iloc[1:]
show("BTC buy&hold", bh)
for k in [3,7]:
    for hi in [20,40]:
        sig=known["BTCUSDT"].rolling(k).mean()*36500; N+=1
        show(f"long unless f{k}>{hi}%", timing((sig<=hi).astype(float)), bh)
    for lo in [0,5]:
        sig=known["BTCUSDT"].rolling(k).mean()*36500; N+=1
        show(f"long only if f{k}<{lo}%", timing((sig<lo).astype(float)), bh)
        N+=1; show(f"long only if f{k}>{lo}% (momentum)", timing((sig>lo).astype(float)), bh)
print("=== cross-sectional: long 2 lowest-funding coins, short 2 highest (perps, weekly, receives funding spread + price spread), 5bps/leg")
for k in [7,14]:
    sig=known.rolling(k).mean().where(P.notna())
    rk=sig.rank(axis=1); n=sig.notna().sum(axis=1)
    W=((rk<=2).astype(float)-(rk.gt(n-2,axis=0)).astype(float))/4
    W=W.where(n>=5,0)
    W=W.where(pd.Series(W.index.dayofweek==6,index=W.index),axis=0).ffill().fillna(0)
    held=W.shift(1).fillna(0)
    price=(held*R.fillna(0)).sum(axis=1); fund=-(held*earn.reindex(W.index).fillna(0)).sum(axis=1)   # long perp pays funding
    cost=W.diff().abs().sum(axis=1).shift(1).fillna(0)*5e-4
    N+=1
    show(f"XS k={k} total", (price+fund-cost).iloc[1:-1]); show("    price part", price.iloc[1:-1]); show("    funding part", fund.iloc[1:-1])
print("N",N)
