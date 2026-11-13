from base import *
vix, v3 = C["^VIX"], C["^VIX3M"]
rv20 = R["SPY"].rolling(20).std()*np.sqrt(252)*100
rv60 = R["SPY"].rolling(60).std()*np.sqrt(252)*100
one = lambda col, s: s.to_frame(col)
ev("BH SPY 1993+", one("SPY", vix*0+1.0))
print("-- A inverse vol, SPY, 1993+")
res={}
for c in [10,12,15]:
    res[f"vix{c}"]=ev(f"SPY w=min(1,{c}/VIX)", one("SPY",(c/vix).clip(upper=1)))
for c in [8,10,12]:
    res[f"rv{c}"]=ev(f"SPY w=min(1,{c}/rv20)", one("SPY",(c/rv20).clip(upper=1)))
ev("SPY w=min(1,(12/VIX)^2)", one("SPY",((12/vix)**2).clip(upper=1)))
ev("SPY w=min(1,10/max(rv20,rv60))", one("SPY",(10/np.maximum(rv20,rv60)).clip(upper=1)))
# same vol-matched static benchmark: alpha vs SPY already given. sub-periods
for k in ["vix12","rv10"]:
    r=res[k][0]
    for a,b in [("1993","2001"),("2002","2009"),("2010","2018")]:
        x=r.loc[a:b]; s=R["SPY"].loc[a:b]
        print(k,a,b,"SR %.2f vs SPY %.2f"%(x.mean()/x.std()*15.87, s.mean()/s.std()*15.87))
print("-- same_close with rv (SPY-based, observable pre-close)")
ev("SPY w=min(1,10/rv20) same_close", one("SPY",(10/rv20).clip(upper=1)), exec="same_close")
print("-- SPY/TLT")
tl = C["TLT"].notna()
def mix(ws, wt=None):
    p = pd.DataFrame({"SPY":ws, "TLT":(1-ws) if wt is None else wt})[tl.values]
    return p
ev("static 60/40 SPY/TLT", mix(vix*0+0.6))
w=(12/vix).clip(upper=1); ev("SPY 12/VIX, rest TLT", mix(w))
w=(10/rv20).clip(upper=1); ev("SPY 10/rv20, rest TLT", mix(w))
w=(0.6*15/vix).clip(upper=0.6); ev("SPY .6*min(1,15/VIX), TLT .4", mix(w, vix*0+0.4))
ts=vix/v3
w=(ts<1).astype(float).where(ts.notna()); ev("SPY ts<1 else TLT", mix(w)[ts.notna()[tl].values])
w=(0.6*(ts<1)+0.2*(ts>=1)).where(ts.notna()); ev("60/40 -> 20/80 when ts>=1", mix(w)[ts.notna()[tl].values])
ev("static 60/40 2006+", mix(vix*0+0.6)[ts.notna()[tl].values])
