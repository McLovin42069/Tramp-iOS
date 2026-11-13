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
