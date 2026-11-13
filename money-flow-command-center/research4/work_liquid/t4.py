from common import *
import json
cp = pd.read_pickle("cp.pkl"); df = pd.read_pickle("df.pkl"); jx=df.index
def flags(dates):
    f = pd.Series(0, jx); d = pd.DatetimeIndex(sorted(set(dates))); d=d[(d>=jx[0])&(d<=jx[-1])]
    loc = np.unique(jx.searchsorted(d)); loc=loc[loc<len(jx)]; f.iloc[loc]=1; return f
def since(f):
    s = pd.Series(np.nan, f.index); last=None
    for i,v in enumerate(f.values):
        if v: last=i
        if last is not None: s.iloc[i]=i-last
    return s
def rule(classes, N, asset, skip_auc=True, start=None):
    sub = cp[cp.cls.isin(classes)]
    if start: sub=sub
    f = flags(sub.auction_date); s = since(f)
    allf = flags(cp.auction_date)
    pos = ((s>=0)&(s<=N-1)).astype(float)
    if skip_auc: pos = pos*(1-f.shift(-1).fillna(0))     # tomorrow is an auction day of the same set -> stay out
    return lib4.daily_strategy(pos.rename(asset), L, 2.0, "same_close")
ALL=["2","3","5","7","10","30"]
n=0
for asset in ["TLT","IEF"]:
    b=bh(asset)
    for nm,cl in [("all",ALL),("10/30",["10","30"]),("5+",["5","7","10","30"]),("2/5/7",["2","5","7"])]:
        for N in (1,2,3):
            if asset=="IEF" and N!=2: continue
            r=rule(cl,N,asset); n+=1
            print(line(f"{asset} post {nm} N={N}", r, b))
r=rule(ALL,2,"TLT",skip_auc=False); n+=1; print(line("TLT all N=2 no-skip",r,bh("TLT")))
# month-end comparisons
me3=(df.eom<=3)&(df.eom>=1)  # pos on days eom 3..1 earns eom 2..0
r=lib4.daily_strategy(me3.astype(float).rename("TLT"),L,2.0,"same_close"); n+=1; print(line("TLT month-end last3",r,bh("TLT")))
f=flags(cp.auction_date); s=since(f)
post=((s>=0)&(s<=1)).astype(float)*(1-f.shift(-1).fillna(0))
earn_me = (df.eom.shift(-1)<=2)
r=lib4.daily_strategy((post*(~earn_me)).rename("TLT"),L,2.0,"same_close"); n+=1; print(line("TLT post all N=2 EXCL month-end3",r,bh("TLT")))
r=lib4.daily_strategy(((1-post)*earn_me).rename("TLT"),L,2.0,"same_close"); n+=1; print(line("TLT month-end3 EXCL post",r,bh("TLT")))
r=lib4.daily_strategy(((post+earn_me)>0).astype(float).rename("TLT"),L,2.0,"same_close"); n+=1; print(line("TLT post N=2 OR month-end3",r,bh("TLT")))
# mirror: long TLT all other days
r=lib4.daily_strategy((1-post).rename("TLT"),L,2.0,"same_close"); n+=1; print(line("MIRROR TLT not-post",r,bh("TLT")))
# long/short: long post, short auction days
ls = post - f.shift(-1).fillna(0)*0.0
sh = post - (f.shift(-1).fillna(0))   # short over auction days
r=lib4.daily_strategy(sh.clip(-1,1).rename("TLT"),L,2.0,"same_close"); n+=1; print(line("TLT long post / short auction days",r,bh("TLT")))
best=rule(ALL,2,"TLT"); e=ev(best,bh("TLT")); print(json.dumps(e,indent=0)); print("worst day",best.min(),best.idxmin(),"worst month",best.resample("ME").apply(lambda g:(1+g).prod()-1).min())
print("n",n)
