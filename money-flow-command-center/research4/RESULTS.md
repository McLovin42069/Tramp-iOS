# Edge search, round 4 — results (run 2026-11-13)

New ground: macro events (FOMC, jobs days), energy inventories and weather, liquidity (Treasury account, reverse repo,
Treasury auctions), futures sessions at futures costs, crypto carry. Discovery: daily ≤ 2018-12-31, hourly futures first 65%
of sessions, crypto ≤ 2023-12-31. Eight candidates submitted; each run ONCE on hold-out data.

## Agents (discovery)
| Family | Variants | Outcome |
|---|---|---|
| energy | 73 | none. Realised weather is priced; petroleum-inventory surprise → USO t 2.7 but crisis-dependent; XLE Feb–Apr seasonal t 2.8 (alpha t 2.3) |
| fed | ~232 cells | pre-FOMC drift real (+28 bp, t 2.6) but ~2 bp since 2014; FOMC-cycle even weeks t 2.8, timing-fragile; candidates: TLT month-end (fed_1, fed_2) |
| liquid | 85 | TGA/RRP timing claims not supported; TLT rises on days +1/+2 after coupon auctions (t 5.0 / 2.7) — the month-end effect IS the post-auction effect; candidates liquid_1, liquid_2 |
| session | 64 | always-overnight index futures fails since 2005 at realistic cost; overnight ONLY after a down day clears the bar at 0.5–1 bp (session_1, session_2); hourly futures sample (362 sessions) has no power |
| carry | 48 | BTC / BTC+ETH cash-and-carry positive in all four years (carry_1, carry_2) but decaying; t-statistics are model artefacts (no basis noise, no counterparty risk) |

## Hold-out results
| Candidate | Discovery | Hold-out | Reading |
|---|---|---|---|
| session_1 overnight after down day, 4 indices, 1 bp | +5.7%/yr, t 4.0, alpha t 3.1 | 2019→2026: +3.9%/yr, t 1.2, alpha t −0.2, 7/8 years, max drawdown −19%, worst day −7.1% | positive, but no alpha over its market exposure |
| session_2 same, SPY+QQQ, 0.5 bp | +6.7%/yr, t 4.3, alpha t 3.5 | +5.0%/yr, t 1.4, alpha t 0.2, 6/8 years | same |
| fed_1 TLT last trading day of month | +2.4%/yr, t 3.4 | +0.1%/yr, t 0.1, 3/8 years | gone |
| fed_2 TLT last two trading days | +4.0%/yr, t 4.0 | +1.6%/yr, t 1.1, 5/8 years | not confirmed |
| liquid_1 TLT two days after every coupon auction | +6.9%/yr, t 4.6 | +1.2%/yr, t 0.4 (2020 +34%, 2022 −17%) | gone |
| liquid_2 TLT after 2/5/7-year auctions | +4.9%/yr, t 4.4, 17/17 years | −0.7%/yr, t −0.4, 4/8 years | gone |
| carry_1 BTC cash-and-carry, 50% notional | 2020–23: +8.5 / +15.9 / +1.7 / +3.6 % | 2024 +5.8%, 2025 +2.3%, 2026 (to Oct) +1.1% | positive every year, now below cash rates |
| carry_2 BTC+ETH | +11.2 / +17.8 / +0.7 / +3.7 % | 2024 +6.0%, 2025 +2.1%, 2026 +0.8% | same |

No candidate reached t ≥ 2 on hold-out with positive alpha.

## Data notes
- FOMC date list: 2003-09-15 is spurious (decision 09-16); 2017-02-01, 2017-11-01 and 2018-08-01 are missing.
- CPI and jobs-report release dates could not be fetched (BLS blocks automated access); jobs days were approximated as first Fridays.
- Hourly futures history from Yahoo covers only 2024-06 onward.
