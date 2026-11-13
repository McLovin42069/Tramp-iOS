NAME = "Always-on BTC+ETH spot/perp cash-and-carry (50/50 capital, 1x short)"
RATIONALE = ("Cash-and-carry: long spot, short the Binance USDT perpetual in equal notional, always on, no signal. Leveraged longs pay funding to shorts; the premium exists because demand for leverage in crypto exceeds the balance sheet willing to supply it. CAPITAL: 50% of total capital buys spot, 50% is USDT margin for the short (short notional = 1x its margin, liquidation only after roughly a +90% spot rise without top-up; capital is re-split daily and that turnover is charged). Returns are on TOTAL capital; idle margin earns nothing. COSTS: 5 bps per leg on entry and on every rebalance. ASSUMPTIONS: perp and spot price legs cancel exactly (no perp prices available) so the vol and t-stat are grossly understated/overstated - real mark-to-market basis noise is not in the series; exchange/counterparty failure (FTX, Nov 2022 = total loss) and USDT de-peg are NOT in the series. Net of the T-bill rate the yield was about zero or negative in 2022-23. Half BTC, half ETH. ETH alone was -0.2% in 2022 (negative funding around the Merge).")
VARIANTS_TRIED = 48
DATA = "crypto"
BENCH = None
COINS = ['BTCUSDT', 'ETHUSDT']
def strategy(D):
    import numpy as np, pandas as pd
    N, FEE = 0.5, 5.0            # hedged notional = 50% of TOTAL capital (50% spot, 50% margin; short at 1x of its margin); 5 bps per leg per trade
    spot = {"BTCUSDT": "BTC-USD", "ETHUSDT": "ETH-USD"}
    f = D["funding"][COINS].copy(); f.index = f.index.round("h"); f = f[~f.index.duplicated()]
    g = f.copy(); g.index = g.index - pd.Timedelta(hours=8)          # a short opened at the close of D-1 (00:00 UTC of D) earns the
    earn = g.groupby(g.index.normalize()).sum(min_count=1)           # 08:00 and 16:00 payments of D and the 00:00 payment of D+1
    W = pd.DataFrame(1.0 / len(COINS), index=earn.index, columns=COINS)   # always on, fixed weights, no signal
    held = W.shift(1).fillna(0.0)
    fund = (held * earn.fillna(0.0)).sum(axis=1) * N
    turn = W.diff().abs().fillna(W.abs()).shift(1).fillna(0.0).sum(axis=1)
    cost = turn * N * 2 * FEE / 1e4                                   # entry: both legs
    r = D["C"][[spot[c] for c in COINS]].pct_change(fill_method=None).set_axis(COINS, axis=1).reindex(earn.index).abs().fillna(0.0)
    rebal = (held * r).sum(axis=1) * N * 2 * FEE / 1e4                # daily re-split of capital between spot and margin: both legs trade N*|r|
    return (fund - cost - rebal).iloc[1:-1]
DISCOVERY = {'days': 1459, 'active_days_pct': 100.0, 'ann_return_pct': 5.422127985004814, 'ann_vol_pct': 0.6220318533157932, 'sharpe': 8.7168011671777, 't': 20.974157034733757, 'max_drawdown_pct': -0.45114135767929664, 'positive_years': '4/4', 'first_half_ann_pct': 9.327100907591523, 'second_half_ann_pct': 1.52250434039425, 'mde_ann_pct': 0.6462867585125862, 'by_year_pct': {2020: 11.22, 2021: 17.77, 2022: 0.74, 2023: 3.72}, 'from': '2020-01-01', 'to': '2023-12-29', 'worst_day_pct': -0.19301469877546507, 'worst_month_pct': -0.33654075269124273, 'ann_return_365_pct': 7.85347902589983}
