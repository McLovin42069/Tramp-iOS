from common import *
import t4
ALL=t4.ALL
for nm,cl,N in [("all N=2",ALL,2),("2/5/7 N=2",["2","5","7"],2),("3/10/30 N=2",["3","10","30"],2),("3/10/30 N=3",["3","10","30"],3)]:
    r=t4.rule(cl,N,"TLT"); b=bh("TLT")
    for s,e in [("2002","2006"),("2007","2010"),("2011","2014"),("2015","2018")]:
        x=ev(r,b,s+"-01-01",e+"-12-31"); print(nm,s,e,f"t={x['t']:.2f} ann={x['ann_return_pct']:.2f} a_t={x['alpha_t']:.2f} bench={x['bench_ann_pct']:.2f}")
    print(nm, "worst day",round(r.min()*100,2),r.idxmin().date(),"worst month",round(r.resample('ME').apply(lambda g:(1+g).prod()-1).min()*100,2), "corr w SPY", round(r.corr(bh("SPY").reindex(r.index)),2))
# cost sensitivity 5bps and next-open-ish: exec next_close shift (enter one day late)
pos_r = t4.rule(ALL,2,"TLT")
