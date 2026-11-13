from common import *
a = L["auctions"].copy(); a["issue_date"]=pd.to_datetime(a["issue_date"])
cp = a[a.security_type!="Bill"].copy()
def yrs(s):
    import re
    m=re.search(r"(\d+)-Year",s); y=int(m.group(1)) if m else 0
    m2=re.search(r"(\d+)-Month",s); return y+(int(m2.group(1))/12 if m2 else 0)
cp["mat"]=cp.security_term.map(yrs)
cp["cls"]=np.where(cp.mat>19,"30",np.where(cp.mat>8,"10",np.where(cp.mat>6,"7",np.where(cp.mat>4,"5",np.where(cp.mat>2.5,"3","2")))))
print(cp.groupby("cls").size(), cp[cp.auction_date>="2003"].groupby([cp.auction_date.dt.year,"cls"]).size().unstack().tail(8))
print(cp[cp.cls.isin(["10","30"])].tail(12).to_string())
cp.to_pickle("cp.pkl")
r = C[["TLT","IEF","SPY"]].pct_change(fill_method=None)
pos_of = pd.Series(np.arange(len(ix)), ix)
def study(dates, lab, start="2002-08-01"):
    dates = pd.DatetimeIndex(sorted(set(dates))); dates = dates[(dates>=start)]
    loc = ix.searchsorted(dates)   # first trading day >= date
    out=[]
    for k in range(-6,7):
        j = loc+k; j=j[(j>=0)&(j<len(ix))]
        x = r.iloc[j]
        out.append((k, len(j), x.TLT.mean()*1e4, x.TLT.mean()/x.TLT.std()*np.sqrt(x.TLT.count()), x.IEF.mean()*1e4, x.IEF.mean()/x.IEF.std()*np.sqrt(x.IEF.count())))
    print(lab); print(pd.DataFrame(out,columns=["k","n","TLT_bp","t","IEF_bp","t"]).round(2).to_string(index=False))
print("uncond TLT bp/day", r.TLT.mean()*1e4, "IEF", r.IEF.mean()*1e4)
study(cp[cp.cls=="10"].auction_date, "10Y auctions (k=0 auction day)")
study(cp[cp.cls=="30"].auction_date, "30Y auctions")
study(cp[cp.cls.isin(["10","30"])].auction_date, "10Y+30Y")
study(cp[cp.cls.isin(["10","30"])&(cp.auction_date>="2009")].auction_date, "10Y+30Y 2009+", "2009")
study(cp[cp.cls.isin(["10","30"])].issue_date, "10/30 issue (settlement) dates")
study(cp[cp.cls.isin(["2","5","7"])].auction_date, "2/5/7Y auctions")
