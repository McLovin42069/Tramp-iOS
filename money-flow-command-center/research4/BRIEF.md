# Edge search, round 4 — rules for every research agent

Three rounds (about 1,400 variants: price/volume, flows, short interest and daily short volume, earnings, analyst ratings,
volatility, NAV premia, calendar, intraday bars, a 161k-pair lead-lag scan) found correlations but nothing tradable that
survived to recent data. One pattern WAS confirmed out of sample: US equity indices earn their return overnight
(close to open), about +4 to +6 bp per night, with roughly zero return in the day session — but it could not be traded in
ETFs at 2 bps per trade. This round goes wider: macro events, energy, weather, liquidity, the futures market (far lower
costs, nearly 24-hour trading), and carry.

Your candidates will be tested ONCE on hold-out data you never see (daily: 2019-01 onward; hourly futures: the last 35%
of sessions; crypto: 2024-01 onward).

## Hard rules
1. Work only in `research4/work_<family>/`. Start with
   `import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research4"); import lib4`
   and read the docstring of `lib4.py` first (data, publication lags, execution helpers, costs).
2. NEVER read `*_full.pkl` anywhere, anything under `../cache/`; never set `MFCC_HOLDOUT`; never download data; never modify
   `lib4.py`, `BRIEF.md`, `build_data.py`, `holdout4.py`, other rounds' libraries or `../app.py`. Do not commit or push.
3. No look-ahead: respect the publication lags in the lib4 docstring. Calendars known in advance (FOMC days, weekdays,
   month-ends, scheduled report weekdays) may be used ahead of time; data values may not.
4. Build returns only with `lib4.daily_strategy`, `lib4.segment_strategy` or `lib4.bar_strategy`, always with costs, and
   evaluate with `lib4.ts_eval`. No leverage (sum of absolute weights ≤ 1). "^" symbols are signals only.
   For crypto carry, compute the P&L explicitly from the funding series and spot/futures prices, state every assumption
   (fees per leg, how often the hedge is rebalanced, what happens when funding is negative) and evaluate with `lib4.ts_eval`.
5. Count every distinct variant you evaluate.
6. Submit AT MOST 3 candidates; none is a valid result. Bar: net t ≥ 3.0 (and alpha_t ≥ 3.0 if benchmarked against
   buy-and-hold of the same asset), positive in both halves and in ≥ 70% of calendar years (hourly data: both halves and
   ≥ 5 of the available calendar quarters... report quarters), not explained by one episode, robust to neighbouring
   parameters, an economic reason to persist, practical for a private investor. Report worst day and worst month.
7. Budget: roughly 30–45 minutes; think first, avoid sweeps beyond ~50 variants.

## Candidate file: `research4/candidates/<family>_<n>.py`
```python
NAME = "..."; RATIONALE = "..."; VARIANTS_TRIED = 20
DATA = "long"            # or "fut" or "crypto"
BENCH = "SPY"            # ticker for buy-and-hold comparison (long/fut), or None
def strategy(D):         # D = lib4.load_long() / load_fut() / load_crypto(); must work unchanged on longer data
    import lib4, numpy as np, pandas as pd
    ...
    return ret           # DAILY net return Series
DISCOVERY = {...}        # dict from lib4.ts_eval on discovery data
```

## Final report (your reply)
Ideas tried → best net t → verdict; candidates with stats; VARIANTS_TRIED; minimum detectable effects; surprises. Be blunt.
