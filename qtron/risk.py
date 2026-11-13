"""Qtron risk tools: portfolio risk, scenarios, position sizing and price levels. Pure pandas/numpy."""
import numpy as np
import pandas as pd

FACTORS = {"SPY": "Aandelen wereldwijd dalen 20%", "QQQ": "Technologie daalt 20%", "TLT": "Rente stijgt 1 procentpunt (lange obligaties −15%)", "UUP": "Dollar daalt 10%"}
SHOCKS = {"SPY": -0.20, "QQQ": -0.20, "TLT": -0.15, "UUP": -0.10}


def portfolio_risk(values: pd.Series, C: pd.DataFrame, total: float, days: int = 500):
    """values: market value per ticker (base currency). C: daily closes. total: portfolio value including cash.
    Historical simulation: today's weights applied to the last `days` daily returns (currency moves not included)."""
    tk = [t for t in values.index if t in C.columns]
    if not tk or total <= 0:
        return None
    R = C[tk].pct_change(fill_method=None).tail(days).dropna(how="all").fillna(0.0)
    w = (values[tk] / total)
    pr = R @ w
    cum20 = (1 + pr).rolling(20).apply(np.prod, raw=True) - 1
    corr = R.corr()
    avg_corr = float(corr.values[np.triu_indices(len(tk), 1)].mean()) if len(tk) > 1 else 1.0
    ind_vol = R.std() * np.sqrt(252)
    out = {"vol_pct": float(pr.std() * np.sqrt(252) * 100), "var95_pct": float(-np.percentile(pr, 5) * 100), "worst_day_pct": float(pr.min() * 100),
           "worst_20d_pct": float(cum20.min() * 100) if cum20.notna().any() else np.nan, "avg_corr": avg_corr, "invested_pct": float(w.sum() * 100),
           "largest_pct": float(w.max() * 100), "largest": w.idxmax(), "n": len(tk),
           "risk_share": ((w * ind_vol) / (w * ind_vol).sum() * 100).sort_values(ascending=False), "returns": pr, "corr": corr}
    sc = []
    for f, label in FACTORS.items():
        if f in C.columns:
            fr = C[f].pct_change(fill_method=None).reindex(R.index).fillna(0.0)
            beta = float(np.cov(pr, fr)[0, 1] / fr.var()) if fr.var() > 0 else 0.0
            sc.append({"Scenario": label, "Gevoeligheid": beta, "Effect op portefeuille %": beta * SHOCKS[f] * 100, "Effect": beta * SHOCKS[f] * total})
    out["scenarios"] = pd.DataFrame(sc)
    return out


def levels(P: dict, t: str):
    """Price levels a trader looks at: moving averages, 52-week range, recent swing levels, average true range and a volatility stop."""
    if t not in P["Close"].columns:
        return None
    c, h, l = P["Close"][t].dropna(), P["High"][t].dropna(), P["Low"][t].dropna()
    if len(c) < 30:
        return None
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    atr = float(tr.rolling(14).mean().iloc[-1])
    last = float(c.iloc[-1])
    ma = lambda n: float(c.rolling(n).mean().iloc[-1]) if len(c) >= n else np.nan
    return {"last": last, "ma50": ma(50), "ma200": ma(200), "hi52": float(h.tail(252).max()), "lo52": float(l.tail(252).min()),
            "support": float(l.tail(20).min()), "resistance": float(h.tail(20).max()), "atr": atr, "atr_pct": atr / last * 100 if last else np.nan,
            "stop": last - 2.5 * atr, "stop_pct": 2.5 * atr / last * 100 if last else np.nan, "ma50_series": c.rolling(50).mean(), "ma200_series": c.rolling(200).mean()}


def size_by_risk(total: float, risk_pct: float, stop_pct: float, max_pos_pct: float = 15.0):
    """Amount to invest so that hitting the stop loses `risk_pct` of the portfolio, capped at `max_pos_pct` of it."""
    if not stop_pct or stop_pct <= 0 or total <= 0:
        return 0.0
    return float(min(total * risk_pct / stop_pct, total * max_pos_pct / 100))
