import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research2")
import lib2, numpy as np, pandas as pd
L0 = lib2.load_long()
us = L0["C"]["SPY"].dropna().index            # US trading sessions since 1993-01-29
L = {"C": L0["C"].reindex(us)}                 # US-session calendar (avoids losing post-holiday returns)
C = L["C"]; Cf = C.ffill(limit=3)              # signals: tiny ffill for index/yield gaps
me = pd.Series(us, index=us).groupby([us.year, us.month]).max().values   # month-end sessions
N = [0]
def monthly(sig):
    """sig: daily frame/series -> sampled at month end, held (ffilled) daily."""
    s = sig.reindex(us).loc[me]
    return s.reindex(us).ffill()
def with_cash(pos, cash="SHY"):
    pos = pos.to_frame() if isinstance(pos, pd.Series) else pos.copy()
    pos = pos.fillna(0.0)
    if cash:
        rest = (1 - pos.sum(axis=1)).clip(lower=0)
        pos[cash] = pos.get(cash, 0.0) + rest.where(C[cash].notna(), 0.0)
    return pos
def run(pos, exec="next_close", cash="SHY"):
    return lib2.daily_strategy(with_cash(pos, cash), L, exec=exec)
SPYr = lib2.daily_strategy(pd.Series(1.0, index=us, name="SPY"), L)
p6040 = pd.DataFrame({"SPY": 0.6, "IEF": 0.4}, index=us).where(C["IEF"].notna())
B64 = lib2.daily_strategy(p6040.dropna(), L)
def per(r, a, b):
    x = r.loc[a:b]; return round(((1 + x).prod() - 1) * 100, 1) if len(x) else None
def ev(name, pos, exec="next_close", cash="SHY", start=None, risk=None, show=True):
    N[0] += 1
    pos = with_cash(pos, cash)
    if start: pos = pos.loc[start:]
    r = lib2.daily_strategy(pos, L, exec=exec)
    e = lib2.ts_eval(r, SPYr); e2 = lib2.ts_eval(r.loc[B64.index[0]:], B64)
    b = lib2.ts_eval(SPYr.loc[r.index[0]:]); b6 = lib2.ts_eval(B64.loc[r.index[0]:])
    risk = [c for c in pos.columns if c not in ("SHY", "BIL")] if risk is None else risk
    P = pos.reindex(r.index)
    out = dict(name=name, frm=e["from"], t=round(e["t"], 2), sh=round(e["sharpe"], 2), spy_sh=round(b["sharpe"], 2), b64_sh=round(b6.get("sharpe", np.nan), 2),
               ann=round(e["ann_return_pct"], 1), vol=round(e["ann_vol_pct"], 1), mdd=round(e["max_drawdown_pct"], 0), spy_mdd=round(b["max_drawdown_pct"], 0),
               beta=round(e["beta"], 2), a=round(e["alpha_ann_pct"], 1), a_t=round(e["alpha_t"], 2), a64_t=round(e2.get("alpha_t", np.nan), 2),
               h1=round(e["first_half_ann_pct"], 1), h2=round(e["second_half_ann_pct"], 1), py=e["positive_years"], mde=round(e["mde_ann_pct"], 1),
               inmkt=round(P[risk].sum(axis=1).mean() * 100), tr_yr=round(P.diff().abs().sum(axis=1).sum() / 2 / (len(r) / 252), 1),
               y0002=per(r, "2000-01", "2002-12"), y08=per(r, "2008-01", "2008-12"),
               d90=per(r, "1993", "1999"), d00=per(r, "2000", "2009"), d10=per(r, "2010", "2018"))
    if show: print(out)
    return r, out, e
