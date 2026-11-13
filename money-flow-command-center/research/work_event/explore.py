import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research"); import lib
import numpy as np, pandas as pd
D = lib.load()
C=D["C"]; m=D["meta"]
print(C.shape, C.index[0], C.index[-1])
print(m.groupby(["cls","core"]).size())
print(m[m.core][["name","cls","group"]].to_string())
for t in ["SPY","QQQ","IWM","TLT","IEF"]:
    if t in C: print(t, C[t].first_valid_index(), C[t].notna().sum())
# index weekday check
print(pd.Series(C.index.dayofweek).value_counts())
print(C["SPY"].isna().sum() if "SPY" in C else None)
