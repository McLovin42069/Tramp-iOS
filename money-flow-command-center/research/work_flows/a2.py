from common import *
print((fl_raw.abs()>0.2).sum().sort_values().tail(12).to_dict())
# SPY 60d flow by sub-period
s = FLP["SPY"].rolling(60).sum()
for a,b in [("2006","2007-12-31"),("2008","2009-12-31"),("2010","2012-12-31"),("2013","2016-11-01"),("2016-11-14","2019-12-31"),("2020","2023-12-31")]:
    print(a, pred(s, start=a, end=b, hs=(5,20)))
print("ex 2008-09 pre2016:", pred(s.where(~s.index.year.isin([2008,2009])), end="2016-11-01"))
# cross-section among equity funds, long NAV history
grp = {c:"sect" for c in SECT}; grp.update({c:"ind" for c in IND})
for c in ['SPY','DIA','MDY','SPYG','SPYV','SPMD','SPSM','SPYD','SDY','RWR']: grp[c]="broad"
for c in ['SPDW','SPEM','FEZ','GXC','SPEU','GNR']: grp[c]="intl"
DE = mkD(EQ, grp)
r = navc[EQ]
def rk(x): return x.rank(axis=1, pct=True)
X = {}
for w in (5, 20, 60):
    f = FLP[EQ].rolling(w, min_periods=w//2).sum()
    X[f"flow{w}"] = f
    X[f"zflow{w}"] = z(f)
X["diverg60"] = rk(r/r.shift(60)-1) - rk(X["flow60"])     # price up, money leaving -> high
X["diverg20"] = rk(r/r.shift(20)-1) - rk(X["flow20"])
X["mom60_ctrl"] = r/r.shift(60)-1
for k, sg in X.items():
    for h in (5, 20):
        for nm, kw in [("long", {}), ("pre16", {"end":"2016-11-01"}), ("disc", {"start":"2016-11-14"})]:
            e = lib.xs_eval(sg, DE, h, min_names=20, **kw)
            print(f"{k:11s} h{h:2d} {nm:5s} spread {e['spread_pct']:+.3f} t {e['t']:+.2f} net {e['net_spread_pct']:+.3f} n/side {e['names_per_side']:.1f}", end=" | ")
        print()
