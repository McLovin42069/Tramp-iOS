from base import *
import numpy.linalg as la
def alpha(ret, cols):
    X = R[cols].reindex(ret.index).fillna(0); X.insert(0,"c",1.0)
    b = la.lstsq(X.values, ret.values, rcond=None)[0]; e = ret.values - X.values@b
    se = np.sqrt(e.var()*la.inv(X.values.T@X.values)[0,0]); return b[0]*25200, b[0]/se, b[1:]
vix, v3 = C["^VIX"], C["^VIX3M"]; ts=vix/v3
rv20 = R["SPY"].rolling(20).std()*np.sqrt(252)*100
sv = C["SVXY"].notna(); S=sv.values
FEB = pd.to_datetime(["2018-02-05","2018-02-06"])
def both(name, p, bench="SPY"):
    r,e = ev(name, p, bench=bench)
    N[0]-=1
    r2,e2 = ev("   ...excl 2018-02-05/06", p, bench=bench, excl=FEB)
    print("   by year", e["by_year_pct"], " alpha vs SPY+TLT: %.2f t=%.2f"%alpha(r,["SPY","TLT"])[:2])
    return r
one = lambda col, s: s.astype(float).to_frame(col)[S]
print("== SVXY alone, full size")
both("BH SVXY", one("SVXY", sv))
for th in [0.9,0.95,1.0]:
    both(f"SVXY if VIX/VIX3M<{th}", one("SVXY",(ts<th)))
both("SVXY if VIX9D<VIX<VIX3M", one("SVXY",(C["^VIX9D"]<vix)&(vix<v3)))
both("SVXY if VIX>rv20+2 & ts<1", one("SVXY",(vix>rv20+2)&(ts<1)))
both("SVXY if ts<1 & VVIX<100", one("SVXY",(ts<1)&(C["^VVIX"]<100)))
print("== realistic sizes: SPY/TLT/SVXY")
def P(ws, wt, wv): return pd.DataFrame({"SPY":ws,"TLT":wt,"SVXY":wv})[S]*1.0
u = vix*0+1.0
both("50/50 SPY/TLT (2011-10+)", P(.5*u,.5*u,0*u))
both("45/45/10 static SVXY", P(.45*u,.45*u,.10*u))
both("40/40/20 static SVXY", P(.4*u,.4*u,.2*u))
c=(ts<0.95)*1.0
both("45/45 + 10 SVXY if ts<.95 (else cash)", P(.45*u,.45*u,.10*c))
both("40/40 + 20 SVXY if ts<.95 (else cash)", P(.4*u,.4*u,.2*c))
c=(ts<1.0)*1.0
both("45/45 + 10 SVXY if ts<1", P(.45*u,.45*u,.10*c))
# SVXY replacing equity: 10% SVXY ~ 35-40% SPY beta
both("0 SPY /80 TLT /20 SVXY if ts<1", P(0*u,.8*u,.2*c))
# vol-targeted SVXY: weight = min(.2, .2*15/VIX)
both("45/45 + min(.1,.1*13/VIX) SVXY", P(.45*u,.45*u,(.1*13/vix).clip(upper=.1)))
