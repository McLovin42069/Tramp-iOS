import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research")
import lib, numpy as np, pandas as pd
D = lib.load(); C = D["C"]; R = C.pct_change(fill_method=None)
START = "2017-12-01"
spy = R["SPY"]
W6040 = pd.DataFrame({"SPY":0.6,"IEF":0.4}, index=C.index)
# rebalance monthly only
def month_end(W):
    me = pd.Series(W.index, index=W.index).groupby([W.index.year, W.index.month]).max().values
    return W.loc[me].reindex(W.index).ffill()
r6040 = lib.weights_to_returns(month_end(W6040), D)
N = [0]
def ev(W, name, start=START, show=True, monthly=True):
    N[0] += 1
    if monthly: W = month_end(W)
    r = lib.weights_to_returns(W, D)
    e = lib.ts_eval(r, spy, start=start)
    e2 = lib.ts_eval(r, r6040, start=start)
    h1 = lib.ts_eval(r, spy, start=start, end="2020-12-31"); h2 = lib.ts_eval(r, spy, start="2021-01-01")
    to = W.diff().abs().sum(axis=1)[start:].sum() / (len(W[start:]) / 252)
    if show:
        print(f"{name:42s} ret {e['ann_return_pct']:5.1f} vol {e['ann_vol_pct']:5.1f} SR {e['sharpe']:.2f} DD {e['max_drawdown_pct']:6.1f} beta {e['beta']:.2f} a {e['alpha_ann_pct']:5.1f} at {e['alpha_t']:5.2f} | a6040_t {e2['alpha_t']:5.2f} | h1 at {h1['alpha_t']:5.2f} h2 at {h2['alpha_t']:5.2f} TO {to:4.1f} | "
              + " ".join(f"{str(y)[2:]}:{v:.0f}" for y, v in e['by_year_pct'].items()))
    return e, e2, r
def base():
    for n, r in [("SPY", spy), ("60/40", r6040)]:
        e = lib.ts_eval(r, spy, start=START)
        print(f"{n:42s} ret {e['ann_return_pct']:5.1f} vol {e['ann_vol_pct']:5.1f} SR {e['sharpe']:.2f} DD {e['max_drawdown_pct']:6.1f} | " + " ".join(f"{str(y)[2:]}:{v:.0f}" for y, v in e['by_year_pct'].items()))
