from base import *
r1=ratio(1)
post = ix[ix>="2018-08-01"]
print(len(post), (S.loc[post].notna().sum(axis=1)<100).sum(), D["C"]["AAPL"].loc[post].isna().sum(), D["C"]["SPY"].loc[post].isna().sum())
print(S.loc[post].notna().sum(axis=1)[S.loc[post].notna().sum(axis=1)<300].head(30))
print(r1.median(axis=1).groupby(ix.year).mean())
print(S.notna().sum().describe())
for n in (1,5,20):
    for h in (1,5,20):
        ev(ratio(n), h, f"level_r{n}")
