NAME = "Month-end Treasury bid: hold TLT over the last two trading days of each month"
RATIONALE = ("Bond indices extend duration and index funds/benchmarked managers buy at month-end; in discovery every Treasury/aggregate "
             "instrument (TLT, IEF, SHY, AGG, LQD, ZB, ZN) rose abnormally on the last trading day (TLT +24 bp, t 4.2; 3 sub-periods all positive) "
             "and the 10y/30y yield fell ~1.4 bp on that day in 1993-2002 as well, before the ETFs existed. Calendar-only: buy at the close of the "
             "third-to-last trading day, sell at the close of the last trading day; 12 round trips a year, flat otherwise. "
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
    pos = left.isin([1, 2]).astype(float).rename("TLT")
    return lib4.daily_strategy(pos, L, 2.0, exec="same_close").loc[idx[0]:]
DISCOVERY = {'active_days_pct': 14.32027092404451,
 'alpha_ann_pct': 3.2987696298397893,
 'alpha_t': 3.5253076307709166,
 'ann_return_pct': 3.9453928775157174,
 'ann_vol_pct': 3.968977197324818,
 'bench_ann_pct': 7.162454685483914,
 'bench_max_drawdown_pct': -26.72490271563579,
 'bench_sharpe': 0.5487287267464943,
 'beta': 0.09027955862484335,
 'by_year_pct': {2002: 2.37,
                 2003: 4.52,
                 2004: 4.86,
                 2005: 3.82,
                 2006: 2.26,
                 2007: 6.88,
                 2008: 5.57,
                 2009: 3.93,
                 2010: 12.21,
                 2011: 10.08,
                 2012: 5.62,
                 2013: 1.5,
                 2014: -0.04,
                 2015: 1.4,
                 2016: -0.58,
                 2017: -0.34,
                 2018: 1.52},
 'days': 4134,
 'first_half_ann_pct': 5.137029986318866,
 'from': '2002-07-31',
 'max_drawdown_pct': -8.844908434134968,
 'mde_ann_pct': 2.44981701521343,
 'positive_years': '14/17',
 'second_half_ann_pct': 2.753755768712569,
 'sharpe': 0.9940578343899287,
 't': 4.026211807876589,
 'to': '2018-12-31'}
