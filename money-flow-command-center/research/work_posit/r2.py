from base import *
import warnings; warnings.filterwarnings("ignore")
dl = np.log(SI).diff(); dl = dl.where(dl.abs() < 0.6)
LS = dl.fillna(0).cumsum().where(SI.notna())
dtc = daily(DTC)[[c for c in DTC.columns if c in US]]
cols = list(dtc.columns)
rk = lambda x: lib.residual(x, D).rank(axis=1, pct=True)
r60 = C[cols] / C[cols].shift(60) - 1; r20 = C[cols] / C[cols].shift(20) - 1
dd = C[cols] / C[cols].rolling(250).max() - 1
hi = rk(dtc) > 0.7
print("-- within high-DTC names (top 30%), sort on past return")
for h in (20, 60):
    ev("highDTC: ret60", r60.where(hi), h, cols=cols, q=0.3, min_names=20)
    ev("highDTC: ret20", r20.where(hi), h, cols=cols, q=0.3, min_names=20)
print("-- interaction rank(dtc)-0.5 * rank(ret60)-0.5")
for h in (20, 60): ev("dtc x ret60", (rk(dtc) - .5) * (rk(r60) - .5), h, cols=cols)
print("-- covering after drawdown: among bottom-30% drawdown names, sort on dSI 2 reports")
ch = daily(LS - LS.shift(2))[cols]; ch6 = daily(LS - LS.shift(6))[cols]
low = rk(dd) < 0.3
for h in (20, 60):
    ev("drawdown: dSI2", ch.where(low), h, cols=cols, q=0.3, min_names=20)
    ev("drawdown: dSI6", ch6.where(low), h, cols=cols, q=0.3, min_names=20)
print("-- shorts building into strength: among top-30% ret60, sort dSI6")
ev("winners: dSI6", ch6.where(rk(r60) > 0.7), 60, cols=cols, q=0.3, min_names=20)
print("-- issuance")
sh = D["shares"]; i12 = sh - sh.shift(250); i6 = sh - sh.shift(125)
for nm, u in (("US", US), ("EU", EU), ("AS", AS)):
    for h in (60, 120): ev(f"iss12 {nm}", i12, h, cols=u)
ev("iss12 EU+AS", i12, 60, cols=EU + AS)
ev("iss6 EU", i6, 60, cols=EU)
