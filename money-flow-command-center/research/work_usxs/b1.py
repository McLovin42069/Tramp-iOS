from common import *
print(C.shape, C.index[0], C.index[-1], C.notna().sum(axis=1).iloc[[0,300,-1]].tolist())
dv = (C*V); av = np.log(V.rolling(5).mean()/V.rolling(60).mean())
abv1 = V/V.rolling(60).mean().shift(1)
vol60 = r.rolling(60).std()
# 1-3 reversal
ev("rev5", -rr.rolling(5).sum(), 5)
ev("rev5/vol", -rr.rolling(5).sum()/vol60, 5)
ev("rev1", -rr, 1); ev("rev1", -rr, 2); ev("rev2", -rr.rolling(2).sum(), 2)
lowv = av.rank(axis=1,pct=True)<0.5
ev("rev5 lowvol-only", (-rr.rolling(5).sum()).where(lowv), 5)
ev("rev5 highvol-only", (-rr.rolling(5).sum()).where(~lowv), 5)
# 4 abnormal-volume drift
z = rr/vol60
ev_day = (abv1>2.5)
s = (z.where(ev_day)).ffill(limit=20)   # most recent event-day move within 20d
ev("abvol-event drift (last evt 20d)", s, 20); ev("abvol-event drift (last evt 20d)", s, 5)
s60 = (z.where(ev_day,0)).rolling(60).sum()
ev("abvol-event sum 60d", s60, 20); ev("abvol-event sum 60d", s60, 60)
# 5 overnight / intraday
for w in (20,120):
    ev(f"overnight sum {w}", on.rolling(w).sum(), 20)
    ev(f"intraday sum {w}", intr.rolling(w).sum(), 20)
ev("overnight sum 20", on.rolling(20).sum(), 5)
ev("intraday sum 20", intr.rolling(20).sum(), 5)
