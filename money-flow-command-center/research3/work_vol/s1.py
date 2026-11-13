from base import *
print(C[["^VIX","^VIX9D","^VIX3M","^VIX6M","^VVIX","^SKEW","^MOVE","SVXY","VIXY","VIXM","UVXY","VXX","SPY","TLT"]].apply(lambda s:(s.first_valid_index(), s.count())).T)
print(R["SVXY"].nsmallest(5)); print(R["SVXY"].loc["2018-02"].head(8))
vix, v3 = C["^VIX"], C["^VIX3M"]
ts = vix/v3
one = lambda col, s: s.astype(float).to_frame(col)
# benchmarks
ev("BH SPY 2006+", one("SPY", ts.notna()), start="2006-09-01")
ev("BH SVXY", one("SVXY", C["SVXY"].notna()))
# 1 SPY timing by TS
for th in [0.95,1.0,1.05]:
    p = one("SPY", ts<th).where(ts.notna().values[:,None])
    ev(f"SPY if VIX/VIX3M<{th}", p)
    ev(f"SPY if VIX/VIX3M<{th} same_close(prev)", one("SPY", ts.shift(1)<th).where(ts.shift(1).notna().values[:,None]), exec="same_close")
# SPY/TLT switch
p = pd.DataFrame({"SPY":(ts<1).astype(float),"TLT":(ts>=1).astype(float)}).where(ts.notna().values[:,None])
ev("SPY contango / TLT backw", p)
# SVXY switch
sv = C["SVXY"].notna()
for th in [0.9,0.95,1.0]:
    p = one("SVXY", (ts<th)&sv)[sv.values]
    ev(f"SVXY if ts<{th}", p)
    ev(f"SVXY if ts<{th} sameclose prev", one("SVXY", (ts.shift(1)<th)&sv)[sv.values], exec="same_close")
