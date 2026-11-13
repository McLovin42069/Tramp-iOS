from base import *
from s4 import alpha, both, one, P, S, sv, FEB
import io, contextlib
vix, v3 = C["^VIX"], C["^VIX3M"]; ts=vix/v3
print("\n\n===== S5")
lev = pd.Series(np.where(C.index < pd.Timestamp("2018-02-28"), 1.0, 0.5), C.index)
for th in [0.86,0.88,0.92]:
    both(f"SVXY if ts<{th}", one("SVXY", ts<th))
both("SVXY w=clip((1-ts)/0.2,0,1)", (((1-ts)/0.2).clip(0,1)).to_frame("SVXY")[S])
both("SVXY if 5d-mean ts<0.9", one("SVXY", ts.rolling(5).mean()<0.9))
print("== carry spread SVXY + VIXM (constant -0.25 VIXY-equivalent)")
u=vix*0+1.0
def SP(wv, wm): return pd.DataFrame({"SVXY":wv/lev,"VIXM":wm})[S]
r1=both(".25 short-front + .5 VIXM", SP(.25*u,.5*u), bench="SPY")
r2=both(".25 short-front + .5 VIXM if ts<1", SP(.25*(ts<1),.5*(ts<1)), bench="SPY")
r3=both(".3 short-front + .4 VIXM", SP(.3*u,.4*u), bench="SPY")
print("== MOVE & TLT")
mv=C["^MOVE"]; tl=C["TLT"].notna()
ev("BH TLT", (mv*0+1.0).to_frame("TLT")[mv.notna().values], bench="TLT")
ev("TLT if MOVE<1y median", (mv<mv.rolling(252).median()).astype(float).to_frame("TLT")[mv.rolling(252).median().notna().values], bench="TLT")
ev("TLT if MOVE>1y median", (mv>mv.rolling(252).median()).astype(float).to_frame("TLT")[mv.rolling(252).median().notna().values], bench="TLT")
ev("TLT w=min(1,80/MOVE)", (80/mv).clip(upper=1).to_frame("TLT")[mv.notna().values], bench="TLT")
