import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research3"); import lib3
import numpy as np, pandas as pd, json
D = lib3.load_stocks()
C = D["C"]; idx = C.index
REG = {"US": ["US Stocks"], "EU": ["Europe Stocks"], "AS": ["Asia Stocks"]}
COLS = {k: lib3.tickers(D, cls=v, core=False) for k, v in REG.items()}
COST = {"US": 5, "EU": 15, "AS": 15}
ALL = sum(COLS.values(), [])
Cf = C[ALL].ffill(limit=5)
r1 = Cf.pct_change(fill_method=None)
rr1 = lib3.residual(r1, D)            # sector/country-neutral daily return

def events():
    E = D["earnings"].copy().sort_values(["ticker", "ts"])
    E = E[E.ticker.isin(ALL)]
    E["diff"] = E.eps_rep - E.eps_est
    g = E.groupby("ticker")
    # own-history std of forecast errors (previous 8 events, excluding current), back to 2002
    E["sd8"] = g["diff"].transform(lambda x: x.shift(1).rolling(8, min_periods=4).std())
    E["sue_h"] = (E["diff"] / E["sd8"].replace(0, np.nan)).clip(-5, 5)
    E["beat"] = np.sign(E["diff"])
    def streak(x):
        out, s = [], 0
        for v in x.values:
            if np.isnan(v): s = 0
            elif v > 0: s = s + 1 if s > 0 else 1
            elif v < 0: s = s - 1 if s < 0 else -1
            else: s = 0
            out.append(s)
        return pd.Series(out, index=x.index)
    E["streak"] = g["beat"].transform(streak).clip(-6, 6)
    E["beat4"] = g["beat"].transform(lambda x: x.rolling(4, min_periods=3).mean())
    E["surp_w"] = E.surprise_pct.clip(-100, 100)
    E = E.dropna(subset=["usable_date"])
    E = E[E.usable_date.isin(idx)]
    pos = idx.get_indexer(E.usable_date)
    def at(df, off):
        p = pos + off; ok = (p >= 0) & (p < len(idx))
        ci = df.columns.get_indexer(E.ticker)
        v = np.full(len(E), np.nan); v[ok] = df.values[p[ok], ci[ok]]; return v
    E["px"] = at(Cf, -1)
    E["sue_p"] = (E["diff"] / E["px"]).clip(-0.05, 0.05)
    E["ar1"] = at(rr1, 0)                       # known at close of usable_date
    E["ar2"] = E["ar1"] + at(rr1, 1)            # known one row later
    pre = rr1.rolling(10, min_periods=5).sum().shift(1)
    E["pre10"] = at(pre, 0)
    vol = rr1.rolling(60, min_periods=30).std().shift(1)
    E["vol"] = at(vol, 0)
    E["ar1z"] = (E["ar1"] / E["vol"]).clip(-8, 8)
    return E

def panel(E, col, hold, lag=0):
    p = lib3.event_panel(E, D, col, hold)
    return p.shift(lag) if lag else p

N = [0]
def ev(sig, reg, h=20, label="", verbose=True, **kw):
    N[0] += 1
    cols = COLS[reg]
    a = lib3.xs_eval(sig, D, h, cols=cols, cost_bps=COST[reg], **kw)
    b = lib3.xs_eval(lib3.size_neutral(sig[cols], D), D, h, cols=cols, cost_bps=COST[reg], **kw)
    if verbose and a.get("n_eff"):
        yrs = a["by_year_pct"]; pos = sum(v > 0 for v in yrs.values())
        print(f"{label:38s} {reg} h={h:2d} raw sp={a['spread_pct']:+.2f} t={a['t']:+.2f} net={a['net_spread_pct']:+.2f} | sn sp={b['spread_pct']:+.2f} t={b['t']:+.2f} net={b['net_spread_pct']:+.2f} | H1 {a['first_half_pct']:+.2f} H2 {a['second_half_pct']:+.2f} yrs+ {pos}/{len(yrs)} n/side {a['names_per_side']:.0f} to={a['turnover']:.2f}")
    elif verbose: print(label, reg, a)
    return a, b

def dte_panel(center=None):
    """Trading rows until the EXPECTED next announcement = announcement timestamp of any past event + 364 calendar days
    (same quarter one year earlier, same weekday), mapped to the first row on/after it. Uses no realised future date."""
    E = D["earnings"]; E = E[E.ticker.isin(ALL)]
    exp = E.ts.dt.normalize() + pd.Timedelta(days=364)
    p = np.searchsorted(idx.values, exp.values.astype(idx.values.dtype))
    ok = p < len(idx)
    A = np.full((len(idx), len(ALL)), np.nan)
    ci = pd.Index(ALL).get_indexer(E.ticker.values[ok])
    A[p[ok], ci] = 0.0
    # backward fill a counter: rows until next expected date
    pos = np.arange(len(idx), dtype=float)[:, None]
    nxt = pd.DataFrame(np.where(np.isnan(A), np.nan, pos), index=idx, columns=ALL).bfill()
    return nxt - pos
