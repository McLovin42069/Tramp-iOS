from core import *
# 1 short-horizon: event day signal, H=1,2
ev("ud W1 (event day)",rsum(r,"ud",1),1)
ev("ptrev W1",rmean(r,"ptrev",1),1)
ev("ud W2",rsum(r,"ud",2),2)
ev("ptrev W3",rmean(r,"ptrev",3),2)
# 2 momentum-residualised
for W,h in ((20,5),(20,20),(60,20)):
    ev(f"ud W{W} resid on r20,r250",mom_resid(rsum(r,"ud",W),(20,250)),h)
    ev(f"ptrev W{W} resid on r20,r250",mom_resid(rmean(r,"ptrev",W),(20,250)),h)
# 3 ex-earnings / earnings-only
ne=r[~r.near_earn]; ye=r[r.near_earn]; print("share near earnings",r.near_earn.mean())
for h in (5,20):
    ev("ud W20 ex-earn",rsum(ne,"ud",20),h); ev("ptrev W20 ex-earn",rmean(ne,"ptrev",20),h)
    ev("ptrev W20 earn-only",rmean(ye,"ptrev",20),h)
# 4 up only / down only
up=r[r.ud>0]; dn=r[r.ud<0]
for h in (5,20):
    ev("upgrades count W20",rsum(up,"one",20),h); ev("downgrades count W20 (neg)",-rsum(dn,"one",20),h)
# 5 initiations
ini=r[r.Action=="init"].copy()
pos_=ini.ToGrade.isin(["Buy","Overweight","Outperform","Strong Buy","Positive","Market Outperform","Sector Outperform","Accumulate","Top Pick","Conviction Buy","Outperformer"])
neg_=ini.ToGrade.isin(["Sell","Underweight","Underperform","Reduce","Negative","Strong Sell","Sector Underperform","Market Underperform"])
ini["g"]=np.where(pos_,1.0,np.where(neg_,-1.0,-0.3))
for h in (5,20): ev("initiation grade W20",rsum(ini,"g",20),h)
ev("initiation count W60",rsum(ini,"one",60),20)
print("variants",N[0])
