from base import *
s=slice("2000",None); b=R["SPY"][s]
print("== B. FOMC cycle (CMV: day 0 = FOMC day; week0 = days -1..3, week2 = 9..13, week4 = 19..23, week6 = 29..33)")
k=k_since(Fc)
# days until next FOMC (uses full advance calendar incl. corrections)
allF = pd.DatetimeIndex(L["fomc"]).difference(pd.to_datetime(["2003-09-15"])).union(FIX_ADD)
nxt = pd.Series(idx.isin(allF.intersection(idx)),index=idx)
even = k.isin([0,1,2,3, 9,10,11,12,13, 19,20,21,22,23, 29,30,31,32,33]) | flag(Fc,-1)
even=even[s]; r=R["SPY"][s]
print("even weeks", cmp(r,even), subs(r,even))
for w,days in [("w0",[-1,0,1,2,3]),("w1",[4,5,6,7,8]),("w2",range(9,14)),("w3",range(14,19)),("w4",range(19,24)),("w5",range(24,29)),("w6",range(29,34))]:
    m=k.isin([d for d in days if d>=0]) | (flag(Fc,-1) if -1 in days else False)
    m=m[s]; print(w, cmp(r,m), subs(r,m))
for c in (2.0,1.0):
    print("strategy even weeks",c, ev(hold(even.reindex(idx,fill_value=False),"SPY",c), b))
odd=~even
print("odd weeks (complement) raw:", cmp(r,odd))
print("\n== C. post-FOMC conditional on yield move on FOMC day (dovish = ^TNX down; alt ^IRX down, ^FVX down)")
fut={}
for tk in ["SPY","QQQ","TLT","GLD","UUP"]:
    lr=np.log(C[tk]).diff()
    fut[tk]={1:lr.shift(-1), 5:lr.rolling(5).sum().shift(-5)}
for sig in ["^TNX","^FVX","^IRX"]:
    dchg=C[sig].diff().reindex(Fc)
    for tk in ["SPY","QQQ","TLT","GLD","UUP"]:
        row=[]
        for h in (1,5):
            f=fut[tk][h].reindex(Fc)
            dov=f[dchg<0].dropna(); hawk=f[dchg>0].dropna()
            se=np.sqrt(dov.var()/len(dov)+hawk.var()/len(hawk))
            row.append(f"h{h}: dov {dov.mean()*1e4:6.1f}bp (t {tt(dov):5.2f}, n {len(dov)})  hawk {hawk.mean()*1e4:6.1f}bp (t {tt(hawk):5.2f}, n {len(hawk)}) diff t {(dov.mean()-hawk.mean())/se:5.2f}")
        print(sig,tk," | ".join(row))
print("\n rate-change days (|d^IRX| over 5d window around >= 0.15) vs none: SPY FOMC-day return")
irx=C["^IRX"]; chg=(irx.shift(-3)-irx.shift(5)).abs().reindex(Fc)
rr=R["SPY"].reindex(Fc)
for nm,m in [("change",chg>=0.15),("no change",chg<0.15)]:
    x=rr[m]; print(nm,len(x),round(x.mean()*1e4,1),round(tt(x),2))
