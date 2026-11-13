import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research"); import lib, numpy as np, pandas as pd
D = lib.load()
eu = lib.tickers(D, cls="Europe Stocks", core=False); asia = lib.tickers(D, cls="Asia Stocks", core=False)
print(len(eu), len(asia), D["C"].shape, D["C"].index[0], D["C"].index[-1])
m = D["meta"]
print(m.loc[eu+asia].groupby(["cls","group"]).size())
C = D["C"][eu+asia]
print("coverage first valid by group"); print(C.apply(lambda s: s.first_valid_index()).groupby(m.loc[eu+asia,"group"]).agg(["min","max"]))
print("nan frac", C.isna().mean().groupby(m.loc[eu+asia,"group"]).mean())
sh = D["shares"]; cc=[c for c in eu+asia if c in sh.columns]; print("shares cols", len(cc), len(eu+asia)); print(sh[cc].notna().mean().groupby(m.loc[cc,"group"]).mean())
print((sh[cc]-sh[cc].shift(250)).iloc[-1].describe())
V = D["V"][eu+asia]; print("vol zero/nan frac", ((V==0)|V.isna()).mean().groupby(m.loc[eu+asia,"group"]).mean())
r = C.pct_change(fill_method=None); print("abs ret>30%", (r.abs()>0.3).sum().sum(), "zero ret frac", (r==0).mean().groupby(m.loc[eu+asia,"group"]).mean())
