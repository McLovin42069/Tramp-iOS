from fw import *
# 1 hourly reversal every bar
s = -rc
p = s.rank(axis=1, pct=True); w = (p>0.8).astype(float)-(p<=0.2).astype(float)
lp=w.clip(lower=0); sp=(-w).clip(lower=0); Ph=(0.5*lp.div(lp.sum(1),axis=0)-0.5*sp.div(sp.sum(1),axis=0)).fillna(0)
rep('hourly reversal q20 every bar', Ph)
# intraday only (flat overnight)
rep('hourly reversal, flat overnight', Ph.where(pd.Series(~last,index=idx),0.0,axis=0))
# 2 gap: enter 10:30 hold to close
rep('gap reversal 10:30->close', sched(xw(-gap),0,'L'))
rep('on1 (prevC->10:30) reversal ->close', sched(xw(-on1),0,'L'))
rep('first-hour reversal ->close', sched(xw(-fh),0,'L'))
# first-hour vs SPY is same cross-sectionally. vol-scaled
rep('first-hour/vol reversal ->close', sched(xw(-fh/vol20.shift(1)),0,'L'))
# morning momentum into close
for j in (3,5):
    m = Ck(j)/Op.reindex(days)-1
    rep(f'open->bar{j} winners -> close', sched(xw(m),j,'L'))
    m2 = Ck(j)/Cl.shift(1).reindex(days)-1
    rep(f'prevC->bar{j} winners -> close', sched(xw(m2),j,'L'))
# overnight strategies: decided at last close, exit at 10:30 next day
lasthr = Cl/Ck(5).where(pd.Series(nb[last]==7,index=days),np.nan,axis=0)-1 if False else None
pl = C.shift(1)[last]; pl.index=pl.index.normalize(); lh = Cl/pl-1
rep('last-hour losers overnight ->10:30', sched(xw(-lh),'L','N1'))
dayret = Cl/Cl.shift(1)-1
rep('day losers overnight ->10:30', sched(xw(-dayret),'L','N1'))
rep('intraday losers overnight ->10:30', sched(xw(-intr),'L','N1'))
rep('day losers ->next close', sched(xw(-dayret),'L','N7'))
# tug of war: trailing on1 (overnight+first hr) mean 20d
for L_ in (20,60):
    tn = on1.rolling(L_).mean(); ti = rod.rolling(L_).mean()
    rep(f'past{L_} overnight(+1h) winners held overnight', sched(xw(tn),'L','N1'))
    rep(f'past{L_} intraday(10:30-cl) winners held 10:30->cl', sched(xw(ti),0,'L'))
    rep(f'past{L_} overnight winners SHORT intraday', sched(xw(-tn.shift(0)),0,'L'))
    rep(f'past{L_} intraday winners SHORT overnight', sched(xw(-ti),'L','N1'))
print(N[0])
