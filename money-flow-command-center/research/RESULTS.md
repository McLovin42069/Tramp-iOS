# Edge search — results (run 2026-11-13)

Seven research agents searched the discovery data (2016-11 → 2023-12-29) with a shared evaluation library
(`lib.py`): signal at close t, trade at close t+1, sector/region-neutral returns, t-statistics on non-overlapping
periods, 10 bps costs. Bar for submission: t ≥ 2.5, stable across years and halves, positive after costs.

| Family | Variants | Best honest result | Submitted |
|---|---|---|---|
| alloc — cross-asset trend / allocation | 41 | alpha t 1.75 | 0 |
| posit — short interest, issuance | 51 | t 1.84 | 0 |
| leadlag — lead-lag, pairs, CFTC | 75 | t ≈ 1.7 | 0 |
| intl — Europe / Asia stocks | 36 (×3 universes) | t 2.07 (Asia, residual momentum + low issuance, 60d) | 0 |
| usxs — US stocks price/volume | 53 | below bar; illiquidity t 5.1 is a survivorship artefact | 0 |
| flows — SPDR fund flows | ~160 | uniformly mild contrarian, a few bps/week | 0 |
| event — calendar / events | ~130 | Treasury month-end gross t 3.1, dead after costs | 0 |

Total ≈ 546 variants, 0 candidates cleared the bar.

## Findings that change earlier conclusions
- **Survivorship bias is large.** 0 of 343 US tickers delist; the equal-weight universe beats SPY in 6 of 7 years;
  the lowest dollar-volume quintile earns 25%/yr vs 14%. Anything proxying past smallness/illiquidity/volatility
  looks predictive. The app's model no longer uses volatility or illiquidity as inputs; without them its
  validation IC is ≈ 0.
- **Real fund flows are mildly contrarian, never tradable.** The one large statistic (SPY 60d flow, t ≈ −4 over
  2006–2023) comes from 2008–09.
- **Lead-lag vanishes after a one-day delay.**

## One-shot hold-out checks (2024-01-02 → 2026-11-13) of the three closest misses
| Pattern | Discovery | Hold-out | Reading |
|---|---|---|---|
| Asia: residual momentum 12-1 + low issuance, 60d, country-neutral | +1.91% / 60d, t 2.07 | +1.86% / 60d, t 1.32 (11 periods), positive in 2024, 2025, 2026; full sample t 2.61 | Same size out of sample; not significant alone |
| Overnight vs intraday return, index ETFs (gross) | SPY +3.9 bp/night (t 2.2), IWM +6.8 (3.1), QQQ +4.6 (2.2); intraday ≈ 0 | SPY +5.7 (t 2.5), IWM +6.6 (2.0), QQQ +7.5 (2.4); intraday +1.7 / −0.6 / +0.8 (t < 0.6) | Replicates. Not an excess return over buy-and-hold; useful for order timing |
| Treasuries, last 3 trading days of the month | IEF +7.6 bp/day vs −1.0 (t 3.1) | IEF +4.8 vs −0.1 (t 1.3); TLT +1.1 vs −1.4 (t 0.3) | Not confirmed |

Hold-out data were opened only by `holdout.py` and `holdout_extra.py`, once, after the definitions were fixed.
