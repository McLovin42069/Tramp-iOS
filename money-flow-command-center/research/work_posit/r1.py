from base import *
import warnings; warnings.filterwarnings("ignore")
dl = np.log(SI).diff(); dl = dl.where(dl.abs() < 0.6)       # drop split-like jumps
LS = dl.fillna(0).cumsum().where(SI.notna())                 # split-cleaned log SI level
for k in (1, 2, 6):
    s = daily(LS - LS.shift(k))
    for h in (20, 60): ev(f"dlogSI {k} reports", s, h)
z = (LS - LS.rolling(24, min_periods=12).mean()) / LS.rolling(24, min_periods=12).std()
for h in (20, 60, 120): ev("z logSI 24rep", daily(z), h)
ld = np.log(DTC.where(DTC > 0))
zd = (ld - ld.rolling(24, min_periods=12).mean()) / ld.rolling(24, min_periods=12).std()
for h in (20, 60): ev("z logDTC 24rep", daily(zd), h)
for h in (20, 120): ev("DTC level", daily(DTC), h)
