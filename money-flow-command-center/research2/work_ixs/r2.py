import warnings; warnings.filterwarnings('ignore')
from fw import *
pl = C.shift(1)[last]; pl.index=pl.index.normalize(); lh = Cl/pl-1
dayret = Cl/Cl.shift(1)-1
# fixed tug of war (no look-ahead)
for L_ in (20,60):
    ti = rod.rolling(L_).mean().shift(1)
    rep(f'FIX past{L_} intraday winners 10:30->cl', sched(xw(ti),0,'L'))
    rep(f'FIX past{L_} intraday winners SHORT 10:30->cl', sched(xw(-ti),0,'L'))
# deciles / extremes, conditional on dispersion
rep('last-hour losers overnight q10', sched(xw(-lh,q=0.1),'L','N1'))
rep('last-hour losers overnight rank', sched(xw(-lh,mode='rank'),'L','N1'))
rep('last-hour losers -> next close', sched(xw(-lh),'L','N7'))
# volume conditioned: last-bar volume vs 20d avg of last-bar volume
Vl = V[last]; Vl.index=Vl.index.normalize(); rv = Vl/Vl.rolling(20).mean().shift(1)
hi = rv.rank(axis=1,pct=True)>0.5
rep('last-hour losers overnight, high relvol', sched(xw((-lh).where(hi)),'L','N1'))
rep('last-hour losers overnight, low relvol', sched(xw((-lh).where(~hi)),'L','N1'))
# first-hour volume conditioned gap/first-hour
V0 = V[k==0]; V0.index=V0.index.normalize(); rv0 = V0/V0.rolling(20).mean().shift(1); hi0 = rv0.rank(axis=1,pct=True)>0.5
rep('first-hour winners ->close, high relvol', sched(xw(fh.where(hi0)),0,'L'))
rep('first-hour winners ->close, low relvol', sched(xw(fh.where(~hi0)),0,'L'))
rep('gap continuation, high relvol ->close', sched(xw(gap.where(hi0)),0,'L'))
# only trade on big-dispersion days (top third of |gap| dispersion, trailing threshold)
disp = on1.std(axis=1); thr = disp.rolling(60).quantile(0.67).shift(1)
w = xw(on1, q=0.1).where(disp>thr, 0.0)
rep('on1 continuation q10, big-dispersion days', sched(w,0,'L'))
rep('on1 reversal q10, big-dispersion days', sched(-w,0,'L'))
# hourly reversal conditioned on bar volume
Vb = V/ V.groupby(k).transform(lambda x: x.rolling(20).mean().shift(1)) if False else None
# midday -> last hour
m5 = Ck(5)/Ck(0)-1
rep('10:30->15:30 losers -> close(last 30m)', sched(xw(-m5),5,'L'))
m4 = Ck(4)/Ck(0)-1
rep('10:30->14:30 winners -> close', sched(xw(m4),4,'L'))
# long-only vs RSP
rsp = lib2.bar_strategy(pd.DataFrame({'RSP':1.0},index=I['C'].index), I, cost_bps=0)
ew = lib2.bar_strategy(pd.DataFrame(1.0/len(STK),index=idx,columns=STK), I, cost_bps=0)
def lo(name, wlong, enter, exit):
    N[0]+=1
    base = pd.DataFrame(1.0/len(STK), index=idx, columns=STK)
    # tilt: half the book in equal weight, half in the long leg during the window, else all EW
    Pw = sched(wlong, enter, exit); act = Pw.abs().sum(axis=1)>0
    P = base.where(~act, 0.5*base + 0.5*Pw, axis=0)
    for c in (2,5,10):
        r = lib2.bar_strategy(P, I, cost_bps=c); a = r-ew.reindex(r.index); e = lib2.ts_eval(a)
        print(f"{name:42s} {c}bp active vs EW: ann {e['ann_return_pct']:6.2f} t {e['t']:5.2f}", end=' | ')
    print(f"q {qtrs(a)} mde {e['mde_ann_pct']:.1f}")
lo('LO tilt: last-hour losers overnight', xw(-lh,long_only=True),'L','N1')
lo('LO tilt: first-hour winners ->close', xw(fh,long_only=True),0,'L')
print(N[0])
