# Edge search, round 2 — rules for every research agent

Round 1 (daily data 2016–2023, trades one day late, 10 bps costs, 20–120-day horizons) found nothing above its bar, but it
could only detect effects larger than roughly 8–10% a year. This round raises the statistical power: far more independent
observations (hourly bars; 20–30 years of daily history on index products that have no survivorship bias), realistic costs
for liquid instruments, and execution conventions that allow same-day effects.

Your candidates will be tested ONCE on hold-out data you never see (daily: 2019-01 onward; hourly: the last 256 sessions).

## Hard rules
1. Work only in `research2/work_<family>/`. Start with:
   `import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research2"); import lib2`
   and read the docstring of `lib2.py` first: it defines the data and the execution conventions.
2. NEVER read `*_full.pkl`, anything under `../cache/` or `../research/`, never set `MFCC_HOLDOUT`, never download market data,
   never modify `lib2.py`, `BRIEF.md`, `build_data.py`, `holdout2.py` or `../app.py`. Do not commit or push.
3. No look-ahead. Positions must be computable from information available at the stated decision time. Build every strategy's
   returns ONLY through `lib2.daily_strategy`, `lib2.segment_strategy` or `lib2.bar_strategy`, and evaluate with `lib2.ts_eval`
   on the resulting daily net return series. Always include costs (2 bps ETFs/futures, 5 bps single stocks). No leverage:
   sum of absolute weights ≤ 1. Symbols starting with "^" are signals only, never positions.
4. Keep a count of every distinct variant you evaluate.
5. Submit AT MOST 3 candidates; none is a valid result. Bar for submission (higher than round 1 because power is higher):
   - net t ≥ 3.0 on discovery (for strategies judged against a benchmark: alpha_t ≥ 3.0, or a Sharpe clearly above the
     benchmark with a much smaller drawdown AND t ≥ 3.0 on the strategy's own net returns),
   - positive in both halves of the sample and in at least 70% of calendar years (hourly data: both halves and at least
     5 of the 8 calendar quarters),
   - a believable economic reason, robustness to neighbouring parameters, and practical for a private investor
     (a few trades a day at most; liquid instruments).
   Report `mde_ann_pct` for your main tests so that "nothing found" can be told apart from "could not have been seen".
6. Budget: roughly 30–45 minutes. Think first; avoid sweeps beyond ~50 variants.

## Candidate file: `research2/candidates/<family>_<n>.py`
```python
NAME = "..."; RATIONALE = "..."; VARIANTS_TRIED = 23
DATA = "long"        # or "intra"
BENCH = "SPY"        # ticker for buy-and-hold comparison, or None
EXECUTION = "next_close"   # describe: next_close / same_close / open+close segments / hourly bars
def strategy(D):     # D = lib2.load_long() or lib2.load_intra(); must work unchanged on longer data
    import lib2, numpy as np, pandas as pd
    ...
    return ret       # DAILY net return Series produced by lib2.daily_strategy / segment_strategy / bar_strategy
DISCOVERY = {...}    # dict from lib2.ts_eval on discovery data
```

## Final report (your reply)
A compact table of ideas tried → best net t → verdict; submitted candidates with stats; total VARIANTS_TRIED; the minimum
detectable effect of your main tests; anything surprising. Be blunt about weak results.
