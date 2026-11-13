import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research4"); import lib4
import numpy as np, pandas as pd
L = lib4.us_calendar(lib4.load_long())
C,O = L["C"],L["O"]
idx = C.index
R = C.pct_change(fill_method=None)
F = pd.DatetimeIndex(L["fomc"]); 
Fd = F[(F<=idx[-1])]
def tt(x):
    x=x.dropna(); return x.mean()/x.std()*np.sqrt(len(x)) if len(x)>2 else np.nan
def cmp(r, mask, label=""):
    r=r.dropna(); m=mask.reindex(r.index).fillna(False)
    a,b=r[m],r[~m]
    se=np.sqrt(a.var()/len(a)+b.var()/len(b))
    return dict(label=label,n=len(a),mean_in_bp=round(a.mean()*1e4,1),mean_out_bp=round(b.mean()*1e4,1),t_in=round(tt(a),2),t_diff=round((a.mean()-b.mean())/se,2))
def ev(ret, bench=None, keys=("t","alpha_t","ann_return_pct","alpha_ann_pct","sharpe","active_days_pct","positive_years","first_half_ann_pct","second_half_ann_pct","mde_ann_pct","max_drawdown_pct","beta")):
    e=lib4.ts_eval(ret, bench)
    return {k:(round(e[k],2) if isinstance(e.get(k),float) else e.get(k)) for k in keys if k in e}
# corrected calendar: public record. 2003-09-15 is not a decision day (meeting was 16 Sep); missing 2017-02-01, 2017-11-01, 2018-08-01
FIX_ADD = pd.to_datetime(["2017-02-01","2017-11-01","2018-08-01"])
Fc = Fd.difference(pd.to_datetime(["2003-09-15"])).union(FIX_ADD)
Fc = Fc[Fc.isin(idx)]
def flag(dates, shift=0, index=idx):
    s=pd.Series(index.isin(dates),index=index)
    return s.shift(shift,fill_value=False) if shift else s
def k_since(dates):  # trading days since last event (0 on event day)
    f=flag(dates).values; out=np.full(len(idx),np.nan); k=np.nan
    for i,v in enumerate(f):
        k = 0 if v else (k+1 if k==k else np.nan); out[i]=k
    return pd.Series(out,index=idx)
SUB=[("2000","2007"),("2008","2013"),("2014","2018")]
def subs(r,mask):
    return {a+"-"+b[2:]:(round(r[a:b][mask[a:b]].mean()*1e4,1), round(tt(r[a:b][mask[a:b]]),2), int(mask[a:b].sum())) for a,b in SUB}
def hold(mask, tk, cost=2.0):
    """mask[t]=True -> hold tk over day t (close t-1 -> close t). Calendar known in advance: pos set on t-1, exec same_close."""
    pos = mask.shift(-1,fill_value=False).astype(float).rename(tk)
    return lib4.daily_strategy(pos, L, cost, exec="same_close")["2000":]
