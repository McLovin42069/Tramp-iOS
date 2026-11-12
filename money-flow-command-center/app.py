"""
MONEY FLOW COMMAND CENTER
=========================
Cross-asset capital-flow terminal built only on free/public data.

Run:
    pip install -r requirements.txt
    streamlit run app.py

Data sources (all free, no API key):
    * Yahoo Finance via yfinance  - daily OHLCV for every instrument (+ intraday for sparklines)
    * FRED public CSV endpoint    - Fed balance sheet, TGA, reverse repo, HY spread
    * CFTC Socrata public API     - Commitments of Traders (legacy futures-only)

IMPORTANT: true fund-flow data (creations/redemptions, custody flows) is not free.
Everything called "flow" here is a transparent PROXY computed from price x volume.
See the METHODOLOGY view inside the app, or the README.

How to plug in better data later (search for "EXTENSION POINT" in this file):
    1. ETF shares-outstanding deltas (true creations/redemptions) -> replace `dollar_flow`
    2. A FRED API key -> more series / faster refresh in `fetch_fred`
    3. CFTC disaggregated / TFF reports -> extend `COT_CONTRACTS` + `fetch_cot`
    4. Any OHLCV vendor (Stooq, Tiingo free tier, Polygon free tier) -> swap `fetch_live`
"""
from __future__ import annotations

import io
import time
import zlib
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

# ════════════════════════════════════════════════════════════════════════════
# 1. UNIVERSE  — edit here to expand. Format: (ticker, name, asset_class, group)
#    Any Yahoo Finance symbol works. `pool` (Sankey node) is derived in POOL_OF.
# ════════════════════════════════════════════════════════════════════════════
U = [
    # ── Cash ────────────────────────────────────────────────────────────────
    ("BIL", "1-3M T-Bill", "Cash", "T-Bills"), ("SGOV", "0-3M Treasury", "Cash", "T-Bills"),
    ("SHV", "Short Treasury", "Cash", "T-Bills"),
    # ── Sovereign bonds ─────────────────────────────────────────────────────
    ("SHY", "UST 1-3Y", "Sovereign Bonds", "US Treasuries"), ("IEI", "UST 3-7Y", "Sovereign Bonds", "US Treasuries"),
    ("IEF", "UST 7-10Y", "Sovereign Bonds", "US Treasuries"), ("TLT", "UST 20Y+", "Sovereign Bonds", "US Treasuries"),
    ("TIP", "US TIPS", "Sovereign Bonds", "Inflation-Linked"), ("VTIP", "Short TIPS", "Sovereign Bonds", "Inflation-Linked"),
    ("BWX", "Intl Treasuries", "Sovereign Bonds", "Global Sovereign"), ("IGOV", "Intl Govt Bonds", "Sovereign Bonds", "Global Sovereign"),
    ("EMB", "EM USD Sovereign", "Sovereign Bonds", "EM Sovereign"), ("EMLC", "EM Local Sovereign", "Sovereign Bonds", "EM Sovereign"),
    # ── Credit ──────────────────────────────────────────────────────────────
    ("LQD", "IG Corporate", "Credit", "Investment Grade"), ("VCIT", "Interm. Corporate", "Credit", "Investment Grade"),
    ("VCSH", "Short Corporate", "Credit", "Investment Grade"),
    ("HYG", "High Yield", "Credit", "High Yield"), ("JNK", "High Yield (SPDR)", "Credit", "High Yield"),
    ("BKLN", "Senior Loans", "Credit", "High Yield"),
    ("MUB", "Municipals", "Credit", "Munis & MBS"), ("MBB", "Agency MBS", "Credit", "Munis & MBS"),
    # ── US equities: indices ────────────────────────────────────────────────
    ("SPY", "S&P 500", "US Equities", "US Indices"), ("QQQ", "Nasdaq 100", "US Equities", "US Indices"),
    ("IWM", "Russell 2000", "US Equities", "US Indices"), ("DIA", "Dow 30", "US Equities", "US Indices"),
    ("MDY", "S&P MidCap 400", "US Equities", "US Indices"), ("RSP", "S&P 500 Equal Wt", "US Equities", "US Indices"),
    # ── US equities: sectors (ETF + leading single stocks) ──────────────────
    ("XLK", "Technology", "US Equities", "Technology"), ("AAPL", "Apple", "US Equities", "Technology"),
    ("MSFT", "Microsoft", "US Equities", "Technology"), ("NVDA", "NVIDIA", "US Equities", "Technology"),
    ("AVGO", "Broadcom", "US Equities", "Technology"), ("SMH", "Semiconductors", "US Equities", "Technology"),
    ("XLC", "Communication", "US Equities", "Communication"), ("GOOGL", "Alphabet", "US Equities", "Communication"),
    ("META", "Meta", "US Equities", "Communication"), ("NFLX", "Netflix", "US Equities", "Communication"),
    ("XLY", "Cons. Discretionary", "US Equities", "Cons. Discretionary"), ("AMZN", "Amazon", "US Equities", "Cons. Discretionary"),
    ("TSLA", "Tesla", "US Equities", "Cons. Discretionary"), ("HD", "Home Depot", "US Equities", "Cons. Discretionary"),
    ("XLP", "Cons. Staples", "US Equities", "Cons. Staples"), ("PG", "Procter & Gamble", "US Equities", "Cons. Staples"),
    ("KO", "Coca-Cola", "US Equities", "Cons. Staples"), ("WMT", "Walmart", "US Equities", "Cons. Staples"),
    ("XLF", "Financials", "US Equities", "Financials"), ("JPM", "JPMorgan", "US Equities", "Financials"),
    ("BAC", "Bank of America", "US Equities", "Financials"), ("GS", "Goldman Sachs", "US Equities", "Financials"),
    ("KRE", "Regional Banks", "US Equities", "Financials"),
    ("XLV", "Health Care", "US Equities", "Health Care"), ("LLY", "Eli Lilly", "US Equities", "Health Care"),
    ("UNH", "UnitedHealth", "US Equities", "Health Care"), ("JNJ", "Johnson & Johnson", "US Equities", "Health Care"),
    ("XLE", "Energy", "US Equities", "Energy Equities"), ("XOM", "Exxon Mobil", "US Equities", "Energy Equities"),
    ("CVX", "Chevron", "US Equities", "Energy Equities"),
    ("XLI", "Industrials", "US Equities", "Industrials"), ("CAT", "Caterpillar", "US Equities", "Industrials"),
    ("GE", "GE Aerospace", "US Equities", "Industrials"), ("BA", "Boeing", "US Equities", "Industrials"),
    ("XLB", "Materials", "US Equities", "Materials"), ("LIN", "Linde", "US Equities", "Materials"),
    ("FCX", "Freeport-McMoRan", "US Equities", "Materials"),
    ("XLU", "Utilities", "US Equities", "Utilities"), ("NEE", "NextEra", "US Equities", "Utilities"),
    ("XLRE", "Real Estate", "US Equities", "Real Estate"), ("PLD", "Prologis", "US Equities", "Real Estate"),
    # ── Europe ──────────────────────────────────────────────────────────────
    ("VGK", "Europe Broad", "Europe Equities", "Europe"), ("EZU", "Eurozone", "Europe Equities", "Europe"),
    ("EWG", "Germany", "Europe Equities", "Europe"), ("EWU", "United Kingdom", "Europe Equities", "Europe"),
    ("EWQ", "France", "Europe Equities", "Europe"), ("EWI", "Italy", "Europe Equities", "Europe"),
    ("EWP", "Spain", "Europe Equities", "Europe"), ("EWL", "Switzerland", "Europe Equities", "Europe"),
    ("EWN", "Netherlands", "Europe Equities", "Europe"), ("EWD", "Sweden", "Europe Equities", "Europe"),
    # ── Asia-Pacific developed ──────────────────────────────────────────────
    ("EWJ", "Japan", "Asia-Pacific Equities", "Developed Asia"), ("EWA", "Australia", "Asia-Pacific Equities", "Developed Asia"),
    ("EWH", "Hong Kong", "Asia-Pacific Equities", "Developed Asia"), ("EWS", "Singapore", "Asia-Pacific Equities", "Developed Asia"),
    ("EWY", "South Korea", "Asia-Pacific Equities", "Developed Asia"), ("EWT", "Taiwan", "Asia-Pacific Equities", "Developed Asia"),
    # ── Emerging markets ────────────────────────────────────────────────────
    ("EEM", "EM Broad", "EM Equities", "Emerging Markets"), ("FXI", "China Large-Cap", "EM Equities", "Emerging Markets"),
    ("KWEB", "China Internet", "EM Equities", "Emerging Markets"), ("INDA", "India", "EM Equities", "Emerging Markets"),
    ("EWZ", "Brazil", "EM Equities", "Emerging Markets"), ("EWW", "Mexico", "EM Equities", "Emerging Markets"),
    ("EZA", "South Africa", "EM Equities", "Emerging Markets"), ("TUR", "Turkey", "EM Equities", "Emerging Markets"),
    ("EIDO", "Indonesia", "EM Equities", "Emerging Markets"), ("KSA", "Saudi Arabia", "EM Equities", "Emerging Markets"),
    # ── Commodities (ETF) ───────────────────────────────────────────────────
    ("GLD", "Gold", "Commodities", "Precious Metals"), ("SLV", "Silver", "Commodities", "Precious Metals"),
    ("PPLT", "Platinum", "Commodities", "Precious Metals"), ("GDX", "Gold Miners", "Commodities", "Precious Metals"),
    ("USO", "WTI Crude", "Commodities", "Energy"), ("BNO", "Brent Crude", "Commodities", "Energy"),
    ("UNG", "Natural Gas", "Commodities", "Energy"),
    ("CPER", "Copper", "Commodities", "Industrial Metals"), ("DBB", "Base Metals", "Commodities", "Industrial Metals"),
    ("DBA", "Agriculture", "Commodities", "Agriculture"), ("CORN", "Corn", "Commodities", "Agriculture"),
    ("WEAT", "Wheat", "Commodities", "Agriculture"), ("SOYB", "Soybeans", "Commodities", "Agriculture"),
    ("DBC", "Broad Commodities", "Commodities", "Broad Commodities"),
    # ── FX (ETF proxies carry volume; spot pairs are price-only) ────────────
    ("UUP", "US Dollar Index ETF", "FX", "US Dollar"), ("DX-Y.NYB", "DXY Index", "FX", "US Dollar"),
    ("FXE", "Euro ETF", "FX", "G10 FX"), ("FXY", "Yen ETF", "FX", "G10 FX"), ("FXB", "Sterling ETF", "FX", "G10 FX"),
    ("FXA", "Aussie ETF", "FX", "G10 FX"), ("FXC", "Loonie ETF", "FX", "G10 FX"), ("FXF", "Swiss Franc ETF", "FX", "G10 FX"),
    ("EURUSD=X", "EUR/USD", "FX", "Spot Pairs"), ("JPY=X", "USD/JPY", "FX", "Spot Pairs"),
    ("GBPUSD=X", "GBP/USD", "FX", "Spot Pairs"), ("AUDUSD=X", "AUD/USD", "FX", "Spot Pairs"),
    ("CAD=X", "USD/CAD", "FX", "Spot Pairs"), ("CHF=X", "USD/CHF", "FX", "Spot Pairs"),
    ("CNY=X", "USD/CNY", "FX", "Spot Pairs"), ("MXN=X", "USD/MXN", "FX", "Spot Pairs"),
    # ── Futures & derivative proxies ────────────────────────────────────────
    ("ES=F", "S&P 500 E-mini", "Futures & Vol", "Equity Futures"), ("NQ=F", "Nasdaq E-mini", "Futures & Vol", "Equity Futures"),
    ("RTY=F", "Russell E-mini", "Futures & Vol", "Equity Futures"),
    ("ZN=F", "10Y T-Note Fut", "Futures & Vol", "Rates Futures"), ("ZB=F", "30Y T-Bond Fut", "Futures & Vol", "Rates Futures"),
    ("ZT=F", "2Y T-Note Fut", "Futures & Vol", "Rates Futures"),
    ("CL=F", "WTI Crude Fut", "Futures & Vol", "Commodity Futures"), ("NG=F", "Nat Gas Fut", "Futures & Vol", "Commodity Futures"),
    ("GC=F", "Gold Fut", "Futures & Vol", "Commodity Futures"), ("SI=F", "Silver Fut", "Futures & Vol", "Commodity Futures"),
    ("HG=F", "Copper Fut", "Futures & Vol", "Commodity Futures"), ("ZC=F", "Corn Fut", "Futures & Vol", "Commodity Futures"),
    ("^VIX", "VIX Index", "Futures & Vol", "Volatility"), ("VIXY", "VIX Short-Term Fut", "Futures & Vol", "Volatility"),
    ("SVXY", "Short VIX", "Futures & Vol", "Volatility"),
    # ── Crypto ──────────────────────────────────────────────────────────────
    ("BTC-USD", "Bitcoin", "Crypto", "Crypto"), ("ETH-USD", "Ethereum", "Crypto", "Crypto"),
    ("SOL-USD", "Solana", "Crypto", "Crypto"), ("IBIT", "Bitcoin ETF", "Crypto", "Crypto"),
]
META = pd.DataFrame(U, columns=["ticker", "name", "cls", "group"]).drop_duplicates("ticker").set_index("ticker")

# Sankey pools: (asset_class, group) -> pool. Classes not listed map to themselves.
POOL_OF = {
    ("Commodities", "Precious Metals"): "Precious Metals", ("Commodities", "Energy"): "Energy Cmdty",
    ("Commodities", "Industrial Metals"): "Industrial & Ags", ("Commodities", "Agriculture"): "Industrial & Ags",
    ("Commodities", "Broad Commodities"): "Industrial & Ags",
    ("FX", "US Dollar"): "US Dollar", ("FX", "G10 FX"): "Non-USD FX", ("FX", "Spot Pairs"): None,
    ("Credit", "Investment Grade"): "IG Credit", ("Credit", "Munis & MBS"): "IG Credit", ("Credit", "High Yield"): "HY Credit",
}
EXCLUDE_FROM_POOLS = {"Futures & Vol"}  # avoids double counting with the ETF pools
META["pool"] = [None if c in EXCLUDE_FROM_POOLS else POOL_OF.get((c, g), c) for c, g in zip(META["cls"], META["group"])]

RISK_ON_BASKET = ["SPY", "QQQ", "IWM", "EEM", "HYG", "CPER"]  # equal-weight
DAILY_TF = {"5D": 5, "20D": 20, "60D": 60, "120D": 120}
BARS_PER_DAY = 26                                  # 15-minute bars in one US session
TIMEFRAMES = {"LIVE 1D": BARS_PER_DAY, **DAILY_TF}   # LIVE 1D runs the same engine on 15-minute bars
DEFAULT_WEIGHTS = {"CMF": 30, "MFI": 20, "RS vs Peers": 10, "RS vs Risk-On": 10, "Flow Momentum": 15, "Volume Intensity": 15}
COMP_COLS = list(DEFAULT_WEIGHTS)

# Cross-asset regime pairs: (label, numerator, denominator, +1 if rising = risk-on)
REGIME_PAIRS = [
    ("Stocks / Bonds", "SPY", "TLT", 1), ("High Yield / Treasuries", "HYG", "IEF", 1),
    ("Copper / Gold", "CPER", "GLD", 1), ("Discretionary / Staples", "XLY", "XLP", 1),
    ("Small / Large Cap", "IWM", "SPY", 1), ("EM / US Equities", "EEM", "SPY", 1),
    ("Semis / S&P 500", "SMH", "SPY", 1), ("Bitcoin / Gold", "BTC-USD", "GLD", 1),
    ("VIX (inverted)", "^VIX", None, -1), ("US Dollar (inverted)", "UUP", None, -1),
]
FRED_SERIES = {"WALCL": "Fed balance sheet ($M)", "WTREGEN": "Treasury General Account ($B)",
               "RRPONTSYD": "Reverse repo ($B)", "BAMLH0A0HYM2": "HY OAS (%)", "T10Y2Y": "10Y-2Y curve (%)"}
COT_CONTRACTS = {"13874A": "S&P 500 E-mini", "209742": "Nasdaq 100 E-mini", "043602": "10Y T-Note", "020601": "30Y T-Bond",
                 "088691": "Gold", "084691": "Silver", "085692": "Copper", "067651": "WTI Crude",
                 "099741": "Euro FX", "097741": "Japanese Yen", "098662": "US Dollar Index", "133741": "Bitcoin"}

# ════════════════════════════════════════════════════════════════════════════
# 2. THEME
# ════════════════════════════════════════════════════════════════════════════
BG, PANEL, BORDER, TXT, DIM = "#0a0e17", "#0f1522", "#1c2638", "#d5deec", "#6b7a93"
GREEN, RED, AMBER, CYAN = "#00ff9c", "#ff2d55", "#ffb020", "#22d3ee"
SCALE = [[0, "#ff2d55"], [0.25, "#8a1f38"], [0.5, "#161d2c"], [0.75, "#0c8f5c"], [1, "#00ff9c"]]
MONO = "'JetBrains Mono','SF Mono','Cascadia Code',Consolas,Menlo,monospace"

st.set_page_config(page_title="Money Flow Command Center", page_icon="◈", layout="wide", initial_sidebar_state="auto")
st.markdown(f"""<style>
.stApp,[data-testid="stHeader"]{{background:{BG};}}
[data-testid="stSidebar"]{{background:#080b13;border-right:1px solid {BORDER};}}
.block-container{{padding:3.4rem 1.4rem 2rem 1.4rem;max-width:100%;}}
html,body,.stApp,p,label,span,div{{color:{TXT};}}
h1,h2,h3,h4{{font-family:{MONO};letter-spacing:.06em;}}
.hdr{{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid {BORDER};padding-bottom:6px;margin-bottom:8px;}}
.hdr .t{{font-family:{MONO};font-size:20px;font-weight:700;color:{GREEN};letter-spacing:.14em;}}
.hdr .s{{font-family:{MONO};font-size:11px;color:{DIM};text-align:right;}}
.sec{{font-family:{MONO};font-size:11px;font-weight:700;color:{CYAN};letter-spacing:.16em;text-transform:uppercase;
     border-left:3px solid {CYAN};padding-left:8px;margin:10px 0 4px 0;}}
.kpi{{background:{PANEL};border:1px solid {BORDER};border-radius:4px;padding:8px 10px;height:100%;}}
.kpi .l{{font-family:{MONO};font-size:10px;color:{DIM};letter-spacing:.12em;text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.kpi .v{{font-family:{MONO};font-size:22px;font-weight:700;line-height:1.25;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.kpi .d{{font-family:{MONO};font-size:11px;color:{DIM};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.note{{font-family:{MONO};font-size:11px;color:{DIM};line-height:1.5;}}
.banner{{font-family:{MONO};font-size:12px;border:1px solid {AMBER};color:{AMBER};background:#1a1405;padding:6px 10px;border-radius:4px;margin-bottom:8px;}}
div[role="radiogroup"]{{gap:4px;}}
div[role="radiogroup"] label{{background:{PANEL};border:1px solid {BORDER};border-radius:3px;padding:3px 10px;margin:0;}}
div[role="radiogroup"] label:has(input:checked){{border-color:{GREEN};background:#0b2a20;}}
div[role="radiogroup"] label p{{font-family:{MONO};font-size:12px;letter-spacing:.06em;}}
[data-testid="stMetricValue"]{{font-family:{MONO};}}
.stButton button{{font-family:{MONO};font-size:12px;border:1px solid {BORDER};background:{PANEL};}}
@media (max-width:640px){{
 .block-container{{padding:3.2rem .6rem 2rem .6rem;}}
 .hdr{{display:block;}} .hdr .t{{font-size:15px;letter-spacing:.08em;}} .hdr .s{{text-align:left;font-size:10px;}}
 [data-testid="stHorizontalBlock"]:has(.kpi){{flex-wrap:wrap;gap:.4rem;}}
 [data-testid="stColumn"]:has(.kpi):not(:has(.js-plotly-plot)){{min-width:calc(50% - .4rem)!important;width:calc(50% - .4rem)!important;flex:1 1 calc(50% - .4rem)!important;}}
 .kpi .v{{font-size:18px;}}
 div[role="radiogroup"] label{{padding:2px 6px;}}
}}
</style>""", unsafe_allow_html=True)


def col(v):  # score -> colour
    return GREEN if v > 5 else RED if v < -5 else AMBER


def sec(title):
    st.markdown(f'<div class="sec">{title}</div>', unsafe_allow_html=True)


def kpi(label, value, sub="", color=TXT):
    st.markdown(f'<div class="kpi"><div class="l">{label}</div><div class="v" style="color:{color}">{value}</div>'
                f'<div class="d">{sub}</div></div>', unsafe_allow_html=True)


def lay(fig, h=320, **kw):
    fig.update_layout(height=h, paper_bgcolor=PANEL, plot_bgcolor=PANEL, margin=dict(l=8, r=8, t=28, b=8),
                      font=dict(family=MONO, size=11, color=TXT), showlegend=False,
                      hoverlabel=dict(bgcolor="#060910", font_family=MONO, font_size=11), **kw)
    fig.update_xaxes(gridcolor="#161e2e", zerolinecolor=BORDER, linecolor=BORDER)
    fig.update_yaxes(gridcolor="#161e2e", zerolinecolor=BORDER, linecolor=BORDER)
    return fig


def show(fig, **kw):
    return st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, **kw)


def fmt_usd(x):
    if x is None or not np.isfinite(x):
        return "—"
    a = abs(x)
    s = "-" if x < 0 else "+"
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= div:
            return f"{s}${a / div:,.1f}{suf}"
    return f"{s}${a:,.0f}"


# ════════════════════════════════════════════════════════════════════════════
# 3. DATA  (cached; every network call is wrapped so one bad ticker never kills the app)
# ════════════════════════════════════════════════════════════════════════════
def _clean(panels: dict) -> dict:
    """Align to a weekday calendar, forward-fill small gaps, zero-fill volume."""
    out = {}
    idx = panels["Close"].index
    idx = idx[idx.dayofweek < 5]
    for k, df in panels.items():
        df = df.loc[df.index.isin(idx)].sort_index()
        df = df.loc[~df.index.duplicated(keep="last")]
        out[k] = df.fillna(0.0) if k == "Volume" else df.ffill(limit=5)
    good = out["Close"].columns[out["Close"].notna().sum() >= 130]
    return {k: v[good] for k, v in out.items()}


def _download(tickers: tuple, period: str = "2y", interval: str = "1d"):
    """EXTENSION POINT: swap this for any other OHLCV vendor. Must return
    ({'Open','High','Low','Close','Volume'} -> DataFrame[date x ticker], failed_tickers)."""
    import yfinance as yf
    frames, failed = {}, []
    tick = list(tickers)
    try:  # fast reachability probe so an offline machine falls back in seconds, not minutes
        requests.get("https://query1.finance.yahoo.com", timeout=6, headers={"User-Agent": "Mozilla/5.0"})
    except Exception:
        return None, tick
    for i in range(0, len(tick), 40):
        chunk = tick[i:i + 40]
        try:
            raw = yf.download(chunk, period=period, interval=interval, auto_adjust=True, group_by="ticker",
                              threads=True, progress=False)
        except Exception:
            raw = pd.DataFrame()
        for t in chunk:
            try:
                d = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
                d = d.dropna(subset=["Close"])
                if len(d) < 30:
                    raise ValueError
                frames[t] = d
            except Exception:
                failed.append(t)
    for t in list(failed):  # one retry, individually
        try:
            d = yf.Ticker(t).history(period=period, interval=interval, auto_adjust=True).dropna(subset=["Close"])
            if len(d) >= 30:
                frames[t] = d
                failed.remove(t)
        except Exception:
            pass
    if not frames:
        return None, failed
    panels = {}
    for f in ["Open", "High", "Low", "Close", "Volume"]:
        intr = interval != "1d"
        df = pd.DataFrame({t: (d[f].tz_convert("UTC") if intr and d.index.tz is not None else d[f]) for t, d in frames.items()})
        idx = pd.to_datetime(df.index)
        if not intr:
            df.index = idx.tz_localize(None).normalize()
        elif idx.tz is not None:
            df.index = idx.tz_convert("America/New_York").tz_localize(None)
        panels[f] = df.groupby(level=0).last()
    return panels, failed


@st.cache_data(ttl=900, show_spinner=False)
def fetch_live(tickers: tuple, period: str = "5y"):          # 5 years so the model has history to learn from
    return _download(tickers, period, "1d")


@st.cache_data(ttl=240, show_spinner=False)
def fetch_bars(tickers: tuple):
    """15-minute bars for the whole universe (last month), aligned to the US cash session (SPY's bars)
    so every instrument is measured on the same clock. Returns panels or None."""
    try:
        P, _ = _download(tickers, "1mo", "15m")
    except Exception:
        return None
    if P is None or "SPY" not in P["Close"].columns:
        return None
    anchor = P["Close"]["SPY"].dropna().index
    return {k: (v.reindex(anchor).fillna(0.0) if k == "Volume" else v.ffill(limit=8).reindex(anchor)) for k, v in P.items()}


@st.cache_data(ttl=3600, show_spinner=False)
def make_demo(tickers: tuple, n: int = 900):
    """Deterministic synthetic OHLCV with class/group factor structure. Used ONLY when live data is
    unreachable or Demo mode is selected; the UI shows a banner whenever this is active."""
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
    vol_of = {"Cash": .0003, "Sovereign Bonds": .005, "Credit": .004, "FX": .005, "Crypto": .035,
              "Futures & Vol": .013, "Commodities": .015}
    fac = {}

    def factor(key, scale):
        if key not in fac:
            r = np.random.default_rng(zlib.crc32(key.encode()))
            drift = np.repeat(r.normal(0, .0011, n // 40 + 1), 40)[:n]  # slow regime rotation
            fac[key] = (drift + r.normal(0, 1, n) * scale)
        return fac[key]

    P = {k: {} for k in ["Open", "High", "Low", "Close", "Volume"]}
    for t in tickers:
        cls, grp = (META.loc[t, "cls"], META.loc[t, "group"]) if t in META.index else ("US Equities", "Custom")
        sv = vol_of.get(cls, .011)
        r = np.random.default_rng(zlib.crc32(t.encode()))
        ret = .6 * factor(cls, sv) * (sv / max(sv, 1e-9)) + .5 * factor(cls + grp, sv) + r.normal(0, sv * .8, n)
        if t in ("^VIX", "VIXY"):
            ret = -4 * factor("US Equities", .011) + r.normal(0, .03, n)
        c = 100 * np.exp(np.cumsum(ret - ret.mean() * .5))
        rng_ = np.abs(r.normal(0, sv, n)) + sv * .4
        pos = np.clip(.5 + ret / (sv * 3) + r.normal(0, .2, n), .02, .98)  # close location inside the bar
        lo = c * (1 - rng_ * pos)
        hi = c * (1 + rng_ * (1 - pos))
        o = lo + (hi - lo) * r.uniform(.2, .8, n)
        base = r.uniform(5e5, 5e7)
        v = base * np.exp(r.normal(0, .3, n)) * (1 + 6 * np.abs(ret) / sv * .15)
        if t.endswith("=X") or t.startswith("^") or t == "DX-Y.NYB":
            v = np.zeros(n)
        for k, arr in zip(P, [o, hi, lo, c, v]):
            P[k][t] = arr
    return {k: pd.DataFrame(d, index=idx) for k, d in P.items()}


@st.cache_data(ttl=600, show_spinner=False)
def fetch_intraday(ticker: str, demo: bool):
    """15-minute bars for the 1D / 5D sparklines. Returns a Close series or None."""
    if demo:
        r = np.random.default_rng(zlib.crc32(ticker.encode()) + 7)
        idx = pd.date_range(end=pd.Timestamp.now().floor("15min"), periods=130, freq="15min")
        return pd.Series(100 * np.exp(np.cumsum(r.normal(0, .0015, 130))), index=idx)
    try:
        import yfinance as yf
        d = yf.Ticker(ticker).history(period="5d", interval="15m")["Close"].dropna()
        return d if len(d) > 5 else None
    except Exception:
        return None


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def fetch_fred():
    """EXTENSION POINT: add series ids to FRED_SERIES. Uses the key-less public CSV endpoint."""
    out = {}
    for sid in FRED_SERIES:
        try:
            r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd=2022-01-01", timeout=6,
                             headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            d = pd.read_csv(io.StringIO(r.text))
            s = pd.to_numeric(d.iloc[:, 1], errors="coerce")
            s.index = pd.to_datetime(d.iloc[:, 0])
            out[sid] = s.dropna()
        except Exception:
            if not out:   # first series failed => FRED unreachable; don't wait on the rest
                break
    return out


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def fetch_cot():
    """CFTC legacy futures-only COT via the public Socrata API (no key). EXTENSION POINT."""
    try:
        codes = ",".join(f"'{c}'" for c in COT_CONTRACTS)
        r = requests.get("https://publicreporting.cftc.gov/resource/6dca-aqww.json", timeout=12, params={
            "$select": "cftc_contract_market_code,report_date_as_yyyy_mm_dd,open_interest_all,"
                       "noncomm_positions_long_all,noncomm_positions_short_all",
            "$where": f"cftc_contract_market_code in ({codes})",
            "$order": "report_date_as_yyyy_mm_dd DESC", "$limit": 52 * len(COT_CONTRACTS)})
        r.raise_for_status()
        d = pd.DataFrame(r.json())
        if d.empty:
            return None
        d["date"] = pd.to_datetime(d["report_date_as_yyyy_mm_dd"])
        for c in ["open_interest_all", "noncomm_positions_long_all", "noncomm_positions_short_all"]:
            d[c] = pd.to_numeric(d[c], errors="coerce")
        d["net"] = d["noncomm_positions_long_all"] - d["noncomm_positions_short_all"]
        d["net_pct_oi"] = 100 * d["net"] / d["open_interest_all"]
        rows = []
        for code, g in d.sort_values("date").groupby("cftc_contract_market_code"):
            if len(g) < 3:
                continue
            last, prev, h = g.iloc[-1], g.iloc[-2], g["net_pct_oi"]
            rng = h.max() - h.min()
            rows.append({"Contract": COT_CONTRACTS.get(code, code), "As of": last["date"].date(),
                         "Net Spec (contracts)": int(last["net"]), "Net % OI": last["net_pct_oi"],
                         "1W Δ % OI": last["net_pct_oi"] - prev["net_pct_oi"],
                         "52W Percentile": 100 * (last["net_pct_oi"] - h.min()) / rng if rng else 50.0,
                         "History": h.tolist()})
        return pd.DataFrame(rows) if rows else None
    except Exception:
        return None


# ════════════════════════════════════════════════════════════════════════════
# 4. FLOW ENGINE  — every metric is vectorised over a [date x ticker] panel
# ════════════════════════════════════════════════════════════════════════════
def flow_panels(P: dict, n: int, groups: pd.Series, classes: pd.Series) -> dict:
    """Return component panels in [-1, +1] plus raw diagnostics, for lookback n."""
    H, L, C, V = P["High"], P["Low"], P["Close"], P["Volume"]
    has_vol = np.broadcast_to((V.tail(120).sum() > 0).values, V.shape)   # per-ticker mask, broadcast over dates
    Vx = V.where(has_vol, 1.0)  # price-only instruments: constant volume => CMF = mean close-location
    rng = (H - L)
    mfm = (((C - L) - (H - C)) / rng.where(rng > 0)).fillna(0.0)          # money-flow multiplier
    tp = (H + L + C) / 3

    cmf = (mfm * Vx).rolling(n).sum() / Vx.rolling(n).sum().where(lambda x: x > 0)

    m = max(n, 7)                                                           # MFI period
    rmf = tp * Vx
    up = rmf.where(tp > tp.shift(1), 0.0).rolling(m).sum()
    dn = rmf.where(tp < tp.shift(1), 0.0).rolling(m).sum()
    mfi = 100 * up / (up + dn).where(lambda x: x > 0)

    r1 = C.pct_change(fill_method=None)
    ret = C / C.shift(n) - 1
    sig = (r1.rolling(60, min_periods=20).std() * np.sqrt(n)).where(lambda x: x > 0)

    grp_med = ret.T.groupby(groups.reindex(ret.columns).values).transform("median").T
    cls_med = ret.T.groupby(classes.reindex(ret.columns).values).transform("median").T
    single = groups.reindex(ret.columns).map(groups.value_counts()) < 2    # 1-member groups fall back to class
    peer = pd.DataFrame(np.where(single.values[None, :], cls_med.values, grp_med.values), index=ret.index, columns=ret.columns)
    rs_peer = np.tanh((ret - peer) / sig)

    basket = [t for t in RISK_ON_BASKET if t in C.columns]
    if basket:
        bret = ret[basket].mean(axis=1)
        bsig = sig[basket].mean(axis=1)
        rs_risk = np.tanh(ret.sub(bret, axis=0) / np.sqrt(sig ** 2 + (bsig ** 2).values[:, None]))
    else:
        rs_risk = rs_peer * 0

    k = max(n // 2, 3)
    flow_mom = np.tanh(5 * (cmf - cmf.shift(k)))                            # rate of change of the flow

    base = Vx.rolling(max(60, 2 * n), min_periods=20).mean().shift(n)
    rvol = (Vx.rolling(n).mean() / base.where(base > 0)).where(has_vol, 1.0).fillna(1.0)
    vol_int = (np.tanh(ret / sig) * rvol / 1.5).clip(-1, 1)                # direction x relative volume

    dollar = (mfm * tp * V).rolling(n).sum().where(has_vol)                 # signed $ proxy  (EXTENSION POINT)
    gross = (tp * V).rolling(n).sum().where(has_vol)

    return {"CMF": (cmf * 2.5).clip(-1, 1), "MFI": ((mfi - 50) / 50).clip(-1, 1), "RS vs Peers": rs_peer,
            "RS vs Risk-On": rs_risk, "Flow Momentum": flow_mom, "Volume Intensity": vol_int,
            "_cmf": cmf, "_mfi": mfi, "_ret": ret, "_rvol": rvol, "_dollar": dollar, "_gross": gross, "_k": k}


def composite(fp: dict, w: dict) -> pd.DataFrame:
    tot = sum(w.values()) or 1
    return 100 * sum(fp[c].fillna(0) * (w[c] / tot) for c in COMP_COLS)


@st.cache_data(ttl=900, show_spinner=False)
def compute(_P: dict, stamp: str, n: int, wt: tuple, extra: tuple, bpd: int = 1):
    """stamp/extra are cache keys only (data identity + off-universe tickers)."""
    w = dict(zip(COMP_COLS, wt))
    cols = _P["Close"].columns
    groups = pd.Series({t: (META.loc[t, "group"] if t in META.index else "Custom") for t in cols})
    classes = pd.Series({t: (META.loc[t, "cls"] if t in META.index else "Custom") for t in cols})
    fp = flow_panels(_P, n, groups, classes)
    score = composite(fp, w)
    snap = pd.DataFrame({"Score": score.iloc[-1]})
    snap["Δ Score"] = score.iloc[-1] - score.iloc[-1 - fp["_k"]]
    for c in COMP_COLS:
        snap[c] = fp[c].iloc[-1] * 100
    snap["CMF raw"], snap["MFI raw"] = fp["_cmf"].iloc[-1], fp["_mfi"].iloc[-1]
    snap["Return %"], snap["RVOL"] = fp["_ret"].iloc[-1] * 100, fp["_rvol"].iloc[-1]
    snap["Net $ Flow"], snap["Gross $"] = fp["_dollar"].iloc[-1], fp["_gross"].iloc[-1]
    snap["Last"] = _P["Close"].iloc[-1]
    snap["1D %"] = (_P["Close"].iloc[-1] / _P["Close"].iloc[-1 - bpd] - 1) * 100
    snap["Name"] = [META.loc[t, "name"] if t in META.index else t for t in snap.index]
    snap["Class"], snap["Group"] = classes, groups
    snap["Pool"] = [META.loc[t, "pool"] if t in META.index else None for t in snap.index]
    snap["Trend"] = [(_P["Close"][t].tail(60) / _P["Close"][t].tail(60).iloc[0]).round(4).tolist() for t in snap.index]
    snap.index.name = "Ticker"
    return snap, score, fp["_dollar"], fp["_gross"]


def pool_table(snap: pd.DataFrame) -> pd.DataFrame:
    s = snap[snap["Pool"].notna()]
    g = s.groupby("Pool")
    out = pd.DataFrame({"Score": g["Score"].mean(), "Δ Score": g["Δ Score"].mean(), "Net $ Flow": g["Net $ Flow"].sum(),
                        "Gross $": g["Gross $"].sum(), "Return %": g["Return %"].mean(), "N": g.size()})
    out["Flow % of $Vol"] = 100 * out["Net $ Flow"] / out["Gross $"].where(out["Gross $"] > 0)
    return out.sort_values("Score", ascending=False)


def regime_table(P: dict, n: int) -> pd.DataFrame:
    C, rows = P["Close"], []
    for label, a, b, sgn in REGIME_PAIRS:
        if a not in C or (b and b not in C):
            continue
        s = (C[a] / C[b] if b else C[a]).dropna()
        if len(s) < n + 61:
            continue
        ret = s.iloc[-1] / s.iloc[-1 - n] - 1
        sig = s.pct_change().rolling(60).std().iloc[-1] * np.sqrt(n)
        z = ret / sig if sig and sig > 0 else 0.0
        hist = (np.tanh((s / s.shift(n) - 1) / (s.pct_change().rolling(60).std() * np.sqrt(n))) * sgn * 100).dropna()
        rows.append({"Signal": label, "Move %": ret * 100, "Z": z, "Vote": float(np.tanh(z) * sgn * 100),
                     "Reads": "RISK-ON" if z * sgn > .25 else "RISK-OFF" if z * sgn < -.25 else "NEUTRAL",
                     "Trend": (s.tail(60) / s.tail(60).iloc[0]).round(4).tolist(), "_hist": hist})
    return pd.DataFrame(rows)


def signal_frame(s5: pd.DataFrame, s20: pd.DataFrame, s60: pd.DataFrame) -> pd.DataFrame:
    """Combine short, swing and positioning horizons into one plain-language signal per instrument."""
    d = s20[["Name", "Class", "Group", "Return %", "Trend"]].copy()
    d["5D"], d["20D"], d["60D"] = s5["Score"], s20["Score"], s60["Score"]
    d["Totaal"] = .3 * d["5D"] + .4 * d["20D"] + .3 * d["60D"]
    up = (d[["5D", "20D", "60D"]] > 10).all(axis=1)
    dn = (d[["5D", "20D", "60D"]] < -10).all(axis=1)
    d["Signaal"] = np.select([up & (d["Totaal"] > 35), up | (d["Totaal"] > 25), dn & (d["Totaal"] < -35), dn | (d["Totaal"] < -25)],
                             ["STERK ▲", "POSITIEF ▲", "STERK ▼", "NEGATIEF ▼"], "NEUTRAAL")
    d["Fase"] = np.select([d["5D"] > d["20D"] + 10, d["5D"] < d["20D"] - 10], ["versnelt", "verzwakt"], "stabiel")
    return d


@st.cache_data(ttl=900, show_spinner=False)
def backtest(_score: pd.DataFrame, _close: pd.DataFrame, stamp: str, horizons: tuple = (5, 20)):
    """Did a high score actually precede higher returns? On non-overlapping dates, rank the universe into
    score quintiles and measure the average forward return of each. No look-ahead: the score at date t
    only uses data up to t."""
    cols = [c for c in _score.columns if c in META.index]
    S, C = _score[cols], _close[cols]
    rows, verdict = [], {}
    for h in horizons:
        fwd = C.shift(-h) / C - 1
        q_rows = []
        for dt in S.index[130:len(S) - h:h]:
            sc, f = S.loc[dt], fwd.loc[dt]
            ok = sc.notna() & f.notna()
            if ok.sum() < 50:
                continue
            q = pd.qcut(sc[ok].rank(method="first"), 5, labels=False)
            q_rows.append(f[ok].groupby(q).mean())
        if len(q_rows) < 5:
            continue
        Q = pd.DataFrame(q_rows)
        spread = Q[4] - Q[0]
        t = float(spread.mean() / spread.std() * np.sqrt(len(spread))) if spread.std() > 0 else 0.0
        for qi in range(5):
            rows.append({"Horizon": f"{h}D", "Kwintiel": qi + 1, "ret": Q[qi].mean() * 100, "pos": (Q[qi] > 0).mean() * 100})
        verdict[h] = (float(spread.mean() * 100), t, len(spread), float((spread > 0).mean() * 100))
    return pd.DataFrame(rows), verdict


# ── machine-learning forecast with honest self-tuning ───────────────────────
# Candidate settings the model tries on itself: (forecast horizon in days, tree depth, min samples per leaf)
ML_CONFIGS = [(h, d, leaf) for h in (10, 20, 40) for d, leaf in ((2, 400), (3, 200))]


def _fit_predict(Xtr, ytr, Xte, depth=3, leaf=200):
    """Gradient-boosted trees (scikit-learn). Falls back to ridge regression if scikit-learn is missing."""
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor
        m = HistGradientBoostingRegressor(max_iter=80, learning_rate=0.08, max_depth=depth, min_samples_leaf=leaf,
                                          l2_regularization=1.0, random_state=0)
        m.fit(Xtr, ytr)
        return m.predict(Xte), "Gradient boosting (scikit-learn)"
    except ImportError:
        mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
        A = (Xtr - mu) / sd
        w = np.linalg.solve(A.T @ A + 50.0 * np.eye(A.shape[1]), A.T @ (ytr - ytr.mean()))
        return ((Xte - mu) / sd) @ w + ytr.mean(), "Ridge-regressie (numpy)"


def _walk_forward(F, valid, Y, R, h, step, retrain, depth, leaf, start):
    """Train on the past only (with an h-day gap so no future leaks in), predict the next block, repeat.
    Returns one row per non-overlapping test date: (date position, rank-IC, top-bottom spread, quintile returns)."""
    lab = valid & ~np.isnan(Y)
    gap = int(np.ceil(h / step)) + 1
    PR = np.full(Y.shape, np.nan)
    for i0 in range(start, len(Y), retrain):
        tr = lab[: max(i0 - gap, 0)]
        te = valid[i0:i0 + retrain]
        if tr.sum() < 3000 or not te.any():
            continue
        pred, _ = _fit_predict(F[: i0 - gap][tr], Y[: i0 - gap][tr], F[i0:i0 + retrain][te], depth, leaf)
        blk = PR[i0:i0 + retrain]
        blk[te] = pred
    rows = []
    for i in range(start, len(Y), gap):
        ok = ~np.isnan(PR[i]) & ~np.isnan(R[i])
        if ok.sum() < 50:
            continue
        p, r = pd.Series(PR[i][ok]), pd.Series(R[i][ok])
        qm = r.groupby(pd.qcut(p.rank(method="first"), 5, labels=False)).mean()
        rows.append((i, p.corr(r, method="spearman"), qm.iloc[-1] - qm.iloc[0], qm.values))
    return rows, lab


def _metrics(rows):
    ic, sp = np.array([r[1] for r in rows]), np.array([r[2] for r in rows])
    t = lambda x: float(x.mean() / x.std(ddof=1) * np.sqrt(len(x))) if len(x) > 2 and x.std(ddof=1) > 0 else 0.0
    return {"ic": float(ic.mean()), "ic_t": t(ic), "spread": float(sp.mean() * 100), "spread_t": t(sp),
            "hit": float((sp > 0).mean() * 100), "n": len(rows), "quint": np.mean([r[3] for r in rows], axis=0) * 100}


@st.cache_data(ttl=3600, show_spinner=False)
def ml_forecast(_P: dict, stamp: str, step: int = 3, retrain: int = 30):
    """Learn from history which flow patterns preceded out-performance, tune itself, and report honestly.

    Features : 6 flow components on 5D/20D/60D lookbacks + volatility-scaled momentum on 5/20/60/120D (22 inputs).
    Target   : cross-sectional rank of the return over the NEXT h trading days.
    Tuning   : every setting in ML_CONFIGS is walked forward through history. The setting that ranks best on the
               VALIDATION period (first 65% of the test span) is selected.
    Verdict  : measured only on the HOLD-OUT period (last 35%), which played no part in choosing the setting.
               Tuning until the same test data looks significant would manufacture a false result, so the
               hold-out is looked at exactly once.
    Returns None when there is too little history."""
    cols = [c for c in _P["Close"].columns if c in META.index]
    P_ = {k: v[cols] for k, v in _P.items()}
    groups, classes = META.loc[cols, "group"], META.loc[cols, "cls"]
    C = P_["Close"]
    r1 = C.pct_change(fill_method=None)
    feats = {}
    for n in (5, 20, 60):
        fp = flow_panels(P_, n, groups, classes)
        for c in COMP_COLS:
            feats[f"{c} · {n}D"] = fp[c]
    for n in (5, 20, 60, 120):
        feats[f"Momentum · {n}D"] = np.tanh((C / C.shift(n) - 1) / (r1.rolling(60, min_periods=20).std() * np.sqrt(n)))
    names = list(feats)
    dates = C.index[130::step]
    if len(dates) < 160:
        return None
    F = np.stack([feats[k].reindex(dates).values for k in names], axis=2)        # (dates, tickers, features)
    valid = ~np.isnan(F).any(axis=2)
    start = max(int(250 / step), int(len(dates) * 0.3))
    split = start + int((len(dates) - start) * 0.65)
    trials = []
    for h, depth, leaf in ML_CONFIGS:
        fwd = C.shift(-h) / C - 1
        Y, R = (fwd.rank(axis=1, pct=True) - 0.5).reindex(dates).values, fwd.reindex(dates).values
        rows, lab = _walk_forward(F, valid, Y, R, h, step, retrain, depth, leaf, start)
        val, hold = [r for r in rows if r[0] < split], [r for r in rows if r[0] >= split]
        if len(val) < 6 or len(hold) < 4:
            continue
        trials.append({"h": h, "depth": depth, "leaf": leaf, "val": _metrics(val), "hold": _metrics(hold), "rows": rows,
                       "Y": Y, "lab": lab})
    if not trials:
        return None
    best = max(trials, key=lambda t: t["val"]["ic_t"])                             # chosen on validation only
    Xnow = np.column_stack([feats[k].iloc[-1].values for k in names])
    oknow = ~np.isnan(Xnow).any(axis=1)
    pnow, model_name = _fit_predict(F[best["lab"]], best["Y"][best["lab"]], Xnow[oknow], best["depth"], best["leaf"])
    yl = best["Y"][best["lab"]]
    table_ = pd.DataFrame([{"Horizon": f"{t['h']}D", "Diepte": t["depth"], "Gekozen": "◀ gekozen" if t is best else "",
                            "Validatie IC": t["val"]["ic"], "Validatie t": t["val"]["ic_t"], "Validatie n": t["val"]["n"],
                            "Eindtoets IC": t["hold"]["ic"], "Eindtoets t": t["hold"]["ic_t"], "Eindtoets n": t["hold"]["n"],
                            "Eindtoets top−bodem %": t["hold"]["spread"]} for t in trials])
    return {"best": {k: best[k] for k in ("h", "depth", "leaf", "val", "hold")}, "trials": table_,
            "curve": pd.Series(np.cumsum([r[2] for r in best["rows"]]) * 100, index=[dates[r[0]] for r in best["rows"]]),
            "split_date": dates[split], "forecast": pd.Series(np.clip(pnow * 200, -100, 100), index=np.array(cols)[oknow]),
            "relevance": pd.Series({k: float(np.corrcoef(F[..., j][best["lab"]], yl)[0, 1]) for j, k in enumerate(names)}),
            "model": model_name, "examples": int(best["lab"].sum()), "first": dates[0], "test_from": dates[start], "n_feat": len(names)}


# ════════════════════════════════════════════════════════════════════════════
# 5. CHART BUILDERS
# ════════════════════════════════════════════════════════════════════════════
def sankey_fig(pt: pd.DataFrame, mode: str):
    """Rotation model: pools with negative flow are sources, positive are destinations. Each source's
    outflow is split across destinations pro-rata to their inflow. This is an ALLOCATION MODEL of net
    pressure, not observed pairwise transfers (those are not observable in any dataset)."""
    val = pt["Score"] if mode == "Flow Score" else pt["Flow % of $Vol"].fillna(0) if mode == "% of $ Volume" else pt["Net $ Flow"].fillna(0)
    src, dst = val[val < 0].abs().sort_values(ascending=False), val[val > 0].sort_values(ascending=False)
    if src.empty or dst.empty:
        return None
    so, di = src.sum(), dst.sum()
    labels = [f"{p}  ▼" for p in src.index] + [f"{p}  ▲" for p in dst.index]
    colors = [RED] * len(src) + [GREEN] * len(dst)
    S, T, Vv, LC, HV = [], [], [], [], []
    scale = min(so, di)
    for i, (a, av) in enumerate(src.items()):
        for j, (b, bv) in enumerate(dst.items()):
            v = (av / so) * (bv / di) * scale
            S.append(i); T.append(len(src) + j); Vv.append(v)
            LC.append(f"rgba(0,255,156,{0.12 + 0.45 * bv / dst.max():.2f})")
            HV.append(f"{a} → {b}")
    # residual: imbalance goes to / comes from an external node so ribbon widths stay honest
    if so > di:
        labels.append("Unallocated / Outside universe"); colors.append(DIM)
        for i, (a, av) in enumerate(src.items()):
            S.append(i); T.append(len(labels) - 1); Vv.append(av * (so - di) / so); LC.append("rgba(255,45,85,0.28)"); HV.append(f"{a} → outside")
    elif di > so:
        labels.insert(0, "New money / Outside universe"); colors.insert(0, DIM)
        S, T = [s + 1 for s in S], [t + 1 for t in T]
        for j, (b, bv) in enumerate(dst.items()):
            S.append(0); T.append(1 + len(src) + j); Vv.append(bv * (di - so) / di); LC.append("rgba(0,255,156,0.22)"); HV.append(f"outside → {b}")
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=labels, color=colors, pad=14, thickness=16, line=dict(color=BG, width=1),
                  hovertemplate="%{label}<br>magnitude %{value:.3s}<extra></extra>"),
        link=dict(source=S, target=T, value=Vv, color=LC, customdata=HV,
                  hovertemplate="%{customdata}<br>%{value:.3s}<extra></extra>")))
    return lay(fig, 470, title=dict(text="OUTFLOW POOLS  ──►  INFLOW POOLS", font=dict(size=11, color=DIM)))


def bar_scores(s: pd.Series, h=470, title="", highlight=None):
    s = s.sort_values()
    colors = [CYAN if i == highlight else col(v) for i, v in s.items()]
    fig = go.Figure(go.Bar(x=s.values, y=s.index.astype(str), orientation="h", marker_color=colors,
                           text=[f"{v:+.0f}" for v in s.values], textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}: %{x:+.1f}<extra></extra>"))
    lay(fig, h, title=dict(text=title, font=dict(size=11, color=DIM)))
    fig.update_xaxes(range=[-115, 115], zeroline=True)
    fig.update_layout(dragmode=False, clickmode="event+select")
    return fig


def gauge(value, title, h=230):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value, number=dict(font=dict(size=38, color=col(value), family=MONO), valueformat="+.0f"),
        title=dict(text=title, font=dict(size=11, color=DIM)),
        gauge=dict(axis=dict(range=[-100, 100], tickcolor=DIM, tickfont=dict(size=9)), bar=dict(color=col(value), thickness=.28),
                   bgcolor=PANEL, borderwidth=0,
                   steps=[dict(range=[-100, -40], color="#3a0f1c"), dict(range=[-40, -10], color="#22121a"),
                          dict(range=[-10, 10], color="#161d2c"), dict(range=[10, 40], color="#0e2a22"),
                          dict(range=[40, 100], color="#0b3d2c")])))
    lay(fig, h)
    fig.update_layout(margin=dict(l=34, r=34, t=56, b=10))
    return fig


def spark(s: pd.Series, title: str, h=120):
    s = s.dropna()
    chg = (s.iloc[-1] / s.iloc[0] - 1) * 100 if len(s) > 1 else 0.0
    c = GREEN if chg >= 0 else RED
    fig = go.Figure(go.Scatter(x=list(range(len(s))), y=s.values, mode="lines", line=dict(color=c, width=1.6),
                               fill="tozeroy", fillcolor=f"rgba({'0,255,156' if chg >= 0 else '255,45,85'},0.08)",
                               hovertemplate="%{y:.2f}<extra></extra>"))
    lay(fig, h, title=dict(text=f"{title}  <span style='color:{c}'>{chg:+.2f}%</span>", font=dict(size=11)))
    fig.update_xaxes(visible=False)
    pad = (s.max() - s.min()) * .1 or 1
    fig.update_yaxes(visible=False, range=[s.min() - pad, s.max() + pad])
    return fig


def treemap_fig(snap: pd.DataFrame, size_mode: str):
    d = snap.reset_index()
    d["size"] = np.sqrt(d["Gross $"].fillna(d["Gross $"].median()).clip(lower=1)) if size_mode == "√ Dollar volume" else 1.0
    d["size"] = d["size"].fillna(d["size"].median() if d["size"].notna().any() else 1.0)
    ids, labels, parents, vals, cols_, txt = ["ALL"], ["ALL MARKETS"], [""], [d["size"].sum()], [d["Score"].mean()], [""]
    for c, dc in d.groupby("Class"):
        ids.append(c); labels.append(c.upper()); parents.append("ALL"); vals.append(dc["size"].sum()); cols_.append(dc["Score"].mean()); txt.append("")
        for g, dg in dc.groupby("Group"):
            gid = f"{c}/{g}"
            ids.append(gid); labels.append(g); parents.append(c); vals.append(dg["size"].sum()); cols_.append(dg["Score"].mean()); txt.append("")
            for _, r in dg.iterrows():
                ids.append(f"{gid}/{r['Ticker']}"); labels.append(r["Ticker"]); parents.append(gid); vals.append(r["size"]); cols_.append(r["Score"])
                txt.append(f"{r['Name']}<br>CMF {r['CMF raw']:+.2f} · MFI {r['MFI raw']:.0f}<br>Ret {r['Return %']:+.1f}% · RVOL {r['RVOL']:.2f}x")
    fig = go.Figure(go.Treemap(
        ids=ids, labels=labels, parents=parents, values=vals, branchvalues="total", customdata=np.array(txt, dtype=object),
        marker=dict(colors=cols_, colorscale=SCALE, cmin=-100, cmax=100, line=dict(color=BG, width=1.5),
                    colorbar=dict(title="Score", thickness=10, len=.8, tickfont=dict(size=9))),
        text=[f"{v:+.0f}" for v in cols_], texttemplate="<b>%{label}</b><br>%{text}", textfont=dict(family=MONO, size=12, color="#ffffff"),
        hovertemplate="<b>%{label}</b>  score %{color:+.1f}<br>%{customdata}<extra></extra>",
        pathbar=dict(visible=True, thickness=20), maxdepth=4, tiling=dict(pad=2)))
    return lay(fig, 640)


def price_flow_fig(P, t, n):
    d = pd.DataFrame({k: P[k][t] for k in ["Open", "High", "Low", "Close", "Volume"]}).dropna(subset=["Close"]).tail(180)
    rng = (d["High"] - d["Low"])
    mfm = (((d["Close"] - d["Low"]) - (d["High"] - d["Close"])) / rng.where(rng > 0)).fillna(0)
    full_v = P["Volume"][t].where(P["Volume"][t] > 0, 1.0) if P["Volume"][t].tail(120).sum() == 0 else P["Volume"][t]
    fr = (P["High"][t] - P["Low"][t])
    fm = (((P["Close"][t] - P["Low"][t]) - (P["High"][t] - P["Close"][t])) / fr.where(fr > 0)).fillna(0)
    cmf = ((fm * full_v).rolling(n).sum() / full_v.rolling(n).sum()).reindex(d.index)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[.58, .18, .24], vertical_spacing=.02)
    fig.add_trace(go.Candlestick(x=d.index, open=d["Open"], high=d["High"], low=d["Low"], close=d["Close"],
                                 increasing_line_color=GREEN, decreasing_line_color=RED, increasing_fillcolor=GREEN,
                                 decreasing_fillcolor=RED, line_width=1), 1, 1)
    for w_, c_ in ((20, AMBER), (50, CYAN)):
        fig.add_trace(go.Scatter(x=d.index, y=P["Close"][t].rolling(w_).mean().reindex(d.index), line=dict(color=c_, width=1),
                                 hoverinfo="skip"), 1, 1)
    fig.add_trace(go.Bar(x=d.index, y=d["Volume"], marker_color=[GREEN if m > 0 else RED for m in mfm], opacity=.7), 2, 1)
    fig.add_trace(go.Scatter(x=d.index, y=cmf, line=dict(color=CYAN, width=1.4), fill="tozeroy", fillcolor="rgba(34,211,238,0.10)"), 3, 1)
    lay(fig, 520, title=dict(text=f"{t} · PRICE (MA20 amber / MA50 cyan) · VOLUME (colour = close location) · CMF({n})", font=dict(size=11, color=DIM)))
    fig.update_xaxes(rangeslider_visible=False, rangebreaks=[dict(bounds=["sat", "mon"])])
    return fig


def volume_profile_fig(P, t, days=60):
    d = pd.DataFrame({"tp": (P["High"][t] + P["Low"][t] + P["Close"][t]) / 3, "v": P["Volume"][t],
                      "up": P["Close"][t] >= P["Open"][t]}).dropna().tail(days)
    if d["v"].sum() <= 0:
        d["v"] = 1.0
    bins = np.linspace(d["tp"].min(), d["tp"].max() + 1e-9, 25)
    d["b"] = pd.cut(d["tp"], bins, include_lowest=True)
    upv = d[d["up"]].groupby("b", observed=False)["v"].sum()
    dnv = d[~d["up"]].groupby("b", observed=False)["v"].sum()
    mids = [iv.mid for iv in upv.index]
    fig = go.Figure([go.Bar(y=mids, x=upv.values, orientation="h", marker_color=GREEN, opacity=.8, name="Up-day vol"),
                     go.Bar(y=mids, x=dnv.values, orientation="h", marker_color=RED, opacity=.8, name="Down-day vol")])
    last = P["Close"][t].dropna().iloc[-1]
    poc = mids[int(np.argmax((upv + dnv).values))]
    fig.add_hline(y=last, line=dict(color=CYAN, width=1, dash="dot"), annotation_text=f"last {last:,.2f}", annotation_font_color=CYAN)
    fig.add_hline(y=poc, line=dict(color=AMBER, width=1), annotation_text=f"POC {poc:,.2f}", annotation_position="bottom right", annotation_font_color=AMBER)
    lay(fig, 520, barmode="stack", title=dict(text=f"VOLUME PROFILE · {days}D (volume at price)", font=dict(size=11, color=DIM)))
    fig.update_xaxes(showticklabels=False)
    return fig


# ════════════════════════════════════════════════════════════════════════════
# 6. STATE, SIDEBAR, DATA LOAD
# ════════════════════════════════════════════════════════════════════════════
ss = st.session_state
VIEWS = ["SIGNALEN", "VOORSPELLING", "COMMAND CENTER", "HEATMAP", "DEEP DIVE", "REGIME & LIQUIDITY", "LEADERBOARDS", "METHODOLOGY", "HANDLEIDING"]
if "pins" not in ss:
    qp = st.query_params.get("pins", "")
    ss.pins = [p for p in qp.split(",") if p] or ["SPY", "TLT", "GLD", "UUP", "HYG", "BTC-USD"]
ss.setdefault("view", VIEWS[0])
ss.setdefault("ticker", "SPY")
ss.setdefault("extra", [])
ss.setdefault("pool", None)


def goto(ticker=None, view="DEEP DIVE"):
    """Queue a navigation. It is applied at the top of the next run, before the view widget exists
    (Streamlit forbids changing a widget's value after it has been drawn)."""
    ss["_goto"] = (ticker, view)


if "_goto" in ss:                       # apply queued navigation before any widget is created
    _t, _v = ss.pop("_goto")
    if _t:
        ss.ticker = _t
    ss.view = _v


def toggle_pin(t):
    ss.pins = [p for p in ss.pins if p != t] if t in ss.pins else ss.pins + [t]
    st.query_params["pins"] = ",".join(ss.pins)


def on_search():
    q = (ss.get("q") or "").strip()
    if not q:
        return
    qu = q.upper()
    hit = qu if qu in META.index else None
    if not hit:  # match by name
        m = META[META["name"].str.contains(q, case=False, regex=False)]
        hit = m.index[m["name"].str.len().argmin()] if len(m) else qu  # shortest name = closest match
    if hit not in META.index and hit not in ss.extra:
        ss.extra = ss.extra + [hit]
    goto(hit)
    ss.q = ""


def on_pick():
    if ss.get("pick"):
        goto(ss.pick.split(" · ")[0])
        ss.pick = None


with st.sidebar:
    st.markdown(f"<div style='font-family:{MONO};font-size:15px;font-weight:700;color:{GREEN};letter-spacing:.14em'>◈ MFCC</div>",
                unsafe_allow_html=True)
    sec("Search any ticker")
    st.text_input("Ticker or name (any Yahoo symbol)", key="q", on_change=on_search, placeholder="e.g. NVDA, gold, ^GDAXI, ETH-USD",
                  label_visibility="collapsed")
    st.selectbox("Universe", [f"{t} · {r['name']} · {r['cls']}" for t, r in META.iterrows()], index=None, key="pick",
                 on_change=on_pick, placeholder="…or browse the universe", label_visibility="collapsed")
    sec("Data")
    mode = st.radio("Data mode", ["Live", "Demo"], horizontal=True, label_visibility="collapsed",
                    help="Live = Yahoo Finance. Demo = synthetic data so the terminal can be explored offline.")
    if st.button("⟳ Refresh data", width="stretch"):
        st.cache_data.clear()
    st.toggle("Auto-refresh (5 min)", key="auto", help="Herlaadt de pagina elke 5 minuten. Dagdata ververst elke 15 min, LIVE 1D elke 4 min.")
    sec("Composite weights")
    wt = tuple(st.slider(c, 0, 50, DEFAULT_WEIGHTS[c], 5, key=f"w_{c}") for c in COMP_COLS)
    if sum(wt) == 0:
        wt = tuple(DEFAULT_WEIGHTS.values())
    st.markdown(f"<div class='note'>Weights are renormalised to 100%. Score = Σ weight × component, each component in [-100, +100].</div>",
                unsafe_allow_html=True)

tickers = tuple(list(META.index) + [t for t in ss.extra if t not in META.index])
demo, failed, P = (mode == "Demo"), [], None
if not demo:
    with st.spinner("Fetching market data from Yahoo Finance…"):
        try:
            P, failed = fetch_live(tickers)
        except Exception:
            P = None
    if P is None or P["Close"].shape[1] < 20:
        demo, P, failed = True, None, []
        st.markdown("<div class='banner'>⚠ LIVE DATA UNREACHABLE (Yahoo Finance did not respond) — showing SYNTHETIC DEMO DATA. "
                    "Numbers below are not real markets. Check your connection / <code>pip install -U yfinance</code> and press Refresh.</div>",
                    unsafe_allow_html=True)
if demo:
    if mode == "Demo":
        st.markdown("<div class='banner'>DEMO MODE — synthetic data, not real markets. Switch to Live in the sidebar.</div>", unsafe_allow_html=True)
    P = make_demo(tickers)
P = _clean(P)
dropped = [t for t in tickers if t not in P["Close"].columns]


def mkstamp(X):
    return f"{'demo' if demo else 'live'}|{X['Close'].index[-1]}|{X['Close'].shape}|{float(X['Close'].iloc[-1].sum()):.4f}"


stamp = mkstamp(P)

# ── header + global controls ────────────────────────────────────────────────
asof = P["Close"].index[-1].strftime("%Y-%m-%d")
st.markdown(f"<div class='hdr'><div class='t'>◈ MONEY FLOW COMMAND CENTER</div><div class='s'>"
            f"{'DEMO DATA' if demo else 'LIVE · YAHOO FINANCE'} · last bar {asof} · {P['Close'].shape[1]} instruments · "
            f"rendered {datetime.now(timezone.utc):%H:%M:%S} UTC</div></div>", unsafe_allow_html=True)
with st.expander("ⓘ  What do these “flows” represent? (read once)"):
    st.markdown("""
**No free dataset reports actual money moving between asset classes.** This terminal infers *flow pressure* from price × volume:

| Component (default weight) | What it measures |
|---|---|
| **CMF** — Chaikin Money Flow (30%) | Where each bar closes inside its range, volume-weighted. Closes near highs on volume = accumulation. |
| **MFI** — Money Flow Index (20%) | Volume-weighted RSI of typical price × volume. |
| **RS vs Peers** (10%) | Return minus the median return of the instrument's sector/region group, volatility-scaled. |
| **RS vs Risk-On** (10%) | Return minus an equal-weight basket of SPY, QQQ, IWM, EEM, HYG, CPER, volatility-scaled. |
| **Flow Momentum** (15%) | Rate of change of CMF — is accumulation accelerating or fading? |
| **Volume Intensity** (15%) | Direction × relative volume (current vs prior baseline). |

**Composite Money Flow Score** = weighted sum, −100 (heavy distribution) to +100 (heavy accumulation). **Net $ Flow** = Σ(close-location × typical price × volume) — a signed dollar-volume proxy, *not* fund subscriptions. The Sankey allocates net pressure between pools pro-rata; it is a model, not observed transfers. Full detail in **METHODOLOGY**.
""")
c1, c2 = st.columns([2.2, 1])
with c1:
    st.radio("View", VIEWS, key="view", horizontal=True, label_visibility="collapsed")
with c2:
    tf = st.radio("Timeframe", list(TIMEFRAMES), index=2, horizontal=True, label_visibility="collapsed", key="tf",
                  help="Lookback for every flow metric. LIVE 1D = last session on 15-minute bars. 5D = tactical, 20D = swing, 60D/120D = positioning.")
N = TIMEFRAMES[tf]
PF, bpd = P, 1                      # PF = panels the flow engine runs on (daily, or 15-minute bars in LIVE 1D)


def get_bars():
    """Cleaned 15-minute panels restricted to instruments that also have daily data, or None."""
    if demo:
        return None
    with st.spinner("15-minutenkoersen ophalen…"):
        B = fetch_bars(tickers)
    if B is None:
        return None
    B = _clean(B)
    keep_ = [c for c in B["Close"].columns if c in P["Close"].columns]
    if len(keep_) < 20 or len(B["Close"]) < 150:
        return None
    return {k_: v_[keep_] for k_, v_ in B.items()}


if tf == "LIVE 1D":
    PB = get_bars()
    keep = list(PB["Close"].columns) if PB is not None else []
    if PB is None:
        N = 5
        st.markdown("<div class='banner'>LIVE 1D niet beschikbaar (" + ("demo-modus" if demo else "Yahoo gaf geen 15-minutenkoersen") +
                    ") — 5D op dagkoersen wordt getoond.</div>", unsafe_allow_html=True)
    else:
        PF, bpd = PB, BARS_PER_DAY
        st.markdown(f"<div class='note'>LIVE 1D · 15-minutenkoersen · laatste bar {PF['Close'].index[-1]:%d %b %H:%M} New York-tijd · "
                    f"{len(keep)} instrumenten · Yahoo-koersen kunnen tot 15 min vertraagd zijn; buiten de Amerikaanse handelsuren zie je de laatste sessie.</div>",
                    unsafe_allow_html=True)

snap, score_hist, dollar_hist, gross_hist = compute(PF, mkstamp(PF), N, wt, tuple(ss.extra), bpd)
uni = snap[snap.index.isin(META.index)]
pt = pool_table(uni)
reg = regime_table(PF, N)
regime_score = float(reg["Vote"].mean()) if len(reg) else 0.0

# ── KPI strip ───────────────────────────────────────────────────────────────
breadth = 100 * (uni["Score"] > 0).mean()
k = st.columns(6)
with k[0]:
    kpi("Regime", f"{regime_score:+.0f}", "RISK-ON" if regime_score > 15 else "RISK-OFF" if regime_score < -15 else "MIXED", col(regime_score))
with k[1]:
    kpi("Flow breadth", f"{breadth:.0f}%", "instruments with score > 0", col(breadth - 50))
with k[2]:
    kpi("Top inflow pool", pt.index[0], f"score {pt['Score'].iloc[0]:+.0f} · {fmt_usd(pt['Net $ Flow'].iloc[0])}", GREEN)
with k[3]:
    kpi("Top outflow pool", pt.index[-1], f"score {pt['Score'].iloc[-1]:+.0f} · {fmt_usd(pt['Net $ Flow'].iloc[-1])}", RED)
with k[4]:
    b = uni["Score"].idxmax()
    kpi("Strongest name", b, f"{uni.loc[b, 'Name']} · {uni.loc[b, 'Score']:+.0f}", GREEN)
with k[5]:
    w_ = uni["Score"].idxmin()
    kpi("Weakest name", w_, f"{uni.loc[w_, 'Name']} · {uni.loc[w_, 'Score']:+.0f}", RED)

# ── pinned watch panel (always visible) ─────────────────────────────────────
pins = [p for p in ss.pins if p in snap.index]
if pins:
    sec(f"Watch panel · {tf}")
    pc = st.columns(min(len(pins), 8))
    for i, t in enumerate(pins[:8]):
        r = snap.loc[t]
        with pc[i]:
            kpi(f"{t} · {r['Last']:,.2f}", f"{r['Score']:+.0f}", f"{r['1D %']:+.2f}% 1D · CMF {r['CMF raw']:+.2f}", col(r["Score"]))
            st.button("open", key=f"po_{t}", on_click=goto, args=(t,), width="stretch")

TABLE_COLS = ["Name", "Class", "Group", "Score", "Δ Score", "CMF raw", "MFI raw", "RS vs Peers", "RS vs Risk-On", "RVOL",
              "Return %", "Net $ Flow", "Trend"]
COLCFG = {
    "Score": st.column_config.ProgressColumn("Score", min_value=-100, max_value=100, format="%+.0f"),
    "Δ Score": st.column_config.NumberColumn("Δ Score", format="%+.0f", help="Change in score over half the lookback"),
    "CMF raw": st.column_config.NumberColumn("CMF", format="%+.2f"), "MFI raw": st.column_config.NumberColumn("MFI", format="%.0f"),
    "RS vs Peers": st.column_config.NumberColumn("RS Peers", format="%+.0f"),
    "RS vs Risk-On": st.column_config.NumberColumn("RS Risk-On", format="%+.0f"),
    "RVOL": st.column_config.NumberColumn("RVOL", format="%.2fx"), "Return %": st.column_config.NumberColumn(f"Ret {tf}", format="%+.2f%%"),
    "Net $ Flow": st.column_config.NumberColumn("Net $ Flow", format="compact"),
    "Flow % of $Vol": st.column_config.NumberColumn("Flow % $Vol", format="%+.1f%%"),
    "Gross $": st.column_config.NumberColumn("Gross $", format="compact"),
    "Trend": st.column_config.LineChartColumn("Trend", width="small"),
    "Model": st.column_config.ProgressColumn("Model", min_value=-100, max_value=100, format="%+.0f",
                                             help="Modelverwachting voor de komende 20 handelsdagen: +100 = verwacht bij de best presterende, −100 = bij de slechtste"),
    "Live": st.column_config.NumberColumn("Live", format="%+.0f", help="Flow score vandaag, op 15-minutenkoersen"),
    "5D": st.column_config.NumberColumn("5D", format="%+.0f", help="Flow score, laatste 5 handelsdagen"),
    "20D": st.column_config.NumberColumn("20D", format="%+.0f", help="Flow score, laatste 20 handelsdagen"),
    "60D": st.column_config.NumberColumn("60D", format="%+.0f", help="Flow score, laatste 60 handelsdagen"),
    "Totaal": st.column_config.ProgressColumn("Totaal", min_value=-100, max_value=100, format="%+.0f",
                                              help="30% × 5D + 40% × 20D + 30% × 60D"),
}


def styled(df):
    def c(v):
        return f"color:{GREEN}" if v > 5 else f"color:{RED}" if v < -5 else f"color:{AMBER}"
    cols = [x for x in ["Score", "Δ Score", "CMF raw", "RS vs Peers", "RS vs Risk-On", "Return %", "Net $ Flow", "Flow % of $Vol",
                        "Vote", "Move %", "Z", "Live", "5D", "20D", "60D", "Totaal", "Model"] if x in df.columns]
    sty = df.style.map(lambda v: c(v * 100) if isinstance(v, (int, float)) and np.isfinite(v) else "", subset=cols)
    if "Signaal" in df.columns:
        sty = sty.map(lambda v: f"color:{GREEN};font-weight:700" if "▲" in str(v) else f"color:{RED};font-weight:700" if "▼" in str(v) else f"color:{DIM}",
                      subset=["Signaal"])
    return sty


def table(df, key, h=420, cols=None):
    """Sortable table (click any header). Selecting a row opens the Deep Dive."""
    d = df[cols or [c for c in TABLE_COLS if c in df.columns]]
    ev = st.dataframe(styled(d), column_config=COLCFG, height=h, width="stretch", key=key, on_select="rerun",
                      selection_mode="single-row")
    rows = ev.selection.rows if ev and ev.selection else []
    picked = d.index[rows[0]] if rows else None
    if picked == ss.get(f"_sel_{key}"):   # already handled (selection survives reruns) -> don't navigate again
        return None
    ss[f"_sel_{key}"] = picked
    return picked


# ════════════════════════════════════════════════════════════════════════════
# 7. VIEWS
# ════════════════════════════════════════════════════════════════════════════
view = ss.view

if view == "SIGNALEN":
    S3 = {k_: compute(P, stamp, n_, wt, tuple(ss.extra)) for k_, n_ in (("5D", 5), ("20D", 20), ("60D", 60), ("120D", 120))}
    PBs = get_bars()
    live = compute(PBs, mkstamp(PBs), BARS_PER_DAY, wt, tuple(ss.extra), BARS_PER_DAY)[0] if PBs is not None else None
    if live is not None:
        live = live[live.index.isin(META.index)]
    s3 = {k_: v_[0][v_[0].index.isin(META.index)] for k_, v_ in S3.items()}
    sig = signal_frame(s3["5D"], s3["20D"], s3["60D"])
    if live is not None:
        sig["Live"] = live["Score"].reindex(sig.index)
    pt5, pt20 = pool_table(s3["5D"]), pool_table(s3["20D"])
    reg20 = regime_table(P, 20)
    rs20 = float(reg20["Vote"].mean()) if len(reg20) else 0.0
    into = [f"<b style='color:{GREEN}'>{p}</b> ({pt20.loc[p, 'Score']:+.0f})" for p in pt20.index[:3] if pt20.loc[p, "Score"] > 5]
    away = [f"<b style='color:{RED}'>{p}</b> ({pt20.loc[p, 'Score']:+.0f})" for p in pt20.index[::-1][:3] if pt20.loc[p, "Score"] < -5]
    turn = (pt5["Score"] - pt20["Score"].reindex(pt5.index)).sort_values()
    n_up, n_dn = int(sig["Signaal"].str.contains("▲").sum()), int(sig["Signaal"].str.contains("▼").sum())
    rtxt = ("RISK-ON — beleggers zoeken risico op (aandelen, high yield, cyclische grondstoffen)" if rs20 > 15 else
            "RISK-OFF — beleggers mijden risico (richting dollar, cash, obligaties)" if rs20 < -15 else
            "GEMENGD — geen duidelijke richting tussen risico en veiligheid")
    sec(f"Waar stroomt het geld naartoe? · stand per {asof}")
    st.markdown(f"""<div class='kpi' style='font-family:{MONO};font-size:13px;line-height:1.9'>
<b>Marktklimaat:</b> <span style='color:{col(rs20)}'>{rtxt}</span> (meter {rs20:+.0f})<br>
<b>Geld stroomt naar</b> (20 dagen): {", ".join(into) or "geen enkele pool duidelijk positief"}<br>
<b>Geld stroomt weg uit</b> (20 dagen): {", ".join(away) or "geen enkele pool duidelijk negatief"}<br>
<b>Draait bij</b> (laatste 5 dagen sterker dan 20 dagen): <b style='color:{GREEN}'>{turn.index[-1]}</b> ({turn.iloc[-1]:+.0f} punten) ·
<b>Verliest vaart:</b> <b style='color:{RED}'>{turn.index[0]}</b> ({turn.iloc[0]:+.0f} punten)<br>
<b>Signalen:</b> <span style='color:{GREEN}'>{n_up} positief</span> · <span style='color:{RED}'>{n_dn} negatief</span> · {len(sig) - n_up - n_dn} neutraal
van {len(sig)} instrumenten</div>""", unsafe_allow_html=True)

    # ── where is money going, per horizon: live / short / medium / long ──
    sec("Waar vloeit het geld · live, korte en lange termijn naast elkaar")
    hz = {}
    if live is not None:
        hz["LIVE (vandaag)"] = pool_table(live)["Score"]
    for lab_, k_ in (("KORT (5 dagen)", "5D"), ("MIDDEL (20 dagen)", "20D"), ("LANG (60 dagen)", "60D"), ("ZEER LANG (120 dagen)", "120D")):
        hz[lab_] = pool_table(s3[k_])["Score"]
    hm = pd.DataFrame(hz)
    hm = hm.loc[hm["MIDDEL (20 dagen)"].sort_values().index]
    fig = go.Figure(go.Heatmap(z=hm.values, x=hm.columns, y=hm.index, colorscale=SCALE, zmin=-70, zmax=70, xgap=3, ygap=3,
                               text=hm.round(0).values, texttemplate="%{text:+.0f}", textfont=dict(size=13),
                               colorbar=dict(thickness=10, tickfont=dict(size=9)), hovertemplate="%{y} · %{x}: %{z:+.1f}<extra></extra>"))
    lay(fig, 30 * len(hm) + 70)
    fig.update_xaxes(side="top")
    show(fig)
    st.markdown("<div class='note'>Groen = netto instroom, rood = netto uitstroom. Een rij die van links naar rechts overal groen is, trekt op elke "
                "termijn geld aan; groen links maar rood rechts is een recente omslag." +
                ("" if live is not None else " De LIVE-kolom ontbreekt omdat er nu geen 15-minutenkoersen beschikbaar zijn.") + "</div>",
                unsafe_allow_html=True)

    SIGCOLS = ["Name", "Group", "Signaal", "Fase", "Totaal"] + (["Live"] if live is not None else []) + ["5D", "20D", "60D", "Return %", "Trend"]
    a, b = st.columns(2)
    with a:
        sec("Sterkste instroom · alle horizonten · klik een rij voor details")
        pick = table(sig.sort_values("Totaal", ascending=False).head(15), "sig_in", 560, SIGCOLS)
        if pick:
            goto(pick); st.rerun()
    with b:
        sec("Sterkste uitstroom · alle horizonten · klik een rij voor details")
        pick = table(sig.sort_values("Totaal").head(15), "sig_out", 560, SIGCOLS)
        if pick:
            goto(pick); st.rerun()

    sec("Hoe betrouwbaar is dit signaal? · toets op de afgelopen 2 jaar van dit universum")
    bt, verdict = backtest(S3["20D"][1], P["Close"], stamp)
    c1_, c2_ = st.columns([1.3, 1])
    with c1_:
        if len(bt):
            fig = go.Figure()
            for hz, c_ in (("5D", CYAN), ("20D", AMBER)):
                d_ = bt[bt["Horizon"] == hz]
                fig.add_trace(go.Bar(x=[f"Q{q}" for q in d_["Kwintiel"]], y=d_["ret"], name=f"rendement na {hz}", marker_color=c_,
                                     text=[f"{v:+.2f}%" for v in d_["ret"]], textposition="outside", cliponaxis=False,
                                     hovertemplate="%{x} · %{y:+.2f}%<extra>" + hz + "</extra>"))
            lay(fig, 330, barmode="group", title=dict(text="GEMIDDELD RENDEMENT NA HET SIGNAAL · Q1 = laagste 20D-scores · Q5 = hoogste",
                                                      font=dict(size=11, color=DIM)))
            fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.12, font=dict(size=10)))
            show(fig)
        else:
            st.info("Te weinig historie voor een toets.")
    with c2_:
        lines = []
        for h_, (sp, t_, n_, pos_) in verdict.items():
            if sp > 0 and t_ > 2:
                v_txt, v_col = "bruikbare voorsprong", GREEN
            elif sp > 0:
                v_txt, v_col = "zwak positief, statistisch niet overtuigend", AMBER
            else:
                v_txt, v_col = "geen voorspellende waarde in deze periode", RED
            lines.append(f"<b>{h_} dagen vooruit:</b> hoogste scores deden het gemiddeld <b style='color:{col(sp * 20)}'>{sp:+.2f}%</b> "
                         f"{'beter' if sp > 0 else 'slechter'} dan de laagste, in {pos_:.0f}% van {n_} meetmomenten "
                         f"(t = {t_:+.1f}). Oordeel: <b style='color:{v_col}'>{v_txt}</b>.")
        st.markdown(f"<div class='kpi' style='font-family:{MONO};font-size:12px;line-height:1.8'>" + "<br><br>".join(lines) +
                    f"<br><br><span style='color:{DIM}'>Methode: op niet-overlappende data het universum in vijf groepen naar 20D-score, "
                    "daarna het werkelijke rendement gemeten. Geen kosten, geen voorkennis van latere koersen. "
                    "Resultaten uit het verleden zeggen niets zeker over de toekomst.</span></div>", unsafe_allow_html=True)

    with st.expander("Hoe lees ik dit?"):
        st.markdown("""
- **Score** (−100 tot +100): hoe sterk er netto gekocht (+) of verkocht (−) wordt, afgeleid uit koers × volume. Geen echte geldstroomcijfers; die zijn niet gratis beschikbaar.
- **5D / 20D / 60D**: dezelfde score over de laatste 5, 20 en 60 handelsdagen. **Totaal** weegt ze 30/40/30.
- **Signaal**: `STERK ▲` = alle drie de horizonten positief én totaal boven +35. `POSITIEF ▲` = alle drie positief of totaal boven +25. De ▼-varianten zijn het spiegelbeeld.
- **Fase**: *versnelt* = de korte termijn is sterker dan de middellange (instroom neemt toe); *verzwakt* = het omgekeerde.
- **LIVE 1D** (rechtsboven): dezelfde berekening op 15-minutenkoersen van de laatste handelsdag, voor de andere schermen.
- Dit zijn signalen, geen advies op maat. Het blok *Hoe betrouwbaar* laat zien of ze in dit universum historisch iets voorspelden.
""")

elif view == "VOORSPELLING":
    sec("Zelflerend model · leert uit het verleden welke geldstroompatronen aan koersstijgingen voorafgingen")
    with st.spinner("Model trainen, zichzelf afstellen en toetsen op historische data… (eerste keer ±1 minuut, daarna 1 uur onthouden)"):
        ml = ml_forecast(P, stamp)
    if ml is None:
        st.info("Te weinig historie om een model te trainen en eerlijk te toetsen. In Live-modus wordt 5 jaar data gebruikt.")
    else:
        bst, hd, vl = ml["best"], ml["best"]["hold"], ml["best"]["val"]
        H = bst["h"]
        good = hd["ic_t"] > 2 and hd["spread"] > 0
        weak = hd["ic"] > 0 and hd["spread"] > 0
        v_txt, v_col = (("JA — AANTOONBAAR", GREEN) if good else ("ZWAK", AMBER) if weak else ("NEE", RED))
        k_ = st.columns(5)
        with k_[0]:
            kpi("Voorspellend? · eindtoets", v_txt, f"{hd['n']} ongeziene perioden van {H}D", v_col)
        with k_[1]:
            kpi("Rangcorrelatie (IC)", f"{hd['ic']:+.3f}", f"t = {hd['ic_t']:+.1f} · overtuigend vanaf 2", col(hd["ic"] * 1000))
        with k_[2]:
            kpi("Top 20% min bodem 20%", f"{hd['spread']:+.2f}%", f"per {H} dagen · t = {hd['spread_t']:+.1f}", col(hd["spread"] * 20))
        with k_[3]:
            kpi("Trefkans", f"{hd['hit']:.0f}%", "top versloeg bodem", col(hd["hit"] - 50))
        with k_[4]:
            kpi("Geleerd van", f"{ml['examples']:,}".replace(",", "."), f"voorbeelden sinds {ml['first']:%m/%Y}")
        st.markdown(f"<div class='note'>Model: {ml['model']} · {ml['n_feat']} kenmerken per instrument per dag · gekozen instelling: horizon {H} dagen, "
                    f"boomdiepte {bst['depth']} · afgesteld op {ml['test_from']:%b %Y} – {ml['split_date']:%b %Y} (validatie-IC {vl['ic']:+.3f}, t = {vl['ic_t']:+.1f}) · "
                    f"eindtoets vanaf {ml['split_date']:%b %Y} op data die bij het afstellen niet gebruikt is.</div>", unsafe_allow_html=True)
        g1_, g2_, g3_ = st.columns([1.2, 1, 1])
        with g1_:
            cv = ml["curve"]
            fig = go.Figure(go.Scatter(x=cv.index, y=cv.values, line=dict(color=CYAN, width=1.8), fill="tozeroy",
                                       fillcolor="rgba(34,211,238,0.06)", hovertemplate="%{x|%b %Y}: %{y:+.1f}%<extra></extra>"))
            fig.add_hline(y=0, line=dict(color=BORDER))
            fig.add_vline(x=ml["split_date"], line=dict(color=AMBER, width=1, dash="dot"))
            fig.add_annotation(x=ml["split_date"], y=1, yref="paper", text="eindtoets ►", showarrow=False, xanchor="left",
                               font=dict(color=AMBER, size=10))
            show(lay(fig, 320, title=dict(text="OPGETELD VERSCHIL TOP − BODEM (%, zonder kosten) · links afstellen, rechts eindtoets",
                                          font=dict(size=11, color=DIM))))
        with g2_:
            fig = go.Figure(go.Bar(x=[f"Q{i}" for i in range(1, 6)], y=hd["quint"], marker_color=[col(v * 20) for v in hd["quint"]],
                                   text=[f"{v:+.2f}%" for v in hd["quint"]], textposition="outside", cliponaxis=False))
            show(lay(fig, 320, title=dict(text=f"EINDTOETS: RENDEMENT NA {H}D PER MODELGROEP · Q5 = hoogste verwachting", font=dict(size=11, color=DIM))))
        with g3_:
            show(bar_scores(ml["relevance"].sort_values().pipe(lambda x: pd.concat([x.head(6), x.tail(6)])) * 1000, 320,
                            "WELKE KENMERKEN WOGEN MEE (samenhang ×1000)"))
        fc = compute(P, stamp, 20, wt, tuple(ss.extra))[0]
        fc = fc[fc.index.isin(ml["forecast"].index)][["Name", "Class", "Group", "Score", "Return %", "Trend"]].copy()
        fc["Model"] = ml["forecast"].reindex(fc.index)
        FCOLS = ["Name", "Group", "Model", "Score", "Return %", "Trend"]
        a, b = st.columns(2)
        with a:
            sec(f"Hoogste modelverwachting · komende {H} handelsdagen · klik een rij voor details")
            pick = table(fc.sort_values("Model", ascending=False).head(15), "ml_top", 560, FCOLS)
            if pick:
                goto(pick); st.rerun()
        with b:
            sec(f"Laagste modelverwachting · komende {H} handelsdagen · klik een rij voor details")
            pick = table(fc.sort_values("Model").head(15), "ml_bot", 560, FCOLS)
            if pick:
                goto(pick); st.rerun()
        sec("Zelf-afstelling · alle geteste instellingen")
        st.dataframe(ml["trials"].style.format({"Validatie IC": "{:+.3f}", "Validatie t": "{:+.1f}", "Eindtoets IC": "{:+.3f}",
                                                "Eindtoets t": "{:+.1f}", "Eindtoets top−bodem %": "{:+.2f}"})
                     .map(lambda v: f"color:{GREEN}" if v > 2 else f"color:{RED}" if v < 0 else f"color:{AMBER}", subset=["Validatie t", "Eindtoets t"]),
                     width="stretch", hide_index=True)
        st.markdown(f"<div class='kpi' style='font-family:{MONO};font-size:12px;line-height:1.8'><b>Zo lees je dit.</b> "
                    "<b>Model</b> is een verwachte rangorde, geen koersdoel: +100 betekent dat het model dit instrument bij de best presterende van het universum "
                    "verwacht, −100 bij de slechtste. <b>Score</b> is de gewone 20-daagse geldstroomscore ter vergelijking.<br>"
                    "<b>Zelf-afstelling.</b> Het model probeert elke instelling in de tabel uit en kiest de beste op de <i>validatieperiode</i>. "
                    "Het oordeel bovenaan komt uitsluitend uit de <i>eindtoets</i>: een latere periode die bij het kiezen niet is gebruikt. "
                    "Dat is bewust. Een model dat mag blijven sleutelen tot dezelfde testdata er goed uitziet, vindt altijd iets dat overtuigend lijkt, "
                    "ook in puur toeval, en faalt daarna met echt geld. Blijft het oordeel zwak, dan is dat de eerlijke uitkomst voor deze data.<br>"
                    "Het model traint en stelt zichzelf opnieuw af bij elke verversing van de data (maximaal eens per uur).</div>", unsafe_allow_html=True)

elif view == "HANDLEIDING":
    doc = Path(__file__).with_name("HANDLEIDING.md")
    if doc.exists():
        txt = "\n".join(l for l in doc.read_text(encoding="utf-8").splitlines() if not l.startswith("!["))
        st.markdown(txt)
    else:
        st.info("HANDLEIDING.md niet gevonden naast app.py.")

elif view == "COMMAND CENTER":
    a, b = st.columns([1.7, 1])
    with a:
        sec(f"Global money flow · {tf} · net rotation between pools")
        smode = st.radio("Ribbon magnitude", ["Flow Score", "% of $ Volume", "Net $ Flow"], horizontal=True, label_visibility="collapsed",
                         help="Flow Score = composite (comparable across pools). % of $ Volume = net $ flow / gross $ volume. "
                              "Net $ Flow = raw signed dollar proxy (dominated by the largest pools).")
        fig = sankey_fig(pt, smode)
        if fig is None:
            st.info("All pools point the same direction on this metric — no rotation to draw. See the pool bars →")
        else:
            show(fig)
        st.markdown("<div class='note'>Left (crimson ▼) = pools under distribution · right (green ▲) = pools under accumulation · "
                    "ribbon width = magnitude. Grey node = imbalance vs. outside the universe.</div>", unsafe_allow_html=True)
    with b:
        sec("Pool scores · click a bar to drill down")
        ev = show(bar_scores(pt["Score"], 430, highlight=ss.pool), key="poolbar", on_select="rerun", selection_mode="points")
        try:
            pts = ev.selection.points
            if pts:
                ss.pool = pts[0]["y"]
        except Exception:
            pass
        opts = list(pt.index)
        sel = st.selectbox("Drill into pool", opts, index=opts.index(ss.pool) if ss.pool in opts else 0, label_visibility="collapsed")
        if sel != ss.pool and not (ss.pool in opts and sel == opts[0] and ss.pool != opts[0] and False):
            ss.pool = sel

    pool = ss.pool if ss.pool in pt.index else pt.index[0]
    sec(f"Drill-down · {pool} · groups → securities")
    d1, d2, d3 = st.columns([1, 1.25, 1.75])
    members = uni[uni["Pool"] == pool]
    with d1:
        r = pt.loc[pool]
        kpi(f"{pool} score", f"{r['Score']:+.0f}", f"Δ {r['Δ Score']:+.0f} · {int(r['N'])} instruments", col(r["Score"]))
        kpi("Net $ flow proxy", fmt_usd(r["Net $ Flow"]), f"{r['Flow % of $Vol']:+.1f}% of gross $ volume" if np.isfinite(r["Flow % of $Vol"]) else "no volume data",
            col(r["Net $ Flow"] if np.isfinite(r["Net $ Flow"]) else 0))
        show(bar_scores(members.groupby("Group")["Score"].mean(), 190, "GROUPS"))
    with d2:
        show(bar_scores(members["Score"], max(300, 24 * len(members) + 60), "SECURITIES"))
    with d3:
        pick = table(members.sort_values("Score", ascending=False), "drill_tbl", h=max(300, 24 * len(members) + 60),
                     cols=["Name", "Group", "Score", "Δ Score", "CMF raw", "MFI raw", "RVOL", "Return %", "Net $ Flow", "Trend"])
        if pick:
            goto(pick); st.rerun()

    sec(f"Pool flow score history · {tf} lookback, last 120 sessions")
    ph = pd.DataFrame({p: score_hist[[t for t in uni.index[uni["Pool"] == p]]].mean(axis=1) for p in pt.index}).tail(120)
    if bpd > 1:
        ph.index = ph.index.strftime("%d %b %H:%M")
    fig = go.Figure(go.Heatmap(z=ph.T.values, x=ph.index, y=ph.columns, colorscale=SCALE, zmin=-80, zmax=80,
                               colorbar=dict(thickness=10, tickfont=dict(size=9)), hovertemplate="%{y} · %{x|%d %b}: %{z:+.0f}<extra></extra>"))
    lay(fig, 330)
    if bpd > 1:
        fig.update_xaxes(type="category", nticks=8)
    show(fig)

    l, r_ = st.columns(2)
    with l:
        sec("Strongest inflows · click a row to open")
        pick = table(uni.nlargest(12, "Score"), "top_in", 455, ["Name", "Group", "Score", "Δ Score", "CMF raw", "RVOL", "Return %", "Trend"])
        if pick:
            goto(pick); st.rerun()
    with r_:
        sec("Strongest outflows · click a row to open")
        pick = table(uni.nsmallest(12, "Score"), "top_out", 455, ["Name", "Group", "Score", "Δ Score", "CMF raw", "RVOL", "Return %", "Trend"])
        if pick:
            goto(pick); st.rerun()

elif view == "HEATMAP":
    sec(f"Multi-level heatmap · asset class → sector/region → security · colour = flow score ({tf})")
    h1, h2 = st.columns([1, 3])
    with h1:
        size_mode = st.radio("Tile size", ["Equal", "√ Dollar volume"], horizontal=True, label_visibility="collapsed")
    with h2:
        st.markdown("<div class='note'>Click a tile to zoom into that class or group; click the path bar on top to zoom out. "
                    "Hover for components.</div>", unsafe_allow_html=True)
    show(treemap_fig(uni, size_mode))

    sec("Group × timeframe matrix · where short and medium term agree")
    mat = {}
    for lab, n_ in DAILY_TF.items():
        s_, *_ = compute(P, stamp, n_, wt, tuple(ss.extra))
        s_ = s_[s_.index.isin(META.index)]
        mat[lab] = s_.groupby(["Class", "Group"])["Score"].mean()
    mat = pd.DataFrame(mat)
    mat = mat.loc[mat.mean(axis=1).sort_values().index]
    ylab = [f"{c} · {g}" for c, g in mat.index]
    fig = go.Figure(go.Heatmap(z=mat.values, x=mat.columns, y=ylab, colorscale=SCALE, zmin=-80, zmax=80,
                               text=mat.round(0).values, texttemplate="%{text:+.0f}", textfont=dict(size=10),
                               colorbar=dict(thickness=10, tickfont=dict(size=9)), hovertemplate="%{y} · %{x}: %{z:+.1f}<extra></extra>"))
    show(lay(fig, max(500, 19 * len(mat) + 60)))

elif view == "DEEP DIVE":
    t = ss.ticker
    if t not in snap.index:
        why = "Yahoo returned no usable history for it (check the symbol, e.g. BMW.DE, ^N225, EURUSD=X)."
        st.error(f"**{t}** could not be loaded — {why}")
        t = "SPY" if "SPY" in snap.index else snap.index[0]
    r = snap.loc[t]
    in_uni = t in META.index
    peers = snap[(snap["Group"] == r["Group"])] if in_uni else pd.concat([snap.loc[[t]], uni[uni["Group"] == "US Indices"]])
    cls_peers = uni[uni["Class"] == r["Class"]] if in_uni else uni
    rank = int((uni["Score"] < r["Score"]).mean() * 100)

    hd1, hd2 = st.columns([5, 1])
    with hd1:
        sec(f"{t} · {r['Name']} · {r['Class']} / {r['Group']} · {tf} lookback")
    with hd2:
        st.button("★ Unpin" if t in ss.pins else "☆ Pin to watch", on_click=toggle_pin, args=(t,), width="stretch")
    if not in_uni:
        st.markdown("<div class='note'>Off-universe ticker: peer comparison uses US index ETFs; add it to the universe list in app.py "
                    "to give it a proper peer group.</div>", unsafe_allow_html=True)

    m = st.columns(7)
    with m[0]:
        kpi("Flow score", f"{r['Score']:+.0f}", f"Δ {r['Δ Score']:+.0f} · pct-rank {rank}", col(r["Score"]))
    with m[1]:
        kpi(f"CMF({N})", f"{r['CMF raw']:+.3f}", "accumulation" if r["CMF raw"] > .05 else "distribution" if r["CMF raw"] < -.05 else "balanced", col(r["CMF raw"] * 100))
    with m[2]:
        kpi(f"MFI({max(N, 7)})", f"{r['MFI raw']:.0f}", "overbought >80" if r["MFI raw"] > 80 else "oversold <20" if r["MFI raw"] < 20 else "0–100 scale", col(r["MFI raw"] - 50))
    with m[3]:
        kpi("RS vs peers", f"{r['RS vs Peers']:+.0f}", f"group median basis", col(r["RS vs Peers"]))
    with m[4]:
        kpi("RS vs risk-on", f"{r['RS vs Risk-On']:+.0f}", "vs SPY/QQQ/IWM/EEM/HYG/CPER", col(r["RS vs Risk-On"]))
    with m[5]:
        kpi("Rel. volume", f"{r['RVOL']:.2f}x", f"{tf} avg vs baseline", GREEN if r["RVOL"] > 1.2 else TXT)
    with m[6]:
        kpi("Net $ flow", fmt_usd(r["Net $ Flow"]), f"ret {r['Return %']:+.2f}% · last {r['Last']:,.2f}",
            col(r["Net $ Flow"]) if np.isfinite(r["Net $ Flow"]) else DIM)

    intr = fetch_intraday(t, demo)
    daily = P["Close"][t].dropna()
    sp = st.columns(4)
    with sp[0]:
        if intr is not None:
            last_day = intr[intr.index.normalize() == intr.index.normalize()[-1]]
            show(spark(last_day if len(last_day) > 3 else intr.tail(26), "1D · 15m bars"))
        else:
            show(spark(daily.tail(2), "1D · daily close"))
    with sp[1]:
        show(spark(intr if intr is not None else daily.tail(6), "5D · 15m bars" if intr is not None else "5D"))
    with sp[2]:
        show(spark(daily.tail(21), "20D"))
    with sp[3]:
        show(spark(daily.tail(61), "60D"))

    g1, g2 = st.columns([2.2, 1])
    with g1:
        show(price_flow_fig(P, t, N if bpd == 1 else 5))
    with g2:
        show(volume_profile_fig(P, t))

    q1, q2, q3 = st.columns([1, 1.2, 1.2])
    with q1:
        sec("Score decomposition")
        tot = sum(wt)
        comp = pd.Series({f"{c} ({100 * w / tot:.0f}%)": r[c] for c, w in zip(COMP_COLS, wt)})
        show(bar_scores(comp, 300))
        st.markdown(f"<div class='note'>Contribution to score: " + " · ".join(f"{c} {r[c] * w / tot:+.1f}" for c, w in zip(COMP_COLS, wt)) + "</div>",
                    unsafe_allow_html=True)
    with q2:
        sec(f"Flow score history vs group · {r['Group']}")
        sh = score_hist[t].tail(180)
        fig = go.Figure()
        gp = [p for p in peers.index if p != t]
        if gp:
            fig.add_trace(go.Scatter(x=sh.index, y=score_hist[gp].mean(axis=1).tail(180), line=dict(color=DIM, width=1.2, dash="dot"), name="group"))
        fig.add_trace(go.Scatter(x=sh.index, y=sh, line=dict(color=CYAN, width=1.8), name=t))
        fig.add_hline(y=0, line=dict(color=BORDER))
        lay(fig, 300, title=dict(text=f"{t} (cyan) vs group mean (dotted)", font=dict(size=11, color=DIM)))
        fig.update_yaxes(range=[-100, 100])
        show(fig)
    with q3:
        sec("Group comparison · score")
        show(bar_scores(peers["Score"], 300, highlight=t))
    sec(f"Peers in {r['Class'] if in_uni else 'universe'} · click a row to open")
    pick = table(cls_peers.sort_values("Score", ascending=False), "peer_tbl", 320)
    if pick and pick != t:
        goto(pick); st.rerun()

elif view == "REGIME & LIQUIDITY":
    fred = {} if demo else fetch_fred()
    liq_mkt = float(np.mean([uni.loc[x, "Score"] * s for x, s in (("HYG", 1), ("LQD", 1), ("EMB", 1), ("UUP", -1), ("BIL", -1), ("VIXY", -1)) if x in uni.index]))
    a, b, c = st.columns([1, 1, 1.6])
    with a:
        sec(f"Risk-on / risk-off meter · {tf}")
        show(gauge(regime_score, "CROSS-ASSET REGIME"))
        n_on, n_off = (reg["Reads"] == "RISK-ON").sum(), (reg["Reads"] == "RISK-OFF").sum()
        st.markdown(f"<div class='note'>{n_on} of {len(reg)} signals risk-on · {n_off} risk-off · "
                    f"confirmation {'STRONG' if max(n_on, n_off) >= .7 * len(reg) else 'MIXED'}</div>", unsafe_allow_html=True)
    with b:
        sec("Liquidity proxy (market-implied)")
        show(gauge(liq_mkt, "LIQUIDITY / FUNDING APPETITE"))
        st.markdown("<div class='note'>Mean flow score of HYG, LQD, EMB minus UUP, BIL, VIXY: credit bid + weak dollar + "
                    "cash leaving bills + vol selling = easy liquidity.</div>", unsafe_allow_html=True)
    with c:
        sec("Regime history · mean of signal votes")
        if len(reg):
            rh = pd.concat([h for h in reg["_hist"]], axis=1, sort=True).mean(axis=1).tail(250)
            fig = go.Figure(go.Scatter(x=rh.index, y=rh, line=dict(color=CYAN, width=1.5), fill="tozeroy", fillcolor="rgba(34,211,238,0.08)"))
            fig.add_hline(y=0, line=dict(color=BORDER))
            lay(fig, 270)
            fig.update_yaxes(range=[-100, 100])
            show(fig)

    sec("Cross-asset confirmation")
    cc1, cc2 = st.columns([1.4, 1])
    with cc1:
        st.dataframe(styled(reg.drop(columns="_hist").set_index("Signal")), width="stretch", height=390, column_config={
            "Move %": st.column_config.NumberColumn(f"Move {tf}", format="%+.2f%%"), "Z": st.column_config.NumberColumn("Z", format="%+.2f"),
            "Vote": st.column_config.ProgressColumn("Vote", min_value=-100, max_value=100, format="%+.0f"),
            "Trend": st.column_config.LineChartColumn("60D ratio")})
    with cc2:
        show(bar_scores(reg.set_index("Signal")["Vote"], 390, "SIGNAL VOTES (+ = RISK-ON)"))

    sec("Central-bank liquidity · FRED (public CSV, no key)")
    if all(x in fred for x in ("WALCL", "WTREGEN", "RRPONTSYD")):
        w = fred["WALCL"] / 1000  # $M -> $B
        net = (w - fred["WTREGEN"].reindex(w.index, method="ffill") - fred["RRPONTSYD"].reindex(w.index, method="ffill")).dropna()
        f1, f2, f3, f4 = st.columns([1, 1, 1, 3])
        with f1:
            kpi("Net liquidity", f"${net.iloc[-1] / 1000:,.2f}T", f"as of {net.index[-1]:%d %b %Y}")
        with f2:
            d4 = net.iloc[-1] - net.iloc[-5]
            kpi("4-week change", f"{d4:+,.0f}B", "Fed assets − TGA − RRP", col(d4))
        with f3:
            if "BAMLH0A0HYM2" in fred:
                hy = fred["BAMLH0A0HYM2"]
                kpi("HY spread (OAS)", f"{hy.iloc[-1]:.2f}%", f"20D Δ {hy.iloc[-1] - hy.iloc[-21]:+.2f}pp", col(-(hy.iloc[-1] - hy.iloc[-21]) * 100))
        with f4:
            fig = go.Figure(go.Scatter(x=net.index, y=net / 1000, line=dict(color=GREEN, width=1.5)))
            show(lay(fig, 220, title=dict(text="NET LIQUIDITY ($T) = WALCL − WTREGEN − RRPONTSYD", font=dict(size=11, color=DIM))))
    else:
        st.info("FRED series unavailable " + ("in Demo mode." if demo else "right now (network/timeout).") + " The market-implied liquidity gauge above still works.")

    sec("Futures positioning · CFTC Commitments of Traders (non-commercial net)")
    cot = None if demo else fetch_cot()
    if cot is not None and len(cot):
        st.dataframe(styled(cot.set_index("Contract")), width="stretch", height=38 * len(cot) + 40, column_config={
            "Net Spec (contracts)": st.column_config.NumberColumn(format="%d"), "Net % OI": st.column_config.NumberColumn(format="%+.1f%%"),
            "1W Δ % OI": st.column_config.NumberColumn(format="%+.1f"),
            "52W Percentile": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
            "History": st.column_config.LineChartColumn("52W net % OI")})
    else:
        st.info("CFTC COT feed unavailable " + ("in Demo mode." if demo else "right now.") + " Futures price/volume flows are still in the heatmap under “Futures & Vol”.")

elif view == "LEADERBOARDS":
    lv = st.radio("Level", ["Individual names", "Sector / Region groups", "Asset classes", "Sankey pools"], horizontal=True, label_visibility="collapsed")
    if lv == "Individual names":
        f1, f2, f3 = st.columns([2, 2, 1])
        with f1:
            fc = st.multiselect("Asset class", sorted(uni["Class"].unique()), placeholder="All asset classes", label_visibility="collapsed")
        d = snap if not fc else snap[snap["Class"].isin(fc)]
        with f2:
            fg = st.multiselect("Group", sorted(d["Group"].unique()), placeholder="All sectors / regions", label_visibility="collapsed")
        with f3:
            side = st.radio("Side", ["All", "Inflows", "Outflows"], horizontal=True, label_visibility="collapsed")
        d = d if not fg else d[d["Group"].isin(fg)]
        d = d[d["Score"] > 0] if side == "Inflows" else d[d["Score"] < 0] if side == "Outflows" else d
        sec(f"{len(d)} instruments · click any column header to sort · click a row to open the deep dive")
        pick = table(d.sort_values("Score", ascending=(side == "Outflows")), "lb_names", 640)
        if pick:
            goto(pick); st.rerun()
        st.download_button("⬇ Export CSV", d.drop(columns=["Trend"]).to_csv().encode(), f"money_flow_{tf}_{asof}.csv", "text/csv")
    else:
        if lv == "Sankey pools":
            agg = pt.copy()
        else:
            keys = ["Class", "Group"] if lv.startswith("Sector") else ["Class"]
            g = uni.groupby(keys)
            agg = pd.DataFrame({"Score": g["Score"].mean(), "Δ Score": g["Δ Score"].mean(), "CMF raw": g["CMF raw"].mean(),
                                "MFI raw": g["MFI raw"].mean(), "RVOL": g["RVOL"].mean(), "Return %": g["Return %"].mean(),
                                "Net $ Flow": g["Net $ Flow"].sum(), "Gross $": g["Gross $"].sum(), "N": g.size()})
            agg["Flow % of $Vol"] = 100 * agg["Net $ Flow"] / agg["Gross $"].where(agg["Gross $"] > 0)
            if len(keys) == 2:
                agg.index = [f"{c} · {g_}" for c, g_ in agg.index]
        agg = agg.sort_values("Score", ascending=False)
        x1, x2 = st.columns([1.6, 1])
        with x1:
            sec("Click any column header to sort")
            st.dataframe(styled(agg), column_config=COLCFG, width="stretch", height=max(300, 36 * len(agg) + 42))
        with x2:
            show(bar_scores(agg["Score"], max(300, 22 * len(agg) + 60), "FLOW SCORE"))

elif view == "METHODOLOGY":
    tot = sum(wt)
    st.markdown(f"""
### What is measured
True flow data (ETF creations/redemptions, custody flows, prime-broker books) is proprietary. This terminal uses **transparent
price × volume proxies** computed identically for every instrument, over the selected lookback **N = {N} sessions**.

| # | Component | Formula | Mapped to [-100, +100] | Weight now |
|---|---|---|---|---|
| 1 | **CMF** | Σ(MFM × V) / Σ(V), MFM = ((C−L) − (H−C)) / (H−L) | clip(CMF × 2.5) | {100 * wt[0] / tot:.0f}% |
| 2 | **MFI** | 100 × Σ(+TP×V) / Σ(|TP×V|) over max(N, 7), TP = (H+L+C)/3 | (MFI − 50) / 50 | {100 * wt[1] / tot:.0f}% |
| 3 | **RS vs Peers** | N-day return − median return of the group | tanh(excess / σ_N) | {100 * wt[2] / tot:.0f}% |
| 4 | **RS vs Risk-On** | N-day return − equal-weight basket {", ".join(RISK_ON_BASKET)} | tanh(excess / √(σ² + σ_b²)) | {100 * wt[3] / tot:.0f}% |
| 5 | **Flow Momentum** | CMF_N(t) − CMF_N(t − N/2) | tanh(5 × Δ) | {100 * wt[4] / tot:.0f}% |
| 6 | **Volume Intensity** | tanh(return / σ_N) × RVOL / 1.5, RVOL = mean V(N) / prior baseline | clip | {100 * wt[5] / tot:.0f}% |

**Composite Money Flow Score** = Σ weightᵢ × componentᵢ. Weights are the sliders in the sidebar.
σ_N = 60-day daily return volatility × √N.

**Net $ Flow proxy** = Σ over N of (MFM × typical price × volume). Signed dollar volume, not subscriptions.
**Aggregation**: group / class / pool score = equal-weight mean of member scores; $ flows are summed.
**Sankey**: pools with negative value are sources, positive are sinks; each source's outflow is split pro-rata to sink size.
It visualises *relative rotation pressure*, not observed pairwise transfers. Futures and spot FX are excluded from pools (no
comparable dollar volume / would double count) but are scored in the heatmap, leaderboards and deep dive.
**Regime**: each cross-asset ratio's N-day move is z-scored by its own volatility and mapped by tanh to a −100…+100 vote; the meter is the mean.

### Known limitations
* Close-location flow can't see dark pools, block trades or primary-market ETF flows.
* Spot FX and index symbols have no volume on Yahoo → their CMF/MFI are price-only (constant volume).
* Yahoo data is delayed and occasionally revised; the latest bar may be a partial session.
* Scores are descriptive, not predictive. Nothing here is investment advice.

### Data sources
* **Yahoo Finance** (`yfinance`): 2 years of daily OHLCV, cached 15 min; 15-minute bars for 1D/5D sparklines.
* **FRED** public CSV: {", ".join(FRED_SERIES)} — net liquidity = WALCL − WTREGEN − RRPONTSYD.
* **CFTC** Socrata API (legacy futures-only COT): non-commercial net positioning.

### Upgrading the data (all free)
1. **True ETF flows**: scrape daily shares outstanding from issuer sites (iShares/SPDR/Invesco CSVs); Δshares × NAV replaces `_dollar` in `flow_panels`.
2. **FRED API key** (free): more series (SOFR, bank reserves, global M2) in `FRED_SERIES`.
3. **CFTC TFF / disaggregated reports**: asset-manager vs leveraged-fund positioning — change the dataset id in `fetch_cot`.
4. **Treasury fiscal data API**: daily TGA instead of weekly.
5. **Other OHLCV vendors** (Stooq, Tiingo, Polygon free tiers): replace `fetch_live`; it only has to return five date×ticker frames.

### Universe ({len(META)} instruments) — to expand, append `(ticker, name, asset_class, group)` rows to `U` at the top of `app.py`
""")
    st.dataframe(META.rename(columns={"name": "Name", "cls": "Asset class", "group": "Group", "pool": "Sankey pool"}), width="stretch", height=420)

# ── footer: data health ─────────────────────────────────────────────────────
bad = sorted(set(failed) | set(dropped))
if bad:
    with st.expander(f"⚠ {len(bad)} ticker(s) unavailable from the data source"):
        st.write(", ".join(bad))
st.markdown("<div class='note' style='margin-top:10px'>Flows are price × volume proxies, not reported fund flows. Data: Yahoo Finance, FRED, CFTC. "
            "Not investment advice.</div>", unsafe_allow_html=True)

# ── optional auto-refresh: a timer fragment that reruns the whole app ─────────
ss["_last_run"] = time.time()
if ss.get("auto"):
    @st.fragment(run_every=300)
    def _tick():
        if time.time() - ss.get("_last_run", 0) > 290:
            st.rerun()
    _tick()
