from common import *
last = C.apply(lambda s: s.last_valid_index()); first = C.apply(lambda s: s.first_valid_index())
print("ending before last date:", (last<C.index[-1]).sum(), " starting after first:", (first>C.index[0]).sum())
print([t for t in D["C"].columns if t in ("RSP","SPY","IWM","MDY","QQQ")])
dv = np.log((C*V).rolling(120,min_periods=60).mean())
ev("neg log dollar volume 120d", -dv, 20)
ev("neg log dollar volume 120d", -dv, 60)
vol = r.rolling(120).std()
ami = np.log((r.abs()/(C*V).replace(0,np.nan)).rolling(120,min_periods=60).mean())
# amihud orthogonal to dollar volume cross-sectionally
def xres(y,x):
    yd=y.sub(y.mean(axis=1),axis=0); xd=x.where(y.notna()).sub(x.where(y.notna()).mean(axis=1),axis=0)
    b=(yd*xd).sum(axis=1)/(xd**2).sum(axis=1); return yd-xd.mul(b,axis=0)
ev("amihud orth. to dollar volume", xres(ami,dv), 20)
ev("amihud raw returns (no resid)", ami, 20, resid=False)
# universe equal-weight vs SPY to gauge survivorship
ew = r.mean(axis=1); spy = D["C"]["SPY"].pct_change()
for nm,x in (("EW universe",ew),("SPY",spy)): print(nm, {y: round(((1+g).prod()-1)*100,1) for y,g in x.groupby(x.index.year)})
# low-dv quintile vs high-dv quintile raw EW returns
rk = dv.shift(2).rank(axis=1,pct=True)
for nm,m in (("illiquid q",rk<=.2),("liquid q",rk>.8)):
    x=r.where(m).mean(axis=1); print(nm, round(x.mean()*252*100,1), "%/yr")
if "RSP" in D["C"].columns:
    x=D["C"]["RSP"].pct_change(); print("RSP", round(x.mean()*252*100,1), "SPY", round(spy.mean()*252*100,1))
