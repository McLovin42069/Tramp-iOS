NAME = "TLT long only on the last 3 trading days of each month"
RATIONALE = ("Month-end demand for duration: bond indices extend/rebalance at the month-end close and index-tracking funds, insurers and balanced funds must buy then; Treasuries rally into the last close. Same sign in IEF, IEI, AGG, TIP and ZN/ZB futures, in both halves and every 5-year block 2002-2018; 10y-yield data show the pattern from the 1990s on and strengthening. In the market 14% of days, 12 round trips a year.")
VARIANTS_TRIED = 123
DATA = "long"
BENCH = "TLT"
EXECUTION = ("same_close: pure calendar rule, the position is known in advance and is put on at the close of the trading day "
             "before each window (lib2.daily_strategy exec='same_close', 2 bps per unit turnover)")
SHORT_FIRST = False


def strategy(D):
    import lib2, numpy as np, pandas as pd
    px = D["C"]["TLT"].dropna()                 # TLT's own trading days (the shared calendar has NaN rows on US holidays)
    d = px.index
    one = pd.Series(1, index=d)
    f = one.groupby([d.year, d.month]).cumsum()                                        # 1 = first trading day of month
    rev = one[::-1]
    b = rev.groupby([rev.index.year, rev.index.month]).cumsum()[::-1]                  # 1 = last trading day of month
    # the final month of the data may be incomplete -> "days remaining" unknown there: take no month-end position in it
    last = d[-1]
    if (last + pd.offsets.BDay(1)).month == last.month:
        b[(d.year == last.year) & (d.month == last.month)] = 99
    held = (b <= 3).astype(float)               # long on the last 3 trading days of the month
    if SHORT_FIRST:
        held = held - (f <= 3).astype(float)    # short on the first 3 trading days
    pos = held.shift(-1).fillna(0.0)            # set at the close of the day BEFORE each held day (calendar known in advance)
    return lib2.daily_strategy(pos.rename("TLT"), {"C": D["C"][["TLT"]].dropna()}, cost_bps=2.0, exec="same_close")


DISCOVERY = {'days': 4134,
 'active_days_pct': 19.085631349782293,
 'ann_return_pct': 4.4901733570185005,
 'ann_vol_pct': 4.947844535673588,
 'sharpe': 0.9075008975412803,
 't': 3.6756320436644443,
 'max_drawdown_pct': -12.533717151048474,
 'positive_years': '16/17',
 'first_half_ann_pct': 4.03331997664864,
 'second_half_ann_pct': 4.947026737388361,
 'mde_ann_pct': 3.0540144549820023,
 'by_year_pct': {2002: 6.45,
                 2003: 0.76,
                 2004: -0.29,
                 2005: 4.89,
                 2006: 0.47,
                 2007: 7.41,
                 2008: 7.21,
                 2009: 0.25,
                 2010: 12.11,
                 2011: 6.02,
                 2012: 5.52,
                 2013: 1.13,
                 2014: 6.07,
                 2015: 1.94,
                 2016: 5.37,
                 2017: 2.54,
                 2018: 6.2},
 'from': '2002-07-31',
 'to': '2018-12-31',
 'beta': 0.1364000621932915,
 'alpha_ann_pct': 3.532930692873931,
 'alpha_t': 3.1118081578406787,
 'bench_ann_pct': 7.01790489499974,
 'bench_sharpe': 0.5241069897204083,
 'bench_max_drawdown_pct': -26.58535634211442,
 'time_in_market_pct': 19.085631349782293,
 'trades_per_year': 12}
