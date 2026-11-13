NAME = "Down-day overnight, 4 index futures proxy (1.0 bp)"
RATIONALE = ("Overnight reversal premium in US equity-index futures: buy at the 16:00 cash close ONLY after a down day (close < previous close), sell at the next 09:30 cash open, flat during the day. 1993-2018 the night after a down day earned ~6-8 bp in SPY/QQQ/IWM/DIA (since 2005: ~6-7 bp) versus ~0.5-2 bp after an up day; liquidity providers who absorb end-of-day selling are paid overnight. ETF close->open is used as a PROXY for the futures contract and is costed at an ASSUMED 1.0 bp per trade (MES/MNQ/M2K/MYM micro futures, conservative). At the 2 bp ETF cost the rule is NOT significant (t ~2.1-2.4, alpha_t ~1.0-1.3): the edge exists only at futures costs. Needs a futures account (micro E-minis, margin; position opened at the cash close and closed at the cash open every signal day, ~115 round trips a year); carries overnight gap risk (worst night -5.8% to -6.6%). Weaker since 2010 (t ~1.9-2.4 alone).")
VARIANTS_TRIED = 64
DATA = "long"
BENCH = "SPY"
TICKERS = ['SPY', 'QQQ', 'IWM', 'DIA']
COST_BPS = 1.0      # ASSUMED futures cost per trade (one way). ETF data are only a proxy for the futures contract.


def strategy(D):
    import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research4")
    import lib4, numpy as np, pandas as pd
    L = lib4.us_calendar(D)
    C = L["C"]; ix = C["SPY"].dropna().index
    tks = [t for t in TICKERS if t in C.columns]
    Cx = C[tks].reindex(ix)
    down = (Cx.pct_change(fill_method=None) < 0)            # known at the close of day t (compute a minute before 16:00)
    avail = Cx.notna()
    W = (down & avail).astype(float).div(avail.sum(axis=1).clip(lower=1), axis=0)   # equal weight, sum |w| <= 1
    ret = lib4.segment_strategy(W, W * 0.0, L, cost_bps=COST_BPS)   # long close(t) -> open(t+1) only; flat in the day session
    return ret[ret.index >= ix[0]]


DISCOVERY = {'active_days_pct': 83.14950980392157,
 'alpha_ann_pct': 3.9930263490530353,
 'alpha_t': 3.0858777528136745,
 'ann_return_pct': 5.654516152236999,
 'ann_vol_pct': 7.220976703304097,
 'bench_ann_pct': 10.27427265100969,
 'bench_max_drawdown_pct': -55.18944108505597,
 'bench_sharpe': 0.5610836464611436,
 'beta': 0.1617136180458169,
 'by_year_pct': {1993: 2.54,
                 1994: 2.48,
                 1995: -1.07,
                 1996: -1.89,
                 1997: 5.92,
                 1998: 17.01,
                 1999: 29.13,
                 2000: 12.91,
                 2001: -5.75,
                 2002: 2.46,
                 2003: 3.05,
                 2004: 13.04,
                 2005: 11.93,
                 2006: 5.08,
                 2007: 14.2,
                 2008: -6.95,
                 2009: 8.05,
                 2010: 7.59,
                 2011: -2.89,
                 2012: 2.8,
                 2013: 8.59,
                 2014: 4.9,
                 2015: 0.65,
                 2016: 0.81,
                 2017: 8.23,
                 2018: 7.5},
 'days': 6528,
 'first_half_ann_pct': 6.772174110426694,
 'from': '1993-01-29',
 'max_drawdown_pct': -15.045567539648907,
 'mde_ann_pct': 3.5468771792278724,
 'positive_years': '21/26',
 'second_half_ann_pct': 4.536858194047304,
 'sharpe': 0.7830680508427158,
 'since_2005': {'alpha_t': 1.9173865159028292,
                'ann_return_pct': 5.053791480161443,
                'max_drawdown_pct': -15.045567539648841,
                'positive_years': '12/14',
                'sharpe': 0.6808794619805146,
                't': 2.545811743711933},
 'since_2010': {'alpha_t': 0.7861352742289406,
                'ann_return_pct': 4.325872311709094,
                'max_drawdown_pct': -13.542457718794566,
                'positive_years': '8/9',
                'sharpe': 0.6301095382968502,
                't': 1.8886609228015592},
 't': 3.9855595968704676,
 'to': '2018-12-31',
 'worst_day': '2015-08-24',
 'worst_day_pct': -5.815018746156344,
 'worst_month': '(np.int32(2011), np.int32(9))',
 'worst_month_pct': -7.758385327482619}
