from h import *
import pickle; S = pickle.load(open("S.pkl","rb"))
rk = lambda X: X.rank(axis=1, pct=True)
O = D["O"][ALL]
on = (O/C.shift(1)-1).where(lambda x: x.abs()<0.2); intr = (C/O-1).where(lambda x: x.abs()<0.2)
print("open coverage", O.notna().mean().mean(), "open==prev close frac", (O==C.shift(1)).mean().mean())
ev("overnight20 (high=long)", z(on.rolling(20, min_periods=12).sum()), 20)
ev("intraday20 (high=long)", z(intr.rolling(20, min_periods=12).sum()), 20)
ev("overnight60 (high=long)", z(on.rolling(60, min_periods=40).sum()), 20)
# cost sensitivity of the best ones at 25 bps
c2 = rk(S["resmom12_1"]) + rk(S["issu12"]); c3 = c2 + rk(S["str20"])
print("--- 25 bps"); ev("combo2 h60 25bp", c2, 60, cost_bps=25); ev("combo3 h20 25bp", c3, 20, cost_bps=25); ev("resmom h60 25bp", S["resmom12_1"], 60, cost_bps=25)
e = lib.xs_eval(c2, D, 60, cols=AS); print(e["by_year_pct"])
e = lib.xs_eval(c3, D, 20, cols=ALL); print(e["by_year_pct"])
