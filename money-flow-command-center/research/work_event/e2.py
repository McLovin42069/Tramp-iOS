import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research"); import lib
import numpy as np, pandas as pd
D = lib.load()
C=D["C"];V=D["V"];O=D["O"]
for d in ["2022-12-23","2022-12-26","2022-12-27","2023-07-03","2023-07-04","2023-07-05","2023-11-23","2023-11-24"]:
    print(d, C.loc[d,"SPY"], O.loc[d,"SPY"], V.loc[d,"SPY"], C.loc[d,"AAPL"], V.loc[d,"AAPL"], C.loc[d,"EWG"])
r=C["SPY"].pct_change()
print((r==0).sum(), (V["SPY"].isna()).sum(), (V["SPY"]==0).sum())
print(r[r==0].index[:70].strftime("%Y-%m-%d").tolist())
