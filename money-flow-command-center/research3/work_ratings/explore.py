import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research3"); import lib3
import pandas as pd, numpy as np
pd.set_option("display.width",250); pd.set_option("display.max_columns",30)
D=lib3.load_stocks(); r=D["ratings"]
print(r.shape, r.dtypes); print(r.tail(8))
u=r.dropna(subset=["usable_date"]); print(len(u))
print(u.Action.value_counts()); print(u.priceTargetAction.value_counts())
print(u.groupby(u.usable_date.dt.year).size())
print(u.groupby(u.usable_date.dt.year).ticker.nunique())
print(u.ToGrade.value_counts().head(30))
print(u.Firm.value_counts().head(25))
print(u[["currentPriceTarget","priorPriceTarget"]].describe())
print((u.currentPriceTarget>0).mean(), (u.priorPriceTarget>0).mean())
print(u.ts.dt.hour.value_counts().sort_index())
print(D["C"].index[[0,-1]], len(lib3.tickers(D,cls="US Stocks",core=False)))
print(D["earnings"].tail(3)); print(D["meta"].head())
print(u.groupby(["usable_date"]).size().describe())
