import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research"); import lib
import pandas as pd, numpy as np
D = lib.load()
C=D["C"]; m=D["meta"]
print(C.shape, C.index[0], C.index[-1])
print(m.groupby(["cls","core"]).size())
for c in m.cls.unique():
    if m[m.cls==c].core.any(): print(c, list(m[m.cls==c].index))
print(m[m.cls=="US Stocks"].group.value_counts())
print(m[m.cls=="Europe Stocks"].group.value_counts())
print(m[m.cls=="Asia Stocks"].group.value_counts())
print(D["cot"].contract.value_counts()); print(D["cot"].head()); print(D["cot"].date.min())
print(C.notna().sum().describe())
