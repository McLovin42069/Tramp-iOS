"""Shared research library. Every candidate must be evaluated with these functions so results are comparable.

CONVENTIONS (do not change them)
  * A signal value on row t may use only information available at the CLOSE of day t.
  * Trades happen at the CLOSE of day t+1 (one full day later). This removes time-zone leakage
    (Asia/Europe close before the US) and makes every result executable by a private investor.
  * Cross-sectional results are measured on sector/region-neutral ("residual") forward returns.
  * t-statistics credit only NON-overlapping periods.
  * Costs: `cost_bps` per unit of turnover (default 10 bps one-way).

DATA  D = load()
  D["O"], D["H"], D["L"], D["C"], D["V"]  DataFrames [date x ticker], prices adjusted for splits/dividends, local currency
  D["meta"]   index ticker; columns name, cls (asset class), group (sector or country), core (True = ETF/future/FX/crypto)
              classes: 'US Stocks' (groups = sectors), 'Europe Stocks' / 'Asia Stocks' (groups = countries), and core classes
              'US Equities','Europe Equities','Asia-Pacific Equities','EM Equities','Sovereign Bonds','Credit','Cash',
              'Commodities','FX','Futures & Vol','Crypto'
  D["spdr"]   dict so / nav / tna / close: [date x fund] for 55 SPDR ETFs (so = shares outstanding; daily flow = so.diff()*nav).
              so for day t is public on t+1.
  D["short"]  long frame: date (settlement), pub_date (first usable day), symbol, si (shares short), adv, dtc (days to cover). US only.
  D["shares"] [date x ticker] cumulative log net share issuance (already lagged). 12-month issuance = x - x.shift(250).
  D["cot"]    long frame: date (already lagged to publication), contract, spec_net_pct_oi, comm_net_pct_oi, open_interest_all
"""
import os, pickle
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
CUTOFF = pd.Timestamp("2023-12-29")


def load():
    """Discovery data (ends 2023-12-29). The hold-out file is only opened by holdout.py."""
    name = "data_full.pkl" if os.environ.get("MFCC_HOLDOUT") == "1" else "data_discovery.pkl"
    return pickle.load(open(HERE / name, "rb"))


def tickers(D, cls=None, core=None):
    m = D["meta"]
    if cls is not None:
        m = m[m["cls"].isin([cls] if isinstance(cls, str) else cls)]
    if core is not None:
        m = m[m["core"] == core]
    return [t for t in m.index if t in D["C"].columns]


def residual(X, D):
    """X minus the median of the instrument's own group on that date (asset class if the group has < 3 members)."""
    cols = list(X.columns)
    g, c = D["meta"]["group"].reindex(cols), D["meta"]["cls"].reindex(cols)
    small = (g.map(g.value_counts()) < 3).values
    gm = X.T.groupby(g.values).transform("median").T.values
    cm = X.T.groupby(c.values).transform("median").T.values
    return X - np.where(small[None, :], cm, gm)


def fwd_return(D, h, resid=True, cols=None):
    """Return from the close of t+1 to the close of t+1+h, aligned on row t."""
    C = D["C"] if cols is None else D["C"][cols]
    f = C.shift(-h - 1) / C.shift(-1) - 1
    return residual(f, D) if resid else f


def xs_eval(sig, D, h, cols=None, q=0.2, step=5, start=None, end=None, resid=True, cost_bps=10.0, min_names=30):
    """Cross-sectional test: top q minus bottom q of `sig` (DataFrame [date x ticker]) on forward returns over h days.
    Returns a dict; 'spread_pct' is per h-day period. Positive means HIGH signal outperformed."""
    cols = [c for c in (cols or list(sig.columns)) if c in D["C"].columns and c in sig.columns]
    S = sig[cols].replace([np.inf, -np.inf], np.nan)
    R = fwd_return(D, h, resid, cols)
    idx = S.index.intersection(R.index)
    pos = np.arange(260, len(idx) - h - 1, step)
    dates = idx[pos]
    if start is not None:
        dates = dates[dates >= pd.Timestamp(start)]
    if end is not None:
        dates = dates[dates <= pd.Timestamp(end)]
    sr = S.loc[dates].rank(axis=1, pct=True)
    rr = R.loc[dates]
    ok = sr.notna() & rr.notna()
    enough = ok.sum(axis=1) >= min_names
    top, bot = (sr > 1 - q) & ok, (sr <= q) & ok
    sp = (rr.where(top).mean(axis=1) - rr.where(bot).mean(axis=1))[enough].dropna()
    if len(sp) < 10:
        return {"n_eff": 0, "note": "too few dates"}
    ic = sr.where(ok).corrwith(rr.rank(axis=1, pct=True).where(ok), axis=1)[enough].dropna()
    n_eff = max(len(sp) * step / (h + 1), 1.0)
    t = lambda x: float(x.mean() / (x.std(ddof=1) / np.sqrt(n_eff))) if x.std(ddof=1) > 0 else 0.0
    # turnover of the long and short books between consecutive NON-overlapping rebalances
    k = max(int(round((h + 1) / step)), 1)
    tt, bb = top[enough].iloc[::k], bot[enough].iloc[::k]
    def churn(m):
        a, b = m.iloc[:-1].values, m.iloc[1:].values
        den = np.maximum(a.sum(1), 1)
        return float(np.mean((a & ~b).sum(1) / den)) if len(a) else np.nan
    turn = np.nanmean([churn(tt), churn(bb)])
    cost = 2 * 2 * turn * cost_bps / 100.0          # long+short books, sell+buy, in % per period
    half = len(sp) // 2
    return {"h": h, "spread_pct": float(sp.mean() * 100), "t": t(sp), "n_eff": int(round(n_eff)), "hit_pct": float((sp > 0).mean() * 100),
            "ic": float(ic.mean()), "ic_t": t(ic), "turnover": float(turn), "net_spread_pct": float(sp.mean() * 100 - cost),
            "first_half_pct": float(sp.iloc[:half].mean() * 100), "second_half_pct": float(sp.iloc[half:].mean() * 100),
            "by_year_pct": {int(y): round(float(v) * 100, 3) for y, v in sp.groupby(sp.index.year).mean().items()},
            "names_per_side": float(top[enough].sum(axis=1).mean()), "from": str(sp.index[0].date()), "to": str(sp.index[-1].date())}


def weights_to_returns(W, D, cost_bps=10.0):
    """Daily strategy returns from target weights W [date x ticker] decided at the close of t and traded at the
    close of t+1 (so they earn the return of day t+2 onward). Costs charged on turnover."""
    cols = [c for c in W.columns if c in D["C"].columns]
    r = D["C"][cols].pct_change(fill_method=None)
    Wl = W[cols].reindex(r.index).ffill().shift(2)
    gross = (Wl * r).sum(axis=1, min_count=1)
    cost = Wl.diff().abs().sum(axis=1) * cost_bps / 1e4
    return (gross - cost).dropna()


def ts_eval(ret, bench=None, start=None, end=None):
    """Evaluate a daily return series. If `bench` (daily returns) is given, also reports alpha versus it."""
    ret = ret.dropna()
    if start is not None:
        ret = ret[ret.index >= pd.Timestamp(start)]
    if end is not None:
        ret = ret[ret.index <= pd.Timestamp(end)]
    if len(ret) < 60:
        return {"days": len(ret), "note": "too short"}
    ann, vol = ret.mean() * 252, ret.std() * np.sqrt(252)
    eq = (1 + ret).cumprod()
    out = {"days": len(ret), "ann_return_pct": float(ann * 100), "ann_vol_pct": float(vol * 100), "sharpe": float(ann / vol) if vol > 0 else 0.0,
           "t": float(ret.mean() / ret.std() * np.sqrt(len(ret))) if ret.std() > 0 else 0.0, "max_drawdown_pct": float((eq / eq.cummax() - 1).min() * 100),
           "by_year_pct": {int(y): round(float((1 + g).prod() - 1) * 100, 2) for y, g in ret.groupby(ret.index.year)},
           "from": str(ret.index[0].date()), "to": str(ret.index[-1].date())}
    if bench is not None:
        b = bench.reindex(ret.index).fillna(0.0)
        beta = float(np.cov(ret, b)[0, 1] / b.var()) if b.var() > 0 else 0.0
        a = ret - beta * b
        out.update({"beta": beta, "alpha_ann_pct": float(a.mean() * 252 * 100), "alpha_t": float(a.mean() / a.std() * np.sqrt(len(a))) if a.std() > 0 else 0.0,
                    "bench_sharpe": float(b.mean() / b.std() * np.sqrt(252)) if b.std() > 0 else 0.0})
    return out
