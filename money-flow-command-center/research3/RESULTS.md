# Edge search, round 3 — results (run 2026-11-13)

New information sources: daily short-sale volume (FINRA), earnings dates and EPS surprises (Yahoo, 47,641 events),
analyst rating and target changes (131,294), the volatility family (VIX term structure, vol ETPs), ETF premium to NAV.
Discovery: stocks ≤ 2023-12-29, long history ≤ 2018-12-31. No candidate was submitted by any family.

| Family | Variants | Best honest result | Verdict |
|---|---|---|---|
| shortvol | ~94 | cross-section \|t\| ≤ 2.2 (2.6 on a post-hoc split); aggregate-ratio timing of SPY/QQQ/IWM alpha t 1.8–2.0, 5/5 years but 4.3 years and one episode | nothing; the daily ratio's 1-day spread is 1–2 bps |
| earn | 45 | Asia: rank(2-day announcement return) + rank(surprise), t 2.84 raw / 3.02 size-neutral, 19 names per side | nothing; post-earnings drift absent in US and Europe large caps |
| ratings | 80 | all revision signals have the WRONG sign (reversal); target dispersion t 2.0 = volatility proxy | nothing; no drift after the first close |
| vol | ~48 | vol signals forecast volatility, not mean return; SVXY returns are leveraged equity beta (alpha t ≈ 0) | nothing; risk reduction only |
| nav | ~85 | premium predicts NAV (IC 0.3–0.5), price effect gone by t+2 | nothing |

Near misses worth one pre-registered check later: the Asia earnings combination; aggregate short-volume timing.
