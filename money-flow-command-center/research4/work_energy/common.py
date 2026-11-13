import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research4"); import lib4
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
L = lib4.us_calendar(lib4.load_long())
C = L["C"]; R = C.pct_change(fill_method=None); IX = C.index
def ev(name, pos, bench=None, exec="same_close", cost=2.0, start=None):
    ret = lib4.daily_strategy(pos, L, cost, exec=exec)
    if start: ret = ret[ret.index>=start]
    # trim to first nonzero
    nz = ret[ret!=0]
    if len(nz)==0: print(name,'flat'); return ret
    ret = ret[ret.index>=nz.index[0]]
    b = R[bench] if bench else None
    e = lib4.ts_eval(ret, b)
    x = ret[(ret.index.year!=2008)&~ret.index.year.isin([2014,2015,2016])]
    tx = x.mean()/x.std()*np.sqrt(len(x)) if len(x)>60 else np.nan
    print(f"{name:45s} t={e['t']:5.2f} ann={e['ann_return_pct']:6.2f} sh={e['sharpe']:5.2f} act={e['active_days_pct']:4.0f}% yrs={e['positive_years']:6s} h1={e['first_half_ann_pct']:6.2f} h2={e['second_half_ann_pct']:6.2f} mde={e['mde_ann_pct']:5.2f} a_t={e.get('alpha_t',float('nan')):5.2f} t_ex={tx:5.2f} from={e['from']}")
    return ret
def seas_surprise(s, k=5):
    """weekly change minus mean of same ISO week change over previous k years (past only). s indexed by week-ending Friday."""
    d = s.diff()
    wk = d.index.isocalendar().week.clip(upper=52).values
    df = pd.DataFrame({'d':d.values,'wk':wk}, index=d.index)
    norm = df.groupby('wk')['d'].transform(lambda g: g.shift(1).rolling(k, min_periods=k).mean())
    return d - norm
def seas_level(s, k=5):
    wk = s.index.isocalendar().week.clip(upper=52).values
    df = pd.DataFrame({'v':s.values,'wk':wk}, index=s.index)
    g = df.groupby('wk')['v']
    mn = g.transform(lambda x: x.shift(1).rolling(k,min_periods=k).min()); mx = g.transform(lambda x: x.shift(1).rolling(k,min_periods=k).max())
    return (s-mn)/(mx-mn)   # 0 = bottom of 5y range, 1 = top
def rel(s, col):   # redate to release day, align to trading calendar (next trading day if holiday)
    off = 6 if col=="natgas_storage" else 5
    x = s.dropna().set_axis(s.dropna().index + pd.Timedelta(days=off))
    pos = IX.searchsorted(x.index); ok = pos < len(IX)
    out = pd.Series(x.values[ok], index=IX[pos[ok]]); return out[~out.index.duplicated(keep='last')]
