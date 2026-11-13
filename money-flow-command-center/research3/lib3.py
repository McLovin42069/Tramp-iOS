"""Round-3 research library: new information sources.

    import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research3"); import lib3
    D = lib3.load_stocks()     # stocks + core instruments, daily, discovery ends 2023-12-29
    L = lib3.load_long()       # long-history ETFs/indices + volatility family, discovery ends 2018-12-31

STOCK DATA  D
  D["O"],D["H"],D["L"],D["C"],D["V"]   [date x ticker] 2016-11 onward, 828 instruments (343 US, 200 Europe, 142 Asia stocks + 143 core)
  D["meta"]     index ticker: name, cls, group (sector for US stocks, country for Europe/Asia), core
  D["shortvol"] {"short": [date x ticker], "total": [date x ticker]}  FINRA off-exchange short-sale volume and total reported
                volume per day, US-listed stocks and ETFs, from 2018-08-01. Published the same evening: a value for day t
                is known after the close of t, so it may be used in a signal on row t (trades happen at the close of t+1).
  D["earnings"] long frame: ticker, ts (announcement time, New York), usable_date (first row whose close is after the
                announcement), eps_est, eps_rep, surprise_pct. Worldwide, back to ~2002. Rows with NaN eps_rep are future/unknown.
  D["ratings"]  long frame (US stocks, 2012 onward): ticker, ts, usable_date, Firm, ToGrade, FromGrade,
                Action (up / down / main / init / reit), priceTargetAction, currentPriceTarget, priorPriceTarget.
  D["short"], D["shares"], D["spdr"], D["cot"]  as in round 1 (twice-monthly short interest, net issuance, SPDR flows, CFTC).

LONG DATA  L   (see lib2 docstring for O/H/L/C/V and L["spdr"]); added in round 3:
  volatility family in L["C"]: ^VIX (1990), ^VIX9D (2011), ^VIX3M (2006), ^VIX6M (2008), ^VVIX (2007), ^SKEW (1990), ^VXN, ^OVX,
  ^GVZ, ^MOVE (2002) as signals; tradable vol products VIXY, VIXM (2011), SVXY, UVXY (2011-10), VXX (2018).
  NOTE: SVXY changed from -1x to -0.5x leverage in Feb 2018 after losing ~90% in one day; UVXY from 2x to 1.5x. Treat with care.
  L["spdr_premium_pct"]  [date x fund] unadjusted close versus the SAME DAY's NAV, in percent. NAV is published in the evening,
                         so the premium of day t may be used in a signal on row t only with exec="next_close".

CONVENTIONS
  Cross-sectional stock signals: evaluate ONLY with lib3.xs_eval(sig, D, h, cols=..., cost_bps=...) — signal on row t uses data
  up to the close of t, trades at the close of t+1, sector/region-neutral forward returns, t-statistics on non-overlapping
  periods. Costs: 5 bps US large caps, 15 bps Europe/Asia.
  Strategies on ETFs: lib3.daily_strategy / segment_strategy (2 bps) and lib3.ts_eval; call L = lib3.us_calendar(L) first so
  that sessions after US holidays are not dropped.
  SURVIVORSHIP: the stock list contains only companies that are large TODAY. Signals that proxy for past smallness,
  illiquidity or volatility show large FAKE edges. Every stock signal must also be evaluated after lib3.size_neutral(sig, D).
"""
import os, sys, pickle
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "research")); sys.path.insert(0, str(HERE.parent / "research2"))
import lib as _l1, lib2 as _l2
xs_eval, residual, tickers, fwd_return = _l1.xs_eval, _l1.residual, _l1.tickers, _l1.fwd_return
daily_strategy, segment_strategy, session_returns, ts_eval = _l2.daily_strategy, _l2.segment_strategy, _l2.session_returns, _l2.ts_eval
SCUT, LCUT = pd.Timestamp("2023-12-29"), pd.Timestamp("2018-12-31")
_HO = lambda: os.environ.get("MFCC_HOLDOUT") == "1"


def load_stocks():
    return pickle.load(open(HERE / ("stocks_full.pkl" if _HO() else "stocks_discovery.pkl"), "rb"))


def load_long():
    return pickle.load(open(HERE / ("long_full.pkl" if _HO() else "long_discovery.pkl"), "rb"))


def us_calendar(L):
    """Restrict every [date x ticker] frame to US sessions (days on which SPY traded)."""
    ix = L["C"]["SPY"].dropna().index
    return {k: (v.loc[v.index.isin(ix)] if isinstance(v, pd.DataFrame) else v) for k, v in L.items()}


def size_neutral(sig, D, n=3):
    """Remove the part of a stock signal explained by size/liquidity: subtract the mean signal of the stock's own
    dollar-volume bucket (terciles within asset class, trailing 250 days) on each date."""
    cols = [c for c in sig.columns if c in D["C"].columns]
    dv = (D["C"][cols] * D["V"][cols]).rolling(250, min_periods=60).median()
    cls = D["meta"]["cls"].reindex(cols)
    out = sig[cols].copy()
    for c in cls.unique():
        m = (cls == c).values
        if m.sum() < 9:
            continue
        b = np.ceil(dv.loc[:, m].rank(axis=1, pct=True) * n).clip(1, n)
        s = sig[cols].loc[:, m]
        adj = s.copy()
        for k in range(1, n + 1):
            mk = b.reindex(s.index) == k
            adj = adj.where(~mk, s.sub(s.where(mk).mean(axis=1), axis=0))
        out.loc[:, m] = adj
    return out


def event_panel(events, D, value_col, hold=20, agg="last"):
    """Place event values on (usable_date, ticker) and carry them forward for `hold` trading days.
    events: long frame with columns ticker, usable_date and `value_col`. Returns [date x ticker] with NaN elsewhere."""
    e = events.dropna(subset=["usable_date", value_col])
    e = e[e["ticker"].isin(D["C"].columns) & e["usable_date"].isin(D["C"].index)]
    p = e.pivot_table(index="usable_date", columns="ticker", values=value_col, aggfunc=agg)
    return p.reindex(index=D["C"].index, columns=D["C"].columns).ffill(limit=max(hold - 1, 0))
