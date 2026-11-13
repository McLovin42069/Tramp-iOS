import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research4"); import lib4, pprint
import numpy as np, pandas as pd
TPL = '''NAME = "Month-end Treasury bid: hold {tk} over the {lab} of each month"
RATIONALE = ("Bond indices extend duration and index funds/benchmarked managers buy at month-end; in discovery every Treasury/aggregate "
             "instrument (TLT, IEF, SHY, AGG, LQD, ZB, ZN) rose abnormally on the last trading day (TLT +24 bp, t 4.2; 3 sub-periods all positive) "
             "and the 10y/30y yield fell ~1.4 bp on that day in 1993-2002 as well, before the ETFs existed. Calendar-only: buy at the close of the "
             "{ent} trading day, sell at the close of the last trading day; 12 round trips a year, flat otherwise. "
             "Found as a side result of a ~230-cell macro-calendar event study, so it carries a multiple-testing discount.")
VARIANTS_TRIED = 232
DATA = "long"
BENCH = "{tk}"
def strategy(D):
    import lib4, numpy as np, pandas as pd
    L = lib4.us_calendar(D)
    idx = L["C"]["{tk}"].dropna().index
    ym = pd.Series(idx.year * 100 + idx.month, index=idx)
    left = ym.groupby(ym).cumcount(ascending=False)          # trading days left in the month after t (exact for completed months)
    lastm = ym == ym.iloc[-1]                                # final month of the data may be incomplete: count weekdays instead
    wd = [max(len(pd.bdate_range(d + pd.Timedelta(days=1), d + pd.offsets.MonthEnd(0))), 0) for d in idx[lastm.values]]
    left[lastm.values] = wd
    # pos[t] is held over day t+1 (exec="same_close"); the exchange calendar is public, so this is known in advance
    pos = left.isin({days}).astype(float).rename("{tk}")
    return lib4.daily_strategy(pos, L, 2.0, exec="same_close").loc[idx[0]:]
DISCOVERY = {disc}
'''
import importlib.util
for n,tk,days,lab,ent in [(1,"TLT","[1]","last trading day","second-to-last"),(2,"TLT","[1, 2]","last two trading days","third-to-last")]:
    p=f"candidates/fed_{n}.py"; open(p,"w").write(TPL.format(tk=tk,days=days,lab=lab,ent=ent,disc="{}"))
    sp=importlib.util.spec_from_file_location("c",p); m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    D=lib4.load_long(); r=m.strategy(D); b=D["C"][tk].pct_change(fill_method=None)
    e=lib4.ts_eval(r,b); open(p,"w").write(TPL.format(tk=tk,days=days,lab=lab,ent=ent,disc=pprint.pformat(e,width=150)))
    print(tk,{k:(round(v,2) if isinstance(v,float) else v) for k,v in e.items()})
    print(" worst day",round(r.min()*100,2),r.idxmin().date(),"worst month",round(r.resample("ME").sum().min()*100,2),"trades/yr",round((r!=0).sum()/2/ (len(r)/252),1))
    x=r[(r.index<"2009")|(r.index>"2011-12-31")]; print(" ex 2009-11 t",round(x.mean()/x.std()*np.sqrt(len(x)),2))
    for a,bb in [("2002","2007"),("2008","2013"),("2014","2018")]:
        x=r[a:bb]; print(" ",a,bb,"t",round(x.mean()/x.std()*np.sqrt(len(x)),2),"ann%",round(x.mean()*252*100,2))
    r1=r.copy(); 
    # hand check alignment: Oct 2011 -> held over 2011-10-28 and 2011-10-31
    print(r["2011-10-26":"2011-11-01"].round(4).to_dict()); print(b["2011-10-26":"2011-11-01"].round(4).to_dict())
