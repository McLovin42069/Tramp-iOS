from base import *
import warnings; warnings.filterwarnings("ignore")
sh = D["shares"]; i12 = sh - sh.shift(250)
ALL = US + EU + AS
rk = lambda x: lib.residual(x, D).rank(axis=1, pct=True)
print("-- Asia issuance robustness"); 
ev("iss12 AS q=.3", i12, 60, cols=AS, q=0.3); ev("iss12 AS h20", i12, 20, cols=AS)
ev("iss24 AS", sh - sh.shift(500), 60, cols=AS)
ev("iss12 AS unresid", i12, 60, cols=AS, resid=False)
print("-- worldwide"); ev("iss12 ALL", i12, 60, cols=ALL); ev("iss12 ALL", i12, 120, cols=ALL)
print("-- buyback + long-term loser (value proxy)")
ltr = C.shift(250) / C.shift(1250 if len(C) > 1500 else 750) - 1
ltr3 = C.shift(20) / C.shift(750) - 1
combo = lambda u: (rk(-i12[u]) + rk(-ltr3[u])) / 2
for nm, u in (("US", US), ("ALL", ALL)):
    for h in (60, 120): ev(f"buyback+3y loser {nm}", combo(u), h, cols=u)
ev("3y loser alone US", -ltr3, 60, cols=US)
print("-- buyback names only: sort on 3y reversal")
bb = i12[US] < -0.02
ev("buybackers: 3y loser", (-ltr3[US]).where(bb), 60, cols=US, q=0.3, min_names=20)
print("-- issuance acceleration"); ev("d iss12 US", i12 - i12.shift(250), 60, cols=US); ev("d iss12 ALL", i12 - i12.shift(250), 60, cols=ALL)
print("-- SI change in ADV units")
ADVm = ADV.rolling(6, min_periods=3).median()
dl = np.log(SI).diff(); ok = dl.abs() < 0.6
for k in (2, 6):
    s = ((SI - SI.shift(k)) / ADVm).where(ok.rolling(k).min() == 1)
    ev(f"dSI/ADV {k}rep", daily(s), 20); ev(f"dSI/ADV {k}rep", daily(s), 60)
print("N", N)
