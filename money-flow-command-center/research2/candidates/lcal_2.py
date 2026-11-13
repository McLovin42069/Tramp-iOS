NAME = "TLT long last 3 trading days of month, short first 3 trading days"
RATIONALE = ("Month-end index-extension / rebalancing demand pushes Treasuries up into the month-end close and the price pressure reverses (plus early-month supply and data risk) in the first three sessions: long leg alpha_t 3.1, short leg alpha_t 4.3 standalone. Requires shorting TLT (or an inverse position) 3 days a month; 24 round trips a year.")
VARIANTS_TRIED = 123
DATA = "long"
BENCH = "TLT"
EXECUTION = ("same_close: pure calendar rule, the position is known in advance and is put on at the close of the trading day "
             "before each window (lib2.daily_strategy exec='same_close', 2 bps per unit turnover)")
SHORT_FIRST = True


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
 'active_days_pct': 33.28495403967102,
 'ann_return_pct': 7.720902023461898,
 'ann_vol_pct': 7.355493758586588,
 'sharpe': 1.049678278150769,
 't': 4.251490136442518,
 'max_drawdown_pct': -15.06728236202035,
 'positive_years': '14/17',
 'first_half_ann_pct': 7.787600163222025,
 'second_half_ann_pct': 7.654203883701773,
 'mde_ann_pct': 4.5401152158866624,
 'by_year_pct': {2002: 2.14,
                 2003: 11.49,
                 2004: 4.72,
                 2005: 10.03,
                 2006: 1.15,
                 2007: 3.98,
                 2008: -2.92,
                 2009: 18.93,
                 2010: 28.73,
                 2011: -3.33,
                 2012: 14.53,
                 2013: 12.55,
                 2014: 11.82,
                 2015: 10.71,
                 2016: 0.39,
                 2017: -2.86,
                 2018: 10.01},
 'from': '2002-07-31',
 'to': '2018-12-31',
 'beta': -0.0315525070194986,
 'alpha_ann_pct': 7.942334516923551,
 'alpha_t': 4.3806537058554245,
 'bench_ann_pct': 7.01790489499974,
 'bench_sharpe': 0.5241069897204083,
 'bench_max_drawdown_pct': -26.58535634211442,
 'time_in_market_pct': 33.28495403967102,
 'trades_per_year': 24}
