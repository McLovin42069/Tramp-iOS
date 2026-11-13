import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research4"); import lib4
import numpy as np, pandas as pd
SPOT = {"BTCUSDT":"BTC-USD","ETHUSDT":"ETH-USD","SOLUSDT":"SOL-USD","BNBUSDT":"BNB-USD","XRPUSDT":"XRP-USD","DOGEUSDT":"DOGE-USD"}
def daily_funding(X):
    """Fd[D] = funding earned by a short opened at the close of D-1 (00:00 UTC of D): payments stamped 08:00, 16:00 of D and 00:00 of D+1.
    Fk[D] = funding KNOWN at the close of D with one payment of slack: payments 00:00, 08:00, 16:00 of D."""
    f = X["funding"].copy(); f.index = f.index.round("h")
    f = f[~f.index.duplicated()]
    known = f.groupby(f.index.normalize()).sum(min_count=1)
    g = f.copy(); g.index = g.index - pd.Timedelta(hours=8)
    earn = g.groupby(g.index.normalize()).sum(min_count=1)
    cnt = g.groupby(g.index.normalize()).count()
    earn = earn.where(cnt >= 1)
    return earn, known
def carry(X, W, n=0.5, fee=5.0, basis=0.0, rebal=True):
    """W[D] in [0,1] per coin (sum<=1) = share of the carry book in that coin, decided at close of D, held over D+1.
    n = hedged notional as a fraction of total capital (0.5: half spot, half margin, short at 1x of its margin;
    2/3: spot 2/3, margin 1/3, short at 2x of its margin). Returns daily net return on TOTAL capital.
    fee bps per leg per trade (2 legs); basis = adverse basis slippage (fraction of notional) per entry and per exit."""
    earn, known = daily_funding(X)
    W = W.reindex(earn.index).fillna(0.0)
    held = W.shift(1).fillna(0.0)
    fund = (held * earn.fillna(0.0)).sum(axis=1) * n
    turn = W.diff().abs().fillna(W.abs()).shift(1).fillna(0.0).sum(axis=1)   # trade at close D, booked on D+1
    cost = turn * n * (2 * fee / 1e4 + basis)
    rc = 0.0
    if rebal:   # daily re-split of capital between legs: both legs trade n*|r|
        r = X["C"][[SPOT[c] for c in W.columns]].pct_change(fill_method=None).set_axis(W.columns, axis=1).reindex(earn.index).abs().fillna(0.0)
        rc = (held * r).sum(axis=1) * n * 2 * fee / 1e4
    ret = fund - cost - rc
    return ret.iloc[1:-1]   # last day lacks the 00:00 next-day payment
def show(name, ret, bench=None):
    e = lib4.ts_eval(ret, bench)
    wm = ret.groupby(ret.index.to_period("M")).sum()
    print(f"{name:42s} t={e['t']:6.1f} ann365={ret.mean()*365*100:6.2f}% vol={ret.std()*np.sqrt(365)*100:5.2f}% act={e['active_days_pct']:4.0f}% wd={ret.min()*100:6.3f}% wm={wm.min()*100:6.2f}% yrs={e['by_year_pct']}" + (f" alpha_t={e['alpha_t']:.2f} beta={e['beta']:.2f}" if bench is not None else ""))
    return e
