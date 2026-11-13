from core import *
X = lib4.load_crypto(); earn, known = daily_funding(X); C=X["C"]; O=X["O"]
cols=list(earn.columns); N=0
print("=== rotation: weekly (Mondays) top-k by trailing funding, only if > thr")
for k in [7,14]:
  for top in [1,2,3]:
    for thr in [0.0]:
      sig = known.rolling(k).mean()*365
      avail = C[[SPOT[c] for c in cols]].set_axis(cols,axis=1).reindex(sig.index).notna()
      sig = sig.where(avail)
      rk = sig.rank(axis=1, ascending=False)
      W = ((rk<=top)&(sig>thr)).astype(float)/top
      W = W.where(pd.Series(W.index.dayofweek==6,index=W.index),axis=0).ffill().fillna(0)  # decide Sunday close
      N+=1
      show(f"rot k={k} top={top}", carry(X,W,0.5))
      if k==7: show(f"   +basis .5%/side", carry(X,W,0.5,basis=0.005))
      print("     turnover/yr (sum|dW|):", round(W.diff().abs().sum().sum()/4,1))
print("=== equal-weight all six always"); N+=1
W = pd.DataFrame(1/6, index=earn.index, columns=cols).where(earn.notna(),0)
show("EW6 always", carry(X,W,0.5))
print("=== liquidation: largest spot rises (close-to-close) 2020-2023")
for c in SPOT.values():
    p=C[c].dropna()["2020":]
    print(c, {h: f"{(p/p.shift(h)-1).max()*100:.0f}% ({(p/p.shift(h)-1).idxmax().date()})" for h in [1,3,7]}, "intraday open->close max", f"{(C[c]/O[c]-1)['2020':].max()*100:.0f}%")
print("=== negative funding streaks BTC/ETH: worst 30d sum of daily funding (% of notional)")
for c in ["BTCUSDT","ETHUSDT"]:
    s=earn[c].rolling(30).sum(); print(c, round(s.min()*100,2), s.idxmin().date(), " worst day", round(earn[c].min()*100,3), earn[c].idxmin().date(), "neg days share", round((earn[c]<0).mean(),3))
print("=== funding persistence: autocorr of daily funding, and corr(trailing7, next7)")
for c in cols:
    print(c, round(earn[c].autocorr(1),2), round(earn[c].rolling(7).mean().shift(7).corr(earn[c].rolling(7).mean()),2))
print("N",N)
