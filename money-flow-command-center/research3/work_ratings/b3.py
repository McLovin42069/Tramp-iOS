from core import *
N[0]=39
up=r[r.ud>0]; dn=r[r.ud<0]
# one-sided (noise breaks ties so the other side = random non-event names), q=0.1
for h in (5,20):
    ev("upgrades count W20 vs rest q.1",rsum(up,"one",20)+NOISE,h,q=0.1)
    ev("downgrades W20 (neg) vs rest q.1",-rsum(dn,"one",20)+NOISE,h,q=0.1)
# initiations
ini=r[r.Action=="init"].copy()
pos_=ini.ToGrade.isin(["Buy","Overweight","Outperform","Strong Buy","Positive","Market Outperform","Sector Outperform","Accumulate","Top Pick","Conviction Buy","Outperformer"])
ini["g"]=np.where(pos_,1.0,-1.0)
for h in (5,20): ev("initiation grade(+buy/-other) W60",rsum(ini,"g",60),h)
# against the trend: revision direction x opposite sign of prior 20d sector-relative return (measured before event window)
rel20=lib3.residual(C/C.shift(20)-1,D).shift(5)
u5=rsum(r,"ud",5); p5=rmean(r,"ptrev",5)
contra=(np.sign(u5)!=np.sign(rel20))
for h in (5,20):
    ev("ud W5 against trend only",(u5.where(contra,0)).rolling(1).sum(),h)
    ev("ud W5 with trend only",(u5.where(~contra,0)),h)
u20a=(rsum(r,"ud",1).where(lambda x:x!=0)); 
# cumulative: against-trend events held 20d
rel20b=lib3.residual(C/C.shift(20)-1,D).shift(1)
e1=rsum(r,"ud",1); ag=e1.where(np.sign(e1)!=np.sign(rel20b),0); wi=e1.where(np.sign(e1)==np.sign(rel20b),0)
for h in (5,20):
    ev("ud against-trend, 20d sum",ag.rolling(20,min_periods=1).sum().where(C.notna()),h)
    ev("ud with-trend, 20d sum",wi.rolling(20,min_periods=1).sum().where(C.notna()),h)
# clusters: >=3 distinct firms moving PT same way within 5 days
nf_up=rsum(r[r.ptdir>0].drop_duplicates(["ticker","usable_date","Firm"]),"one",5); nf_dn=rsum(r[r.ptdir<0].drop_duplicates(["ticker","usable_date","Firm"]),"one",5)
cl=((nf_up>=3)&(nf_dn==0)).astype(float)-((nf_dn>=3)&(nf_up==0)).astype(float)
print("cluster days share",(cl!=0).mean().mean())
for h in (5,20): ev("PT cluster>=3 firms/5d, held 20d",cl.rolling(20,min_periods=1).sum().where(C.notna()),h)
# rating clusters >=2 same-direction rating changes in 10d
cu=rsum(up.drop_duplicates(["ticker","usable_date","Firm"]),"one",10); cd=rsum(dn.drop_duplicates(["ticker","usable_date","Firm"]),"one",10)
rc=((cu>=2)&(cd==0)).astype(float)-((cd>=2)&(cu==0)).astype(float)
ev("rating cluster>=2/10d held 40d",rc.rolling(40,min_periods=1).sum().where(C.notna()),20)
# H=60
ev("ud W60",rsum(r,"ud",60),60); ev("ptrev W60",rmean(r,"ptrev",60),60)
print("variants",N[0])
