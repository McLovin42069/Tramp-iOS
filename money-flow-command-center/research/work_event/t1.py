from cal import *
D = lib.load(); C = D["C"]; V = D["V"]
cal = calendar(C.index)
# 1. holiday calendar vs data
dh = C.index[V["SPY"] == 0]; ch = cal.index[~cal.trading & (cal.index <= C.index[-1])]
print("in data not rule:", dh.difference(ch).strftime("%Y-%m-%d").tolist()); print("in rule not data:", ch.difference(dh).strftime("%Y-%m-%d").tolist())
print(cal.loc["2023-11-20":"2023-12-06"])
print(cal.tail(8))
# 2. hand check of timing: long SPY on tdm_rev==-1 and tdm in 1..3
f = lambda c: (c.tdm_rev == -1) | (c.tdm <= 3)
W = cal_weights(C.index, f, "SPY")
ret = lib.weights_to_returns(W, D, cost_bps=0)
r = C["SPY"].pct_change()
x = pd.DataFrame({"W": W.SPY, "ret": ret, "spy": r, "tdm": cal.tdm, "rev": cal.tdm_rev}).loc["2023-05-22":"2023-06-12"]
print(x)
m = f(cal).reindex(C.index).fillna(False)
print("mismatch days (strategy ret != spy on target days / != 0 off):", ((ret - r.where(m, 0)).abs() > 1e-12).sum())
# truncation invariance: weights from truncated index equal
W2 = cal_weights(C.index[:1500], f, "SPY"); print("trunc equal:", (W2.SPY == W.SPY.iloc[:1500]).all())
