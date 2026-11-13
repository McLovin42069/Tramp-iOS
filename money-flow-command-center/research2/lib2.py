"""Round-2 research library: long daily history (no survivorship) and hourly bars.

DATA
  L = load_long()   dict O/H/L/C/V  [date x ticker], 103 instruments, daily, split/dividend adjusted. Discovery ends 2018-12-31.
                    ETFs from their inception (SPY 1993, sector SPDRs 1998, QQQ 1999, IWM 2000, TLT/IEF/SHY 2002, GLD 2004,
                    HYG/UUP 2007 ...), indices (^GSPC from 1927; opens unreliable before ~1962), yields ^IRX ^FVX ^TNX ^TYX
                    (in percent), ^VIX from 1990, futures from 2000, FX, BTC. Symbols starting with "^" are NOT tradable:
                    use them as signals only. L["spdr"] = dict so/nav/tna for 55 SPDR funds since inception
                    (daily flow = so.diff()*nav; so of day t is public on t+1).
  I = load_intra()  dict O/H/L/C/V  [bar x ticker], hourly bars in New York time, 7 bars per session stamped at bar START
                    (09:30, 10:30, ..., 15:30; the 15:30 bar is 30 minutes). 35 ETFs + 80 liquid US stocks.
                    Discovery = first 474 sessions (2023-12-15 .. 2025-11-05).

EXECUTION CONVENTIONS (all three helpers charge `cost_bps` per unit of turnover, one way)
  daily_strategy(pos, L, exec=...)   pos[t] may use data up to the close of t.
        exec="next_close": traded at the close of t+1 (strict; earns the return of day t+2).
        exec="same_close": traded at the close of t itself (earns day t+1). Realistic only for liquid US ETFs when the
                           signal can be computed a few minutes before the close; say so explicitly if you use it.
  segment_strategy(pos_on, pos_day, L)   pos_on[t]  = position from the close of t to the open of t+1 (info up to close t),
                                         pos_day[t] = position from the open of t to the close of t   (info up to open t,
                                         i.e. it may use the opening price of t but nothing later).
  bar_strategy(pos, I)   pos[b] may use data up to the close of bar b and is held over the next bar's close-to-close
                         return (traded at the close of bar b). A position held across the last bar earns the overnight gap.
  Default costs: 2 bps for liquid US ETFs and futures, 5 bps for single stocks. Never report gross-only results.

EVALUATION
  ts_eval(ret, bench=None)  on a DAILY net return series. Reports t, Sharpe, drawdown, by-year, alpha vs bench, and
                            `mde_ann_pct`: the smallest annual return this sample could have detected at t = 2.5.
"""
import os, pickle
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
CUTS = pickle.load(open(HERE / "cuts.pkl", "rb"))
_HO = lambda: os.environ.get("MFCC_HOLDOUT") == "1"


def load_long():
    return pickle.load(open(HERE / ("long_full.pkl" if _HO() else "long_discovery.pkl"), "rb"))


def load_intra():
    return pickle.load(open(HERE / ("intra_full.pkl" if _HO() else "intra_discovery.pkl"), "rb"))


def _frame(x, like):
    return x.to_frame(like.columns[0]) if isinstance(x, pd.Series) and x.name not in like.columns else (x.to_frame() if isinstance(x, pd.Series) else x)


def daily_strategy(pos, L, cost_bps=2.0, exec="next_close"):
    pos = pos.to_frame() if isinstance(pos, pd.Series) else pos
    cols = [c for c in pos.columns if c in L["C"].columns]
    r = L["C"][cols].pct_change(fill_method=None)
    lag = {"next_close": 2, "same_close": 1}[exec]
    P = pos[cols].reindex(r.index).ffill().shift(lag)
    return ((P * r).sum(axis=1, min_count=1) - P.diff().abs().sum(axis=1) * cost_bps / 1e4).dropna()


def session_returns(L, cols=None):
    """(overnight, intraday) return frames: close(t-1)->open(t) and open(t)->close(t)."""
    C = L["C"] if cols is None else L["C"][cols]
    O = L["O"] if cols is None else L["O"][cols]
    return O / C.shift(1) - 1, C / O - 1


def segment_strategy(pos_on, pos_day, L, cost_bps=2.0):
    pos_on = pos_on.to_frame() if isinstance(pos_on, pd.Series) else pos_on
    pos_day = pos_day.to_frame() if isinstance(pos_day, pd.Series) else pos_day
    cols = [c for c in pos_on.columns if c in L["C"].columns and c in pos_day.columns]
    on, day = session_returns(L, cols)
    Pn = pos_on[cols].reindex(on.index).fillna(0.0).shift(1)     # decided at close t-1, earns overnight into t
    Pd = pos_day[cols].reindex(on.index).fillna(0.0)             # decided at open t, earns the day session of t
    gross = (Pn * on).sum(axis=1, min_count=1).fillna(0) + (Pd * day).sum(axis=1, min_count=1).fillna(0)
    # trades: at the open of t (from overnight position to day position) and at the close of t (day -> next overnight)
    turn = (Pd - Pn).abs().sum(axis=1) + (pos_on[cols].reindex(on.index).fillna(0.0) - Pd).abs().sum(axis=1)
    live = L["V"][cols].reindex(on.index).fillna(0).sum(axis=1) > 0 if "V" in L else True
    return (gross - turn * cost_bps / 1e4)[live].dropna()


def bar_strategy(pos, I, cost_bps=2.0):
    """Returns a DAILY net return series (bars summed per session date of the bar in which the return is earned)."""
    pos = pos.to_frame() if isinstance(pos, pd.Series) else pos
    cols = [c for c in pos.columns if c in I["C"].columns]
    C = I["C"][cols]
    rc = C.pct_change(fill_method=None)
    P = pos[cols].reindex(C.index).fillna(0.0).shift(1)
    net = (P * rc).sum(axis=1, min_count=1).fillna(0) - P.diff().abs().sum(axis=1) * cost_bps / 1e4
    return net.groupby(net.index.normalize()).sum()


def ts_eval(ret, bench=None, start=None, end=None):
    ret = ret.dropna()
    if start is not None:
        ret = ret[ret.index >= pd.Timestamp(start)]
    if end is not None:
        ret = ret[ret.index <= pd.Timestamp(end)]
    if len(ret) < 60 or ret.std() == 0:
        return {"days": len(ret), "note": "too short or flat"}
    ann, vol = ret.mean() * 252, ret.std() * np.sqrt(252)
    eq = (1 + ret).cumprod()
    yrs = ret.groupby(ret.index.year).apply(lambda g: (1 + g).prod() - 1)
    half = len(ret) // 2
    out = {"days": len(ret), "active_days_pct": float((ret != 0).mean() * 100), "ann_return_pct": float(ann * 100), "ann_vol_pct": float(vol * 100),
           "sharpe": float(ann / vol), "t": float(ret.mean() / ret.std() * np.sqrt(len(ret))), "max_drawdown_pct": float((eq / eq.cummax() - 1).min() * 100),
           "positive_years": f"{int((yrs > 0).sum())}/{len(yrs)}", "first_half_ann_pct": float(ret.iloc[:half].mean() * 252 * 100),
           "second_half_ann_pct": float(ret.iloc[half:].mean() * 252 * 100),
           "mde_ann_pct": float(2.5 * ret.std() / np.sqrt(len(ret)) * 252 * 100),
           "by_year_pct": {int(y): round(float(v) * 100, 2) for y, v in yrs.items()}, "from": str(ret.index[0].date()), "to": str(ret.index[-1].date())}
    if bench is not None:
        b = bench.reindex(ret.index).fillna(0.0)
        beta = float(np.cov(ret, b)[0, 1] / b.var()) if b.var() > 0 else 0.0
        a = ret - beta * b
        out.update({"beta": beta, "alpha_ann_pct": float(a.mean() * 252 * 100), "alpha_t": float(a.mean() / a.std() * np.sqrt(len(a))) if a.std() > 0 else 0.0,
                    "bench_ann_pct": float(b.mean() * 252 * 100), "bench_sharpe": float(b.mean() / b.std() * np.sqrt(252)) if b.std() > 0 else 0.0,
                    "bench_max_drawdown_pct": float(((1 + b).cumprod() / (1 + b).cumprod().cummax() - 1).min() * 100)})
    return out
