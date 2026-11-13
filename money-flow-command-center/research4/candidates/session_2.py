NAME = "Down-day overnight, S&P+Nasdaq futures proxy (0.5 bp)"
RATIONALE = ("Overnight reversal premium in US equity-index futures: buy at the 16:00 cash close ONLY after a down day (close < previous close), sell at the next 09:30 cash open, flat during the day. 1993-2018 the night after a down day earned ~6-8 bp in SPY/QQQ/IWM/DIA (since 2005: ~6-7 bp) versus ~0.5-2 bp after an up day; liquidity providers who absorb end-of-day selling are paid overnight. ETF close->open is used as a PROXY for the futures contract and is costed at an ASSUMED 0.5 bp per trade (MES/MNQ only: half a tick plus commission at today's index level; before ~2015 a tick was 1-2 bp so 0.5 bp is hypothetical for the early sample). At the 2 bp ETF cost the rule is NOT significant (t ~2.1-2.4, alpha_t ~1.0-1.3): the edge exists only at futures costs. Needs a futures account (micro E-minis, margin; position opened at the cash close and closed at the cash open every signal day, ~115 round trips a year); carries overnight gap risk (worst night -5.8% to -6.6%). Weaker since 2010 (t ~1.9-2.4 alone).")
VARIANTS_TRIED = 64
DATA = "long"
BENCH = "SPY"
TICKERS = ['SPY', 'QQQ']
COST_BPS = 0.5      # ASSUMED futures cost per trade (one way). ETF data are only a proxy for the futures contract.


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


DISCOVERY = {'active_days_pct': 77.1905637254902,
 'alpha_ann_pct': 4.944272919163794,
 'alpha_t': 3.489022188480949,
 'ann_return_pct': 6.656752090706062,
 'ann_vol_pct': 7.83173459700699,
 'bench_ann_pct': 10.27427265100969,
 'bench_max_drawdown_pct': -55.18944108505597,
 'bench_sharpe': 0.5610836464611436,
 'beta': 0.16667643829502415,
 'by_year_pct': {1993: 3.66,
                 1994: 3.67,
                 1995: -0.09,
                 1996: -0.76,
                 1997: 7.12,
                 1998: 15.5,
                 1999: 33.89,
                 2000: 13.13,
                 2001: -3.17,
                 2002: -3.54,
                 2003: 4.65,
                 2004: 14.91,
                 2005: 13.69,
                 2006: 6.39,
                 2007: 14.61,
                 2008: -4.99,
                 2009: 9.24,
                 2010: 8.81,
                 2011: -3.79,
                 2012: 7.14,
                 2013: 8.55,
                 2014: 6.61,
                 2015: 1.85,
                 2016: 1.22,
                 2017: 10.15,
                 2018: 8.9},
 'days': 6528,
 'first_half_ann_pct': 7.568710073922691,
 'from': '1993-01-29',
 'max_drawdown_pct': -18.075526563582823,
 'mde_ann_pct': 3.846875825424424,
 'positive_years': '20/26',
 'second_half_ann_pct': 5.744794107489435,
 'sharpe': 0.8499716133447673,
 'since_2005': {'alpha_t': 2.5012097510700153,
                'ann_return_pct': 6.284952218926561,
                'max_drawdown_pct': -14.050704308651706,
                'positive_years': '12/14',
                'sharpe': 0.8170384316790626,
                't': 3.054910818402779},
 'since_2010': {'alpha_t': 1.2836375693971818,
                'ann_return_pct': 5.525315881047707,
                'max_drawdown_pct': -14.050704308651873,
                'positive_years': '8/9',
                'sharpe': 0.7711521298771292,
                't': 2.3114154043292423},
 't': 4.326076791139747,
 'to': '2018-12-31',
 'worst_day': '2015-08-24',
 'worst_day_pct': -6.612630256960429,
 'worst_month': '(np.int32(2002), np.int32(6))',
 'worst_month_pct': -9.253287406984278}
