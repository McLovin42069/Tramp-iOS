NAME = "SPY trend ensemble (price vs 6/8/10/12-month moving averages), monthly, cash in SHY"
RATIONALE = ("Faber-style time-series momentum: hold SPY in proportion to how many of four moving averages (126/168/210/252 sessions) "
             "the price is above at month end, remainder in SHY (zero return before SHY exists, 2002). Bear markets unfold slowly, so a "
             "slow trend filter side-steps most of them. CAVEAT: discovery alpha (t 3.0 vs SPY, 2.0 vs 60/40) comes entirely from 2000-02 "
             "and 2008; excluding those two episodes alpha t = 0.5, and 2010-2018 alpha t = 0.2. Effectively two independent events.")
VARIANTS_TRIED = 70
DATA = "long"
BENCH = "SPY"
EXECUTION = "next_close"   # signal at the month-end close, traded at the following session's close; about 1.1 round trips a year


def strategy(D):
    import lib2, numpy as np, pandas as pd
    us = D["C"]["SPY"].dropna().index                     # US sessions only (otherwise post-holiday returns are dropped)
    L = {"C": D["C"].reindex(us)}
    C = L["C"]; spy = C["SPY"]
    w = sum((spy > spy.rolling(21 * m).mean()).astype(float).where(spy.rolling(21 * m).mean().notna()) for m in (6, 8, 10, 12)) / 4
    me = pd.Series(us, index=us).groupby([us.year, us.month]).max().values
    w = w.loc[me].reindex(us).ffill().dropna()
    pos = pd.DataFrame({"SPY": w})
    pos["SHY"] = (1 - w).where(C["SHY"].reindex(w.index).notna(), 0.0)
    return lib2.daily_strategy(pos, L, cost_bps=2.0, exec="next_close")


DISCOVERY = {'days': 6272, 'active_days_pct': 91.58163265306123, 'ann_return_pct': 10.193228537547402, 'ann_vol_pct': 12.26373997601298, 'sharpe': 0.8311680252096544, 't': 4.146594641568017, 'max_drawdown_pct': -19.030031749783525, 'positive_years': '19/25', 'first_half_ann_pct': 10.582258336039141, 'second_half_ann_pct': 9.804198739055664, 'mde_ann_pct': 6.145541955900515, 'by_year_pct': {1994: -9.59, 1995: 36.58, 1996: 20.61, 1997: 33.48, 1998: 14.65, 1999: 16.76, 2000: -6.48, 2001: 0.0, 2002: -3.57, 2003: 24.43, 2004: 9.27, 2005: 2.06, 2006: 16.31, 2007: 4.45, 2008: 2.78, 2009: 20.2, 2010: 5.63, 2011: 2.11, 2012: 12.59, 2013: 32.31, 2014: 13.46, 2015: -8.44, 2016: 5.59, 2017: 21.71, 2018: -2.3}, 'from': '1994-02-02', 'to': '2018-12-31', 'beta': 0.45387084405990663, 'alpha_ann_pct': 5.552470612502177, 'alpha_t': 3.113039052076845, 'bench_ann_pct': 10.224842564314814, 'bench_sharpe': 0.5499033260839199, 'bench_max_drawdown_pct': -55.18944108505597}
