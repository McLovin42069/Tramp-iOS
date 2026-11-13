NAME = "Month-end Treasury bid: hold TLT over the last trading day of each month"
RATIONALE = ("Bond indices extend duration and index funds/benchmarked managers buy at month-end; in discovery every Treasury/aggregate "
             "instrument (TLT, IEF, SHY, AGG, LQD, ZB, ZN) rose abnormally on the last trading day (TLT +24 bp, t 4.2; 3 sub-periods all positive) "
             "and the 10y/30y yield fell ~1.4 bp on that day in 1993-2002 as well, before the ETFs existed. Calendar-only: buy at the close of the "
             "second-to-last trading day, sell at the close of the last trading day; 12 round trips a year, flat otherwise. "
             "Found as a side result of a ~230-cell macro-calendar event study, so it carries a multiple-testing discount.")
VARIANTS_TRIED = 232
DATA = "long"
BENCH = "TLT"
def strategy(D):
    import lib4, numpy as np, pandas as pd
    L = lib4.us_calendar(D)
    idx = L["C"]["TLT"].dropna().index
    ym = pd.Series(idx.year * 100 + idx.month, index=idx)
    left = ym.groupby(ym).cumcount(ascending=False)          # trading days left in the month after t (exact for completed months)
    lastm = ym == ym.iloc[-1]                                # final month of the data may be incomplete: count weekdays instead
    wd = [max(len(pd.bdate_range(d + pd.Timedelta(days=1), d + pd.offsets.MonthEnd(0))), 0) for d in idx[lastm.values]]
    left[lastm.values] = wd
    # pos[t] is held over day t+1 (exec="same_close"); the exchange calendar is public, so this is known in advance
    pos = left.isin([1]).astype(float).rename("TLT")
    return lib4.daily_strategy(pos, L, 2.0, exec="same_close").loc[idx[0]:]
DISCOVERY = {'active_days_pct': 9.554910498306725,
 'alpha_ann_pct': 2.090366694970061,
 'alpha_t': 3.0016306932617103,
 'ann_return_pct': 2.4275972950821525,
 'ann_vol_pct': 2.8868313416860727,
 'bench_ann_pct': 7.162454685483914,
 'bench_max_drawdown_pct': -26.72490271563579,
 'bench_sharpe': 0.5487287267464943,
 'beta': 0.047083104175940346,
 'by_year_pct': {2002: 2.91,
                 2003: 2.9,
                 2004: 4.88,
                 2005: 0.74,
                 2006: 2.32,
                 2007: 1.85,
                 2008: -0.63,
                 2009: 4.55,
                 2010: 9.41,
                 2011: 4.68,
                 2012: -1.54,
                 2013: -0.21,
                 2014: 0.54,
                 2015: 3.3,
                 2016: 1.59,
                 2017: 1.62,
                 2018: 1.19},
 'days': 4134,
 'first_half_ann_pct': 3.17889422063163,
 'from': '2002-07-31',
 'max_drawdown_pct': -6.107495565560783,
 'mde_ann_pct': 1.781871799535857,
 'positive_years': '14/17',
 'second_half_ann_pct': 1.6763003695326752,
 'sharpe': 0.8409210680331254,
 't': 3.4059651425463024,
 'to': '2018-12-31'}
