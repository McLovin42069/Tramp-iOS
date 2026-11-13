# Edge search, round 3 — rules for every research agent

Rounds 1 and 2 searched price/volume patterns, fund flows, twice-monthly short interest, calendar effects, intraday bars and
a full lead-lag scan. Result: correlations exist, but everything strong enough to trade had already decayed by 2019. This
round uses information those rounds never touched. Your candidates will be tested ONCE on hold-out data you never see
(stocks: 2024-01 onward; long-history ETF/volatility strategies: 2019-01 onward).

## Hard rules
1. Work only in `research3/work_<family>/`. Start with
   `import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research3"); import lib3`
   and read the docstring of `lib3.py` first (data, timing conventions, costs, the survivorship warning).
2. NEVER read `*_full.pkl`, anything under `../cache/`, `../research/data_full.pkl` or `../research2/*_full.pkl`; never set
   `MFCC_HOLDOUT`; never download market data; never modify `lib3.py`, `BRIEF.md`, `build_data.py`, `holdout3.py`,
   `../research*/lib*.py` or `../app.py`. Do not commit or push.
3. No look-ahead. Use `usable_date` for earnings and ratings. Evaluate stock signals only with `lib3.xs_eval` and ETF
   strategies only through `lib3.daily_strategy` / `lib3.segment_strategy` + `lib3.ts_eval`. Always include costs.
   No leverage (sum of absolute weights ≤ 1); "^" symbols are signals only.
4. Survivorship: every stock result must be reported twice — raw and after `lib3.size_neutral` — and must hold in
   sector/region-neutral long-short form. Long-only stock baskets benchmarked to an ETF are not acceptable evidence.
5. Count every distinct variant you evaluate.
6. Submit AT MOST 3 candidates; none is a valid result. Bar:
   - cross-sectional: t ≥ 3.0 raw AND ≥ 2.5 size-neutral, net spread positive after costs, right sign in both halves and in
     at least 5 of the calendar years available, ≥ 20 names per side;
   - strategies: net t ≥ 3.0 and (if benchmarked) alpha_t ≥ 3.0, positive in both halves and ≥ 70% of years, not explained by
     one crisis (report results excluding 2008–09 and 2020 where relevant);
   - an economic reason why it should persist, robustness to neighbouring parameters, practical for a private investor.
7. Budget: roughly 30–45 minutes; think first, avoid sweeps beyond ~50 variants.

## Candidate file: `research3/candidates/<family>_<n>.py`
```python
NAME = "..."; RATIONALE = "..."; VARIANTS_TRIED = 20
KIND = "xs"                      # cross-sectional stock signal ...
H = 20; COST_BPS = 5; EXPECTED_SIGN = 1
UNIVERSE = {"cls": ["US Stocks"], "core": False}       # passed to lib3.tickers(D, **UNIVERSE)
def signal(D):                   # D = lib3.load_stocks(); must work unchanged on longer data
    import lib3, numpy as np, pandas as pd
    return df                    # [date x ticker]
# --- or ---
KIND = "long_ts"; BENCH = "SPY"  # (or None)
def strategy(L):                 # L = lib3.load_long(); return a DAILY net return Series built with lib3.daily_strategy/segment_strategy
    ...
DISCOVERY = {...}                # dict from lib3.xs_eval / lib3.ts_eval on discovery data
```

## Final report (your reply)
Ideas tried → best t (raw and size-neutral) → verdict; candidates with stats; VARIANTS_TRIED; what surprised you. Be blunt.
