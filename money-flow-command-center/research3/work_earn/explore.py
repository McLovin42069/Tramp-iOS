import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research3"); import lib3
import numpy as np, pandas as pd
D = lib3.load_stocks()
E = D["earnings"]; print(E.head(10)); print(E.dtypes); print(len(E))
m = D["meta"]; print(m.cls.value_counts())
E = E.merge(m[["cls"]], left_on="ticker", right_index=True, how="left")
u = E.dropna(subset=["usable_date"])
print(u.groupby("cls").size())
print(u.groupby(["cls", u.usable_date.dt.year]).size().unstack(0))
print(u.groupby("cls")[["eps_est","eps_rep","surprise_pct"]].apply(lambda x: x.notna().mean()))
print(u.surprise_pct.describe(percentiles=[.01,.05,.25,.5,.75,.95,.99]))
print(E.ts.dt.hour.value_counts().sort_index())
# events per ticker per year
print(u.groupby(["cls","ticker"]).size().groupby("cls").describe())
print(D["C"].index[[0,-1]], D["C"].shape)
print(E[E.ticker=="AAPL"].tail(12))
print(E[E.eps_rep.isna()].shape, E.ts.max())
