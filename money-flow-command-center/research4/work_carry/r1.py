from core import *
X = lib4.load_crypto(); earn, known = daily_funding(X)
print(earn.describe().T[["count","mean"]].assign(ann=lambda d:d["mean"]*36500))
print("pos share 8h:", (X["funding"]>0).mean().round(3).to_dict())
ones = lambda cols: pd.DataFrame({c:(1.0/len(cols)) for c in cols}, index=earn.index).where(earn[cols].notna().shift(-1).ffill().fillna(False) | True, 0)
N=0
for c in ["BTCUSDT","ETHUSDT"]:
    for n in [0.5, 2/3]:
        W = ones([c]); N+=1
        show(f"always {c} n={n:.2f}", carry(X,W,n))
show("always BTC n=.5 gross(no rebal)", carry(X,ones(["BTCUSDT"]),0.5,fee=0,rebal=False))
show("always BTC+ETH 50/50 n=.5", carry(X,ones(["BTCUSDT","ETHUSDT"]),0.5)); N+=1
# threshold rules
res={}
for c in ["BTCUSDT","ETHUSDT"]:
  for k in [3,7,14]:
    for thr in [0.0,0.05,0.10]:
        sig = known[c].rolling(k).mean()*365
        W = (sig>thr).astype(float).to_frame(c); N+=1
        for b,tag in [(0,""),(0.005," +basis0.5%/side")]:
            if b and not (k==7): continue
            res[(c,k,thr,b)]=show(f"thr {c} k={k} thr={thr}{tag}", carry(X,W,0.5,basis=b))
            print("     trades/yr:", round(W[c].diff().abs().sum()/4,1))
print("N",N)
