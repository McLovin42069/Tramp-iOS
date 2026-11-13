import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research4"); import lib4, numpy as np, pandas as pd
L=lib4.us_calendar(lib4.load_long())
def show(name,r,bench=None):
    e=lib4.ts_eval(r,bench)
    m=r.groupby([r.index.year,r.index.month]).apply(lambda g:(1+g).prod()-1)
    s=f"{name:38s} n={e['days']} ann={e['ann_return_pct']:6.2f} t={e['t']:5.2f} sh={e['sharpe']:5.2f} dd={e['max_drawdown_pct']:6.1f} posy={e['positive_years']} h1={e['first_half_ann_pct']:5.1f} h2={e['second_half_ann_pct']:5.1f} wd={r.min()*100:5.1f} wm={m.min()*100:5.1f} mde={e['mde_ann_pct']:.1f}"
    if bench is not None: s+=f" a_t={e['alpha_t']:.2f} beta={e['beta']:.2f}"
    print(s); return e
on,day=lib4.session_returns(L)
for tk in ["SPY","QQQ","IWM","DIA","TLT","IEF","GLD","USO"]:
    o=on[tk].dropna(); d=day[tk].dropna()
    print(tk, "from",o.index[0].date(),"mean on bp %.2f t %.2f | day bp %.2f t %.2f"%(o.mean()*1e4,o.mean()/o.std()*len(o)**.5,d.mean()*1e4,d.mean()/d.std()*len(d)**.5))
    for a,b in [("1993","1999"),("2000","2004"),("2005","2009"),("2010","2014"),("2015","2018")]:
        oo=o[a:b]; dd=d[a:b]
        if len(oo)>100: print("   %s-%s on %.2f bp (t %.2f) day %.2f bp (t %.2f)"%(a,b,oo.mean()*1e4,oo.mean()/oo.std()*len(oo)**.5,dd.mean()*1e4,dd.mean()/dd.std()*len(dd)**.5))
    one=pd.Series(1.0,index=L["C"][tk].dropna().index); zero=one*0
    bh=L["C"][tk].pct_change().dropna()
    for c in [0.5,1.0,2.0]:
        r=lib4.segment_strategy(one.to_frame(tk),zero.to_frame(tk),L,cost_bps=c)
        r=r[r.index>=one.index[0]]
        show(f"{tk} always-on c={c}",r,bh)
        for st in ["2005","2010"]:
            if r.index[0]<pd.Timestamp(st): show(f"   since {st}",r[st:],bh)
