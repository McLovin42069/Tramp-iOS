import warnings; warnings.filterwarnings('ignore')
from fw import *
pl = C.shift(1)[last]; pl.index=pl.index.normalize(); lh = Cl/pl-1
volr = Cl.pct_change(fill_method=None).std().sort_values(); top5 = list(volr.index[-5:]); print('top5 vol', top5)
keep = [c for c in STK if c not in top5]
rep('last-hr losers ->next close ex5vol', sched(xw(-lh[keep]),'L','N7'))
s=-rc[keep]; p=s.rank(axis=1,pct=True); w=(p>0.8).astype(float)-(p<=0.2).astype(float)
lp=w.clip(lower=0); sp=(-w).clip(lower=0); rep('hourly reversal ex5vol', (0.5*lp.div(lp.sum(axis=1),axis=0)-0.5*sp.div(sp.sum(axis=1),axis=0)).fillna(0))
disp = lh.std(axis=1); thr = disp.rolling(60).quantile(0.67).shift(1)
rep('last-hr losers q10 ->next close, big-disp days', sched(xw(-lh,q=0.1).where(disp>thr,0.0),'L','N7'))
# vol-standardised last-hour move, extremes only (|z|>2), equal weights
z = lh.sub(lh.mean(axis=1),axis=0)/(vol20.shift(1)/np.sqrt(13)); 
w = (z<-2.5).astype(float)-(z>2.5).astype(float)
lp=w.clip(lower=0); sp=(-w).clip(lower=0); n=np.maximum(lp.sum(axis=1),5); m=np.maximum(sp.sum(axis=1),5)
rep('last-hr |z|>2.5 reversal ->next close', sched(0.5*lp.div(n,axis=0)-0.5*sp.div(m,axis=0),'L','N7'))
# continuous slow book: 5-day smoothed last-hour reversal signal, rebalanced once a day at close
sig = (-lh).rolling(5).mean(); W = xw(sig, mode='rank')
rep('5d-avg last-hr reversal, held continuously', sched(W,'L','N7'))
print(N[0])
