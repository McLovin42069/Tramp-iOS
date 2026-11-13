from common import *
n=0
mo = pd.Series(IX.month,index=IX)
def cal(months, etf): return mo.isin(months).astype(float).shift(-1).fillna(0).rename(etf)  # set day before -> same_close legit (calendar)
# monthly mean table (descriptive, counts as 1 look each)
for t in ["UNG","USO","XLE","NG=F","RB=F","HO=F"]:
    r=R[t].dropna(); tb = r.groupby(r.index.month).agg(lambda g: g.mean()/g.std()*np.sqrt(len(g)))
    print(t, ' '.join(f"{v:5.1f}" for v in tb.values)); n+=1
ev("UNG long Sep-Oct... (pre-winter)", cal([9,10],"UNG"), bench="UNG"); n+=1
ev("UNG long Apr-May", cal([4,5],"UNG"), bench="UNG"); n+=1
ev("USO long Feb-Jun (driving season build)", cal([2,3,4,5,6],"USO"), bench="USO"); n+=1
ev("XLE long Feb-Apr", cal([2,3,4],"XLE"), bench="XLE"); n+=1
ev("XLE long Dec-Apr", cal([12,1,2,3,4],"XLE"), bench="XLE"); n+=1
# cross-asset: oil return -> others
cl = R["CL=F"]; uso=R["USO"]
oil = uso.where(uso.notna(), cl)     # signal
for k in [1,5]:
    s = np.sign(C["USO"].pct_change(k))
    ev(f"USO {k}d ret sign -> XLE next (lag)", s.rename("XLE"), bench="XLE"); n+=1
    ev(f"USO {k}d ret sign -> short SPY? (oil up->SPY)", s.rename("SPY"), bench="SPY"); n+=1
# XLE - USO divergence: XLE residual
div = (R["XLE"] - R["USO"]).rolling(5).sum()
ev("XLE-USO 5d divergence -> USO follows XLE", np.sign(div).rename("USO"), bench="USO"); n+=1
ev("XLE-USO 5d divergence -> XLE reverts", (-np.sign(div)).rename("XLE"), bench="XLE"); n+=1
# TIP vs IEF
s = np.sign(C["USO"].pct_change(5)); pos = pd.concat([0.5*s.rename("TIP"), (-0.5*s).rename("IEF")],axis=1)
ev("USO 5d up -> long TIP short IEF", pos); n+=1
# JETS
ev("USO 5d up -> short JETS", (-np.sign(C["USO"].pct_change(5))).rename("JETS"), bench="JETS"); n+=1
# crack spread: (RB+HO)/2 vs CL ratio 20d change -> XLE / XOP
crack = (42*(2*C["RB=F"]+C["HO=F"])/3 - C["CL=F"])
cz = (crack - crack.rolling(60).mean())/crack.rolling(60).std()
ev("crack z60 sign -> XLE", np.sign(cz).rename("XLE"), bench="XLE"); n+=1
ev("crack z60>0 long XLE", (cz>0).astype(float).rename("XLE"), bench="XLE"); n+=1
# oil shock -> SPY following 20 days
sh = C["USO"].pct_change(20); z = sh/sh.rolling(500,min_periods=250).std().shift(1)
ev("oil 20d shock up>1sd -> out of SPY (long otherwise)", (~(z>1)).astype(float).rename("SPY"), bench="SPY"); n+=1
ev("oil 20d crash <-1sd -> long SPY", (z<-1).astype(float).rename("SPY"), bench="SPY"); n+=1
print(n)
