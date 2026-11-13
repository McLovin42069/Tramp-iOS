from core import *
pd.set_option("display.width", 300); pd.set_option("display.max_columns", 40)
rows = []
def E(*a, **k):
    r, o, e = ev(*a, show=False, **k); rows.append(o); return r
print("SPY", lib2.ts_eval(SPYr)["sharpe"], lib2.ts_eval(SPYr)["max_drawdown_pct"], "6040", lib2.ts_eval(B64)["sharpe"], lib2.ts_eval(B64)["max_drawdown_pct"], lib2.ts_eval(B64)["t"])
spy = Cf["SPY"]
# A trend on SPY
for m in (6, 8, 10, 12):
    E(f"SPY>MA{m}m", monthly((spy > spy.rolling(21 * m).mean()).astype(float)).rename("SPY"))
for m in (6, 9, 12):
    E(f"SPY tsmom{m}m", monthly((spy / spy.shift(21 * m) > 1).astype(float)).rename("SPY"))
E("SPY>MA10m same_close", monthly((spy > spy.rolling(210).mean()).astype(float)).rename("SPY"), exec="same_close")
# H dollar
dx = Cf["DX-Y.NYB"]
for d in (63, 126, 252):
    E(f"SPY if DXY {d}d falling (daily)", (dx < dx.shift(d)).astype(float).rename("SPY"))
    E(f"SPY if DXY {d}d falling (monthly)", monthly((dx < dx.shift(d)).astype(float)).rename("SPY"))
# E vol managed
rv = SPYr.reindex(us).fillna(0)
rsp = C["SPY"].pct_change()
for tgt in (0.10, 0.15):
    for w in (21, 63):
        vol = rsp.rolling(w).std() * np.sqrt(252)
        E(f"voltarget {tgt} w{w} monthly", monthly((tgt / vol).clip(upper=1)).rename("SPY"))
vol = rsp.rolling(21).std() * np.sqrt(252)
wv = (0.12 / vol).clip(upper=1); wv = (wv * 10).round() / 10
E("voltarget .12 w21 daily (0.1 steps)", wv.rename("SPY"))
# F yield curve / VIX
slope = Cf["^TNX"] - Cf["^IRX"]
E("SPY unless curve inverted", monthly((slope > 0).astype(float)).rename("SPY"))
E("SPY unless curve inverted in last 12m", monthly((slope.rolling(252).min() > 0).astype(float)).rename("SPY"))
vix = Cf["^VIX"]
for th in (20, 25, 30):
    E(f"SPY if VIX<{th} daily", (vix < th).astype(float).rename("SPY"))
E("SPY if VIX<MA63 daily", (vix < vix.rolling(63).mean()).astype(float).rename("SPY"))
E("SPY if VIX>MA63 daily (contrarian)", (vix > vix.rolling(63).mean()).astype(float).rename("SPY"))
# G credit
for a, lb in (("LQD", 63), ("LQD", 126), ("HYG", 63), ("HYG", 126)):
    ratio = Cf[a] / Cf["IEF"]
    E(f"SPY if {a}/IEF {lb}d up", monthly((ratio > ratio.shift(lb)).astype(float).where(ratio.shift(lb).notna())).rename("SPY").dropna())
df = pd.DataFrame(rows); print(df.to_string()); df.to_pickle("r1.pkl"); print("N", N[0])
