# Money Flow Command Center

Cross-asset capital-flow terminal (Streamlit + Plotly) built only on free public data.

## Run

```bash
cd money-flow-command-center
python -m venv .venv && source .venv/bin/activate   # optional (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
streamlit run app.py
```

Opens at http://localhost:8501. Run it from this folder so `.streamlit/config.toml` (dark theme) is picked up.
First load fetches ~145 tickers from Yahoo (10-30 s), then everything is cached for 15 minutes.
If Yahoo is unreachable the app falls back to clearly-labelled synthetic demo data instead of crashing.

## Views

| View | What it does |
|---|---|
| COMMAND CENTER | Sankey of net rotation between 14 pools, clickable pool bars with drill-down to groups and securities, pool score history, top inflows/outflows |
| HEATMAP | Treemap asset class -> sector/region -> security (click to zoom), plus group x timeframe matrix |
| DEEP DIVE | Any Yahoo ticker: flow score, CMF, MFI, relative strength, relative volume, 1D/5D/20D/60D sparklines, price/volume/CMF chart, volume profile, score decomposition, group comparison |
| REGIME & LIQUIDITY | Risk-on/off meter from 10 cross-asset ratios, market-implied liquidity gauge, FRED net liquidity, CFTC COT positioning |
| LEADERBOARDS | Sortable tables by name, sector/region, asset class, pool; CSV export |
| METHODOLOGY | Formulas, live weights, limitations, full universe |

Global controls: timeframe (5D / 20D / 60D / 120D), search (sidebar, any ticker or name), pin to watch panel
(pins persist in the URL), adjustable composite weights.

## What "flow" means here

True fund-flow data is proprietary. Every number is a transparent price x volume proxy over the chosen lookback N:

| Component | Formula | Default weight |
|---|---|---|
| CMF | sum(MFM x V) / sum(V), MFM = ((C-L)-(H-C))/(H-L) | 30% |
| MFI | volume-weighted RSI of typical price, period max(N,7) | 20% |
| RS vs peers | N-day return minus group median, volatility-scaled | 10% |
| RS vs risk-on | N-day return minus basket (SPY, QQQ, IWM, EEM, HYG, CPER) | 10% |
| Flow momentum | change in CMF over N/2 sessions | 15% |
| Volume intensity | direction x relative volume | 15% |

Composite Money Flow Score = weighted sum, -100 to +100. Net $ flow = sum(MFM x typical price x volume).
The Sankey is an allocation model (outflow pools split pro-rata across inflow pools), not observed transfers.
Spot FX and index symbols have no volume on Yahoo, so their CMF/MFI are price-only.

## Data sources (no API keys)

- Yahoo Finance via `yfinance`: daily OHLCV (2y) and 15-minute bars
- FRED public CSV: WALCL, WTREGEN, RRPONTSYD, BAMLH0A0HYM2, T10Y2Y
- CFTC Socrata API: legacy futures-only Commitments of Traders

## Expanding the universe

Append `(ticker, name, asset_class, group)` rows to the `U` list at the top of `app.py`. Any Yahoo symbol works.
New groups appear automatically everywhere; map a new group to a Sankey pool in `POOL_OF` if needed.

## Upgrading the data

Search `EXTENSION POINT` in `app.py`: ETF shares-outstanding deltas for true creations/redemptions, a free FRED API key,
CFTC TFF/disaggregated reports, Treasury fiscal-data API for daily TGA, or another OHLCV vendor in `fetch_live`.

Not investment advice.

## Signals, live mode and reliability test

- **SIGNALEN** (default view, Dutch): plain-language summary of where money is flowing, a pool matrix across
  live / 5D / 20D / 60D / 120D, and ranked inflow/outflow candidates with a combined signal.
- **LIVE 1D** timeframe: the same flow engine on 15-minute bars of the latest US session (Yahoo, up to 15 min delayed).
- **Reliability test**: ranks the universe into score quintiles on non-overlapping dates over the last 2 years and
  reports the realised forward return of each, so you can see whether the score had predictive value.
- **Auto-refresh** toggle in the sidebar reloads every 5 minutes.

To update an existing install, run `install-money-flow.sh` again.

## Forecast model, manual and desktop app

- **VOORSPELLING**: gradient-boosted model (scikit-learn) trained on 5 years of history. It tunes itself over
  `ML_CONFIGS` on a validation period and is judged only on a later hold-out period (walk-forward, purged).
- **HANDLEIDING.md / HANDLEIDING.pdf**: Dutch user manual, also shown inside the app.
- **Desktop app**: the installer adds a "Money Flow" launcher (menu + desktop) that opens the app in its own
  chromeless window via Brave/Chromium/Chrome `--app` mode and starts the server if needed.
