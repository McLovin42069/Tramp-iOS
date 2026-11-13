# Edge search, round 2 — results (run 2026-11-13)

Round 2 raised statistical power: hourly bars (730 sessions, 115 instruments) and 20–30 years of daily history on index
products without survivorship bias; costs of 2 bps (ETFs) / 5 bps (stocks); same-day execution where realistic.
Discovery: daily ≤ 2018-12-31, hourly first 474 sessions. Hold-out: daily 2019-01 → 2026-11, hourly last 256 sessions.

## Agents (discovery)
| Family | Variants | Outcome |
|---|---|---|
| iidx — intraday ETF patterns | 42 | nothing; largest gross effect 1.5–2 bps per trade vs 4 bps round-trip cost; intraday momentum absent |
| ixs — intraday stock cross-section | 45 | nothing; hourly reversal is real (~0.5–4 bps per unit traded) but below a 5 bps cost |
| night — overnight / gaps | ~114 | nothing net; SPY overnight break-even 2.07 bps/trade (1.5 since 2005); effect shrinking |
| lalloc — long-history allocation | 70 | 1 candidate (trend ensemble) with caveat that all alpha is 2000–02 and 2008 |
| lcal — long-history calendar | ~123 | 2 candidates (Treasury month-end); turn-of-month gone since 2000; mean reversion decayed since 2005 |
| lflow — flows and macro, long history | ~49 | nothing; contrarian sector flow consistent in sign (2–4%/yr), not provable in 12.5 years |

## Systematic lead-lag scan (lead researcher)
161,440 signal→target→lag combinations (daily close-to-close lags 1–5, overnight→session, session→overnight, Asian
index→US session, multi-day horizons, hourly lags and day-part pairs). Bonferroni threshold |t| > 5.12.
**512 hits** on discovery (0.05 expected by chance). Main clusters: equity moves leading slow-priced bond ETFs
(HYG, JNK, EMB, MUB, TIP, LQD), SPY leading EWC, US moves followed by next-day REVERSAL in EWH/FXI/EWT, and
microstructure artefacts (BIL, own-instrument open-price noise).

Rules built from the clusters (threshold |z| > 1 fixed in advance, 2 bps, US trading calendar):

| Rule | Discovery (≤2018) | Hold-out (2019→2026) |
|---|---|---|
| A equity gap → HYG+JNK session | +8.0%/yr, t 4.4 (first half +16%, second half −0.3%) | −3.5%/yr, t −2.8 |
| B HYG day → EMB next day | +7.9%/yr, t 3.9 | −2.3%/yr, t −0.9 |
| C SPY day → EMB next day | +7.6%/yr, t 4.1 | −5.5%/yr, t −2.0 |
| D′ SPY day → EWH+FXI+EWT next day, reversed | +14.0%/yr, t 4.8 | +4.5%/yr, t 0.9 (6/8 years) |
| D″ same, long side only | +9.3%/yr, t 4.0 | +3.6%/yr, t 1.1 |
| F SPY day → EWC next day | +12.7%/yr, t 4.7 (first half +24%, second +1.5%) | +0.7%/yr, t 0.1 |
| G treasury gap → MUB session | +2.3%/yr, t 1.9 | −1.6%/yr, t −1.9 |
| H SPY day → TIP+LQD next day | +1.2%/yr, t 1.3 | −1.9%/yr, t −1.1 |

Reading: the correlations were real and large before 2019 and are gone (or reversed) since. Slow price discovery in
bond and thin country ETFs has been arbitraged away.

## Agent candidates on hold-out (2019→2026)
| Candidate | Discovery | Hold-out |
|---|---|---|
| lalloc_1 SPY trend ensemble | Sharpe 0.83 vs 0.55, alpha t 3.1 | Sharpe 0.90 vs SPY 1.00; 11.5%/yr vs 19.0%; drawdown −25% vs −34%; alpha t 0.85 → de-risking, no alpha |
| lcal_1 TLT last 3 trading days of month | +4.5%/yr, t 3.7 | +2.5%/yr, t 1.4, positive in 7 of 8 years; full sample t 3.8 → same sign, half the size, not significant alone |
| lcal_2 plus short first 3 days | +7.7%/yr, t 4.3 | +1.9%/yr, t 0.7 → not confirmed |

## Method notes
- `lib2.daily_strategy` on the shared weekday calendar drops the first US session after each holiday; the calendar
  agent and the scan rules restrict to US sessions. Other single-ETF results omit about 9 days a year.
- Pearson correlations on hourly bars are dominated by 2025-04-09; rank statistics were used.
