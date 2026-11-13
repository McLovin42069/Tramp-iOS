from base import *
print(P.shape, P.index[0], P.index[-1]); print("tradable", tr); print(sorted(C.columns))
d = P.describe().T; d["first"]=P.apply(lambda s:s.first_valid_index()); d["ac1"]=P.apply(lambda s:s.autocorr(1)); d["inC"]=[t in C.columns for t in d.index]
print(d.round(3))
print({k:type(v) for k,v in S.items()})
