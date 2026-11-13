NAME = "Always-on BTC spot/perp cash-and-carry (50/50 capital, 1x short)"
RATIONALE = ("Cash-and-carry: long spot, short the Binance USDT perpetual in equal notional, always on, no signal. Leveraged longs pay funding to shorts; the premium exists because demand for leverage in crypto exceeds the balance sheet willing to supply it. CAPITAL: 50% of total capital buys spot, 50% is USDT margin for the short (short notional = 1x its margin, liquidation only after roughly a +90% spot rise without top-up; capital is re-split daily and that turnover is charged). Returns are on TOTAL capital; idle margin earns nothing. COSTS: 5 bps per leg on entry and on every rebalance. ASSUMPTIONS: perp and spot price legs cancel exactly (no perp prices available) so the vol and t-stat are grossly understated/overstated - real mark-to-market basis noise is not in the series; exchange/counterparty failure (FTX, Nov 2022 = total loss) and USDT de-peg are NOT in the series. Net of the T-bill rate the yield was about zero or negative in 2022-23. Discovery by year: 2020 +8.5%, 2021 +15.9%, 2022 +1.7%, 2023 +3.6%.")
VARIANTS_TRIED = 48
DATA = "crypto"
BENCH = None
COINS = ['BTCUSDT']
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
DISCOVERY = {'days': 1459, 'active_days_pct': 100.0, 'ann_return_pct': 4.857892466170171, 'ann_vol_pct': 0.5615088284353589, 'sharpe': 8.651497928726533, 't': 20.817025955122944, 'max_drawdown_pct': -0.8353157814176004, 'positive_years': '4/4', 'first_half_ann_pct': 7.906115707398655, 'second_half_ann_pct': 1.8138448732173411, 'mde_ann_pct': 0.5834037576552418, 'by_year_pct': {2020: 8.5, 2021: 15.86, 2022: 1.69, 2023: 3.62}, 'from': '2020-01-01', 'to': '2023-12-29', 'worst_day_pct': -0.22686353362064343, 'worst_month_pct': -0.37307684219993564, 'ann_return_365_pct': 7.036233135524254}
