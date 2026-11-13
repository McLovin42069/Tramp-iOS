from common import *
vol60 = r.rolling(60).std(); vol250=r.rolling(250).std()
mkt = r.mean(axis=1)
# beta & idio vol (250d)
cov = r.rolling(250).cov(mkt); beta = cov.div(mkt.rolling(250).var(),axis=0)
res = r - beta.shift(1).mul(mkt,axis=0)
ivol = res.rolling(60).std()
ev("low total vol60", -vol60, 20); ev("low ivol60", -ivol, 20); ev("low beta", -beta, 20); ev("low ivol60", -ivol, 60)
# residual momentum 12-1 vol scaled
rm = res.rolling(230).sum().shift(20)/res.rolling(230).std().shift(20)
ev("resid mom 12-1 (IR)", rm, 20); ev("resid mom 12-1 (IR)", rm, 60)
m121 = C.shift(20)/C.shift(250)-1
lowvol = vol250.rank(axis=1,pct=True)<0.5
ev("mom12-1 among low-vol half", m121.where(lowvol), 20)
ev("mom12-1 among high-vol half", m121.where(~lowvol), 20)
# frog in pan: pct positive days * sign
pos = (r>0).rolling(230).mean().shift(20)
ev("pct up-days 12-1", pos, 20)
# volume trend
vt = np.log(V.rolling(20).mean()/V.rolling(250).mean())
ev("volume trend 20/250", vt, 20); ev("volume trend 20/250", vt, 60)
# close location
clv = ((C-L)-(H-C))/(H-L).replace(0,np.nan)
ev("CLV 5d mean", clv.rolling(5).mean(), 5); ev("CLV 20d mean", clv.rolling(20).mean(), 20); ev("CLV 1d", clv, 1)
# gap
ev("gap today (rel)", lib.residual(on,D), 1); ev("neg intraday today", -lib.residual(intr,D), 1)
# long-term reversal, skew, seasonality
ev("LT reversal 36-12m", -(C.shift(250)/C.shift(750)-1), 60)
ev("skew 120d (neg)", -r.rolling(120).skew(), 20)
seas = (C.shift(230)/C.shift(250)-1)   # return of the same calendar month last year (approx next 20d a year ago)
ev("seasonality same-month LY", seas, 20)
# Amihud
ami = (r.abs()/(C*V)).rolling(120).mean()
ev("amihud illiq", ami, 20)
# range / ATR compression
rng = (np.log(H/L)).rolling(10).mean()/(np.log(H/L)).rolling(120).mean()
ev("range compression 10/120 (neg)", -rng, 20)
