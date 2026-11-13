from common import *
cp = pd.read_pickle("cp.pkl"); df = pd.read_pickle("df.pkl"); jx=df.index
n=0
# --- weak auctions: bid-to-cover vs trailing 6 same class; tail vs prior close of ^TNX/^TYX (nominal only: |hy - prior yield|<0.5)
cp=cp[cp.auction_date>="2002-08-01"].sort_values("auction_date").copy()
cp["btc_z"]=cp.groupby("cls").bid_to_cover_ratio.transform(lambda s:(s-s.shift(1).rolling(6).mean())/s.shift(1).rolling(6).std())
for cl,y in [("10","^TNX"),("30","^TYX"),("5","^FVX")]:
    m=cp.cls==cl; prev=C[y].shift(1).reindex(jx).reindex(cp.loc[m,"auction_date"],method="ffill").values
    cp.loc[m,"tail"]=cp.loc[m,"high_yield"]-prev
cp.loc[cp.tail.abs()>0.4,"tail"]=np.nan
r=C[["TLT","IEF","SPY"]].pct_change(fill_method=None)
fw={}
for a in ["TLT","SPY"]:
    for h in (1,3,5):
        fw[(a,h)]=(C[a].shift(-h)/C[a]-1)
def fwd(sub,lab):
    d=pd.DatetimeIndex(sub.auction_date.unique()); d=d[d.isin(jx)]
    print(lab,len(d)," ".join(f"{a}{h}d={fw[(a,h)].reindex(d).mean()*1e4:6.1f}bp(t{fw[(a,h)].reindex(d).mean()/fw[(a,h)].reindex(d).std()*np.sqrt(len(d)):5.2f})" for a,h in fw))
L1030=cp[cp.cls.isin(["10","30"])]
fwd(L1030,"all 10/30   "); fwd(L1030[L1030.btc_z<-1],"weak btc z<-1"); fwd(L1030[L1030.btc_z>1],"strong btc z>1")
T=cp[cp.tail.notna()]; print("tail corr w/ same-day yield change is contaminated (prior close vs 13:00) - noted")
fwd(T[T.tail>0.03],"tail>3bp vs prior close"); fwd(T[T.tail<-0.03],"stop-through<-3bp")
allc=cp; fwd(allc[allc.btc_z<-1],"all coupons weak"); fwd(allc[allc.btc_z>1],"all coupons strong")
# as strategies (same_close on auction day, hold 3 days)
def hold(dates,N,asset,sign=1):
    f=pd.Series(0.0,jx); d=pd.DatetimeIndex(dates.unique()); f[d[d.isin(jx)]]=1
    pos=f.rolling(N,min_periods=1).max()*sign
    return lib4.daily_strategy(pos.rename(asset),L,2.0,"same_close")
for lab,sub,sg in [("weak btc -> long TLT 3d",L1030[L1030.btc_z<-1],1),("strong btc -> long TLT 3d",L1030[L1030.btc_z>1],1),("weak all -> long TLT 2d",allc[allc.btc_z<-1],1),("strong all -> long TLT 2d",allc[allc.btc_z>1],1),("weak 10/30 -> long SPY 3d",L1030[L1030.btc_z<-1],1),("strong 10/30 -> long SPY 3d",L1030[L1030.btc_z>1],1)]:
    a="SPY" if "SPY" in lab else "TLT"; N=2 if "2d" in lab else 3
    n+=1; print(line(lab,hold(sub.auction_date,N,a,sg),bh(a)))
# --- tax dates: 15th of Jan/Apr/Jun/Sep/Dec (next business day) ; SPY/IWM/TLT in window [-2,+3]
tx=[]
for y in range(2002,2019):
    for mth in (1,4,6,9,12):
        d=pd.Timestamp(y,mth,15); k=jx.searchsorted(d)
        if k<len(jx): tx.append(k)
tx=np.array(tx)
for a in ["SPY","IWM","TLT"]:
    x=C[a].pct_change(fill_method=None).reindex(jx)
    print("tax", a, " ".join(f"{k:+d}:{x.iloc[tx+k].mean()*1e4:5.1f}({x.iloc[tx+k].mean()/x.iloc[tx+k].std()*np.sqrt(len(tx)):4.1f})" for k in range(-4,6)), "uncond",round(x.mean()*1e4,1))
n+=3
# --- settlement drain: issue dates weighted by size; SPY on big settlement days (top quartile coupon settlement $ / trailing)
a_all=L["auctions"].copy(); a_all["issue_date"]=pd.to_datetime(a_all["issue_date"])
cs=a_all[a_all.security_type!="Bill"].groupby("issue_date").offering_amt.sum()/1e9
cs=cs[cs.index>="2009"]; big=cs[cs>cs.median()].index
for a in ["SPY","TLT","HYG"]:
    x=C[a].pct_change(fill_method=None).reindex(jx); loc=jx.searchsorted(big); loc=loc[loc<len(jx)-3]
    print("big coupon settlement", a, " ".join(f"{k:+d}:{x.iloc[loc+k].mean()*1e4:5.1f}({x.iloc[loc+k].mean()/x.iloc[loc+k].std()*np.sqrt(len(loc)):4.1f})" for k in range(-3,4)))
n+=3
print("n",n)
# --- candidate subperiods
import t4
