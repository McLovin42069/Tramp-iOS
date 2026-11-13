from h import *
S = {}
S["mom12_1"] = z(C.shift(20)/C.shift(250)-1)
S["mom6_1"] = z(C.shift(20)/C.shift(125)-1)
vol = rr.rolling(250, min_periods=150).std()
S["resmom12_1"] = (rr.shift(20).rolling(230, min_periods=150).sum())/vol   # country-residual momentum, vol-scaled
S["str5"] = -z(C/C.shift(5)-1)
S["str20"] = -z(C/C.shift(20)-1)
S["lowvol250"] = -z(r.rolling(250, min_periods=150).std())
S["hi52"] = z(C/C.rolling(250, min_periods=150).max())
sh = D["shares"].reindex(index=C.index, columns=ALL)
S["issu12"] = -z(sh - sh.shift(250))
S["max5_20"] = -z(r.rolling(20).apply(lambda x: np.sort(x)[-5:].mean(), raw=True))
S["ltrev3y"] = -z(C.shift(250)/C.shift(750)-1)
for k in ["mom12_1","mom6_1","resmom12_1","lowvol250","hi52","issu12","ltrev3y"]:
    ev(k, S[k], 20); ev(k, S[k], 60)
for k in ["str5","str20","max5_20"]:
    ev(k, S[k], 5); ev(k, S[k], 20)
import pickle; pickle.dump(S, open("S.pkl","wb"))
