# Edge search — rules for every research agent

Goal: find a tradable, statistically defensible edge in the DISCOVERY data (2016-11 → 2023-12-29).
Your candidates will later be tested ONCE on 2024–2026 data you never see. Overfitting to discovery data is the main
risk, so favour simple rules with an economic reason, few parameters, and stability across years.

## Hard rules
1. Work only in `research/work_<your family>/` (create it). Use `import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research"); import lib; D = lib.load()`.
2. NEVER read `data_full.pkl`, anything under `../cache/`, never set `MFCC_HOLDOUT`, never fetch market data from the network,
   never modify `lib.py`, `BRIEF.md`, `build_data.py`, `holdout.py` or `../app.py`. Do not commit or push.
3. Timing: a signal on row t may use only data up to the close of t. Trades are at the close of t+1. The lib functions enforce this
   if you pass signals aligned on row t; never shift a signal backwards. Remember: D["spdr"]["so"] of day t is public on t+1;
   D["short"] is usable from `pub_date`; D["cot"] dates are already publication dates.
4. Evaluate ONLY with `lib.xs_eval` (cross-sectional) or `lib.weights_to_returns` + `lib.ts_eval` (strategies). Default cost 10 bps.
5. Keep a running count of every distinct variant/parameter setting you evaluate (needed for multiple-testing correction).
6. Submit AT MOST 3 candidates. Submitting none is a valid and useful result. Bar for submission:
   - discovery t ≥ 2.5 (for strategies: alpha_t ≥ 2.5 versus the stated benchmark, or Sharpe improvement that is clearly not leverage),
   - right sign in both halves and in at least 5 of the 7 calendar years,
   - still positive after costs, enough names per side (xs: ≥ 20) and plausible to trade for a private investor,
   - a one-paragraph economic rationale (why should this persist?),
   - robust to small parameter changes (report neighbours).
7. Budget: roughly 25–40 minutes of work. Prefer breadth of thinking over brute-force grids; do not run parameter sweeps of more than ~40 variants.

## Candidate file format: `research/candidates/<family>_<n>.py`
```python
NAME = "short descriptive name"
KIND = "xs"            # or "ts"
RATIONALE = "why this should work and persist"
VARIANTS_TRIED = 17    # total distinct variants you evaluated in your whole search
# --- xs only ---
H = 20                 # holding horizon in trading days
UNIVERSE = {"cls": ["US Stocks"], "core": False}   # passed to lib.tickers(D, **UNIVERSE); or TICKERS = [...]
EXPECTED_SIGN = 1      # +1: high signal outperforms, -1: high signal underperforms
def signal(D):         # must work on any D with the same structure (it will be re-run on longer data)
    ...
    return df          # DataFrame [date x ticker]
# --- ts only ---
BENCH = "SPY"          # ticker whose buy-and-hold is the benchmark, or None
def weights(D):
    ...
    return W           # DataFrame [date x ticker] of target weights, sum of |w| <= 1 (no leverage)
DISCOVERY = {...}      # paste the dict returned by lib.xs_eval / lib.ts_eval on discovery data
```
The functions must be self-contained (import numpy/pandas/lib inside the file) and must not hard-code dates beyond warm-up logic.

## Final report (your reply)
A compact table of what you tried (family of idea → best t, verdict), the candidates you submitted with their discovery stats,
the total VARIANTS_TRIED, and anything that surprised you. Be blunt about weak results.
