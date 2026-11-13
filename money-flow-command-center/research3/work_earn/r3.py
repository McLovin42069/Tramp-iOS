from feat import *
E = events()
COLS["ALL"] = ALL; COST["ALL"] = 15
ev(panel(E, "ar2", 40, lag=1), "AS", 20, "ar2 hold40")
ev(panel(E, "ar2", 90, lag=1), "AS", 20, "ar2 hold90")
ev(panel(E, "ar2", 60, lag=1), "AS", 60, "ar2 hold60")
ev(panel(E, "ar2", 60, lag=1), "ALL", 20, "ar2 hold60 all regions")
E["combo"] = E.groupby(E.usable_date.dt.to_period("Q")).ar2.rank(pct=True) + E.groupby(E.usable_date.dt.to_period("Q")).surp_w.rank(pct=True)
ev(panel(E, "combo", 60, lag=1), "AS", 20, "ar2+surprise rank hold60")
ev(panel(E, "combo", 60, lag=1), "ALL", 20, "ar2+surprise rank hold60")
# US: drift among heavily shorted names
print(type(D["short"]), getattr(D["short"], "keys", lambda: None)())
