from common import *
cp = pd.read_pickle("cp.pkl")
r = C[["TLT","IEF"]].pct_change(fill_method=None).loc["2002-08-01":]
jx = r.index
def flags(dates):
    f = pd.Series(0, jx); d = pd.DatetimeIndex(sorted(set(dates))); d=d[(d>=jx[0])&(d<=jx[-1])]
    loc = np.unique(jx.searchsorted(d)); loc=loc[loc<len(jx)]; f.iloc[loc]=1; return f
auc = flags(cp.auction_date)
auc_long = flags(cp[cp.cls.isin(["10","30"])].auction_date)
# days since last auction day, days to next
def since(f):
    s = pd.Series(np.nan, f.index); last=None
    for i,v in enumerate(f.values):
        if v: last=i
        if last is not None: s.iloc[i]=i-last
    return s
def until(f):
    return since(f[::-1])[::-1]
me = pd.Series(jx.to_period("M"), jx); rank_from_end = me.groupby(me).cumcount(ascending=False)  # 0 = last day
df = pd.DataFrame({"TLT":r.TLT,"IEF":r.IEF,"since":since(auc),"until":until(auc),"sinceL":since(auc_long),"untilL":until(auc_long),"eom":rank_from_end})
df.to_pickle("df.pkl")
def tab(g, lab):
    x = df.groupby(g).agg(n=("TLT","count"), TLT_bp=("TLT",lambda s:s.mean()*1e4), TLT_t=("TLT",lambda s:s.mean()/s.std()*np.sqrt(len(s))), IEF_bp=("IEF",lambda s:s.mean()*1e4), IEF_t=("IEF",lambda s:s.mean()/s.std()*np.sqrt(len(s))))
    print(lab); print(x[x.n>=60].round(2).to_string())
tab(df.since.clip(upper=8),"days since last coupon auction day (0=auction day)")
tab(df.until.clip(upper=8),"days until next coupon auction day")
tab(df.sinceL.clip(upper=10),"days since last 10/30 auction")
tab(df.untilL.clip(upper=10),"days until next 10/30 auction")
tab(df.eom.clip(upper=6),"days from month end (0=last)")
df["me3"]=df.eom<=2; df["post"]=df.since.isin([1,2,3])
tab(["me3","post"],"month-end-3 x post-auction(1..3)")
df["postL"]=df.sinceL.isin([1,2,3]); tab(["me3","postL"],"month-end-3 x post-10/30(1..3)")
for per in [("2002","2008"),("2009","2013"),("2014","2018")]:
    d=df.loc[per[0]:per[1]]; print(per, d.groupby(["me3","post"]).TLT.agg(lambda s: round(s.mean()*1e4,2)).to_dict(), d.groupby("postL").TLT.agg(lambda s: round(s.mean()*1e4,2)).to_dict())
