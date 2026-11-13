"""Round-4 research library: macro events, energy, weather, liquidity, futures sessions, crypto carry.

    import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research4"); import lib4

L = lib4.us_calendar(lib4.load_long())      DAILY, discovery ends 2018-12-31
    L["O"],["H"],["L"],["C"],["V"]  [date x ticker]: ETFs from inception (SPY 1993, sectors 1998, TLT/IEF 2002, GLD 2004, USO 2006,
        UNG 2007, CORN/WEAT/SOYB ~2010-11 ...), futures front contracts from 2000 (ES=F NQ=F RTY=F YM=F ZN=F ZB=F ZT=F ZF=F GC=F SI=F HG=F
        CL=F BZ=F NG=F HO=F RB=F ZC=F ZS=F ZW=F KC=F SB=F CT=F LE=F 6E=F 6J=F BTC=F ETH=F), indices and yields ("^..." are signals only),
        volatility family (^VIX, ^VIX3M, ...). Yahoo continuous futures are spliced at the roll WITHOUT adjustment: returns on roll
        days contain the calendar spread (large for NG=F, CL=F, grains). Prefer ETFs (USO, UNG, CORN, GLD, TLT ...) for anything you
        would trade, and use futures series as signals or for index/rates/metals where the roll gap is small.
    L["fomc"]        DatetimeIndex of scheduled FOMC decision days 2000-2026 (the calendar is public a year ahead -> usable in advance)
    L["eia_weekly"]  weekly frame (index = week-ending Friday): crude_stocks, gasoline_stocks, distillate_stocks (thousand barrels),
                     natgas_storage (Bcf), crude_production. Petroleum data are RELEASED the following Wednesday 10:30 ET (Thursday after a
                     holiday), natural-gas storage the following Thursday 10:30 ET. Use lib4.eia_released(L, col) for a release-dated series.
    L["temp_c"], L["precip_mm"]  daily mean temperature and precipitation for 17 cities since 1990 (US gas-demand cities, corn belt,
                     Amsterdam/Frankfurt/London). Realised weather of day t is known at the end of day t. No forecasts are available.
    L["tga_bn"]      Treasury General Account balance, $bn, daily since 2005 (published next business day ~16:00 -> lag 1 day)
    L["rrp_bn"]      Fed overnight reverse-repo take-up, $bn, daily since 2013 (published same day ~13:15)
    L["auctions"]    Treasury auctions since 2000: auction_date, issue_date, security_type, security_term, offering_amt, bid_to_cover_ratio, high_yield
    L["spdr"], L["spdr_premium_pct"]  as in round 3.

H = lib4.load_fut()     HOURLY bars, New York time, bar stamped at its START, ~730 sessions; discovery = first 65% of days.
    Futures trade ~23 hours (18:00 previous day to 17:00): ES=F NQ=F RTY=F YM=F ZN=F ZB=F ZT=F GC=F SI=F HG=F CL=F NG=F BZ=F 6E=F 6J=F
    BTC=F ETH=F; plus ETFs SPY QQQ TLT GLD USO UNG (regular session only). H["fomc"] = FOMC decision days (statement 14:00 ET).

X = lib4.load_crypto()  discovery ends 2023-12-31
    X["funding"]  [timestamp x symbol] perpetual-futures funding rate per 8 hours (Binance USDT-margined: BTCUSDT ETHUSDT SOLUSDT BNBUSDT
                  XRPUSDT DOGEUSDT), from 2019-09. A SHORT perpetual position RECEIVES the funding rate when it is positive.
    X["C"], X["O"] daily spot closes/opens (BTC-USD ...) and CME front futures (BTC=F, ETH=F).

EXECUTION AND COSTS
  lib4.daily_strategy(pos, L, cost_bps, exec="next_close"|"same_close"), lib4.segment_strategy(pos_on, pos_day, L, cost_bps): see lib2.
     ETFs 2 bps; calendar-only rules may use exec="same_close" with the position set the day before.
  lib4.bar_strategy(pos, H, cost_bps): pos[b] uses data up to the close of bar b and is held over the next bar. Costs per unit turnover:
     1 bp for equity-index futures (micro E-mini: about half a tick plus commission), 2 bps for other futures and ETFs.
  lib4.ts_eval(ret, bench): t, Sharpe, drawdown, by-year, alpha vs bench, mde_ann_pct (smallest annual return detectable at t = 2.5).
"""
import os, sys, pickle
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "research2"))
import lib2 as _l2
daily_strategy, segment_strategy, session_returns, ts_eval = _l2.daily_strategy, _l2.segment_strategy, _l2.session_returns, _l2.ts_eval
CUTS = pickle.load(open(HERE / "cuts.pkl", "rb")) if (HERE / "cuts.pkl").exists() else {}
_HO = lambda: os.environ.get("MFCC_HOLDOUT") == "1"
_ld = lambda stem: pickle.load(open(HERE / f"{stem}_{'full' if _HO() else 'discovery'}.pkl", "rb"))
load_long, load_fut, load_crypto = (lambda: _ld("long")), (lambda: _ld("fut")), (lambda: _ld("crypto"))


def us_calendar(L):
    """Restrict price panels to US sessions (days on which SPY traded). Non-price entries are left untouched."""
    ix = L["C"]["SPY"].dropna().index
    return {k: (v.loc[v.index.isin(ix)] if k in ("O", "H", "L", "C", "V") else v) for k, v in L.items()}


def eia_released(L, col):
    """Weekly EIA series re-dated to the day it became public (week-ending Friday + 5 days for petroleum, + 6 for natural gas)."""
    s = L["eia_weekly"][col].dropna()
    return s.set_axis(s.index + pd.Timedelta(days=6 if col == "natgas_storage" else 5))


def bar_strategy(pos, H, cost_bps=1.0):
    """DAILY net return series from hourly positions. pos[b] is held over bar b+1 (close of b to close of b+1).
    Days are trade dates in New York time (bars from 18:00 belong to the next trade date)."""
    pos = pos.to_frame() if isinstance(pos, pd.Series) else pos
    cols = [c for c in pos.columns if c in H["C"].columns]
    out = []
    for c in cols:                                   # each instrument on its own bar grid (futures and ETFs trade different hours)
        px = H["C"][c].dropna()
        p = pos[c].reindex(px.index).fillna(0.0).shift(1)
        out.append(p * px.pct_change() - p.diff().abs() * cost_bps / 1e4)
    net = pd.concat(out, axis=1).sum(axis=1)
    trade_date = (net.index + pd.Timedelta(hours=6)).normalize()
    return net.groupby(trade_date).sum()
