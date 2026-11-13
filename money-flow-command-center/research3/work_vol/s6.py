from base import *
import numpy.linalg as la
def alpha(ret, cols):
    X = R[cols].reindex(ret.index).fillna(0); X.insert(0,"c",1.0)
    b = la.lstsq(X.values, ret.values, rcond=None)[0]; e = ret.values - X.values@b
    se = np.sqrt(e.var()*la.inv(X.values.T@X.values)[0,0]); return b[0]*25200, b[0]/se
vix=C["^VIX"]; rv20 = R["SPY"].rolling(20).std()*np.sqrt(252)*100
mv=C["^MOVE"].ffill(); med=mv.rolling(252,min_periods=200).median(); ok=med.notna().values
ev("TLT if MOVE<1y median", (mv<med).astype(float).to_frame("TLT")[ok], bench="TLT")
ev("TLT if MOVE>1y median", (mv>med).astype(float).to_frame("TLT")[ok], bench="TLT")
ev("TLT w=min(1,80/MOVE)", (80/mv).clip(upper=1).to_frame("TLT")[mv.notna().values], bench="TLT")
tl=C["TLT"].notna().values
for nm,p in [("SPY .6*min(1,15/VIX), TLT .4", pd.DataFrame({"SPY":(0.6*15/vix).clip(upper=0.6),"TLT":0.4})[tl]),
             ("SPY 10/rv20, rest TLT", pd.DataFrame({"SPY":(10/rv20).clip(upper=1),"TLT":1-(10/rv20).clip(upper=1)})[tl]),
             ("SPY min(1,10/rv20) only 2002+", (10/rv20).clip(upper=1).to_frame("SPY")[tl])]:
    r,e=ev(nm,p); print("   alpha vs SPY+TLT %.2f t=%.2f"%alpha(r,["SPY","TLT"]))
    x=r[~r.index.year.isin([2008,2009])]; print("   ex 2008-09: ann %.2f SR %.2f t %.2f ; alpha2 %.2f t=%.2f"%(x.mean()*25200, x.mean()/x.std()*15.87, x.mean()/x.std()*np.sqrt(len(x)), *alpha(x,["SPY","TLT"])))
print("variants", N[0])
