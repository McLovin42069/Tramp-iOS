from h import *
N[0]=21
# Dual momentum: top-k of risk assets by lb return, only if > BIL; else IEF/BIL
RA = ["SPY","QQQ","IWM","VGK","EWJ","EEM","GLD","DBC","TLT","HYG"]
def dual(lb, k, cash="BIL", RA=RA):
    mom = C[RA]/C[RA].shift(lb)-1; cm = C["BIL"]/C["BIL"].shift(lb)-1
    rk = mom.rank(axis=1, ascending=False)
    sel = (rk<=k) & (mom.sub(cm,axis=0)>0)
    W = sel.astype(float)/k; W[cash] = W.get(cash,0) + 1-W.sum(axis=1)
    return W[mom.notna().all(axis=1)]
for lb in [63,126,252]:
    for k in [1,3]:
        ev(dual(lb,k), f"dual mom lb={lb} top{k} else BIL")
# blended 1/3/6/12m momentum score
def dualblend(k):
    mom = sum(C[RA]/C[RA].shift(l)-1 for l in [21,63,126,252])/4
    cm = sum(C["BIL"]/C["BIL"].shift(l)-1 for l in [21,63,126,252])/4
    rk = mom.rank(axis=1, ascending=False); sel=(rk<=k)&(mom.sub(cm,axis=0)>0)
    W = sel.astype(float)/k; W["BIL"]=1-W.sum(axis=1); return W[mom.notna().all(axis=1)]
ev(dualblend(3), "dual mom blend(1,3,6,12m) top3")
# risk-off switches on SPY (monthly), else IEF or BIL
def sw(on, name, cash="BIL", wm=200):
    W = pd.DataFrame({"SPY": on.astype(float), cash: 1-on.astype(float)}).iloc[wm:]
    return ev(W, name)
for lb in [63,126]:
    cr = (C["HYG"]/C["IEF"]); on = cr > cr.shift(lb)
    sw(on, f"credit HYG/IEF {lb}d mom>0 -> SPY else BIL")
    cg = (C["CPER"]/C["GLD"]); on = cg > cg.shift(lb)
    sw(on, f"copper/gold {lb}d mom>0 -> SPY else BIL")
    on = C["UUP"] < C["UUP"].shift(lb)
    sw(on, f"dollar falling {lb}d -> SPY else BIL")
vix = C["^VIX"]
for th in [20,25]:
    sw(vix < th, f"VIX<{th} -> SPY else BIL")
sw(vix < vix.rolling(252).median()*1.2, "VIX<1.2x 1y median -> SPY else BIL", wm=252)
# composite: fraction of 4 signals on (SPY 12m mom, credit 126, copper/gold 126, VIX<25)
cr = (C["HYG"]/C["IEF"]); cg=(C["CPER"]/C["GLD"])
f = ((C["SPY"]>C["SPY"].shift(252)).astype(float) + (cr>cr.shift(126)) + (cg>cg.shift(126)) + (vix<25))/4
W = pd.DataFrame({"SPY": f, "BIL": 1-f}).iloc[252:]; ev(W, "composite 4-signal fraction SPY/BIL")
# defensive: 60/40 with trend filter per sleeve, gold as third sleeve
A3=["SPY","IEF","GLD"]
for lb in [126,252]:
    on = (C[A3]>C[A3].rolling(lb).mean()); W=on.astype(float)/3; W["BIL"]=1-W.sum(axis=1); ev(W.iloc[lb:], f"SPY/IEF/GLD 1/3 each if >SMA{lb} else BIL")
W = pd.DataFrame(1/3,index=C.index,columns=A3); ev(W.iloc[252:], "static SPY/IEF/GLD 1/3 (ref)")
print("N",N[0])
