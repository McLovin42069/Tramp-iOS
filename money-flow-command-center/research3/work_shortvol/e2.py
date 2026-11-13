from base import *
r1, r5, r20 = ratio(1), ratio(5), ratio(20)
tests = {
 "z20_r1": z(r1,20), "z60_r1": z(r1,60), "z60_r5": r5 - r1.rolling(60,min_periods=30).mean(),
 "z250_r20": r20 - r1.rolling(250,min_periods=120).mean(),
 "chg_r1": r1.diff(), "chg_r5": r5 - r5.shift(5), "chg_r20": r20-r20.shift(20),
}
for k,v in tests.items():
    for h in (1,5,20):
        ev(out(v), h, k)
