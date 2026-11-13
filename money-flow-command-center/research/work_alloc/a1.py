from h import *
base()
A = ["SPY","VGK","EWJ","EEM","IEF","TLT","LQD","HYG","GLD","DBC"]
vol = R[A].rolling(60).std()*np.sqrt(252)
iv = (1/vol); 
def tsmom(lb, cash="BIL", A=A, skip=0, rw="iv"):
    mom = C[A].shift(skip)/C[A].shift(lb)-1
    cm = C["BIL"]/C["BIL"].shift(lb)-1
    on = (mom.sub(cm,axis=0) > 0)
    base_w = iv[A].div(iv[A].sum(axis=1),axis=0) if rw=="iv" else pd.DataFrame(1/len(A),index=C.index,columns=A)
    W = (base_w*on).where(mom.notna())
    W[cash] = 1 - W.sum(axis=1)
    return W.dropna()
for lb in [63,126,189,252]:
    ev(tsmom(lb), f"TSMOM10 iv lb={lb}")
ev(tsmom(252, rw="ew"), "TSMOM10 ew lb=252")
ev(tsmom(126, rw="ew"), "TSMOM10 ew lb=126")
# static risk parity reference
Wrp = iv[A].div(iv[A].sum(axis=1),axis=0).dropna(); ev(Wrp, "static inv-vol 10 (ref)")
# SMA trend on SPY
for n in [100,150,200,250]:
    on = (C["SPY"] > C["SPY"].rolling(n).mean())
    for cash in ["BIL","IEF"]:
        W = pd.DataFrame({"SPY": on.astype(float), cash: (~on).astype(float)}).iloc[n:]
        ev(W, f"SPY>SMA{n} else {cash} monthly")
# vol targeting SPY
for tv in [0.10,0.12,0.15]:
    for win in [20,60]:
        v = spy.rolling(win).std()*np.sqrt(252)
        w = (tv/v).clip(upper=1)
        W = pd.DataFrame({"SPY": w, "BIL": 1-w}).dropna()
        ev(W, f"voltarget SPY tv={tv} win={win} daily", monthly=False)
print("N", N[0])
