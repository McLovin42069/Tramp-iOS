"""
QTRON
=====
Cross-asset money-flow terminal, pattern tracker and data archive, built only on free/public data.

Run:  streamlit run app.py        Nightly data collection:  python collector.py
Modules: universe.py (instruments), store.py (database + archive), feeds.py (data), patterns.py (fixed rules), collector.py.
"""
from __future__ import annotations

import io
import json
import os
import sqlite3
import time
from contextlib import closing
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
import store, patterns, collector, alarm, risk, feeds
from universe import U, STOCKS, META, STOCK_CLASSES

CACHE_DIR = Path(__file__).parent / "cache"

# ── Memory: a local SQLite database (cache/geheugen.db). It keeps what cannot be recomputed later:
#    the signals, model forecasts, analyst picks and sell signals as they stood on each day, plus settings.
MEM_FILE = CACHE_DIR / "geheugen.db"
MEM_SCHEMA = store.SCHEMA


def mem():
    CACHE_DIR.mkdir(exist_ok=True)
    con = sqlite3.connect(MEM_FILE, timeout=10)
    con.executescript(MEM_SCHEMA)
    return con


def mem_write(sql: str, rows: list):
    """Best-effort write: the memory must never be able to break the app."""
    try:
        with closing(mem()) as con, con:
            con.executemany(sql, rows)
    except Exception:
        pass


def mem_read(sql: str, params: tuple = ()) -> pd.DataFrame:
    try:
        with closing(mem()) as con:
            return pd.read_sql_query(sql, con, params=params)
    except Exception:
        return pd.DataFrame()


def mem_settings() -> dict:
    d = mem_read("SELECT key, value FROM settings")
    try:
        return {k: json.loads(v) for k, v in zip(d["key"], d["value"])} if len(d) else {}
    except Exception:
        return {}

# Sankey pools: (asset_class, group) -> pool. Classes not listed map to themselves.
POOL_OF = {
    ("Commodities", "Precious Metals"): "Precious Metals", ("Commodities", "Energy"): "Energy Cmdty",
    ("Commodities", "Industrial Metals"): "Industrial & Ags", ("Commodities", "Agriculture"): "Industrial & Ags",
    ("Commodities", "Broad Commodities"): "Industrial & Ags",
    ("FX", "US Dollar"): "US Dollar", ("FX", "G10 FX"): "Non-USD FX", ("FX", "Spot Pairs"): None,
    ("Credit", "Investment Grade"): "IG Credit", ("Credit", "Munis & MBS"): "IG Credit", ("Credit", "High Yield"): "HY Credit",
}
EXCLUDE_FROM_POOLS = {"Futures & Vol", "Indices", "US Stocks", "Europe Stocks", "Asia Stocks"}  # avoids double counting with the ETF pools
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

st.set_page_config(page_title="Qtron", page_icon="◈", layout="wide", initial_sidebar_state="auto")
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
    good = out["Close"].columns[out["Close"].notna().sum() >= 80]     # 80 days: recent listings are included once the 60-day score exists
    return {k: v[good] for k, v in out.items()}


def _download(tickers: tuple, period: str = "2y", interval: str = "1d"):
    """EXTENSION POINT: swap this for any other OHLCV vendor. Must return
    ({'Open','High','Low','Close','Volume'} -> DataFrame[date x ticker], failed_tickers)."""
    import yfinance as yf
    frames, failed = {}, []
    tick = list(tickers)
    if os.environ.get("MFCC_OFFLINE") == "1":      # test switch: behave as if Yahoo is unreachable
        return None, tick
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
def fetch_live(tickers: tuple, period: str = "10y"):         # 10 years so the model has history to learn from
    return _download(tickers, period, "1d")


@st.cache_data(ttl=900, show_spinner=False)
def load_core(tickers: tuple, period: str = "10y"):
    """Core universe with a safety net. A good download is saved to disk. If Yahoo is unreachable or returns
    less than 80% of the instruments, the last good copy from disk is used instead (real but older prices),
    so the app never silently swaps real markets for synthetic data.
    Returns (panels or None, failed tickers, unix time of the data, stale flag)."""
    f = CACHE_DIR / "core.pkl"
    try:
        P_, failed = _download(tickers, period, "1d")
    except Exception:
        P_, failed = None, list(tickers)
    if P_ is not None and P_["Close"].shape[1] >= 0.8 * len(tickers):
        try:
            CACHE_DIR.mkdir(exist_ok=True)
            pd.to_pickle({"panels": {k: v.astype("float32") for k, v in P_.items()}, "failed": failed}, f)
        except Exception:
            pass
        return P_, failed, time.time(), False
    try:
        saved = pd.read_pickle(f)
        return {k: v.astype(float) for k, v in saved["panels"].items()}, saved["failed"], f.stat().st_mtime, True
    except Exception:
        return None, list(tickers), time.time(), False


@st.cache_resource(ttl=6 * 3600, max_entries=1, show_spinner=False)     # shared, not copied: the panel is 150 MB
def load_stocks(tickers: tuple, period: str = "10y", max_age_h: float = 6.0):
    """Daily history for the extended stock universe. Stored on disk so it is downloaded at most once per
    6 hours, even across restarts. The app does NOT need to keep running to 'collect' data: Yahoo serves
    the full history on demand."""
    f = CACHE_DIR / "stocks.pkl"
    try:
        if f.exists() and time.time() - f.stat().st_mtime < max_age_h * 3600:
            saved = pd.read_pickle(f)
            if saved.get("tickers") == tickers:
                return saved["panels"], saved["failed"], f.stat().st_mtime
    except Exception:
        pass
    P_, failed = _download(tickers, period, "1d")
    if P_ is None or P_["Close"].shape[1] < 0.8 * len(tickers):
        try:                                  # offline or throttled: keep the last good copy, however old
            saved = pd.read_pickle(f)
            return saved["panels"], saved["failed"], f.stat().st_mtime
        except Exception:
            if P_ is None:
                return None, list(tickers), None
    P_ = {k: v.astype("float32") for k, v in P_.items()}
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        pd.to_pickle({"tickers": tickers, "panels": P_, "failed": failed}, f)
    except Exception:
        pass
    return P_, failed, time.time()


# ── Real money-flow data (beyond price x volume) ─────────────────────────────
# SPDR funds publish daily shares outstanding since inception: creations/redemptions are literal fund flows.
SPDR_FUNDS = {
    "XLK": ("Technology", "Sector"), "XLC": ("Communication", "Sector"), "XLY": ("Cons. Discretionary", "Sector"),
    "XLP": ("Cons. Staples", "Sector"), "XLF": ("Financials", "Sector"), "XLV": ("Health Care", "Sector"), "XLE": ("Energy", "Sector"),
    "XLI": ("Industrials", "Sector"), "XLB": ("Materials", "Sector"), "XLU": ("Utilities", "Sector"), "XLRE": ("Real Estate", "Sector"),
    "XBI": ("Biotech", "Industry"), "XOP": ("Oil & Gas E&P", "Industry"), "XME": ("Metals & Mining", "Industry"), "XHB": ("Homebuilders", "Industry"),
    "XRT": ("Retail", "Industry"), "KRE": ("Regional Banks", "Industry"), "KBE": ("Banks", "Industry"), "XSD": ("Semiconductors", "Industry"),
    "XAR": ("Aerospace & Defense", "Industry"), "KIE": ("Insurance", "Industry"), "XES": ("Oil Services", "Industry"), "XPH": ("Pharma", "Industry"),
    "XSW": ("Software", "Industry"), "XTN": ("Transportation", "Industry"),
    "SPY": ("S&P 500", "Broad & Style"), "DIA": ("Dow 30", "Broad & Style"), "MDY": ("MidCap 400", "Broad & Style"), "SPYG": ("S&P Growth", "Broad & Style"),
    "SPYV": ("S&P Value", "Broad & Style"), "SPMD": ("Mid Cap", "Broad & Style"), "SPSM": ("Small Cap", "Broad & Style"),
    "SPYD": ("High Dividend", "Broad & Style"), "SDY": ("Dividend", "Broad & Style"), "RWR": ("US REITs", "Broad & Style"),
    "SPDW": ("Developed ex-US", "Region"), "SPEM": ("Emerging Markets", "Region"), "FEZ": ("Euro Stoxx 50", "Region"), "GXC": ("China", "Region"),
    "SPEU": ("Europe", "Region"), "GNR": ("Natural Resources", "Region"),
    "BIL": ("T-Bills", "Bonds"), "SPTS": ("Short Treasury", "Bonds"), "SPTI": ("Interm. Treasury", "Bonds"), "SPTL": ("Long Treasury", "Bonds"),
    "SPIP": ("TIPS", "Bonds"), "SPAB": ("Aggregate", "Bonds"), "SPIB": ("Interm. Corporate", "Bonds"), "SPSB": ("Short Corporate", "Bonds"),
    "SPLB": ("Long Corporate", "Bonds"), "JNK": ("High Yield", "Bonds"), "SJNK": ("Short High Yield", "Bonds"), "BWX": ("Intl Treasury", "Bonds"),
    "CWB": ("Convertibles", "Bonds"), "SPMB": ("Mortgage-Backed", "Bonds"),
}
SECTOR_ETF = {"Technology": "XLK", "Communication": "XLC", "Cons. Discretionary": "XLY", "Cons. Staples": "XLP", "Financials": "XLF",
              "Health Care": "XLV", "Energy": "XLE", "Energy Equities": "XLE", "Industrials": "XLI", "Materials": "XLB", "Utilities": "XLU",
              "Real Estate": "XLRE"}
_BROWSER_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}


def _disk(name: str, max_age_h: float):
    """Return a pickled object from the cache folder if it is younger than max_age_h, else None."""
    f = CACHE_DIR / name
    try:
        if f.exists() and time.time() - f.stat().st_mtime < max_age_h * 3600:
            return pd.read_pickle(f)
    except Exception:
        pass
    return None


def _disk_save(name: str, obj):
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        pd.to_pickle(obj, CACHE_DIR / name)
    except Exception:
        pass


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def load_spdr(max_age_h: float = 20.0):
    """Daily NAV, shares outstanding and net assets of every SPDR fund (State Street 'navhist' files), plus
    total-return prices from Yahoo. Returns dict(so, nav, tna, close) of [date x fund] frames, or None."""
    got = _disk("spdr.pkl", max_age_h)
    if got is not None:
        return got
    if os.environ.get("MFCC_OFFLINE") == "1":
        return _disk("spdr.pkl", 1e9)
    so, nav, tna = {}, {}, {}
    for t in SPDR_FUNDS:
        try:
            r = requests.get(f"https://www.ssga.com/library-content/products/fund-data/etfs/us/navhist-us-en-{t.lower()}.xlsx",
                             timeout=30, headers=_BROWSER_UA)
            r.raise_for_status()
            x = pd.read_excel(io.BytesIO(r.content), header=None, engine="openpyxl")
            h0 = x.index[x[0].astype(str).str.strip() == "Date"][0]
            d = x.iloc[h0 + 1:, :4].copy()
            d.columns = ["date", "nav", "so", "tna"]
            d["date"] = pd.to_datetime(d["date"], format="%d-%b-%Y", errors="coerce")
            d = d.dropna(subset=["date"]).set_index("date").apply(pd.to_numeric, errors="coerce").sort_index()
            if len(d) > 300:
                so[t], nav[t], tna[t] = d["so"], d["nav"], d["tna"]
        except Exception:
            continue
    if len(so) < 10:
        return _disk("spdr.pkl", 1e9)                 # keep an old copy rather than nothing
    out = {"so": pd.DataFrame(so), "nav": pd.DataFrame(nav), "tna": pd.DataFrame(tna)}
    try:
        px, _ = _download(tuple(so), "10y", "1d")
        out["close"] = px["Close"] if px is not None else out["nav"]
    except Exception:
        out["close"] = out["nav"]
    _disk_save("spdr.pkl", out)
    return out


def spdr_flow_pct(sp: dict, n: int) -> pd.DataFrame:
    """Net creations minus redemptions over n days as % of the fund's assets at the start of the window.
    Shifted one day: shares outstanding for day t are only public the next morning."""
    flow = sp["so"].diff() * sp["nav"]
    return (100 * flow.rolling(n, min_periods=max(2, n // 2)).sum() / sp["tna"].shift(n)).shift(1)


def _si_candidates(start: str = "2018-01-01"):
    """FINRA short-interest settlement dates: mid-month and month-end, moved back when not a business day."""
    out = []
    for m in pd.period_range(start, pd.Timestamp.today(), freq="M"):
        mid = [pd.Timestamp(m.year, m.month, d) for d in (15, 14, 13, 12)]
        end = list(pd.bdate_range(m.start_time, m.end_time)[::-1][:4])
        out.append((f"{m}-A", [d for d in mid if d.dayofweek < 5]))
        out.append((f"{m}-B", end))
    return out


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def load_short_interest(symbols: tuple):
    """Twice-monthly short interest per US-listed stock and ETF (FINRA, free). Downloaded once and kept on
    disk; later runs only fetch new reports. Returns a long frame (date, symbol, si, adv, dtc) or None."""
    saved = _disk("short.pkl", 1e9) or {"rows": [], "done": {}}
    if os.environ.get("MFCC_OFFLINE") == "1":
        return pd.DataFrame(saved["rows"], columns=["date", "symbol", "si", "adv", "dtc"]) if saved["rows"] else None
    want = {t.replace("-", ""): t for t in symbols}
    today, changed = pd.Timestamp.today().normalize(), 0
    for key, cands in _si_candidates():
        if key in saved["done"]:
            continue
        cands = [d for d in cands if d <= today]
        if not cands:
            continue
        hit = None
        for d in cands:
            try:
                r = requests.get(f"https://cdn.finra.org/equity/otcmarket/biweekly/shrt{d:%Y%m%d}.csv", timeout=40, headers=_BROWSER_UA)
            except Exception:
                break                                  # network trouble: try again next time
            if r.status_code == 200 and len(r.content) > 10_000:
                hit = (d, r.content)
                break
        if hit is None:
            if cands[0] < today - pd.Timedelta(days=45):
                saved["done"][key] = None              # old and missing: stop asking
            continue
        d, content = hit
        try:
            x = pd.read_csv(io.BytesIO(content), sep="|", dtype=str, usecols=["symbolCode", "currentShortPositionQuantity",
                                                                             "averageDailyVolumeQuantity", "daysToCoverQuantity"])
            x = x[x["symbolCode"].isin(want)]
            for sym, si, adv, dtc in x.itertuples(index=False):
                saved["rows"].append((d, want[sym], float(si or 0), float(adv or 0), float(dtc or 0)))
            saved["done"][key] = str(d.date())
            changed += 1
            if changed % 25 == 0:
                _disk_save("short.pkl", saved)         # resumable
        except Exception:
            continue
    if changed:
        _disk_save("short.pkl", saved)
    return pd.DataFrame(saved["rows"], columns=["date", "symbol", "si", "adv", "dtc"]) if saved["rows"] else None


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def load_shares(tickers: tuple, max_age_h: float = 7 * 24):
    """Cumulative net share issuance per company (log shares outstanding, Yahoo). Buybacks lower it, new
    issuance raises it. Jumps above 40% between two reports are treated as stock splits and removed."""
    got = _disk("shares.pkl", max_age_h)
    if got is not None and len(got) >= 0.5 * len(tickers):
        return got
    if os.environ.get("MFCC_OFFLINE") == "1":
        return _disk("shares.pkl", 1e9)
    import yfinance as yf
    out, miss = {}, 0
    for t in tickers:
        try:
            s_ = yf.Ticker(t).get_shares_full(start="2014-01-01")
            if s_ is None or len(s_) < 8:
                continue
            s_ = s_[~s_.index.duplicated(keep="last")].astype(float)
            s_.index = pd.to_datetime(s_.index).tz_localize(None).normalize()
            d = np.log(s_.where(s_ > 0)).diff()
            d[d.abs() > np.log(1.4)] = 0.0
            out[t] = d.cumsum().groupby(level=0).last()
            miss = 0
        except Exception:
            miss += 1
            if miss > 25:                               # throttled: stop hammering, keep what we have
                break
    if len(out) < 0.3 * len(tickers):
        return _disk("shares.pkl", 1e9)
    _disk_save("shares.pkl", out)
    return out


def source_features(P: dict, cols: list):
    """Turn the real-flow sources into [date x ticker] model inputs and market-wide inputs.
    Every series is lagged by its publication delay. Missing sources simply leave gaps."""
    idx, feats, macro, status = P["Close"].index, {}, {}, {}
    us = [c for c in cols if "." not in c and "=" not in c and "^" not in c and not c.endswith("-USD")]
    # 1. short interest (FINRA) -------------------------------------------------
    try:
        si = load_short_interest(tuple(us))
        if si is not None and len(si):
            lagged = si.assign(date=si["date"] + pd.offsets.BDay(12))          # published ~8-10 business days after settlement
            dtc = lagged.pivot_table(index="date", columns="symbol", values="dtc", aggfunc="last").sort_index()
            sq = lagged.pivot_table(index="date", columns="symbol", values="si", aggfunc="last").sort_index()
            feats["Short · dagen tot dekking"] = np.log1p(dtc.clip(lower=0, upper=200)).reindex(idx, method="ffill", limit=30).reindex(columns=cols)
            feats["Short · verandering positie"] = (sq / sq.shift(1) - 1).clip(-1, 3).reindex(idx, method="ffill", limit=30).reindex(columns=cols)
            status["Short-posities (FINRA)"] = f"{si['date'].nunique()} rapporten t/m {si['date'].max():%d-%m-%Y} · {si['symbol'].nunique()} instrumenten"
    except Exception:
        pass
    # 2. net share issuance (Yahoo) ---------------------------------------------
    try:
        stocks_ = [c for c in cols if c in META.index and not META.loc[c, "core"]]
        sh = load_shares(tuple(stocks_))
        if sh:
            cum = pd.DataFrame(sh)
            cum = cum.set_axis(cum.index + pd.Timedelta(days=5)).reindex(idx.union(cum.index + pd.Timedelta(days=5))).ffill().reindex(idx)
            feats["Netto-uitgifte aandelen · 250D"] = (cum - cum.shift(250)).reindex(columns=cols)
            status["Inkoop/uitgifte aandelen (Yahoo)"] = f"{len(sh)} bedrijven"
    except Exception:
        pass
    # 3. SPDR fund flows ----------------------------------------------------------
    try:
        sp = load_spdr()
        if sp is not None:
            grp = META["group"].reindex(cols)
            for n in (20, 60):
                fl = spdr_flow_pct(sp, n).reindex(idx, method="ffill", limit=5)
                pan = pd.DataFrame(np.nan, index=idx, columns=cols)
                for c in cols:
                    etf = c if c in fl.columns else SECTOR_ETF.get(grp.get(c)) if c in us and not META.loc[c, "core"] else None
                    if etf in fl.columns:
                        pan[c] = fl[etf]
                feats[f"Echte fondsstroom sector/ETF · {n}D"] = pan
            f20 = spdr_flow_pct(sp, 20).reindex(idx, method="ffill", limit=5)
            for t, lab in (("SPY", "S&P 500"), ("BIL", "kasgeld"), ("JNK", "high yield"), ("SPTL", "lange obligaties")):
                if t in f20.columns:
                    macro[f"Macro · fondsstroom {lab} 20D"] = f20[t]
            status["Fondsstromen (SPDR)"] = f"{sp['so'].shape[1]} fondsen t/m {sp['so'].index[-1]:%d-%m-%Y}"
    except Exception:
        pass
    return feats, pd.DataFrame(macro, index=idx), status


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
            r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd=2014-01-01", timeout=6,
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


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def fetch_cot_history():
    """Weekly non-commercial net positioning (% of open interest) back to 2014 for four macro contracts."""
    want = {"13874A": "S&P 500", "043602": "10Y Treasury", "088691": "Goud", "098662": "Dollar"}
    try:
        r = requests.get("https://publicreporting.cftc.gov/resource/6dca-aqww.json", timeout=15, params={
            "$select": "cftc_contract_market_code,report_date_as_yyyy_mm_dd,open_interest_all,noncomm_positions_long_all,noncomm_positions_short_all",
            "$where": "cftc_contract_market_code in (" + ",".join(f"'{c}'" for c in want) + ") AND report_date_as_yyyy_mm_dd > '2014-01-01'",
            "$limit": 6000})
        r.raise_for_status()
        d = pd.DataFrame(r.json())
        d["date"] = pd.to_datetime(d["report_date_as_yyyy_mm_dd"])
        for c in d.columns[2:5]:
            d[c] = pd.to_numeric(d[c], errors="coerce")
        d["v"] = 100 * (d["noncomm_positions_long_all"] - d["noncomm_positions_short_all"]) / d["open_interest_all"]
        out = d.pivot_table(index="date", columns="cftc_contract_market_code", values="v").rename(columns=want).sort_index()
        return out if len(out) > 100 else None
    except Exception:
        return None


def macro_features(P: dict, fred: dict, cot) -> pd.DataFrame:
    """Market-wide inputs for the model, one row per date. Every external series is shifted by its
    publication delay so the model never sees a number before it was public."""
    C, idx, out = P["Close"], P["Close"].index, {}
    for lab, a, b in (("Aandelen/Obligaties", "SPY", "TLT"), ("High yield/Treasuries", "HYG", "IEF"), ("Koper/Goud", "CPER", "GLD"),
                      ("Dollar", "UUP", None)):
        if a in C and (b is None or b in C):
            s_ = C[a] / C[b] if b else C[a]
            out[f"Macro · {lab} 20D"] = np.tanh((s_ / s_.shift(20) - 1) / (s_.pct_change(fill_method=None).rolling(60).std() * np.sqrt(20)))
    if "^VIX" in C:
        out["Macro · VIX-percentiel"] = C["^VIX"].rolling(250, min_periods=60).rank(pct=True) - 0.5
    lag = lambda s_, days: s_.set_axis(s_.index + pd.Timedelta(days=days)).reindex(idx, method="ffill")
    if "BAMLH0A0HYM2" in fred:
        out["Macro · HY-spread Δ20D"] = lag(fred["BAMLH0A0HYM2"].diff(20), 2)
    if "T10Y2Y" in fred:
        out["Macro · Rentecurve 10Y-2Y"] = lag(fred["T10Y2Y"], 2)
    if all(x in fred for x in ("WALCL", "WTREGEN", "RRPONTSYD")):
        w_ = fred["WALCL"] / 1000
        net = (w_ - fred["WTREGEN"].reindex(w_.index, method="ffill") - fred["RRPONTSYD"].reindex(w_.index, method="ffill")).dropna()
        out["Macro · Netto liquiditeit Δ4w"] = lag(net.pct_change(4) * 100, 3)
    if cot is not None:
        for c in cot.columns:
            out[f"Macro · COT {c}"] = lag(cot[c].rolling(156, min_periods=52).rank(pct=True) - 0.5, 5)
    return pd.DataFrame(out, index=idx)


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

    # Yahoo reports crypto volume in USD already, so it must not be multiplied by the price again.
    px_mult = tp.where(np.broadcast_to(~np.array([str(c).endswith("-USD") for c in tp.columns]), tp.shape), 1.0)
    dollar = (mfm * px_mult * V).rolling(n).sum().where(has_vol)            # signed $ proxy  (EXTENSION POINT)
    gross = (px_mult * V).rolling(n).sum().where(has_vol)

    return {"CMF": (cmf * 2.5).clip(-1, 1), "MFI": ((mfi - 50) / 50).clip(-1, 1), "RS vs Peers": rs_peer,
            "RS vs Risk-On": rs_risk, "Flow Momentum": flow_mom, "Volume Intensity": vol_int,
            "_cmf": cmf, "_mfi": mfi, "_ret": ret, "_rvol": rvol, "_dollar": dollar, "_gross": gross, "_k": k}


def composite(fp: dict, w: dict) -> pd.DataFrame:
    tot = sum(w.values()) or 1
    return 100 * sum(fp[c].fillna(0) * (w[c] / tot) for c in COMP_COLS)


@st.cache_data(ttl=900, show_spinner=False)
def compute(_P: dict, stamp: str, n: int, wt: tuple, extra: tuple, bpd: int = 1, full: bool = False):
    """stamp/extra are cache keys only (data identity + off-universe tickers)."""
    if bpd == 1 and not full and len(_P["Close"]) > 760:          # three years is ample for every lookback and for the 2-year checks; keeps memory flat
        _P = {k_: v_.tail(760) for k_, v_ in _P.items()}
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
        fwd = C.shift(-h - 1) / C.shift(-1) - 1      # enter at the next close, hold h days
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


def residual_returns(fwd: pd.DataFrame, groups: pd.Series, classes: pd.Series) -> pd.DataFrame:
    """Return of each instrument minus the median of its own sector/region on the same date. This strips out
    market, sector and (mostly) currency moves, which no instrument-level flow signal can predict.
    Groups with fewer than 3 members fall back to their asset class."""
    g, c = groups.reindex(fwd.columns), classes.reindex(fwd.columns)
    small = (g.map(g.value_counts()) < 3).values
    gm = fwd.T.groupby(g.values).transform("median").T.values
    cm = fwd.T.groupby(c.values).transform("median").T.values
    return fwd - np.where(small[None, :], cm, gm)


HZ_LOOKBACKS, HZ_FORWARD = (5, 20, 60, 120), (1, 5, 20, 60, 120)
# Hypotheses fixed BEFORE looking at the results: (score lookback, forward horizon, expected sign)
HZ_HYPOTHESES = {(5, 5): -1, (60, 60): +1, (120, 120): +1}


@st.cache_data(ttl=3600, show_spinner=False)
def horizon_test(_P: dict, stamp: str, wt: tuple, scope: str):
    """Does 'follow the money' work, and at which horizon? For every (score lookback, forward horizon) pair:
    on non-overlapping dates, compare the sector/region-neutral forward return of the 20% highest flow scores
    with the 20% lowest. Entry is at the close of the day AFTER the signal."""
    cols = [c for c in _P["Close"].columns if c in META.index]
    if scope == "core":
        cols = [c for c in cols if META.loc[c, "core"]]
    elif scope:
        cols = [c for c in cols if META.loc[c, "cls"] == scope]
    if len(cols) < 40:
        return None
    scope_key = f"|hz|{scope}|{len(cols)}"
    groups, classes = META.loc[cols, "group"], META.loc[cols, "cls"]
    C = _P["Close"][cols]
    _Ph = {k_: v_[cols] for k_, v_ in _P.items()}                      # only this scope, over the whole history
    ranks = {L: compute(_Ph, stamp + scope_key, L, wt, (), 1, True)[1][cols].rank(axis=1, pct=True) for L in HZ_LOOKBACKS}
    rows = []
    for h in HZ_FORWARD:
        res = residual_returns(C.shift(-h - 1) / C.shift(-1) - 1, groups, classes)
        # Non-overlapping periods can start on any day. For long horizons the answer should not depend on that
        # arbitrary choice, so the test is repeated for 4 different start days and the results are AVERAGED
        # (the number of periods is not multiplied: they are the same data seen from shifted grids).
        offsets = [0] if h < 20 else [0, h // 4, h // 2, 3 * h // 4]
        for L in HZ_LOOKBACKS:
            runs = []
            for off in offsets:
                pos = list(range(260 + off, len(C) - h - 1, h))
                rr, sr = res.iloc[pos], ranks[L].iloc[pos]
                ok = sr.notna() & rr.notna()
                sp = (rr.where((sr > 0.8) & ok).mean(axis=1) - rr.where((sr <= 0.2) & ok).mean(axis=1)).dropna()
                if len(sp) >= 8 and sp.std() > 0:
                    runs.append((sp.mean() * 100, sp.mean() / sp.std(ddof=1) * np.sqrt(len(sp)), len(sp), (sp > 0).mean() * 100))
            if runs:
                a_ = np.array(runs)
                rows.append({"L": L, "h": h, "spread": float(a_[:, 0].mean()), "t": float(a_[:, 1].mean()), "n": int(a_[:, 2].min()),
                             "hit": float(a_[:, 3].mean()), "t_min": float(a_[:, 1].min()), "t_max": float(a_[:, 1].max())})
    return pd.DataFrame(rows) if rows else None


# ── Quant score: fixed rules from published research, nothing fitted to this data ──────────────
# (factor, sign from the literature, source). Signs were set from the papers, not from this sample.
QUANT_FACTORS = [
    ("Residu-momentum 12-1 mnd", +1, "Blitz, Huij & Martens 2011"),
    ("Koersmomentum 12-1 mnd", +1, "Jegadeesh & Titman 1993"),
    ("Nabijheid 52-weken-top", +1, "George & Hwang 2004"),
    ("Rendement laatste maand", -1, "Jegadeesh 1990 (korte-termijnomkeer)"),
    ("Grootste dagwinst (loterij)", -1, "Bali, Cakici & Whitelaw 2011"),
    ("Netto-uitgifte aandelen", -1, "Pontiff & Woodgate 2008"),
    ("Short: dagen tot dekking", -1, "Hong, Li, Ni, Scheinkman & Yan 2016"),
    ("Seizoenspatroon", +1, "Heston & Sadka 2008"),
]
QUANT_PRIMARY_H = 60      # the horizon the verdict is based on, fixed in advance


@st.cache_data(ttl=3600, show_spinner=False)
def quant_score(_P: dict, _extra: dict, key: str):
    """Composite of well-documented return anomalies. Each factor is ranked within its asset class per day,
    signed as in the original paper, and averaged with equal weights. No parameter is estimated from this
    data, so the whole history can serve as a test. Returns (score panel, dict of signed factor rank panels)."""
    cols = [c for c in _P["Close"].columns if c in META.index]
    C = _P["Close"][cols]
    groups, classes = META.loc[cols, "group"], META.loc[cols, "cls"]
    r1 = C.pct_change(fill_method=None)
    vol = r1.rolling(60, min_periods=20).std()
    raw = {
        "Residu-momentum 12-1 mnd": residual_returns(r1, groups, classes).shift(20).rolling(230, min_periods=150).sum() / (vol * np.sqrt(230)),
        "Koersmomentum 12-1 mnd": C.shift(20) / C.shift(250) - 1,
        "Nabijheid 52-weken-top": C / C.rolling(250, min_periods=120).max(),
        "Rendement laatste maand": C / C.shift(20) - 1,
        "Grootste dagwinst (loterij)": r1.rolling(20).max(),
        "Seizoenspatroon": sum(C.shift(k - 20) / C.shift(k) - 1 for k in (250, 500, 750)) / 3,
    }
    if "Netto-uitgifte aandelen · 250D" in _extra:
        raw["Netto-uitgifte aandelen"] = _extra["Netto-uitgifte aandelen · 250D"].reindex(index=C.index, columns=cols)
    if "Short · dagen tot dekking" in _extra:
        raw["Short: dagen tot dekking"] = _extra["Short · dagen tot dekking"].reindex(index=C.index, columns=cols)
    cl = classes.values
    signed = {}
    for name, sign, _ in QUANT_FACTORS:
        if name not in raw:
            continue
        x = raw[name].replace([np.inf, -np.inf], np.nan)
        rk = pd.DataFrame(np.nan, index=C.index, columns=cols)
        for c_ in np.unique(cl):
            m = cl == c_
            if m.sum() >= 5:
                rk.loc[:, m] = x.loc[:, m].rank(axis=1, pct=True).values - 0.5
        signed[name] = rk * sign
    stack = np.stack([v.values for v in signed.values()], axis=2)
    cnt = (~np.isnan(stack)).sum(axis=2)
    score = pd.DataFrame(np.where(cnt >= 4, np.nanmean(np.where(cnt[..., None] >= 4, stack, np.nan), axis=2), np.nan), index=C.index, columns=cols)
    return score, signed


@st.cache_data(ttl=3600, show_spinner=False)
def quant_test(_P: dict, _score: pd.DataFrame, _signed: dict, key: str, step: int = 5):
    """Top 20% minus bottom 20% of the score (and of every single factor) on sector/region-neutral forward
    returns, entered at the next close. Means use every 5th day; t-statistics credit only non-overlapping periods.
    Also split by half of the sample and by region, to see whether the result is more than one lucky stretch."""
    cols = list(_score.columns)
    C = _P["Close"][cols]
    groups, classes = META.loc[cols, "group"], META.loc[cols, "cls"]
    is_stock = (~META.loc[cols, "core"]).values
    out, by_factor, by_part = [], [], []

    def spread(sig, res, pos, mask):
        sr = sig.iloc[pos].loc[:, mask].rank(axis=1, pct=True)
        rr = res.iloc[pos].loc[:, mask]
        ok = sr.notna() & rr.notna()
        return (rr.where((sr > 0.8) & ok).mean(axis=1) - rr.where((sr <= 0.2) & ok).mean(axis=1)).dropna()

    def stat(sp, h):
        n_eff = max(len(sp) * step / (h + 1), 1.0)
        t = float(sp.mean() / (sp.std(ddof=1) / np.sqrt(n_eff))) if len(sp) > 5 and sp.std(ddof=1) > 0 else 0.0
        return float(sp.mean() * 100), t, int(round(n_eff)), float((sp > 0).mean() * 100)

    for h in (20, 60, 120):
        res = residual_returns(C.shift(-h - 1) / C.shift(-1) - 1, groups, classes)
        pos = list(range(270, len(C) - h - 1, step))
        sp = spread(_score, res, pos, is_stock)
        m_, t_, n_, hit_ = stat(sp, h)
        out.append({"h": h, "spread": m_, "t": t_, "n": n_, "hit": hit_, "series": sp})
        if h == QUANT_PRIMARY_H:
            half = len(sp) // 2
            for lab, part in (("Eerste helft", sp.iloc[:half]), ("Tweede helft", sp.iloc[half:])):
                a_, b_, c_, _ = stat(part, h)
                by_part.append({"Deel": f"{lab} ({part.index[0]:%Y}–{part.index[-1]:%Y})", "Top−bodem %": a_, "t": b_, "Perioden": c_})
            for lab, cl_ in (("Aandelen VS", "US Stocks"), ("Aandelen Europa", "Europe Stocks"), ("Aandelen Azië", "Asia Stocks")):
                a_, b_, c_, _ = stat(spread(_score, res, pos, (classes == cl_).values), h)
                by_part.append({"Deel": lab, "Top−bodem %": a_, "t": b_, "Perioden": c_})
            a_, b_, c_, _ = stat(spread(_score, res, pos, ~is_stock), h)
            by_part.append({"Deel": "Kern (ETF's, futures, FX)", "Top−bodem %": a_, "t": b_, "Perioden": c_})
            for name, sign, src in QUANT_FACTORS:
                if name in _signed:
                    a_, b_, c_, _ = stat(spread(_signed[name], res, pos, is_stock), h)
                    by_factor.append({"Factor": name, "Richting": "hoog = beter" if sign > 0 else "laag = beter", "Top−bodem %": a_, "t": b_, "Bron": src})
    return out, pd.DataFrame(by_factor), pd.DataFrame(by_part)


ROT_LOOKBACKS, ROT_FORWARD = (5, 20, 60, 120), (5, 20, 60, 120)
ROT_HYPOTHESES = [(20, 20), (60, 60)]      # fixed before looking: does real fund flow over 20/60 days say anything about the next 20/60?


@st.cache_data(ttl=3600, show_spinner=False)
def rotation_test(_sp: dict, key: str):
    """Rotation test on funds with REAL flows (SPDR creations/redemptions), free of survivorship in single stocks.
    Signal: net flow as % of assets, ranked within the fund's own bucket. Outcome: forward total return minus
    the bucket median, entered at the next close. Top third minus bottom third, averaged over 4 start days.
    The same test is run with plain price trend (250-day momentum skipping the last month) for comparison."""
    close = _sp["close"]
    funds = [c for c in _sp["so"].columns if c in close.columns and close[c].notna().sum() > 400]
    close = close[funds].dropna(how="all")
    sp = {k: _sp[k][funds].reindex(close.index).ffill(limit=5) for k in ("so", "nav", "tna")}
    bucket = pd.Series({f: SPDR_FUNDS[f][1] for f in funds})
    small = (bucket.map(bucket.value_counts()) < 3).values

    def neutral(x):                       # minus bucket median (overall median for tiny buckets)
        bm = x.T.groupby(bucket.values).transform("median").T.values
        return x - np.where(small[None, :], np.nanmedian(x.values, axis=1)[:, None], bm)

    def brank(x):                         # rank within bucket per date
        return x.T.groupby(bucket.values).rank(pct=True).T

    sigs = {("Echte fondsstroom", L): brank(spdr_flow_pct(sp, L)) for L in ROT_LOOKBACKS}
    sigs[("Koerstrend", 250)] = brank(close.shift(20) / close.shift(250) - 1)
    rows = []
    for h in ROT_FORWARD:
        res = neutral(close.shift(-h - 1) / close.shift(-1) - 1)
        offsets = [0] if h < 20 else [0, h // 4, h // 2, 3 * h // 4]
        for (kind, L), sr_all in sigs.items():
            runs = []
            for off in offsets:
                pos = list(range(260 + off, len(close) - h - 1, h))
                rr, sr = res.iloc[pos], sr_all.iloc[pos]
                ok = sr.notna() & rr.notna()
                sp_ = (rr.where((sr > 2 / 3) & ok).mean(axis=1) - rr.where((sr <= 1 / 3) & ok).mean(axis=1)).dropna()
                if len(sp_) >= 8 and sp_.std() > 0:
                    runs.append((sp_.mean() * 100, sp_.mean() / sp_.std(ddof=1) * np.sqrt(len(sp_)), len(sp_)))
            if runs:
                a_ = np.array(runs)
                rows.append({"kind": kind, "L": L, "h": h, "spread": float(a_[:, 0].mean()), "t": float(a_[:, 1].mean()), "n": int(a_[:, 2].min()),
                             "t_min": float(a_[:, 1].min()), "t_max": float(a_[:, 1].max())})
    return (pd.DataFrame(rows), len(funds)) if rows else (None, len(funds))


# ── machine-learning forecast with honest self-tuning ───────────────────────
# Candidate settings the model tries on itself: (forecast horizon in days, tree depth, min samples per leaf)
ML_CONFIGS = [(20, 3, 200), (60, 3, 200), (120, 3, 200)]     # (forecast horizon in days, tree depth, min samples per leaf)
ML_MIN_PERIODS = 12    # a verdict of 'proven' needs at least this many unseen, non-overlapping test periods


def ml_verdict(ml):
    """One rule for the model's verdict, used everywhere. 'JA' needs ALL of: hold-out t > 2 with a positive spread,
    at least ML_MIN_PERIODS unseen periods, and t > 2 over the whole walk-forward span as well. The last condition
    stops a model that learned nothing during validation from being called proven on one favourable stretch."""
    if not ml:
        return "NEE", False
    h_, a_ = ml["best"]["hold"], ml["best"].get("all") or ml["best"]["hold"]
    sig = h_["ic_t"] > 2 and h_["spread"] > 0
    if sig and h_["n"] >= ML_MIN_PERIODS and a_["ic_t"] > 2:
        return "JA", True
    if sig and a_["ic_t"] > 1.5:
        return "VEELBELOVEND", False
    return ("ZWAK", False) if h_["ic"] > 0 and h_["spread"] > 0 else ("NEE", False)


def _z(x):
    sd = np.nanstd(x)
    return (x - np.nanmean(x)) / sd if sd > 0 else x * 0.0


def _fit_predict(Xtr, ytr, Xte, depth=3, leaf=200, cap=120_000):
    """Ensemble: two gradient-boosted tree models on different random sub-samples plus a ridge regression.
    Trees find interactions, the linear model keeps the broad tilt stable; averaging their standardised
    forecasts is more robust than any one of them when the signal is weak."""
    preds, name = [], "Ensemble: 2× gradient boosting + ridge"
    Xtr0, Xte0 = np.nan_to_num(Xtr), np.nan_to_num(Xte)
    mu, sd = Xtr0.mean(0), Xtr0.std(0) + 1e-9
    A = (Xtr0 - mu) / sd
    w = np.linalg.solve(A.T @ A + 0.02 * len(A) * np.eye(A.shape[1]), A.T @ (ytr - ytr.mean()))
    preds.append(_z(((Xte0 - mu) / sd) @ w))
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor
        for seed in (0, 1):
            Xs, ys = Xtr, ytr
            if len(ytr) > cap:
                pick = np.random.default_rng(seed).choice(len(ytr), cap, replace=False)
                Xs, ys = Xtr[pick], ytr[pick]
            m = HistGradientBoostingRegressor(max_iter=60, learning_rate=0.08, max_depth=depth, min_samples_leaf=leaf,
                                              l2_regularization=1.0, random_state=seed)
            m.fit(Xs, ys)
            preds.append(_z(m.predict(Xte)))
    except ImportError:
        name = "Ridge-regressie (scikit-learn ontbreekt)"
    return np.mean(preds, axis=0), name


def _walk_forward(F, valid, Y, R, h, step, retrain, depth, leaf, start):
    """Train on the past only (with a gap of h+1 days so no future leaks in), predict the next block, repeat.
    Returns one row per test date: (date position, rank-IC, top-bottom spread, quintile returns)."""
    lab = valid & ~np.isnan(Y)
    gap = int(np.ceil((h + 1) / step)) + 1
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
    for i in range(start, len(Y)):
        ok = ~np.isnan(PR[i]) & ~np.isnan(R[i])
        if ok.sum() < 50:
            continue
        p, r = pd.Series(PR[i][ok]), pd.Series(R[i][ok])
        qm = r.groupby(pd.qcut(p.rank(method="first"), 5, labels=False)).mean()
        rows.append((i, p.corr(r, method="spearman"), qm.iloc[-1] - qm.iloc[0], qm.values))
    return rows, lab, PR


def _metrics(rows, h, step):
    """Averages use EVERY test date (so the result does not hinge on which day a period starts); the t-statistic
    only credits the number of NON-overlapping periods, because overlapping windows are not independent."""
    ic, sp = np.array([r[1] for r in rows]), np.array([r[2] for r in rows])
    n_eff = max(len(rows) * step / (h + 1), 1.0)
    t = lambda x: float(x.mean() / (x.std(ddof=1) / np.sqrt(n_eff))) if len(x) > 2 and x.std(ddof=1) > 0 else 0.0
    return {"ic": float(ic.mean()), "ic_t": t(ic), "spread": float(sp.mean() * 100), "spread_t": t(sp),
            "hit": float((sp > 0).mean() * 100), "n": int(round(n_eff)), "quint": np.mean([r[3] for r in rows], axis=0) * 100}


def ml_forecast(P: dict, macro: pd.DataFrame, extra: dict = None, step: int = 5, retrain: int = 40):
    """Learn from history which patterns preceded out-performance, tune itself, and report honestly.

    Inputs per instrument (each ranked against its own asset class on the same day, so scales are comparable
    through time):
      · money flow: 6 components on 5/20/60 days (CMF, MFI, relative strength x2, flow momentum, volume intensity)
      · price path: momentum 5/20/60/120 days, 250-day momentum skipping the last month, residual momentum
        (own return minus its sector), sector momentum, distance from the 250-day high, largest one-day gain
      · when the money moves: overnight versus intraday return (institutions and news act outside the session)
      · news days: direction of returns on abnormal-volume days (a price x volume proxy for earnings drift)
      · seasonality (same period in the three previous years)
      · real flows, when available: short interest, net share issuance/buybacks, SPDR sector fund flows
    Market-wide inputs: cross-asset regime ratios, VIX, CFTC positioning, FRED, SPDR flows into stocks/cash/credit/duration.
    Target   : rank of the next-h-day return RELATIVE TO the instrument's own sector/region, scaled by volatility.
    Tuning   : each horizon in ML_CONFIGS is walked forward; the one that ranks best on the VALIDATION period
               (first 65% of the test span) is selected. Verdict: only the HOLD-OUT period (last 35%).
    Caveat   : the stock list is today's large caps (survivorship bias)."""
    extra = extra or {}
    cols = [c for c in P["Close"].columns if c in META.index]
    P_ = {k: v[cols] for k, v in P.items()}
    C, O, V = P_["Close"], P_["Open"], P_["Volume"]
    key = f"{C.index[-1].date()}|{len(cols)}|{len(C)}|{','.join(macro.columns)}|{','.join(extra)}|v7"
    try:
        saved = pd.read_pickle(CACHE_DIR / "model.pkl")
        if saved.get("key") == key:
            return saved["result"]
    except Exception:
        pass
    groups, classes = META.loc[cols, "group"], META.loc[cols, "cls"]
    r1 = C.pct_change(fill_method=None)
    vol = r1.rolling(60, min_periods=20).std()
    feats = {}
    for n in (5, 20, 60):
        fp = flow_panels(P_, n, groups, classes)
        for c in COMP_COLS:
            feats[f"{c} · {n}D"] = fp[c]
    n_req = len(feats)                                              # these must be present; later inputs may be missing
    for n in (5, 20, 60, 120):
        feats[f"Momentum · {n}D"] = (C / C.shift(n) - 1) / (vol * np.sqrt(n))
    feats["Momentum · 250D excl. laatste 20D"] = (C.shift(20) / C.shift(250) - 1) / (vol * np.sqrt(230))
    resid_d = residual_returns(r1, groups, classes)
    feats["Residu-momentum · 250D excl. 20D"] = resid_d.shift(20).rolling(230, min_periods=150).sum() / (vol * np.sqrt(230))
    ret120 = C / C.shift(120) - 1
    feats["Sectormomentum · 120D"] = ret120 - residual_returns(ret120, groups, classes)
    feats["Afstand tot 250D-top"] = C / C.rolling(250, min_periods=120).max() - 1
    feats["Grootste dagwinst · 20D"] = r1.rolling(20).max() / vol
    on, intra = np.log(O / C.shift(1)), np.log(C / O)
    for n in (20, 60):
        feats[f"Nachtrendement · {n}D"] = on.rolling(n).sum() / (vol * np.sqrt(n))
        feats[f"Dagrendement · {n}D"] = intra.rolling(n).sum() / (vol * np.sqrt(n))
    hasv = np.broadcast_to((V.tail(250).sum() > 0).values, V.shape)
    relv = (V / V.rolling(60, min_periods=20).median().where(lambda x: x > 0)).where(hasv)
    feats["Nieuwsdag-richting · 60D"] = ((r1 / vol) * (relv - 2).clip(lower=0, upper=5)).rolling(60, min_periods=20).sum()
    # Volatility and illiquidity are deliberately NOT inputs. The stock list holds today's large companies only, so
    # anything that proxies "was small, thinly traded or volatile in the past" looks predictive purely because the
    # small names that are in the list are the ones that grew (survivorship). An edge-search agent measured this:
    # illiquidity alone gave t = 5 on this universe, an artefact that cannot be traded.
    feats["Seizoen · zelfde periode vorige 3 jaar"] = sum(C.shift(k - 20) / C.shift(k) - 1 for k in (250, 500, 750)) / 3
    for k, v in extra.items():
        feats[k] = v.reindex(index=C.index, columns=cols)
    n_rank = len(feats)                                             # everything so far is ranked within asset class
    codes = pd.Series(pd.factorize(classes)[0].astype(float), index=cols)
    feats["Categorie"] = pd.DataFrame(np.tile(codes.values, (len(C), 1)), index=C.index, columns=cols)
    names = list(feats) + list(macro.columns)
    dates = C.index[260::step].union([C.index[-1]])                 # the last bar is always on the grid: it is today's forecast row
    if len(dates) < 160:
        return None
    F = np.empty((len(dates), len(cols), len(names)), dtype="float32")   # (dates, tickers, inputs)
    for j, k in enumerate(feats):
        F[:, :, j] = feats[k].reindex(dates).replace([np.inf, -np.inf], np.nan).values
    for j, k in enumerate(macro.columns, start=len(feats)):
        F[:, :, j] = macro[k].reindex(dates).values[:, None]
    del feats
    valid = ~np.isnan(F[:, :, :n_req]).any(axis=2)
    for cl in np.unique(codes.values):                              # cross-sectional rank within asset class, per date
        m = codes.values == cl
        for j in range(n_rank):
            F[:, m, j] = pd.DataFrame(F[:, m, j]).rank(axis=1, pct=True).values - 0.5
    start = max(int(250 / step), int(len(dates) * 0.3))
    split = start + int((len(dates) - start) * 0.65)
    trials = []
    for h, depth, leaf in ML_CONFIGS:
        # Enter at the NEXT day's close and hold h days (same-day US information must not "predict" Asia/Europe).
        fwd = residual_returns(C.shift(-h - 1) / C.shift(-1) - 1, groups, classes)
        Y, R = ((fwd / (vol * np.sqrt(h))).rank(axis=1, pct=True) - 0.5).reindex(dates).values, fwd.reindex(dates).values
        rows, lab, PR = _walk_forward(F, valid, Y, R, h, step, retrain, depth, leaf, start)
        val, hold = [r for r in rows if r[0] < split], [r for r in rows if r[0] >= split]
        if len(val) * step < 6 * (h + 1) or len(hold) * step < 3 * (h + 1):
            continue
        trials.append({"h": h, "depth": depth, "leaf": leaf, "val": _metrics(val, h, step), "hold": _metrics(hold, h, step),
                       "all": _metrics(rows, h, step), "rows": rows, "Y": Y, "lab": lab})
    if not trials:
        return None
    best = max(trials, key=lambda t: t["val"]["ic_t"])                             # chosen on validation only
    oknow = valid[-1]
    pnow, model_name = _fit_predict(F[best["lab"]], best["Y"][best["lab"]], F[-1][oknow], best["depth"], best["leaf"])
    yl = best["Y"][best["lab"]]

    def _corr(j_):
        x = F[..., j_][best["lab"]]
        m = ~np.isnan(x)
        return float(np.corrcoef(x[m], yl[m])[0, 1]) if m.sum() > 1000 and np.nanstd(x[m]) > 0 else 0.0

    table_ = pd.DataFrame([{"Horizon": f"{t['h']}D", "Gekozen": "◀ gekozen" if t is best else "",
                            "Validatie IC": t["val"]["ic"], "Validatie t": t["val"]["ic_t"], "Validatie n": t["val"]["n"],
                            "Eindtoets IC": t["hold"]["ic"], "Eindtoets t": t["hold"]["ic_t"], "Eindtoets n": t["hold"]["n"],
                            "Eindtoets top−bodem %": t["hold"]["spread"], "Hele testperiode t": t["all"]["ic_t"],
                            "Hele testperiode n": t["all"]["n"]} for t in trials])
    gap_ = int(np.ceil((best["h"] + 1) / step)) + 1
    curve_rows = best["rows"][::gap_]                                              # non-overlapping, for the cumulative chart
    result = {"best": {k: best[k] for k in ("h", "depth", "leaf", "val", "hold", "all")}, "trials": table_,
              "curve": pd.Series(np.cumsum([r[2] for r in curve_rows]) * 100, index=[dates[r[0]] for r in curve_rows]),
              "split_date": dates[split], "forecast": (pd.Series(pnow, index=np.array(cols)[oknow]).rank(pct=True) - 0.5) * 200,
              "relevance": pd.Series({k: _corr(j_) for j_, k in enumerate(names)}),
              "model": model_name, "examples": int(best["lab"].sum()), "first": dates[0], "test_from": dates[start],
              "n_feat": len(names), "n_inst": len(cols), "macro": list(macro.columns), "extra": list(extra), "trained": C.index[-1]}
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        pd.to_pickle({"key": key, "result": result}, CACHE_DIR / "model.pkl")
    except Exception:
        pass
    return result


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
        pathbar=dict(visible=True, thickness=20), maxdepth=3 if len(d) > 300 else 4, tiling=dict(pad=2)))
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
SECTIONS = {"COCKPIT": ["COCKPIT"],
            "GELDSTROMEN": ["SIGNALEN", "COMMAND CENTER", "HEATMAP", "ECHTE STROMEN", "REGIME & LIQUIDITY", "LEADERBOARDS"],
            "INSTRUMENT": ["DEEP DIVE"], "PATRONEN": ["PATRONEN"], "ONDERZOEK": ["VOORSPELLING", "METHODOLOGY"],
            "PORTEFEUILLE": ["PORTEFEUILLE"], "ARCHIEF": ["GEHEUGEN", "HANDLEIDING"]}
LABELS = {"COMMAND CENTER": "STROOMKAART", "REGIME & LIQUIDITY": "REGIME & LIQUIDITEIT", "LEADERBOARDS": "RANGLIJSTEN", "VOORSPELLING": "MODEL & TOETSEN",
          "METHODOLOGY": "METHODE", "GEHEUGEN": "GEHEUGEN & DATA"}
if "pins" not in ss:                      # first run of this session: restore everything from memory
    saved_ = mem_settings()
    qp = st.query_params.get("pins", "")
    ss.pins = [p for p in qp.split(",") if p] or saved_.get("pins") or ["SPY", "TLT", "GLD", "UUP", "HYG", "BTC-USD"]
    sw_ = saved_.get("weights") or {}
    for c_ in COMP_COLS:
        ss[f"w_{c_}"] = int(sw_.get(c_, DEFAULT_WEIGHTS[c_]))
    ss["stocks"] = bool(saved_.get("stocks", True))
    ss["auto"] = bool(saved_.get("auto", False))
    ss["tf"] = saved_.get("tf") if saved_.get("tf") in TIMEFRAMES else "20D"
    ss["extra"] = list(saved_.get("extra", []))
ss.setdefault("sect", "COCKPIT")
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
    _s = next((k_ for k_, v_ in SECTIONS.items() if _v in v_), "COCKPIT")
    ss.sect = _s
    if len(SECTIONS[_s]) > 1:
        ss[f"sub_{_s}"] = _v


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
    st.markdown(f"<div style='font-family:{MONO};font-size:15px;font-weight:700;color:{GREEN};letter-spacing:.14em'>◈ QTRON</div>",
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
    st.toggle(f"Aandelen wereldwijd (±{int((~META['core']).sum())})", key="stocks",
              help="Laadt ook losse aandelen uit de VS (incl. Nasdaq), Europa en Azië. Eerste keer ±5 minuten, daarna 6 uur op schijf bewaard.")
    st.toggle("Auto-refresh (5 min)", key="auto", help="Herlaadt de pagina elke 5 minuten. Dagdata ververst elke 15 min, LIVE 1D elke 4 min.")
    with st.expander("Gewichten van de geldstroomscore"):
        wt = tuple(st.slider(c, 0, 50, step=5, key=f"w_{c}") for c in COMP_COLS)
        if sum(wt) == 0:
            wt = tuple(DEFAULT_WEIGHTS.values())
        st.markdown("<div class='note'>Gewichten worden herschaald naar 100%. Score = Σ gewicht × onderdeel, elk onderdeel tussen −100 en +100.</div>",
                    unsafe_allow_html=True)
    with st.expander("Meldingen op je telefoon"):
        cur_ = mem_settings().get("ntfy_topic", "")
        nt_ = st.text_input("ntfy-onderwerp (leeg = uit)", value=cur_, key="ntfy_in", help="Installeer de gratis app ntfy op je telefoon, abonneer je op een zelfgekozen, "
                            "moeilijk te raden onderwerp en vul datzelfde onderwerp hier in.")
        if nt_ != cur_:
            mem_write("INSERT OR REPLACE INTO settings VALUES (?,?)", [("ntfy_topic", json.dumps(nt_.strip()))])
        st.markdown("<div class='note'>Staat dit aan, dan stuurt de verzamelaar een bericht bij een wijziging van het marktalarm of van de actieve patronen. "
                    "Het bericht loopt via de dienst ntfy.sh en verlaat dus je netwerk. Standaard uit.</div>", unsafe_allow_html=True)

tickers = tuple(list(META.index[META["core"]]) + [t for t in ss.extra if t not in META.index])   # core: refreshed every 15 min
stock_tickers = tuple(META.index[~META["core"]])                                                  # stocks: disk-cached, 6 h
demo, failed, P = (mode == "Demo"), [], None
core_stale, core_asof = False, time.time()
if not demo:
    with st.spinner("Fetching market data from Yahoo Finance…"):
        try:
            P, failed, core_asof, core_stale = load_core(tickers)
        except Exception:
            P, core_stale = None, False
    if P is None or P["Close"].shape[1] < 20:
        demo, P, failed = True, None, []
        st.markdown("<div class='banner'>⚠ LIVE DATA UNREACHABLE (Yahoo Finance did not respond) — showing SYNTHETIC DEMO DATA. "
                    "Numbers below are not real markets. Check your connection / <code>pip install -U yfinance</code> and press Refresh.</div>",
                    unsafe_allow_html=True)
if not demo and core_stale:
    st.markdown(f"<div class='banner'>⚠ YAHOO FINANCE NIET BEREIKBAAR — de app toont de laatst opgeslagen echte koersen van "
                f"{datetime.fromtimestamp(core_asof):%d-%m-%Y %H:%M}. Signalen en portefeuille zijn dus niet actueel. "
                "Druk op Refresh data om het opnieuw te proberen.</div>", unsafe_allow_html=True)
if demo:
    if mode == "Demo":
        st.markdown("<div class='banner'>DEMO MODE — synthetic data, not real markets. Switch to Live in the sidebar.</div>", unsafe_allow_html=True)
    P = make_demo(tickers)
stocks_asof = None
if not demo and ss.get("stocks", True):
    with st.spinner("Aandelen wereldwijd laden (eerste keer ±5 minuten, daarna van schijf)…"):
        SP, sfailed, stime = load_stocks(stock_tickers)
    if SP is not None:
        failed = list(failed) + list(sfailed)
        stocks_asof = stime
else:
    SP = None


@st.cache_resource(max_entries=1, show_spinner=False)
def merged_panels(_core: dict, _stocks, key: str):
    """Core and stock panels joined and cleaned once per data refresh. Shared, not copied, across reruns: with 3,000
    instruments a fresh copy on every click would cost seconds and gigabytes."""
    X = _core if _stocks is None else {k_: pd.concat([_core[k_], _stocks[k_].reindex(_core[k_].index)], axis=1).astype("float32") for k_ in _core}
    return _clean(X)


P = merged_panels(P, SP if stocks_asof else None, f"{'demo' if demo else 'live'}|{core_asof}|{stocks_asof}|{len(tickers)}|{P['Close'].index[-1]}|{P['Close'].shape}")
dropped = [t for t in tickers + (stock_tickers if stocks_asof else ()) if t not in P["Close"].columns]


def mkstamp(X):
    return f"{'demo' if demo else 'live'}|{X['Close'].index[-1]}|{X['Close'].shape}|{float(X['Close'].iloc[-1].sum()):.4f}"


stamp = mkstamp(P)

# ── header + global controls ────────────────────────────────────────────────
asof = P["Close"].index[-1].strftime("%Y-%m-%d")
st.markdown(f"<div class='hdr'><div class='t'>◈ QTRON <span style='font-size:11px;color:{DIM};letter-spacing:.1em'>GELDSTROMEN · PATRONEN · ARCHIEF</span></div><div class='s'>"
            f"{'DEMO DATA' if demo else 'OPGESLAGEN KOERSEN' if core_stale else 'LIVE · YAHOO FINANCE'} · last bar {asof} · {P['Close'].shape[1]} instruments · "
            f"rendered {datetime.now(timezone.utc):%H:%M:%S} UTC</div></div>", unsafe_allow_html=True)
c1, c2, c3 = st.columns([2.2, 1, 0.45])
with c3:
    open_analyst = st.button("🧠 ANALIST", width="stretch", type="primary", help="Laat alle data samen beoordelen en toon koopkandidaten met uitleg")
with c1:
    st.radio("Sectie", list(SECTIONS), key="sect", horizontal=True, label_visibility="collapsed")
    _subs = SECTIONS[ss.sect]
    if len(_subs) > 1:
        if ss.get(f"sub_{ss.sect}") not in _subs:
            ss[f"sub_{ss.sect}"] = _subs[0]
        st.radio("Scherm", _subs, key=f"sub_{ss.sect}", horizontal=True, label_visibility="collapsed", format_func=lambda v_: LABELS.get(v_, v_))
        view = ss[f"sub_{ss.sect}"]
    else:
        view = _subs[0]
with c2:
    tf = st.radio("Timeframe", list(TIMEFRAMES), horizontal=True, label_visibility="collapsed", key="tf",
                  help="Lookback for every flow metric. LIVE 1D = last session on 15-minute bars. 5D = tactical, 20D = swing, 60D/120D = positioning.")
N = TIMEFRAMES[tf]
if view in SECTIONS["GELDSTROMEN"]:
  with st.expander("ⓘ  Wat stellen deze “stromen” voor? (één keer lezen)"):
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
FLOW_VIEWS = SECTIONS["GELDSTROMEN"] + ["DEEP DIVE"]
if view in FLOW_VIEWS:
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
if pins and view in FLOW_VIEWS + ["COCKPIT"]:
    sec(f"Volglijst · {tf}")
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
    "Kwant": st.column_config.ProgressColumn("Kwant", min_value=-100, max_value=100, format="%+.0f",
                                             help="Kwantscore: vaste regels uit onderzoek. +100 = hoogste van het universum, −100 = laagste"),
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
                        "Vote", "Move %", "Z", "Live", "5D", "20D", "60D", "Totaal", "Model", "Kwant"] if x in df.columns]
    sty = df.style.map(lambda v: c(v * 100) if isinstance(v, (int, float)) and np.isfinite(v) else "", subset=cols)
    if "Signaal" in df.columns:
        sty = sty.map(lambda v: f"color:{GREEN};font-weight:700" if "▲" in str(v) else f"color:{RED};font-weight:700" if "▼" in str(v) else f"color:{DIM}",
                      subset=["Signaal"])
    return sty


SCOPES = {"Alles": None, "Kern · ETF's, futures, FX": "core", "Aandelen VS": "US Stocks", "Aandelen Europa": "Europe Stocks",
          "Aandelen Azië": "Asia Stocks"}


def scope_filter(df, key):
    """Radio that narrows a table to the core cross-asset set or one stock region."""
    if not (~META["core"]).reindex(df.index).fillna(False).any():
        return df
    ch = SCOPES[st.radio("Toon", list(SCOPES), horizontal=True, key=key, label_visibility="collapsed")]
    if ch is None:
        return df
    return df[META["core"].reindex(df.index).fillna(False)] if ch == "core" else df[df["Class"] == ch]


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


# ── paper trading: a simulated portfolio stored on this PC (cache/portfolio.json) ──
PF_FILE = CACHE_DIR / "portfolio.json"
CCY_SUFFIX = {".AS": "EUR", ".BR": "EUR", ".DE": "EUR", ".PA": "EUR", ".MC": "EUR", ".MI": "EUR", ".HE": "EUR", ".L": "GBP", ".SW": "CHF",
              ".CO": "DKK", ".ST": "SEK", ".OL": "NOK", ".T": "JPY", ".HK": "HKD", ".SS": "CNY", ".SZ": "CNY", ".KS": "KRW", ".TW": "TWD",
              ".NS": "INR", ".AX": "AUD", ".SI": "SGD", ".TO": "CAD", ".KQ": "KRW", ".TWO": "TWD", ".IR": "EUR", ".LS": "EUR", ".VI": "EUR"}
FX_DIRECT = {"EUR": "EURUSD=X", "GBP": "GBPUSD=X", "AUD": "AUDUSD=X"}                       # quoted as USD per unit
FX_INVERSE = {c: f"{c}=X" for c in ("JPY", "CHF", "CNY", "DKK", "SEK", "NOK", "HKD", "KRW", "TWD", "INR", "SGD", "CAD")}  # units per USD


def ccy_of(t: str) -> str:
    return next((c for suf, c in CCY_SUFFIX.items() if t.endswith(suf)), "USD")


@st.cache_data(ttl=900, show_spinner=False)
def fx_usd(is_demo: bool) -> dict:
    """USD value of one unit of each currency (latest close)."""
    out = {"USD": 1.0}
    if is_demo:
        return {**out, **{c: 1.0 for c in list(FX_DIRECT) + list(FX_INVERSE)}}
    try:
        import yfinance as yf
        tk = list(FX_DIRECT.values()) + list(FX_INVERSE.values())
        px = yf.download(tk, period="5d", interval="1d", progress=False, auto_adjust=True)["Close"].ffill().iloc[-1]
        for c, t in FX_DIRECT.items():
            if pd.notna(px.get(t)):
                out[c] = float(px[t])
        for c, t in FX_INVERSE.items():
            if pd.notna(px.get(t)) and px[t] > 0:
                out[c] = 1.0 / float(px[t])
    except Exception:
        pass
    return out


def pf_load() -> dict:
    try:
        return json.loads(PF_FILE.read_text())
    except Exception:
        return {"base": "EUR", "start": 100_000.0, "cash": 100_000.0, "fee_pct": 0.10, "realized": 0.0, "positions": {}, "trades": [], "history": {},
                "stop_pct": 10.0, "trail_pct": 15.0, "horizon_days": 60}


def pf_save(pf: dict):
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        PF_FILE.write_text(json.dumps(pf, indent=1))
    except Exception:
        pass


def pf_price(pf: dict, t: str):
    """Latest price of one share in the portfolio's base currency, or None. London quotes are in pence."""
    if demo or t not in P["Close"].columns:       # never value or trade the portfolio on synthetic prices
        return None
    s_ = P["Close"][t].dropna()
    fx = fx_usd(demo)
    c = ccy_of(t)
    if s_.empty or c not in fx or pf["base"] not in fx:
        return None
    return float(s_.iloc[-1]) * (0.01 if t.endswith(".L") else 1.0) * fx[c] / fx[pf["base"]]


def pf_trade(pf: dict, t: str, side: str, amount: float = None, qty: float = None, reason: str = "") -> str:
    """Execute a simulated order at the latest price. Buys are sized by amount, sells by quantity."""
    if demo:
        return "Papierhandel is uitgeschakeld zolang er demo-data wordt getoond"
    px = pf_price(pf, t)
    if px is None or px <= 0:
        return f"{t}: geen koers of wisselkoers beschikbaar"
    pos = pf["positions"].get(t, {"qty": 0.0, "cost": 0.0})
    cost_pct = pf["fee_pct"] + pf.get("tax_pct", 0.35) + pf.get("spread_pct", 0.05)      # broker + exchange tax + half the spread
    if side == "KOOP":
        fee = amount * cost_pct / 100
        if amount + fee > pf["cash"] + 1e-6:
            return f"{t}: te weinig cash ({pf['cash']:,.0f} beschikbaar)"
        q = amount / px
        pos["cost"] = (pos["cost"] * pos["qty"] + amount) / (pos["qty"] + q)
        pos["qty"] += q
        pf["cash"] -= amount + fee
        pf["realized"] -= fee
    else:
        q = min(qty if qty is not None else pos["qty"], pos["qty"])
        if q <= 0:
            return f"{t}: geen positie om te verkopen"
        amount = q * px
        fee = amount * cost_pct / 100
        pf["cash"] += amount - fee
        pf["realized"] += (px - pos["cost"]) * q - fee
        pos["qty"] -= q
    pos["last"] = px
    pos.setdefault("opened", datetime.now().strftime("%Y-%m-%d"))
    pos["high"] = max(pos.get("high", px), px)
    if pos["qty"] > 1e-9:
        pf["positions"][t] = pos
    else:
        pf["positions"].pop(t, None)
    pf["trades"].append({"tijd": datetime.now().strftime("%Y-%m-%d %H:%M"), "ticker": t, "actie": side, "aantal": round(q, 4),
                         "koers": round(px, 4), "bedrag": round(amount, 2), "kosten": round(fee, 2), "reden": (reason or "").strip()[:200]})
    note = ""
    try:                                       # context for the journal, and a warning when results are due
        sg_ = all_signals()
        pf["trades"][-1]["score20"] = round(float(sg_.at[t, "20D"]), 0) if t in sg_.index else None
        al_ = alarm_now(pat_key())
        pf["trades"][-1]["alarm"] = alarm.NAMES[al_["level"]] if al_ else "—"
        de_ = days_to_earnings(t) if side == "KOOP" else None
        if de_ is not None and de_ <= 7:
            note = f" · LET OP: winstcijfers over {de_} dag(en)"
        if side == "KOOP" and al_ and al_["level"] == 2:
            note += " · LET OP: marktalarm staat op ROOD"
    except Exception:
        pass
    pf_save(pf)
    return f"{side} {q:,.2f} × {t} à {px:,.2f} {pf['base']} · kosten {fee:,.2f}{note}"


def pf_value(pf: dict):
    """Mark the portfolio to market. Returns (positions table, invested value, total value)."""
    rows = []
    for t, pos in pf["positions"].items():
        px = pf_price(pf, t) or pos.get("last", pos["cost"])
        pos["last"] = px
        pos["high"] = max(pos.get("high", px), px)
        val = pos["qty"] * px
        opened = pos.get("opened", datetime.now().strftime("%Y-%m-%d"))
        rows.append({"Ticker": t, "Naam": META.loc[t, "name"] if t in META.index else t, "Aantal": pos["qty"], "Aankoop": pos["cost"], "Koers": px,
                     "Waarde": val, "Resultaat": val - pos["qty"] * pos["cost"], "Resultaat %": (px / pos["cost"] - 1) * 100 if pos["cost"] else 0.0,
                     "Van top %": (px / pos["high"] - 1) * 100 if pos["high"] else 0.0,
                     "Dagen": int(np.busday_count(opened, datetime.now().strftime("%Y-%m-%d")))})
    df = pd.DataFrame(rows).set_index("Ticker") if rows else pd.DataFrame()
    inv = float(df["Waarde"].sum()) if len(df) else 0.0
    return df, inv, pf["cash"] + inv


def all_signals() -> pd.DataFrame:
    """Combined 5D/20D/60D signal for every loaded instrument (including off-universe tickers)."""
    if ss.get("_sig_key") != stamp + str(wt):
        S_ = {k_: compute(P, stamp, n_, wt, tuple(ss.extra))[0] for k_, n_ in (("5D", 5), ("20D", 20), ("60D", 60))}
        ss["_sig"] = signal_frame(S_["5D"], S_["20D"], S_["60D"]).join(S_["20D"][["CMF raw", "MFI raw", "RVOL", "RS vs Peers", "Last"]])
        ss["_sig_key"] = stamp + str(wt)
    return ss["_sig"]


def ml_today():
    """The forecast model if it has already been trained for today's data in this session, else None (never trains)."""
    return ss.get("_ml") if ss.get("_ml_key") == f"ml|{P['Close'].index[-1].date()}|{P['Close'].shape}" else None


def pf_advice(pf: dict, pos_df: pd.DataFrame) -> pd.DataFrame:
    """Sell signals. Transparent risk-management rules, checked in this order:
       VERKOPEN       stop-loss hit · trailing stop hit · money flow negative on 5 AND 20 days · outflow on all horizons
       HERBEOORDELEN  20-day flow below zero · inflow fading · holding period elapsed · model expects under-performance
       HOUDEN         none of the above
    They limit losses and enforce discipline; they are not proven to predict prices."""
    if pos_df.empty:
        return pos_df
    if demo:                                         # no advice on synthetic data
        out = pos_df.copy()
        out.insert(1, "Advies", "—")
        out["Score 20D"], out["Reden"] = np.nan, "niet beschikbaar bij demo-data"
        return out
    sg, ml_ = all_signals(), ml_today()
    stop, trail, hor = pf.get("stop_pct", 10.0), pf.get("trail_pct", 15.0), pf.get("horizon_days", 60)
    adv, why, s20 = [], [], []
    for t, r in pos_df.iterrows():
        sell, review = [], []
        g = sg.loc[t] if t in sg.index else None
        if r["Resultaat %"] <= -stop:
            sell.append(f"stop-loss: {r['Resultaat %']:+.1f}% (grens −{stop:.0f}%)")
        if r["Van top %"] <= -trail:
            sell.append(f"{r['Van top %']:+.1f}% onder de hoogste koers sinds aankoop (grens −{trail:.0f}%)")
        if g is not None:
            if g["20D"] < -15 and g["5D"] < 0:
                sell.append(f"geldstroom negatief op 5 en 20 dagen ({g['5D']:+.0f} / {g['20D']:+.0f})")
            elif g["Totaal"] < -25:
                sell.append(f"uitstroom over alle termijnen (totaal {g['Totaal']:+.0f})")
            elif g["20D"] < 0:
                review.append(f"20-daagse geldstroom onder nul ({g['20D']:+.0f})")
            elif g["Fase"] == "verzwakt" and g["Totaal"] < 10:
                review.append("instroom verzwakt")
        if r["Dagen"] >= hor:
            review.append(f"aanhoudperiode van {hor} handelsdagen verstreken")
        if ml_ is not None and t in ml_["forecast"].index and ml_["forecast"][t] < -60:
            review.append(f"model verwacht ondergemiddeld rendement ({ml_['forecast'][t]:+.0f})")
        adv.append("VERKOPEN" if sell else "HERBEOORDELEN" if review else "HOUDEN")
        why.append("; ".join(sell + review) or "geldstroom positief, geen grens geraakt")
        s20.append(float(g["20D"]) if g is not None else np.nan)
    out = pos_df.copy()
    out.insert(1, "Advies", adv)
    out["Score 20D"], out["Reden"] = s20, why
    return out


def analyst_select(scope, n_pick: int, ml):
    """Shared selection logic of the analyst (used by the popup and by the daily memory log)."""
    d = all_signals()
    d = d[d.index.isin(META.index)].copy()
    proven = ml_verdict(ml)[1]
    d["Model"] = ml["forecast"].reindex(d.index) if ml else np.nan
    d["Vol %"] = P["Close"][d.index].pct_change(fill_method=None).tail(60).std() * np.sqrt(252) * 100
    w_m = 0.6 if proven else 0.3                                   # lean on the model only when it has earned it
    d["Kans"] = w_m * d["Model"].fillna(0) + (1 - w_m) * d["Totaal"]
    if scope == "core":
        d = d[META["core"].reindex(d.index).fillna(False)]
    elif scope:
        d = d[d["Class"] == scope]
    d = d[~d["Class"].isin(["Cash", "Futures & Vol", "Indices"]) & ~d["Group"].isin(["Spot Pairs", "Volatility"])]   # things you can actually buy and hold
    picks = d[(d["Kans"] > 15) & (d["Totaal"] > 5) & (d["20D"] > 0) & (d["MFI raw"] < 90)].sort_values("Kans", ascending=False).head(n_pick)
    wgt = pd.Series(dtype=float)
    if not picks.empty:
        inv = 1 / picks["Vol %"].clip(lower=5)
        wgt = (inv / inv.sum() * 100).clip(upper=35)
        wgt = wgt / wgt.sum() * 100
    avoid = d[(d["Kans"] < -20) & (d["20D"] < 0)].sort_values("Kans").head(n_pick)
    return d, picks, wgt, avoid, proven


def remember():
    """Write today's state to memory (once per trading day, and again when the model becomes available)."""
    bar = str(P["Close"].index[-1].date())
    ml_ = ml_today()
    flag = (bar, ml_ is not None, P["Close"].shape[1], mode)
    if demo or ss.get("_remembered") == flag:
        return
    sg = all_signals()
    mdl = ml_["forecast"].reindex(sg.index) if ml_ else pd.Series(np.nan, index=sg.index)
    f = lambda v: None if pd.isna(v) else float(v)
    mem_write("INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?,?,?,?,?,?)",
              [(bar, t, f(r["Last"]), f(r["5D"]), f(r["20D"]), f(r["60D"]), f(r["Totaal"]), r["Signaal"], r["Fase"], f(mdl[t])) for t, r in sg.iterrows()])
    for lab, sc in SCOPES.items():
        _, picks, wgt, _, _ = analyst_select(sc, 5, ml_)
        mem_write("DELETE FROM analyst_log WHERE date=? AND scope=?", [(bar, lab)])
        mem_write("INSERT OR REPLACE INTO analyst_log VALUES (?,?,?,?,?,?,?,?)",
                  [(bar, lab, i, t, float(r["Kans"]), float(wgt[t]), f(r["Last"]), int(ml_ is not None)) for i, (t, r) in enumerate(picks.iterrows(), 1)])
    if ml_:
        b_, h_ = ml_["best"], ml_["best"]["hold"]
        verdict = ml_verdict(ml_)[0]
        mem_write("INSERT OR REPLACE INTO model_log VALUES (?,?,?,?,?,?,?,?,?)",
                  [(bar, b_["h"], b_["depth"], b_["val"]["ic_t"], h_["ic"], h_["ic_t"], h_["n"], h_["spread"], verdict)])
    ss["_remembered"] = flag


def get_quant():
    """Quant score and its test for today's data. Needs get_ml() to have run first (it loads the real-flow sources)."""
    xf_ = ss.get("_xf") or {}
    qk = f"{stamp}|{','.join(xf_)}"
    score, signed = quant_score(P, xf_, qk)
    res, by_factor, by_part = quant_test(P, score, signed, qk)
    prim = next(r for r in res if r["h"] == QUANT_PRIMARY_H)
    halves = by_part[by_part["Deel"].str.contains("helft")]
    proven = bool(prim["t"] > 2 and prim["spread"] > 0 and (halves["Top−bodem %"] > 0).all())
    now = (score.iloc[-1].rank(pct=True) - 0.5) * 200
    return {"now": now, "res": res, "by_factor": by_factor, "by_part": by_part, "proven": proven, "prim": prim}


def get_ml():
    """Train (or load from disk) the forecast model once per trading day."""
    mk = f"ml|{P['Close'].index[-1].date()}|{P['Close'].shape}"
    if ss.get("_ml_key") != mk:
        with st.spinner("Echte geldstroomdata ophalen en model trainen op 10 jaar data… De allereerste keer duurt dit 10–15 minuten "
                        "(short-posities, aandelenaantallen en fondsstromen worden eenmalig gedownload); daarna eens per handelsdag ±3 minuten."):
            fred_ = {} if demo else fetch_fred()
            cot_ = None if demo else fetch_cot_history()
            mac_ = macro_features(P, fred_, cot_)
            xf_, xm_, ss["_src_status"] = ({}, pd.DataFrame(index=P["Close"].index), {}) if demo else \
                source_features(P, [c for c in P["Close"].columns if c in META.index])
            ss["_xf"] = xf_
            ss["_ml"], ss["_ml_key"] = ml_forecast(P, pd.concat([mac_, xm_], axis=1), xf_), mk
    return ss["_ml"]


@st.dialog("Analist · wat zegt alle data samen?", width="large")
def analyst():
    """Rule-based analyst: combines the forecast model, flow signals on three horizons, market regime,
    volume and volatility into a ranked shortlist with reasons, cautions and a sizing suggestion."""
    ml = get_ml()
    reg_ = regime_table(P, 20)
    rs_ = float(reg_["Vote"].mean()) if len(reg_) else 0.0
    H = ml["best"]["h"] if ml else 20
    c1_, c2_ = st.columns([3, 1])
    with c1_:
        scope = SCOPES[st.radio("Waar zoeken", list(SCOPES), horizontal=True, key="an_scope", label_visibility="collapsed")]
    with c2_:
        n_pick = st.select_slider("Aantal ideeën", [3, 5, 8, 10], value=5, key="an_n")
    d, picks, wgt, avoid, proven = analyst_select(scope, n_pick, ml)

    klimaat = ("risk-on: beleggers zoeken risico op" if rs_ > 15 else "risk-off: beleggers mijden risico" if rs_ < -15 else "gemengd: geen duidelijke richting")
    if ml:
        hd_ = ml["best"]["hold"]
        mtxt = (f"Het voorspelmodel is op ongeziene data <b style='color:{GREEN}'>aantoonbaar voorspellend</b> (t = {hd_['ic_t']:+.1f}); het weegt hieronder voor 60% mee."
                if proven else
                f"Het voorspelmodel is op ongeziene data <b style='color:{AMBER}'>niet overtuigend</b> (t = {hd_['ic_t']:+.1f}); het weegt hieronder daarom maar voor 30% mee en de geldstromen voor 70%.")
    else:
        mtxt = "Het voorspelmodel is niet beschikbaar; de selectie steunt alleen op geldstromen."
    st.markdown(f"<div class='kpi' style='font-family:{MONO};font-size:12.5px;line-height:1.8'><b>Marktbeeld.</b> Klimaat: "
                f"<span style='color:{col(rs_)}'>{klimaat}</span> (meter {rs_:+.0f}). {(d['Totaal'] > 10).mean() * 100:.0f}% van de bekeken instrumenten heeft "
                f"netto instroom. {mtxt}</div>", unsafe_allow_html=True)

    if picks.empty:
        st.warning("Geen enkel instrument voldoet nu aan de eisen (positieve geldstroom op middellange termijn, positieve modelverwachting, niet oververhit). "
                   "Dat is ook een uitkomst: de data geeft op dit moment geen koopkandidaten in deze selectie.")
    else:
        st.markdown(f"<div class='sec'>Koopkandidaten · horizon ± {H} handelsdagen</div>", unsafe_allow_html=True)
        PR_an = pattern_results(pat_key())
        AL_an = alarm_now(pat_key())
        if AL_an and AL_an["level"] >= 1:
            st.markdown(f"<div class='banner' style='border-color:{RED if AL_an['level'] == 2 else AMBER};color:{RED if AL_an['level'] == 2 else AMBER}'>"
                        f"MARKTALARM {alarm.NAMES[AL_an['level']]} · {alarm.ADVICE[AL_an['level']]}</div>", unsafe_allow_html=True)
        for i_, (t_, r_) in enumerate(picks.iterrows(), 1):
            why, warn = [], []
            if pd.notna(r_["Model"]) and r_["Model"] > 20:
                why.append(f"het model verwacht bovengemiddeld rendement (modelscore {r_['Model']:+.0f})")
            elif pd.notna(r_["Model"]) and r_["Model"] < -20:
                warn.append(f"het model verwacht ondergemiddeld rendement (modelscore {r_['Model']:+.0f})")
            if min(r_["5D"], r_["20D"], r_["60D"]) > 10:
                why.append(f"instroom op alle termijnen (5D {r_['5D']:+.0f} · 20D {r_['20D']:+.0f} · 60D {r_['60D']:+.0f})")
            else:
                why.append(f"instroom op middellange termijn (20D {r_['20D']:+.0f}, 60D {r_['60D']:+.0f}, 5D {r_['5D']:+.0f})")
            if r_["Fase"] == "versnelt":
                why.append("de instroom versnelt")
            if r_["RVOL"] > 1.25:
                why.append(f"handelsvolume {r_['RVOL']:.1f}× normaal")
            if r_["RS vs Peers"] > 25:
                why.append("sterker dan zijn groep")
            if r_["Fase"] == "verzwakt":
                warn.append("de instroom verzwakt op korte termijn")
            if r_["MFI raw"] > 80:
                warn.append(f"al veel gekocht (MFI {r_['MFI raw']:.0f}); wacht liever een terugval af of stap in delen in")
            if r_["Vol %"] > 40:
                warn.append(f"beweeglijk ({r_['Vol %']:.0f}% per jaar), daarom een kleiner gewicht")
            try:                                   # context from outside the flow data: results due, valuation, patterns, market alarm
                de_ = days_to_earnings(t_)
                if de_ is not None and de_ <= 7:
                    warn.append(f"winstcijfers over {de_} dag(en): de koers kan dan veel sterker bewegen dan normaal")
                if is_cheap(t_):
                    warn.append("goedkoop volgens de balans én sterke instroom: die combinatie deed het in onze toets slechter dan de sector")
                for pid_, ptxt_ in (("azmom", "momentum en inkoop"), ("azearn", "doorloop na winstcijfers")):
                    pst_ = (PR_an or {}).get(pid_, {}).get("state", {})
                    if t_ in pst_.get("longs", []):
                        (why if pat_status(pid_)[0] == "LIVE BEVESTIGD" else warn).append(f"staat in de bovenste groep van het patroon '{ptxt_}' ({pat_status(pid_)[0].lower()})")
                    if t_ in pst_.get("shorts", []):
                        warn.append(f"staat in de onderste groep van het patroon '{ptxt_}'")
            except Exception:
                pass
            if r_["Class"] in ("Europe Stocks", "Asia Stocks"):
                warn.append("noteert in lokale valuta en op een buitenlandse beurs; controleer kosten en handelstijden bij je broker")
            st.markdown(f"<div class='kpi' style='font-family:{MONO};font-size:12.5px;line-height:1.7;margin-bottom:6px'>"
                        f"<b style='color:{GREEN};font-size:15px'>{i_}. {t_}</b>" + (f" · <b>{r_['Name']}</b>" if r_['Name'] != t_ else "") + f" · {r_['Group']} · koers {r_['Last']:,.2f} · "
                        f"voorgesteld gewicht <b>{wgt[t_]:.0f}%</b> van het bedrag dat je hiervoor reserveert<br>"
                        f"<span style='color:{GREEN}'>Waarom:</span> {'; '.join(why)}.<br>"
                        + (f"<span style='color:{AMBER}'>Let op:</span> {'; '.join(warn)}." if warn else f"<span style='color:{DIM}'>Geen bijzondere aandachtspunten in de data.</span>")
                        + "</div>", unsafe_allow_html=True)
    if not picks.empty:
        b1_, b2_ = st.columns([1, 2])
        with b1_:
            amt_ = st.number_input(f"Bedrag ({pf_load()['base']})", 100, 10_000_000, 10_000, 500, key="an_amt", label_visibility="collapsed")
        with b2_:
            if st.button(f"Koop deze selectie op papier (demo) voor het bedrag hiernaast", width="stretch"):
                pf_ = pf_load()
                msgs = [pf_trade(pf_, t_, "KOOP", amount=amt_ * wgt[t_] / 100) for t_ in picks.index]
                ss["_pf_msg"] = " · ".join(msgs)
                goto(None, "PORTEFEUILLE")
                st.rerun()
    if len(avoid):
        st.markdown("<div class='sec'>Nu liever niet · sterkste uitstroom en zwakste verwachting</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi' style='font-family:{MONO};font-size:12.5px;line-height:1.8'>" + " · ".join(
            f"<b style='color:{RED}'>{t_}</b> {r_['Name']} ({r_['Kans']:+.0f})" for t_, r_ in avoid.iterrows()) + "</div>", unsafe_allow_html=True)
    st.markdown("<div class='sec'>Hoe pak je het aan</div>", unsafe_allow_html=True)
    st.markdown(f"""<div class='kpi' style='font-family:{MONO};font-size:12.5px;line-height:1.8'>
<b>1. Spreid.</b> Verdeel over meerdere kandidaten volgens de voorgestelde gewichten. Die zijn omgekeerd evenredig met de beweeglijkheid: rustige instrumenten krijgen meer, wilde minder.<br>
<b>2. Zet alleen geld in dat je kunt missen.</b> Houd het deel dat je op deze signalen inzet klein ten opzichte van je totale vermogen.<br>
<b>3. Stap gefaseerd in.</b> Koop bijvoorbeeld in twee of drie delen over enkele dagen, met limietorders in plaats van marktorders.<br>
<b>4. Houd de horizon aan.</b> De verwachting geldt voor ongeveer {H} handelsdagen. Open de analist daarna opnieuw en herbeoordeel.<br>
<b>5. Bepaal vooraf je uitstap.</b> Verkoop of verklein als het instrument uit deze lijst verdwijnt en zijn 20D-score onder nul zakt, of als je vooraf gekozen verliesgrens bereikt is.<br>
<b>6. Tel de kosten mee.</b> Transactiekosten, wisselkoersen en belasting zitten niet in de toetsen van deze app.<br>
<span style='color:{DIM}'>Deze analist is een rekenregel op koers-, volume- en marktdata. Hij kent je vermogen, doelen en risico niet en leest geen nieuws.
Ook een aantoonbaar voorspellend model heeft een kleine statistische voorsprong over veel posities, geen zekerheid per aankoop. Dit is geen persoonlijk beleggingsadvies.</span></div>""",
                unsafe_allow_html=True)


# ── Qtron: market alarm, instrument context, benchmark ───────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def alarm_now(key: str):
    """Current market alarm (level 0/1/2, component dict, date). Uses its own small download so the three-month VIX is included."""
    off = key.startswith("demo") or os.environ.get("MFCC_OFFLINE") == "1"
    C_ = None
    if not off:
        px_ = feeds.prices(alarm.TICKERS, period="2y")
        C_ = px_["C"] if px_ is not None and "SPY" in px_["C"].columns else None
        if C_ is not None:
            store.disk_save("alarm_px.pkl", C_)
    if C_ is None:
        C_ = store.disk("alarm_px.pkl")
    if C_ is None or "SPY" not in C_.columns:
        return None
    lvl, comp = alarm.state(C_)
    lvl = lvl.dropna()
    if lvl.empty:
        return None
    since = lvl.index[(lvl != lvl.iloc[-1]).cumsum() == (lvl != lvl.iloc[-1]).cumsum().iloc[-1]][-1] if (lvl != lvl.iloc[-1]).any() else lvl.index[0]
    run = int((lvl[::-1] == lvl.iloc[-1]).cumprod().sum())
    return {"level": int(lvl.iloc[-1]), "parts": {k_: (None if pd.isna(v_) else bool(v_)) for k_, v_ in comp.iloc[-1].items()}, "date": str(lvl.index[-1].date()), "days": run}


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def inst_info(t: str):
    return feeds.instrument_info(t)


@st.cache_data(ttl=900, show_spinner=False)
def inst_news(t: str):
    return feeds.instrument_news(t)


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def inst_earnings(t: str):
    return feeds.next_earnings(t)


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def bench_series(base: str):
    """A world equity index fund in the portfolio's currency (MSCI World: IWDA.AS in euro, URTH in dollar)."""
    tk_ = "IWDA.AS" if base == "EUR" else "URTH"
    try:
        px_ = feeds.prices([tk_], period="5y")
        return px_["C"][tk_].dropna() if px_ is not None and tk_ in px_["C"].columns else None
    except Exception:
        return None


def days_to_earnings(t: str):
    if demo or t not in META.index or META.at[t, "cls"] not in STOCK_CLASSES:
        return None
    d_ = inst_earnings(t)
    if d_ is None:
        return None
    n_ = (pd.Timestamp(d_).normalize() - pd.Timestamp.now().normalize()).days
    return n_ if 0 <= n_ <= 60 else None


def is_cheap(t: str):
    """Rough 'cheap on the balance sheet' flag from today's Yahoo figures (used only for a caution note)."""
    i_ = inst_info(t) if not demo else {}
    pe, pb = i_.get("trailingPE"), i_.get("priceToBook")
    return bool(pe and pb and 0 < pe < 12 and 0 < pb < 1.5)


# ── Qtron: pattern tracker and collector glue ────────────────────────────────
def pat_key():
    return f"{'demo' if demo else 'live'}|{datetime.now():%Y-%m-%d %H}|{int(datetime.now().minute >= 30)}"


@st.cache_data(ttl=3600, show_spinner="Patronen doorrekenen…")
def pattern_results(key: str):
    """Every pattern evaluated on its full history. Index series are refreshed here; the heavy inputs (stock panel,
    share counts, earnings, funding) come from disk, where the collector maintains them."""
    off = key.startswith("demo") or os.environ.get("MFCC_OFFLINE") == "1"
    try:
        D = collector.build_D(max_age_h=1.0, offline=off, heavy=False)
        if D is None:
            return None
        res = collector.log_patterns(D) if not off else patterns.evaluate(D)
        return {k_: {"ret": v_["ret"], "state": v_["state"], "zones": v_["zones"]} for k_, v_ in res.items()}
    except Exception:
        return None


def pat_live(pid: str):
    """Statistics of the frozen forward log of one pattern, or None when nothing has been logged yet."""
    lg = mem_read("SELECT date, ret FROM pattern_log WHERE pattern=? ORDER BY date", (pid,))
    if not len(lg):
        return None
    return patterns.zone_stats(pd.Series(lg["ret"].values, index=pd.to_datetime(lg["date"])), ann=365 if pid == "carry" else 252)


def pat_status(pid: str):
    z = pat_live(pid)
    if z is None or z["active"] < 20:
        return "IN OBSERVATIE", DIM
    if pid != "carry" and z["t"] > 2:
        return "LIVE BEVESTIGD", GREEN
    return ("LIVE POSITIEF · NIET BEWEZEN", CYAN) if z["total_pct"] > 0 else ("LIVE NEGATIEF", RED)


def collector_last() -> dict:
    return mem_settings().get("collector_last") or {}


def ensure_collector(force: bool = False):
    """Start the collector in the background when it has not run today (the nightly timer normally does this)."""
    lock = CACHE_DIR / "collector.lock"
    try:
        if lock.exists() and time.time() - lock.stat().st_mtime < 3 * 3600:
            return False
        if not force and str(collector_last().get("at", ""))[:10] == f"{datetime.now():%Y-%m-%d}":
            return False
        CACHE_DIR.mkdir(exist_ok=True)
        lock.write_text(str(time.time()))
        import subprocess, sys
        subprocess.Popen([sys.executable, str(Path(__file__).with_name("collector.py"))], cwd=str(Path(__file__).parent),
                         stdout=open(CACHE_DIR / "collector.log", "a"), stderr=subprocess.STDOUT, start_new_session=True)
        return True
    except Exception:
        return False


if not demo and os.environ.get("MFCC_OFFLINE") != "1" and os.environ.get("QTRON_NO_COLLECT") != "1":
    ensure_collector()


# ════════════════════════════════════════════════════════════════════════════
# 7. VIEWS
# ════════════════════════════════════════════════════════════════════════════
# ── portfolio watch: sell signals are checked on every run and shown on every screen ──
try:
    _pf = pf_load()
    if _pf["positions"] and not demo:
        _adv = pf_advice(_pf, pf_value(_pf)[0])
        _flag = _adv[_adv["Advies"] != "HOUDEN"]
        if len(_flag):
            mem_write("INSERT OR REPLACE INTO sell_log VALUES (?,?,?,?)",
                      [(str(P["Close"].index[-1].date()), t_, r_["Advies"], r_["Reden"]) for t_, r_ in _flag.iterrows()])
        _sell = _adv.index[_adv["Advies"] == "VERKOPEN"].tolist()
        if _sell and view != "PORTEFEUILLE":
            gb1, gb2 = st.columns([5, 1])
            with gb1:
                st.markdown(f"<div class='banner' style='border-color:{RED};color:{RED};background:#1f0a10'>PORTEFEUILLE · verkoopsignaal voor "
                            f"{', '.join(_sell)}</div>", unsafe_allow_html=True)
            with gb2:
                st.button("Bekijk", on_click=goto, args=(None, "PORTEFEUILLE"), width="stretch", key="go_pf")
except Exception:
    pass

if open_analyst:
    analyst()

if view == "COCKPIT":
    s20 = compute(P, stamp, 20, wt, tuple(ss.extra))[0]
    s20 = s20[s20.index.isin(META.index)]
    sg = all_signals()
    sg = sg[sg.index.isin(META.index)]
    pt20 = pool_table(s20)
    reg20 = regime_table(P, 20)
    rs20 = float(reg20["Vote"].mean()) if len(reg20) else 0.0
    PR = pattern_results(pat_key())
    pf_ = pf_load()
    try:
        _, _, pf_tot = pf_value(pf_)
    except Exception:
        pf_tot = pf_["cash"]
    ml_ = ml_today()
    if ml_:
        mv, mv_sub = ml_verdict(ml_)[0], "vandaag getraind"
    else:
        ml_last = mem_read("SELECT date, verdict FROM model_log ORDER BY date DESC LIMIT 1")
        mv, mv_sub = (ml_last["verdict"].iloc[0], f"stand {ml_last['date'].iloc[0]}") if len(ml_last) else ("—", "open ONDERZOEK om te trainen")
    arch = store.archive_status()
    n_act = sum(1 for v in PR.values() if v["state"].get("active")) if PR else 0
    n_strong, n_up = int((sg["Signaal"] == "STERK ▲").sum()), int(sg["Signaal"].str.contains("▲").sum())
    k_ = st.columns(6)
    with k_[0]:
        kpi("Marktklimaat", "RISK-ON" if rs20 > 15 else "RISK-OFF" if rs20 < -15 else "GEMENGD", f"meter {rs20:+.0f} · 20 dagen", col(rs20))
    with k_[1]:
        kpi("Patronen actief", f"{n_act} / {len(patterns.PATTERNS)}" if PR else "—", "vandaag een positie volgens de regel", GREEN if n_act else DIM)
    with k_[2]:
        kpi("Koopsignalen stromen", f"{n_strong}", f"sterk · {n_up} positief van {len(sg)}", GREEN if n_strong else DIM)
    with k_[3]:
        kpi("Voorspelmodel", mv, mv_sub, GREEN if mv == "JA" else AMBER if mv in ("VEELBELOVEND", "ZWAK") else DIM)
    with k_[4]:
        kpi("Papieren portefeuille", f"{pf_tot:,.0f}".replace(",", "."), f"{(pf_tot / pf_['start'] - 1) * 100:+.2f}% · {len(pf_['positions'])} posities",
            GREEN if pf_tot >= pf_["start"] else RED)
    with k_[5]:
        kpi("Data-archief", f"{int(arch['dagen'].max()) if len(arch) else 0} dagen", f"{len(arch)} datasets · {arch['MB'].sum() if len(arch) else 0:.0f} MB", CYAN)

    AL = alarm_now(pat_key())
    if AL:
        ac_ = {0: GREEN, 1: AMBER, 2: RED}[AL["level"]]
        dots = " &nbsp; ".join(f"<span style='color:{RED if v_ else GREEN if v_ is not None else DIM}'>{'●' if v_ else '○'}</span> "
                               f"<span style='color:{TXT if v_ else DIM}'>{alarm.PARTS[k_]}</span>" for k_, v_ in AL["parts"].items())
        st.markdown(f"""<div class='kpi' style='font-family:{MONO};font-size:12.5px;line-height:1.7;border-left:4px solid {ac_};margin:8px 0'>
<b style='color:{ac_};font-size:15px'>MARKTALARM {alarm.NAMES[AL['level']]}</b> &nbsp;<span style='color:{DIM}'>sinds {AL['days']} handelsdag{'en' if AL['days'] != 1 else ''} · stand {AL['date']}</span>
&nbsp;·&nbsp; {alarm.ADVICE[AL['level']]}<br><span style='font-size:11.5px'>{dots}</span></div>""", unsafe_allow_html=True)
    with st.expander("Agenda · rentebesluiten en winstcijfers van je posities en volglijst"):
        ag = []
        for d_ in (feeds.fomc_dates() if not demo else []):
            n_ = (pd.Timestamp(d_).normalize() - pd.Timestamp.now().normalize()).days
            if 0 <= n_ <= 60:
                ag.append({"Datum": pd.Timestamp(d_).strftime("%d-%m-%Y"), "Over (dagen)": n_, "Wat": "Rentebesluit Amerikaanse centrale bank (20:00 onze tijd)", "Instrument": "alle markten"})
        for t_ in list(dict.fromkeys(list(pf_["positions"]) + list(ss.pins)))[:25]:
            n_ = days_to_earnings(t_)
            if n_ is not None and n_ <= 30:
                ag.append({"Datum": inst_earnings(t_).strftime("%d-%m-%Y"), "Over (dagen)": n_, "Wat": "Winstcijfers" + (" · in portefeuille" if t_ in pf_["positions"] else ""),
                           "Instrument": f"{t_} · {META.at[t_, 'name']}" if t_ in META.index else t_})
        if ag:
            st.dataframe(pd.DataFrame(ag).sort_values("Over (dagen)"), hide_index=True, width="stretch")
        else:
            st.caption("Geen rentebesluit of winstcijfers in de komende weken voor je posities en volglijst.")
        st.markdown("<div class='note'>Het marktalarm is getoetst op de S&P 500 sinds 1993. Bij ROOD was de kans op meer dan 10% verlies binnen 20 dagen 6,7%, tegenover 0,7% bij GROEN; "
                    "het gemiddelde rendement was bij ROOD niet lager, omdat scherpe hersteldagen in dezelfde toestand vallen. Uitstappen bij ORANJE of ROOD verkleinde het grootste verlies "
                    "van −55% naar −31%, maar kostte ongeveer 3,5 procentpunt rendement per jaar. Het alarm is dus een risicomaat, geen voorspelling.</div>", unsafe_allow_html=True)

    a, b = st.columns([1.25, 1])
    with a:
        sec(f"Vandaag · wat de vaste regels zeggen · stand {asof}")
        if not PR:
            st.info("Patroondata is nog niet beschikbaar. De verzamelaar haalt die op; dat gebeurt automatisch op de achtergrond.")
        else:
            html = ""
            for p_ in patterns.PATTERNS:
                st_ = PR[p_["id"]]["state"]
                on = bool(st_.get("active"))
                lab, lc = pat_status(p_["id"])
                html += (f"<div style='border-left:3px solid {GREEN if on else BORDER};padding:5px 10px;margin-bottom:6px;background:{PANEL}'>"
                         f"<span style='color:{GREEN if on else DIM};font-weight:700'>{'● ACTIEF' if on else '○ WACHT'}</span> &nbsp;<b>{p_['naam']}</b> "
                         f"<span style='color:{lc};font-size:10px'>&nbsp;{lab}</span><br>"
                         f"<span style='font-size:12px'>{st_.get('action', '')}</span><br><span style='color:{DIM};font-size:11px'>{st_.get('detail', '')[:230]}</span></div>")
            st.markdown(f"<div style='font-family:{MONO};font-size:12.5px;line-height:1.55'>{html}</div>", unsafe_allow_html=True)
            st.button("Open PATRONEN · uitleg, bewijs en uitvoering per regel", on_click=goto, args=(None, "PATRONEN"), key="ck_pat")
    with b:
        sec("Waar stroomt het geld · 20 dagen · per pool")
        show(bar_scores(pt20["Score"], h=390), key="ck_pool")
        into = [f"<b style='color:{GREEN}'>{p}</b>" for p in pt20.index[:3] if pt20.loc[p, "Score"] > 5]
        away = [f"<b style='color:{RED}'>{p}</b>" for p in pt20.index[::-1][:3] if pt20.loc[p, "Score"] < -5]
        st.markdown(f"<div class='note'>Naar: {', '.join(into) or '—'} &nbsp;·&nbsp; Weg uit: {', '.join(away) or '—'}</div>", unsafe_allow_html=True)
        st.button("Open GELDSTROMEN", on_click=goto, args=(None, "SIGNALEN"), key="ck_flow")

    CK = ["Name", "Class", "Signaal", "Fase", "5D", "20D", "60D", "Totaal", "Trend"]
    a, b = st.columns(2)
    with a:
        sec("Sterkste instroom · klik een rij voor details")
        pick = table(sg.sort_values("Totaal", ascending=False).head(10), "ck_in", 390, CK)
        if pick:
            goto(pick); st.rerun()
    with b:
        sec("Sterkste uitstroom · klik een rij voor details")
        pick = table(sg.sort_values("Totaal").head(10), "ck_out", 390, CK)
        if pick:
            goto(pick); st.rerun()

    sec("Hoe je Qtron gebruikt")
    cl = collector_last()
    st.markdown(f"""<div class='kpi' style='font-family:{MONO};font-size:12.5px;line-height:1.8'>
<b>1. COCKPIT</b> (dit scherm): elke dag de stand. Links de vaste regels die vandaag een positie voorschrijven, rechts waar het geld heen stroomt.<br>
<b>2. PATRONEN</b>: de zeven regels die uit ruim 2.300 geteste varianten overbleven. Per regel het bewijs, de uitvoering stap voor stap, de risico's en de live-score sinds de start.<br>
<b>3. PORTEFEUILLE</b>: probeer het eerst met papieren geld. Qtron bewaakt de posities en geeft verkoopsignalen.<br>
<b>4. ARCHIEF</b>: elke nacht legt de verzamelaar data vast die later nergens meer te krijgen is. Hoe langer Qtron draait, hoe meer er te toetsen valt.<br>
<span style='color:{AMBER}'>Stand van het bewijs: geen enkele regel is statistisch bewezen op ongeziene data. Ze hielden na hun zoekperiode wel hetzelfde teken.
De live-score vanaf vandaag is de echte toets; reken op maanden tot jaren voordat die iets bewijst.</span><br>
<span style='color:{DIM}'>Verzamelaar: {('laatste run ' + cl.get('at', '—') + f" · {cl.get('seconden', '?')} s") if cl else 'heeft nog niet gedraaid'}.
Hij draait elke nacht vanzelf, ook als dit venster dicht is, zolang de pc aan staat.</span></div>""", unsafe_allow_html=True)

elif view == "PATRONEN":
    PR = pattern_results(pat_key())
    if not PR:
        st.info("Patroondata is nog niet beschikbaar (Yahoo niet bereikbaar en nog niets op schijf). De verzamelaar probeert het opnieuw.")
    else:
        gl = collector.golive_dates()
        sec("Patronen · vaste regels uit het onderzoek, vanaf de startdatum live getoetst")
        st.markdown(f"<div class='note'>Vier onderzoeksrondes (ruim 2.300 varianten, 161.000 voorloop-combinaties, 15 databronnen) leverden deze regels op. "
                    f"<b>Zoek</b> = de periode waarin de regel gevonden is. <b>Toets</b> = latere data die bij het zoeken niet gebruikt is. "
                    f"<b>Live</b> = sinds Qtron de regel bevroor"
                    f"{(' op ' + min(gl.values())) if gl else ''}; alleen dat deel kan niet achteraf mooier gemaakt worden. "
                    f"t boven 2 geldt als statistisch overtuigend; geen enkele regel haalt dat in de toetsperiode. Rendementen zijn na kosten.</div>", unsafe_allow_html=True)
        rows_ = []
        for p_ in patterns.PATTERNS:
            v_ = PR[p_["id"]]
            z_ = v_["zones"]
            zl = pat_live(p_["id"])
            no_t = p_["id"] == "carry"
            rows_.append({"Patroon": p_["naam"], "Soort": p_["soort"], "Vandaag": "● ACTIEF" if v_["state"].get("active") else "○ wacht",
                          "Zoek %/jr": z_["zoek"]["ann_pct"], "Zoek t": np.nan if no_t else z_["zoek"]["t"],
                          "Toets %/jr": z_["toets"]["ann_pct"], "Toets t": np.nan if no_t else z_["toets"]["t"],
                          "Live dagen": zl["days"] if zl else 0, "Live %": zl["total_pct"] if zl else np.nan, "Status": pat_status(p_["id"])[0]})
        sb = pd.DataFrame(rows_).set_index("Patroon").drop(columns=["Soort"])
        for c_, f_ in (("Zoek %/jr", "{:+.1f}"), ("Zoek t", "{:+.1f}"), ("Toets %/jr", "{:+.1f}"), ("Toets t", "{:+.1f}"), ("Live %", "{:+.2f}")):
            sb[c_] = [("—" if pd.isna(v) else f_.format(v)) for v in sb[c_]]
        clr = lambda v: f"color:{GREEN}" if str(v).startswith("+") else f"color:{RED}" if str(v).startswith("-") else f"color:{DIM}"
        st.dataframe(sb.style.map(clr, subset=["Zoek %/jr", "Toets %/jr", "Live %"])
                     .map(lambda v: f"color:{GREEN};font-weight:700" if "ACTIEF" in str(v) else f"color:{DIM}", subset=["Vandaag"]),
                     width="stretch", height=38 * len(sb) + 40)

        names = [p_["naam"] for p_ in patterns.PATTERNS]
        pk = st.radio("Patroon", names, horizontal=True, key="pat_pick", label_visibility="collapsed")
        p_ = patterns.PATTERNS[names.index(pk)]
        v_ = PR[p_["id"]]
        r_, st_ = v_["ret"], v_["state"]
        on = bool(st_.get("active"))
        lab, lc = pat_status(p_["id"])
        st.markdown(f"""<div class='kpi' style='font-family:{MONO};font-size:13px;line-height:1.7;border-left:3px solid {GREEN if on else BORDER}'>
<b style='font-size:15px'>{p_['naam']}</b> &nbsp;<span style='color:{DIM}'>{p_['soort']}</span> &nbsp;<span style='color:{lc}'>{lab}</span><br>
{p_['kern']}<br>
<b style='color:{GREEN if on else DIM}'>{'● VANDAAG ACTIEF' if on else '○ VANDAAG GEEN POSITIE'}</b> · {st_.get('action', '')}<br>
<span style='color:{DIM};font-size:11.5px'>{st_.get('detail', '')}</span></div>""", unsafe_allow_html=True)

        a, b = st.columns([1.5, 1])
        with a:
            sec("Opgebouwd rendement na kosten · zoekperiode, toetsperiode en live")
            if len(r_):
                cum = r_.cumsum() * 100
                t1 = pd.Timestamp(p_["disc_end"])
                t2 = pd.Timestamp(gl.get(p_["id"], "2100-01-01"))
                fig = go.Figure()
                for nm_, seg_, c_ in (("zoekperiode", cum[cum.index <= t1], DIM), ("toetsperiode", cum[(cum.index >= t1) & (cum.index <= t2)], CYAN),
                                      ("live", cum[cum.index >= t2], GREEN)):
                    if len(seg_):
                        fig.add_trace(go.Scatter(x=seg_.index, y=seg_.values, mode="lines", name=nm_, line=dict(color=c_, width=2 if nm_ != "live" else 3),
                                                 hovertemplate="%{x|%d-%m-%Y}: %{y:+.1f}%<extra>" + nm_ + "</extra>"))
                fig.add_vline(x=t1, line_color=BORDER, line_dash="dot")
                if t2.year < 2100:
                    fig.add_vline(x=t2, line_color=GREEN, line_dash="dot")
                lay(fig, 340)
                fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.12, x=0, font=dict(size=10)))
                fig.update_yaxes(ticksuffix="%")
                show(fig, key="pat_cum")
                yr = r_.groupby(r_.index.year).sum() * 100
                yc = [DIM if y_ <= t1.year else CYAN for y_ in yr.index]
                fy = go.Figure(go.Bar(x=yr.index.astype(str), y=yr.values, marker_color=[c_ if v >= 0 else RED for c_, v in zip(yc, yr.values)],
                                      hovertemplate="%{x}: %{y:+.1f}%<extra></extra>"))
                lay(fy, 210, title=dict(text="per kalenderjaar · grijs = zoekperiode, blauw = daarna, rood = verliesjaar", font=dict(size=10, color=DIM)))
                fy.update_yaxes(ticksuffix="%")
                show(fy, key="pat_year")
            else:
                st.info("Voor dit patroon is de benodigde data nog niet opgehaald. De verzamelaar doet dat bij zijn eerstvolgende run.")
        with b:
            sec("Zo buit je het uit")
            st.markdown(f"<div class='kpi' style='font-family:{MONO};font-size:12.5px;line-height:1.7'>" +
                        "<br>".join(f"<b style='color:{GREEN}'>{i_}.</b> {s_}" for i_, s_ in enumerate(p_["uitbuiten"], 1)) + "</div>", unsafe_allow_html=True)
            sec("Risico's en beperkingen")
            st.markdown(f"<div class='kpi' style='font-family:{MONO};font-size:12.5px;line-height:1.7'>" +
                        "<br>".join(f"<b style='color:{AMBER}'>!</b> {s_}" for s_ in p_["risico"]) + "</div>", unsafe_allow_html=True)
            sec("Bewijs")
            z_ = v_["zones"]
            zl = pat_live(p_["id"])
            live_txt = (f"{zl['days']} dagen, waarvan {zl['active']} in positie · totaal {zl['total_pct']:+.2f}%" if zl else "nog geen afgeronde dagen")
            st.markdown(f"""<div class='kpi' style='font-family:{MONO};font-size:12px;line-height:1.7'>
<b>Onderzoek, zoekperiode:</b> {p_['zoek']}<br><b>Onderzoek, toetsperiode:</b> {p_['toets']}<br>
<b>Nagerekend door Qtron:</b> zoek {z_['zoek']['ann_pct']:+.1f}%/jr · toets {z_['toets']['ann_pct']:+.1f}%/jr
{'' if p_['id'] == 'carry' else f"(t = {z_['toets']['t']:+.1f})"} · slechtste dag {min(z_['zoek'].get('worst_day_pct', 0), z_['toets'].get('worst_day_pct', 0)):+.1f}%<br>
<b style='color:{GREEN}'>Live sinds {gl.get(p_['id'], '—')}:</b> {live_txt}</div>""", unsafe_allow_html=True)
            if st_.get("longs"):
                with st.expander(f"Selectie van deze maand · {len(st_['longs'])} bovenaan, {len(st_.get('shorts', []))} onderaan"):
                    nm = lambda t_: f"{t_} · {META.at[t_, 'name']}" if t_ in META.index else t_
                    st.markdown("**Bovenste groep (kopen):** " + ", ".join(nm(t_) for t_ in st_["longs"]))
                    st.markdown("**Onderste groep (mijden):** " + ", ".join(nm(t_) for t_ in st_.get("shorts", [])))

        sec("Signaallogboek · vastgelegd op het moment zelf, niet achteraf te wijzigen")
        lg = mem_read("SELECT date AS Datum, CASE active WHEN 1 THEN 'ACTIEF' ELSE 'wacht' END AS Stand, action AS Signaal, logged_at AS Vastgelegd "
                      "FROM pattern_signal WHERE pattern=? ORDER BY date DESC LIMIT 60", (p_["id"],))
        if len(lg):
            st.dataframe(lg, width="stretch", hide_index=True, height=min(300, 38 * len(lg) + 40))
        else:
            st.markdown("<div class='note'>Nog geen signalen vastgelegd.</div>", unsafe_allow_html=True)

        with st.expander("Kerkhof · patronen die echt bestonden en verdwenen zijn"):
            st.dataframe(pd.DataFrame(patterns.GRAVEYARD, columns=["Patroon", "Toen", "Nu", "Wat er gebeurde"]), width="stretch", hide_index=True)
            st.markdown("<div class='note'>De les: een patroon dat bekend wordt, wordt weggehandeld. Daarom bevriest Qtron de regels en meet het vanaf nu, "
                        "en daarom bouwt het archief aan data die anderen niet hebben.</div>", unsafe_allow_html=True)

elif view == "SIGNALEN":
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

    sig = scope_filter(sig, "scope_sig")
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
    ml = get_ml()
    qs = None
    if not demo:
        with st.spinner("Kwantscore berekenen en toetsen…"):
            try:
                qs = get_quant()
            except Exception:
                qs = None
    if qs:
        sec("Kwantscore · vaste regels uit gepubliceerd onderzoek · niets afgesteld op deze data")
        pr = qs["prim"]
        k_ = st.columns(5)
        with k_[0]:
            kpi(f"Voorspellend? · {QUANT_PRIMARY_H}D", "JA — AANTOONBAAR" if qs["proven"] else "ZWAK" if pr["spread"] > 0 else "NEE",
                f"{pr['n']} perioden · beide helften {'positief' if (qs['by_part'][qs['by_part']['Deel'].str.contains('helft')]['Top−bodem %'] > 0).all() else 'niet beide positief'}",
                GREEN if qs["proven"] else AMBER if pr["spread"] > 0 else RED)
        for i_, r_ in enumerate(qs["res"]):
            with k_[i_ + 1]:
                kpi(f"Top − bodem · {r_['h']} dagen", f"{r_['spread']:+.2f}%", f"t = {r_['t']:+.1f} · {r_['n']} perioden · {r_['hit']:.0f}% raak", col(r_["t"] * 30))
        with k_[4]:
            kpi("Factoren", f"{len(qs['by_factor'])} van {len(QUANT_FACTORS)}", "beschikbaar in de data")
        st.markdown("<div class='note'>De kwantscore telt acht bekende, in de wetenschappelijke literatuur beschreven effecten bij elkaar op, elk met het teken uit "
                    "het oorspronkelijke artikel en met gelijk gewicht. Er wordt niets geschat of afgesteld op deze data; daarom mag de hele periode 2017–2026 als "
                    f"toets dienen in plaats van alleen het laatste stuk. Het oordeel is vooraf vastgelegd op {QUANT_PRIMARY_H} dagen, alle aandelen samen: "
                    "t boven 2 én positief in beide helften van de periode. Rendement ten opzichte van de eigen sector of regio, instap op de slotkoers van de dag erna, "
                    "zonder kosten. Kanttekening: de aandelenlijst bevat alleen de grote bedrijven van vandaag.</div>", unsafe_allow_html=True)
        q1, q2, q3 = st.columns([1.15, 1.25, 1])
        with q1:
            sp_ = qs["prim"]["series"]
            cum = (sp_ * 5 / (QUANT_PRIMARY_H + 1)).cumsum() * 100
            fig = go.Figure(go.Scatter(x=cum.index, y=cum.values, line=dict(color=GREEN if cum.iloc[-1] > 0 else RED, width=1.8), fill="tozeroy",
                                       fillcolor="rgba(0,255,156,0.06)", hovertemplate="%{x|%b %Y}: %{y:+.1f}%<extra></extra>"))
            fig.add_hline(y=0, line=dict(color=BORDER))
            show(lay(fig, 300, title=dict(text=f"OPGETELD VERSCHIL TOP − BODEM · {QUANT_PRIMARY_H}D · hele periode (%, zonder kosten)", font=dict(size=11, color=DIM))))
        with q2:
            st.dataframe(qs["by_factor"].style.format({"Top−bodem %": "{:+.2f}", "t": "{:+.1f}"})
                         .map(lambda v: f"color:{GREEN}" if v > 2 else f"color:{RED}" if v < 0 else f"color:{AMBER}", subset=["t"]),
                         width="stretch", hide_index=True, height=300)
        with q3:
            st.dataframe(qs["by_part"].style.format({"Top−bodem %": "{:+.2f}", "t": "{:+.1f}"})
                         .map(lambda v: f"color:{GREEN}" if v > 2 else f"color:{RED}" if v < 0 else f"color:{AMBER}", subset=["t"]),
                         width="stretch", hide_index=True, height=300)
    if ml is None:
        st.info("Te weinig historie om een model te trainen en eerlijk te toetsen. In Live-modus wordt 10 jaar data gebruikt.")
    else:
        sec("Zelflerend model · leert uit het verleden welke patronen aan koersstijgingen voorafgingen")
        bst, hd, vl = ml["best"], ml["best"]["hold"], ml["best"]["val"]
        H = bst["h"]
        vd_, good = ml_verdict(ml)
        sig_ = vd_ == "VEELBELOVEND"
        v_txt, v_col = {"JA": ("JA — AANTOONBAAR", GREEN), "VEELBELOVEND": ("VEELBELOVEND", CYAN), "ZWAK": ("ZWAK", AMBER), "NEE": ("NEE", RED)}[vd_]
        k_ = st.columns(5)
        with k_[0]:
            kpi("Voorspellend? · eindtoets", v_txt, f"{hd['n']} ongeziene perioden van {H}D · hele periode t = {bst['all']['ic_t']:+.1f}", v_col)
        with k_[1]:
            kpi("Rangcorrelatie (IC)", f"{hd['ic']:+.3f}", f"t = {hd['ic_t']:+.1f} · overtuigend vanaf 2", col(hd["ic"] * 1000))
        with k_[2]:
            kpi("Top 20% min bodem 20%", f"{hd['spread']:+.2f}%", f"per {H}D t.o.v. sector/regio · t = {hd['spread_t']:+.1f}", col(hd["spread"] * 20))
        with k_[3]:
            kpi("Trefkans", f"{hd['hit']:.0f}%", "top versloeg bodem", col(hd["hit"] - 50))
        with k_[4]:
            kpi("Geleerd van", f"{ml['examples']:,}".replace(",", "."), f"voorbeelden sinds {ml['first']:%m/%Y}")
        st.markdown(f"<div class='note'>Model: {ml['model']} · {ml['n_inst']} instrumenten · {ml['n_feat']} kenmerken per instrument per dag "
                    f"(waarvan {len(ml['macro'])} marktbrede) · gekozen instelling: horizon {H} dagen, "
                    f"ensemble · afgesteld op {ml['test_from']:%b %Y} – {ml['split_date']:%b %Y} (validatie-IC {vl['ic']:+.3f}, t = {vl['ic_t']:+.1f}) · "
                    f"eindtoets vanaf {ml['split_date']:%b %Y} op data die bij het afstellen niet gebruikt is.</div>", unsafe_allow_html=True)
        al_ = bst.get("all")
        srcs = ss.get("_src_status") or {}
        st.markdown("<div class='note'>" + (f"Hele testperiode (afstellen + eindtoets samen, {al_['n']} perioden): IC {al_['ic']:+.3f}, t = {al_['ic_t']:+.1f}, "
                                            f"top−bodem {al_['spread']:+.2f}% (t = {al_['spread_t']:+.1f}). Dit getal is iets geflatteerd, omdat de horizon "
                                            "op een deel van deze periode gekozen is. " if al_ else "") +
                    "Echte databronnen in het model: " + (" · ".join(f"<b>{k_}</b> ({v_})" for k_, v_ in srcs.items()) or "geen (alleen koers en volume)") +
                    ".</div>", unsafe_allow_html=True)
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
            show(bar_scores(ml["relevance"].sort_values().pipe(lambda x: pd.concat([x.head(7), x.tail(7)])) * 1000, 320,
                            "WELKE KENMERKEN WOGEN MEE (samenhang ×1000)"))
        fc = compute(P, stamp, 20, wt, tuple(ss.extra))[0]
        fc = fc[fc.index.isin(ml["forecast"].index)][["Name", "Class", "Group", "Score", "Return %", "Trend"]].copy()
        fc["Model"] = ml["forecast"].reindex(fc.index)
        if qs:
            fc["Kwant"] = qs["now"].reindex(fc.index)
        fc = scope_filter(fc, "scope_ml")
        FCOLS = ["Name", "Group"] + (["Kwant"] if qs else []) + ["Model", "Score", "Return %", "Trend"]
        fc_sort = st.radio("Sorteer op", (["Kwant"] if qs else []) + ["Model"], horizontal=True, key="fc_sort", label_visibility="collapsed")
        a, b = st.columns(2)
        with a:
            sec("Hoogste verwachting · klik een rij voor details")
            pick = table(fc.sort_values(fc_sort, ascending=False).head(15), "ml_top", 560, FCOLS)
            if pick:
                goto(pick); st.rerun()
        with b:
            sec("Laagste verwachting · klik een rij voor details")
            pick = table(fc.sort_values(fc_sort).head(15), "ml_bot", 560, FCOLS)
            if pick:
                goto(pick); st.rerun()
        sec("Termijntoets · werkt ‘volg het geld’, en op welke termijn?")
        hz_scope = SCOPES[st.radio("Universum termijntoets", list(SCOPES), horizontal=True, key="hz_scope", label_visibility="collapsed")]
        with st.spinner("Termijntoets berekenen…"):
            hz = horizon_test(P, stamp, wt, hz_scope)
        if hz is None:
            st.info("Te weinig instrumenten of historie voor deze selectie.")
        else:
            lab_h = {1: "1 dag vooruit", 5: "5 dagen", 20: "20 dagen", 60: "60 dagen", 120: "120 dagen"}
            Z = hz.pivot(index="L", columns="h", values="t").reindex(index=HZ_LOOKBACKS, columns=HZ_FORWARD)
            SPm = hz.pivot(index="L", columns="h", values="spread").reindex(index=HZ_LOOKBACKS, columns=HZ_FORWARD)
            txt = [[("" if pd.isna(Z.loc[L, h]) else f"{'★ ' if (L, h) in HZ_HYPOTHESES else ''}{SPm.loc[L, h]:+.2f}%<br>t = {Z.loc[L, h]:+.1f}")
                    for h in HZ_FORWARD] for L in HZ_LOOKBACKS]
            h1_, h2_ = st.columns([1.25, 1])
            with h1_:
                fig = go.Figure(go.Heatmap(z=Z.values, x=[lab_h[h] for h in HZ_FORWARD], y=[f"Score over {L}D" for L in HZ_LOOKBACKS],
                                           colorscale=SCALE, zmin=-4, zmax=4, xgap=3, ygap=3, text=txt, texttemplate="%{text}", textfont=dict(size=12),
                                           colorbar=dict(title="t", thickness=10, tickfont=dict(size=9)), hoverinfo="skip"))
                lay(fig, 330, title=dict(text="HOOGSTE 20% SCORES MIN LAAGSTE 20% · rendement t.o.v. eigen sector/regio · ★ = vooraf vastgelegde hypothese",
                                         font=dict(size=11, color=DIM)))
                fig.update_yaxes(autorange="reversed")
                show(fig)
            with h2_:
                names_ = {(5, 5): "Korte termijn tegendraads: hoge 5D-score → láger rendement in de 5 dagen erna",
                          (60, 60): "Lange termijn meegaand: hoge 60D-score → hóger rendement in de 60 dagen erna",
                          (120, 120): "Zeer lange termijn meegaand: hoge 120D-score → hóger rendement in de 120 dagen erna"}
                lines = []
                for (L, h), sgn in HZ_HYPOTHESES.items():
                    r_ = hz[(hz["L"] == L) & (hz["h"] == h)]
                    if r_.empty:
                        lines.append(f"<b>{names_[(L, h)]}</b><br><span style='color:{DIM}'>te weinig meetmomenten</span>")
                        continue
                    r_ = r_.iloc[0]
                    okk = r_["t"] * sgn > 2.4
                    part = r_["t"] * sgn > 1
                    verdict_ = (f"<b style='color:{GREEN}'>ONDERSTEUND</b>" if okk else f"<b style='color:{AMBER}'>RICHTING KLOPT, NIET OVERTUIGEND</b>" if part
                                else f"<b style='color:{RED}'>NIET ONDERSTEUND</b>")
                    lines.append(f"<b>{names_[(L, h)]}</b><br>gemeten verschil {r_['spread']:+.2f}% · t = {r_['t']:+.1f} (per startmoment {r_['t_min']:+.1f} tot {r_['t_max']:+.1f}) · {int(r_['n'])} perioden · {verdict_}")
                # What drives it: the volume-based flow components, or plain price strength?
                w_flow = tuple(w if c in ("CMF", "MFI", "Flow Momentum") else 0 for c, w in zip(COMP_COLS, DEFAULT_WEIGHTS.values()))
                w_price = tuple(w if c in ("RS vs Peers", "RS vs Risk-On") else 0 for c, w in zip(COMP_COLS, DEFAULT_WEIGHTS.values()))
                hz_f, hz_p = horizon_test(P, stamp, w_flow, hz_scope), horizon_test(P, stamp, w_price, hz_scope)
                dec = []
                for (L, h) in HZ_HYPOTHESES:
                    cell = lambda d_: d_[(d_["L"] == L) & (d_["h"] == h)].iloc[0] if d_ is not None and len(d_[(d_["L"] == L) & (d_["h"] == h)]) else None
                    f_, p_ = cell(hz_f), cell(hz_p)
                    if f_ is not None and p_ is not None:
                        dec.append(f"{L}D → {h}D: alleen geldstroom {f_['spread']:+.2f}% (t = {f_['t']:+.1f}) · alleen koerssterkte {p_['spread']:+.2f}% (t = {p_['t']:+.1f})")
                lines.append("<b>Wat drijft het?</b> Dezelfde toets met alleen de volumegebaseerde geldstroomdelen (CMF, MFI, flow momentum) "
                             "en met alleen de koerssterkte (relatieve sterkte):<br>" + "<br>".join(dec))
                extra_ = hz[(hz["t"].abs() > 3) & ~hz.apply(lambda r: (r["L"], r["h"]) in HZ_HYPOTHESES, axis=1)]
                more = ("<br><br><b>Opvallend buiten de hypothesen</b> (|t| boven 3): " + ", ".join(
                    f"score {int(r['L'])}D → {int(r['h'])}D vooruit ({r['spread']:+.2f}%, t = {r['t']:+.1f})" for _, r in extra_.iterrows())
                        if len(extra_) else "<br><br>Buiten de drie hypothesen haalt geen enkele cel de strengere grens van |t| boven 3.")
                st.markdown(f"<div class='kpi' style='font-family:{MONO};font-size:12px;line-height:1.75'>" + "<br><br>".join(lines) + more +
                            f"<br><br><span style='color:{DIM}'>Groen = hoge scores deden het daarna beter, rood = slechter. Drie hypothesen zijn vooraf "
                            "vastgelegd en gelden als ondersteund vanaf |t| 2,4. De overige 17 cellen zijn verkennend; omdat er zoveel zijn, "
                            "telt daar pas |t| boven 3. Bij horizonten vanaf 20 dagen is de toets voor 4 startmomenten herhaald en gemiddeld. "
                            "Instap op de slotkoers van de dag na het signaal, zonder kosten.</span></div>", unsafe_allow_html=True)

        sec("Zelf-afstelling · alle geteste instellingen")
        st.dataframe(ml["trials"].style.format({"Validatie IC": "{:+.3f}", "Validatie t": "{:+.1f}", "Eindtoets IC": "{:+.3f}",
                                                "Eindtoets t": "{:+.1f}", "Eindtoets top−bodem %": "{:+.2f}"})
                     .map(lambda v: f"color:{GREEN}" if v > 2 else f"color:{RED}" if v < 0 else f"color:{AMBER}", subset=["Validatie t", "Eindtoets t"]),
                     width="stretch", hide_index=True)
        st.markdown(f"<div class='kpi' style='font-family:{MONO};font-size:12px;line-height:1.8'><b>Zo lees je dit.</b> "
                    "<b>Model</b> is een verwachte rangorde, geen koersdoel: +100 is de hoogste verwachting van het hele universum, −100 de laagste, "
                    "0 precies het midden. <b>Score</b> is de gewone 20-daagse geldstroomscore ter vergelijking.<br>"
                    "<b>Doel.</b> Het model voorspelt het rendement <i>ten opzichte van de eigen sector of regio</i>, gecorrigeerd voor beweeglijkheid. "
                    "Het hoeft dus niet te raden of de markt, de sector of de valuta stijgt.<br>"
                    "<b>Zelf-afstelling.</b> Het model probeert elke instelling in de tabel uit en kiest de beste op de <i>validatieperiode</i>. "
                    "Het oordeel bovenaan komt uit de <i>eindtoets</i>: een latere periode die bij het kiezen niet is gebruikt. Voor een JA moet het model "
                    "bovendien over de héle testperiode overtuigen; een model dat tijdens het afstellen niets leerde, telt niet als bewezen op één gunstig stuk. "
                    "Dat is bewust. Een model dat mag blijven sleutelen tot dezelfde testdata er goed uitziet, vindt altijd iets dat overtuigend lijkt, "
                    "ook in puur toeval, en faalt daarna met echt geld. Blijft het oordeel zwak, dan is dat de eerlijke uitkomst voor deze data.<br>"
                    "Het model traint en stelt zichzelf opnieuw af zodra er een nieuwe handelsdag aan data is; het resultaat wordt op schijf bewaard.<br>"
                    "<b>Kanttekening.</b> De aandelenlijst bestaat uit de grote bedrijven van vandaag. Bedrijven die in de afgelopen tien jaar zijn "
                    "verdwenen of gekrompen ontbreken, waardoor rendementen in de toets iets te rooskleurig zijn.</div>", unsafe_allow_html=True)

elif view == "PORTEFEUILLE":
    pf = pf_load()
    pos_df, invested, total = pf_value(pf)
    pos_df = pf_advice(pf, pos_df)
    today = datetime.now().strftime("%Y-%m-%d")
    if (pf["positions"] or pf["trades"]) and not demo:
        pf["history"][today] = round(total, 2)
        pf_save(pf)
    if demo:
        st.markdown("<div class='banner'>Er wordt demo-data getoond. De portefeuille is daarom alleen-lezen: posities staan op hun laatst bekende echte "
                    "koers, orders en verkoopsignalen zijn uitgeschakeld.</div>", unsafe_allow_html=True)
    B = pf["base"]
    res = total - pf["start"]
    cost_pct = pf["fee_pct"] + pf.get("tax_pct", 0.35) + pf.get("spread_pct", 0.05)
    sec("Papieren portefeuille · gesimuleerd geld, echte koersen · bewaard op deze pc")
    if ss.get("_pf_msg"):
        st.success(ss.pop("_pf_msg"))
    RK = risk.portfolio_risk(pos_df["Waarde"], P["Close"], total) if len(pos_df) else None
    k_ = st.columns(6)
    with k_[0]:
        kpi("Totale waarde", f"{total:,.0f} {B}", f"startkapitaal {pf['start']:,.0f}")
    with k_[1]:
        kpi("Resultaat", f"{res:+,.0f} {B}", f"{res / pf['start'] * 100:+.2f}% sinds start", col(res))
    with k_[2]:
        kpi("Belegd", f"{invested:,.0f} {B}", f"{invested / total * 100 if total else 0:.0f}% van totaal · {len(pos_df)} posities")
    with k_[3]:
        kpi("Cash", f"{pf['cash']:,.0f} {B}", "beschikbaar voor aankopen")
    with k_[4]:
        open_res = float(pos_df["Resultaat"].sum()) if len(pos_df) else 0.0
        kpi("Open / gerealiseerd", f"{open_res:+,.0f}", f"gerealiseerd {pf['realized']:+,.0f} (na kosten)", col(open_res))
    with k_[5]:
        kpi("Risico per dag", f"{RK['var95_pct'] * total / 100:,.0f} {B}" if RK else "—", "verlies dat op 1 van de 20 dagen overschreden wordt" if RK else "nog geen posities", AMBER)

    tb = st.tabs(["POSITIES", "HANDELEN", "RISICO", "DAGBOEK", "TEGENOVER DE INDEX", "INSTELLINGEN"])
    with tb[0]:
        if len(pos_df):
            pos_df["Gewicht %"] = pos_df["Waarde"] / total * 100
            sells_ = pos_df.index[pos_df["Advies"] == "VERKOPEN"].tolist()
            if sells_:
                sb1, sb2 = st.columns([3, 1])
                with sb1:
                    st.markdown(f"<div class='banner' style='border-color:{RED};color:{RED};background:#1f0a10'>VERKOOPSIGNAAL voor {', '.join(sells_)} — "
                                "zie de kolom Reden.</div>", unsafe_allow_html=True)
                with sb2:
                    if st.button("Verkoop deze op papier", width="stretch"):
                        ss["_pf_msg"] = " · ".join(pf_trade(pf, t_, "VERKOOP", reason="verkoopsignaal") for t_ in sells_)
                        st.rerun()
            show_df = pos_df[["Naam", "Advies", "Reden", "Resultaat %", "Resultaat", "Waarde", "Gewicht %", "Score 20D", "Van top %", "Dagen", "Aantal", "Aankoop", "Koers"]]
            adv_col = lambda v: f"color:{RED};font-weight:700" if v == "VERKOPEN" else f"color:{AMBER};font-weight:700" if v == "HERBEOORDELEN" else f"color:{GREEN};font-weight:700"
            ev = st.dataframe(show_df.style.map(lambda v: f"color:{GREEN}" if v > 0 else f"color:{RED}" if v < 0 else "", subset=["Resultaat", "Resultaat %", "Score 20D", "Van top %"])
                              .map(adv_col, subset=["Advies"]),
                              width="stretch", on_select="rerun", selection_mode="single-row", key="pf_pos", column_config={
                "Aantal": st.column_config.NumberColumn(format="%.2f"), "Aankoop": st.column_config.NumberColumn(f"Aankoop ({B})", format="%.2f"),
                "Koers": st.column_config.NumberColumn(f"Koers ({B})", format="%.2f"), "Waarde": st.column_config.NumberColumn(f"Waarde ({B})", format="%.0f"),
                "Resultaat": st.column_config.NumberColumn(format="%+.0f"), "Resultaat %": st.column_config.NumberColumn(format="%+.2f%%"),
                "Gewicht %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f%%"),
                "Score 20D": st.column_config.NumberColumn(format="%+.0f", help="Huidige geldstroomscore; onder nul is een signaal om te herbeoordelen"),
                "Van top %": st.column_config.NumberColumn(format="%+.1f%%", help="Afstand tot de hoogste koers sinds aankoop (voor de meeschuivende stop)"),
                "Dagen": st.column_config.NumberColumn(format="%d", help="Handelsdagen sinds de eerste aankoop"),
                "Reden": st.column_config.TextColumn(width="large")})
            rows_ = ev.selection.rows if ev and ev.selection else []
            pk = show_df.index[rows_[0]] if rows_ else None
            if pk != ss.get("_sel_pf_pos"):
                ss["_sel_pf_pos"] = pk
                if pk:
                    goto(pk); st.rerun()
            st.markdown(f"<div class='note'>Klik een rij voor de detailpagina. <b>Advies</b> volgt vaste regels. VERKOPEN: verlies groter dan {pf.get('stop_pct', 10):.0f}% · koers meer dan "
                        f"{pf.get('trail_pct', 15):.0f}% onder de top sinds aankoop · geldstroom negatief op 5 én 20 dagen · uitstroom over alle termijnen. "
                        f"HERBEOORDELEN: 20-daagse geldstroom onder nul · instroom verzwakt · langer dan {pf.get('horizon_days', 60)} handelsdagen in bezit · "
                        "model verwacht ondergemiddeld. Dit zijn regels om verlies te beperken; dat ze koersen voorspellen is niet aangetoond.</div>", unsafe_allow_html=True)
        else:
            st.info("Nog geen posities. Ga naar HANDELEN, of open de ANALIST en kies 'Koop deze selectie op papier'.")

    with tb[1]:
        o1, o2 = st.columns([1, 1.2])
        with o1:
            sec("Order plaatsen · uitvoering tegen de laatste koers")
            if demo:
                st.info("Orders zijn uitgeschakeld zolang er demo-data wordt getoond.")
            else:
                opts = list(snap.index)
                with st.form("order", clear_on_submit=False):
                    tkr = st.selectbox("Instrument", opts, index=opts.index(ss.ticker) if ss.ticker in opts else 0,
                                       format_func=lambda t: f"{t} · {META.loc[t, 'name']}" if t in META.index and META.loc[t, 'name'] != t else t)
                    side = st.radio("Actie", ["KOOP", "VERKOOP"], horizontal=True)
                    amount = st.number_input(f"Bedrag in {B} (bij koop)", 0.0, 1e9, 5000.0, 500.0)
                    qty_s = st.number_input("Aantal stuks (bij verkoop; 0 = alles)", 0.0, 1e12, 0.0)
                    why_ = st.text_input("Waarom deze order? (komt in je dagboek)", placeholder="bv. sterke instroom op alle termijnen, analist nr. 2")
                    if st.form_submit_button("Order uitvoeren", width="stretch", type="primary"):
                        ss["_pf_msg"] = pf_trade(pf, tkr, side, amount=amount, qty=(qty_s or None), reason=why_)
                        st.rerun()
            st.markdown(f"<div class='note'>Kosten per order {cost_pct:.2f}% (makelaar {pf['fee_pct']:.2f}% + beurstaks {pf.get('tax_pct', 0.35):.2f}% + halve spread "
                        f"{pf.get('spread_pct', 0.05):.2f}%) · koersen omgerekend naar {B} · uitvoering tegen de laatste, mogelijk vertraagde slotkoers.</div>", unsafe_allow_html=True)
        with o2:
            sec(f"Hoe groot mag de positie zijn? · {ss.ticker}")
            lv = risk.levels(P, ss.ticker)
            if lv:
                rp = st.slider("Risico per positie, in % van de portefeuille", 0.25, 3.0, float(pf.get("risk_pct", 1.0)), 0.25, key="pf_riskpct")
                amt = risk.size_by_risk(total, rp, lv["stop_pct"], float(pf.get("max_pos_pct", 15.0)))
                st.markdown(f"""<div class='kpi' style='font-family:{MONO};font-size:12.5px;line-height:1.8'>
Dagelijkse beweging (ATR): <b>{lv['atr_pct']:.1f}%</b> · stop op 2,5× die beweging: <b>{lv['stop_pct']:.1f}%</b> onder de koers<br>
Bij {rp:.2f}% risico hoort een positie van <b style='color:{GREEN};font-size:15px'>{amt:,.0f} {B}</b> ({amt / total * 100 if total else 0:.0f}% van de portefeuille)<br>
<span style='color:{DIM}'>Raakt de koers de stop, dan verlies je ongeveer {total * rp / 100:,.0f} {B}. Maximum per positie: {pf.get('max_pos_pct', 15.0):.0f}%.
Beweeglijke instrumenten krijgen zo vanzelf een kleinere positie.</span></div>""", unsafe_allow_html=True)
            else:
                st.caption("Kies eerst een instrument (zoekveld links of een rij in een tabel).")

    with tb[2]:
        if not RK:
            st.info("Het risicoscherm verschijnt zodra er posities zijn.")
        else:
            r_ = st.columns(5)
            with r_[0]:
                kpi("Beweeglijkheid", f"{RK['vol_pct']:.1f}%", "per jaar, hele portefeuille incl. cash")
            with r_[1]:
                kpi("Slechtste dag", f"{RK['worst_day_pct']:+.1f}%", f"{RK['worst_day_pct'] * total / 100:+,.0f} {B} · laatste 2 jaar", RED)
            with r_[2]:
                kpi("Slechtste 20 dagen", f"{RK['worst_20d_pct']:+.1f}%", f"{RK['worst_20d_pct'] * total / 100:+,.0f} {B}", RED)
            with r_[3]:
                kpi("Samenhang", f"{RK['avg_corr']:.2f}", "gemiddelde correlatie · boven 0,6 = weinig spreiding", AMBER if RK["avg_corr"] > .6 else GREEN)
            with r_[4]:
                kpi("Grootste positie", f"{RK['largest_pct']:.0f}%", RK["largest"], AMBER if RK["largest_pct"] > pf.get("max_pos_pct", 15.0) else GREEN)
            a, b = st.columns(2)
            with a:
                sec("Wat als · geschat effect op basis van de laatste 2 jaar")
                sc = RK["scenarios"][["Scenario", "Effect op portefeuille %", "Effect"]]
                st.dataframe(sc.style.map(lambda v: f"color:{GREEN}" if v > 0 else f"color:{RED}", subset=["Effect op portefeuille %", "Effect"]), hide_index=True, width="stretch",
                             column_config={"Effect op portefeuille %": st.column_config.NumberColumn(format="%+.1f%%"),
                                            "Effect": st.column_config.NumberColumn(f"Effect ({B})", format="%+.0f")})
                sec("Waar zit het risico · aandeel per positie")
                rs = RK["risk_share"].head(12)
                fig = go.Figure(go.Bar(x=rs.values[::-1], y=rs.index[::-1].astype(str), orientation="h", marker_color=CYAN, text=[f"{v:.0f}%" for v in rs.values[::-1]], textposition="outside"))
                show(lay(fig, 60 + 26 * len(rs)), key="pf_riskshare")
            with b:
                sec("Verdeling van het belegde deel")
                for lab_, ser_ in (("per categorie", pos_df["Waarde"].groupby([META.at[t_, "cls"] if t_ in META.index else "Overig" for t_ in pos_df.index]).sum()),
                                   ("per sector of land", pos_df["Waarde"].groupby([META.at[t_, "group"] if t_ in META.index else "Overig" for t_ in pos_df.index]).sum()),
                                   ("per munt", pos_df["Waarde"].groupby([ccy_of(t_) for t_ in pos_df.index]).sum())):
                    sh_ = (ser_ / ser_.sum() * 100).sort_values(ascending=False)
                    st.markdown(f"<div class='note'><b>{lab_}:</b> " + " · ".join(f"{k_} {v_:.0f}%" for k_, v_ in sh_.items()) + "</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='note' style='margin-top:10px'>Alle cijfers zijn schattingen uit de koersen van de laatste twee jaar met de huidige gewichten. "
                            "Wisselkoersbewegingen zitten er niet in. In een echte crisis bewegen posities sterker samen dan in rustige tijden: reken op meer verlies dan hier staat.</div>",
                            unsafe_allow_html=True)

    with tb[3]:
        sec("Dagboek · elke aankoop met je reden, en hoe het sindsdien ging")
        buys = [t_ for t_ in pf["trades"] if t_["actie"] == "KOOP"]
        if buys:
            bm = bench_series(B)
            jr = []
            for t_ in buys[::-1]:
                now_px = pf_price(pf, t_["ticker"])
                d0 = pd.Timestamp(t_["tijd"][:10])
                br = (bm.iloc[-1] / bm[bm.index >= d0].iloc[0] - 1) * 100 if bm is not None and (bm.index >= d0).any() else np.nan
                rr = (now_px / t_["koers"] - 1) * 100 if now_px and t_["koers"] else np.nan
                jr.append({"Datum": t_["tijd"], "Ticker": t_["ticker"], "Reden": t_.get("reden") or "—", "Score toen": t_.get("score20"), "Alarm toen": t_.get("alarm", "—"),
                           "Koers toen": t_["koers"], "Sindsdien %": rr, "Index %": br, "Verschil %": rr - br if pd.notna(br) else np.nan,
                           "Nog in bezit": "ja" if t_["ticker"] in pf["positions"] else "nee"})
            J = pd.DataFrame(jr)
            st.dataframe(J.style.map(lambda v: f"color:{GREEN}" if pd.notna(v) and v > 0 else f"color:{RED}" if pd.notna(v) and v < 0 else "", subset=["Sindsdien %", "Index %", "Verschil %"]),
                         hide_index=True, width="stretch", column_config={c_: st.column_config.NumberColumn(format="%+.1f") for c_ in ("Sindsdien %", "Index %", "Verschil %", "Score toen")}
                         | {"Reden": st.column_config.TextColumn(width="large")})
            ok_ = J["Verschil %"].dropna()
            if len(ok_):
                st.markdown(f"<div class='note'>{(ok_ > 0).sum()} van de {len(ok_)} aankopen deden het beter dan de wereldindex over dezelfde periode "
                            f"(gemiddeld verschil {ok_.mean():+.1f} procentpunt). Pas na enkele tientallen aankopen zegt dit iets over je selectie.</div>", unsafe_allow_html=True)
        else:
            st.caption("Nog geen aankopen. Vul bij elke order in waarom je koopt; hier zie je later of die reden klopte.")
        with st.expander("Alle transacties"):
            if pf["trades"]:
                st.dataframe(pd.DataFrame(pf["trades"])[::-1], width="stretch", hide_index=True, height=260)

    with tb[4]:
        sec("Portefeuille tegenover een wereldindex · beide op 100 gezet bij de start")
        hist = pd.Series(pf["history"], dtype=float)
        bm = bench_series(B)
        if len(hist) >= 2:
            hist.index = pd.to_datetime(hist.index)
            fig = go.Figure(go.Scatter(x=hist.index, y=hist.values / pf["start"] * 100, name="portefeuille", line=dict(color=GREEN, width=2.2), mode="lines+markers",
                                       hovertemplate="%{x|%d %b}: %{y:.1f}<extra>portefeuille</extra>"))
            if bm is not None and (bm.index >= hist.index[0]).any():
                b_ = bm[bm.index >= hist.index[0]]
                fig.add_trace(go.Scatter(x=b_.index, y=b_.values / b_.iloc[0] * 100, name="wereldindex", line=dict(color=DIM, width=1.6),
                                         hovertemplate="%{x|%d %b}: %{y:.1f}<extra>wereldindex</extra>"))
                diff = hist.iloc[-1] / pf["start"] * 100 - b_.iloc[-1] / b_.iloc[0] * 100
                st.markdown(f"<div class='note'>Portefeuille {hist.iloc[-1] / pf['start'] * 100 - 100:+.1f}% · wereldindex {b_.iloc[-1] / b_.iloc[0] * 100 - 100:+.1f}% · "
                            f"verschil <b style='color:{GREEN if diff >= 0 else RED}'>{diff:+.1f} procentpunt</b>. Alleen het verschil zegt iets over je keuzes; de rest is de markt.</div>",
                            unsafe_allow_html=True)
            fig.add_hline(y=100, line=dict(color=BORDER, dash="dot"))
            lay(fig, 360)
            fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.1, x=0))
            show(fig, key="pf_bench")
        else:
            st.info("De vergelijking verschijnt zodra de portefeuille op minstens twee verschillende dagen is bekeken.")

    with tb[5]:
        with st.form("pf_settings"):
            s1, s2 = st.columns(2)
            with s1:
                nb = st.selectbox("Basisvaluta", ["EUR", "USD"], index=["EUR", "USD"].index(B))
                ns = st.number_input("Startkapitaal", 1000.0, 1e9, float(pf["start"]), 1000.0)
                nf = st.number_input("Makelaarskosten % per order", 0.0, 5.0, float(pf["fee_pct"]), 0.05)
                ntax = st.number_input("Beurstaks % per order (België: 0,35 aandelen · 0,12 uitkerende ETF · 1,32 kapitaliserende ETF)", 0.0, 5.0, float(pf.get("tax_pct", 0.35)), 0.01)
                nspr = st.number_input("Halve spread % (verschil tussen bied- en laatprijs)", 0.0, 2.0, float(pf.get("spread_pct", 0.05)), 0.01)
            with s2:
                n_stop = st.number_input("Stop-loss: verkoopsignaal bij verlies van … %", 1.0, 90.0, float(pf.get("stop_pct", 10.0)), 1.0)
                n_trail = st.number_input("Meeschuivende stop: … % onder de top sinds aankoop", 1.0, 90.0, float(pf.get("trail_pct", 15.0)), 1.0)
                n_hor = st.number_input("Aanhoudperiode in handelsdagen (daarna herbeoordelen)", 1, 1000, int(pf.get("horizon_days", 60)), 5)
                n_risk = st.number_input("Risico per positie, % van de portefeuille", 0.25, 5.0, float(pf.get("risk_pct", 1.0)), 0.25)
                n_max = st.number_input("Maximum per positie, % van de portefeuille", 2.0, 100.0, float(pf.get("max_pos_pct", 15.0)), 1.0)
            sure = st.checkbox("Ja, wis alle posities en transacties en begin opnieuw")
            if st.form_submit_button("Opslaan / opnieuw beginnen", width="stretch"):
                if sure:
                    pf = {"base": nb, "start": ns, "cash": ns, "fee_pct": nf, "realized": 0.0, "positions": {}, "trades": [], "history": {}}
                    ss["_pf_msg"] = "Portefeuille opnieuw gestart."
                else:
                    pf["fee_pct"] = nf
                    ss["_pf_msg"] = "Instellingen opgeslagen. Basisvaluta en startkapitaal wijzigen alleen bij opnieuw beginnen (vink het vakje aan)."
                pf.update({"stop_pct": n_stop, "trail_pct": n_trail, "horizon_days": int(n_hor), "tax_pct": ntax, "spread_pct": nspr, "risk_pct": n_risk, "max_pos_pct": n_max})
                pf_save(pf)
                st.rerun()

elif view == "ECHTE STROMEN":
    sec("Echte geldstromen · wat er werkelijk in en uit fondsen stroomde (SPDR · dagelijkse uitgifte en inname van aandelen)")
    if demo:
        st.info("Echte stromen zijn niet beschikbaar in demo-modus.")
        sp = None
    else:
        with st.spinner("Fondsgegevens van State Street ophalen… (eerste keer ±1 minuut, daarna van schijf)"):
            sp = load_spdr()
        if sp is None:
            st.info("De fondsgegevens konden niet worden opgehaald (ssga.com niet bereikbaar). Probeer het later opnieuw.")
    if sp is not None:
        funds_ = list(sp["so"].columns)
        tna_now = sp["tna"].ffill().iloc[-1]
        fl_usd = sp["so"].diff() * sp["nav"]
        tab = pd.DataFrame({"Fonds": [SPDR_FUNDS[f][0] for f in funds_], "Soort": [SPDR_FUNDS[f][1] for f in funds_]}, index=funds_)
        tab["Vermogen $ mrd"] = tna_now / 1e9
        for n_ in (5, 20, 60, 120):
            tab[f"{n_}D %"] = spdr_flow_pct(sp, n_).ffill(limit=3).iloc[-1]
        tab["20D $ mln"] = fl_usd.rolling(20, min_periods=10).sum().ffill(limit=3).iloc[-1] / 1e6
        tab.index.name = "Ticker"
        eq_ = tab["Soort"] != "Bonds"
        k_ = st.columns(5)
        with k_[0]:
            v_ = tab.loc[eq_, "20D $ mln"].sum() / 1e3
            kpi("Aandelenfondsen · 20D", f"{v_:+,.1f} mrd $", "netto in- of uitstroom", col(v_ * 10))
        with k_[1]:
            v_ = tab.loc[~eq_, "20D $ mln"].sum() / 1e3
            kpi("Obligatiefondsen · 20D", f"{v_:+,.1f} mrd $", "netto in- of uitstroom", col(v_ * 10))
        with k_[2]:
            t_ = tab["20D %"].idxmax()
            kpi("Sterkste instroom", t_, f"{tab.loc[t_, 'Fonds']} · {tab.loc[t_, '20D %']:+.1f}% van vermogen", GREEN)
        with k_[3]:
            t_ = tab["20D %"].idxmin()
            kpi("Sterkste uitstroom", t_, f"{tab.loc[t_, 'Fonds']} · {tab.loc[t_, '20D %']:+.1f}% van vermogen", RED)
        with k_[4]:
            kpi("Fondsen · stand", f"{len(funds_)}", f"t/m {sp['so'].index[-1]:%d-%m-%Y}")
        st.markdown("<div class='note'>Dit zijn geen afgeleide maar gemeten stromen. Een ETF geeft nieuwe aandelen uit als er netto geld binnenkomt en "
                    "trekt ze in als er geld uitgaat; State Street publiceert het aantal uitstaande aandelen per dag. Stroom = verandering in aantal × "
                    "intrinsieke waarde, als percentage van het fondsvermogen aan het begin van de periode. De cijfers lopen één handelsdag achter. "
                    "Ze dekken alleen SPDR-fondsen; andere fondshuizen stellen deze historie niet vrij beschikbaar. <b>Let op:</b> bij XRT, XOP, KRE, XBI, XHB en XSD "
                    "zijn grote sprongen meestal geen beleggersvraag: daar worden fondsaandelen aangemaakt om uit te lenen aan short-verkopers.</div>", unsafe_allow_html=True)
        f1, f2 = st.columns([1, 1.5])
        with f1:
            by_b = tab.groupby("Soort")["20D $ mln"].sum() / 1e3
            fig = go.Figure(go.Bar(x=by_b.sort_values().values, y=by_b.sort_values().index, orientation="h",
                                   marker_color=[GREEN if v > 0 else RED for v in by_b.sort_values().values],
                                   text=[f"{v:+,.1f}" for v in by_b.sort_values().values], textposition="outside", cliponaxis=False))
            show(lay(fig, 300, title=dict(text="NETTO STROOM PER SOORT · 20 DAGEN · miljard $", font=dict(size=11, color=DIM))))
            top_ = pd.concat([tab.nsmallest(8, "20D %"), tab.nlargest(8, "20D %")[::-1]])["20D %"]
            fig = go.Figure(go.Bar(x=top_.values, y=[f"{t} · {SPDR_FUNDS[t][0]}" for t in top_.index], orientation="h",
                                   marker_color=[GREEN if v > 0 else RED for v in top_.values],
                                   text=[f"{v:+.1f}%" for v in top_.values], textposition="outside", cliponaxis=False))
            show(lay(fig, 470, title=dict(text="GROOTSTE IN- EN UITSTROOM · 20 DAGEN · % van fondsvermogen", font=dict(size=11, color=DIM))))
        with f2:
            pct_cols = ["5D %", "20D %", "60D %", "120D %"]
            st.dataframe(tab.sort_values(["Soort", "20D %"], ascending=[True, False]).style
                         .format({"Vermogen $ mrd": "{:,.1f}", "20D $ mln": "{:+,.0f}", **{c: "{:+.1f}" for c in pct_cols}})
                         .map(lambda v: "" if pd.isna(v) else f"background-color:rgba({'0,255,156' if v > 0 else '255,45,85'},{min(abs(v) / 15, 1) * 0.55:.2f})",
                              subset=pct_cols)
                         .map(lambda v: f"color:{GREEN}" if v > 0 else f"color:{RED}" if v < 0 else "", subset=["20D $ mln"]),
                         width="stretch", height=800)

        sec("Rotatietoets · zegt echte fondsstroom iets over het vervolg?")
        rt, n_f = rotation_test(sp, f"{sp['so'].index[-1]}|{len(funds_)}")
        if rt is None:
            st.info("Te weinig historie voor de rotatietoets.")
        else:
            fl_ = rt[rt["kind"] == "Echte fondsstroom"]
            Z = fl_.pivot(index="L", columns="h", values="t").reindex(index=ROT_LOOKBACKS, columns=ROT_FORWARD)
            SPm = fl_.pivot(index="L", columns="h", values="spread").reindex(index=ROT_LOOKBACKS, columns=ROT_FORWARD)
            txt = [[("" if pd.isna(Z.loc[L, h]) else f"{'★ ' if (L, h) in ROT_HYPOTHESES else ''}{SPm.loc[L, h]:+.2f}%<br>t = {Z.loc[L, h]:+.1f}")
                    for h in ROT_FORWARD] for L in ROT_LOOKBACKS]
            r1_, r2_ = st.columns([1.25, 1])
            with r1_:
                fig = go.Figure(go.Heatmap(z=Z.values, x=[f"{h} dagen vooruit" for h in ROT_FORWARD], y=[f"Stroom over {L}D" for L in ROT_LOOKBACKS],
                                           colorscale=SCALE, zmin=-4, zmax=4, xgap=3, ygap=3, text=txt, texttemplate="%{text}", textfont=dict(size=12),
                                           colorbar=dict(title="t", thickness=10, tickfont=dict(size=9)), hoverinfo="skip"))
                lay(fig, 330, title=dict(text=f"FONDSEN MET MEESTE INSTROOM MIN FONDSEN MET MEESTE UITSTROOM · {n_f} fondsen · rendement t.o.v. eigen soort",
                                         font=dict(size=11, color=DIM)))
                fig.update_yaxes(autorange="reversed")
                show(fig)
            with r2_:
                lines = []
                for (L, h) in ROT_HYPOTHESES:
                    r_ = fl_[(fl_["L"] == L) & (fl_["h"] == h)]
                    if r_.empty:
                        continue
                    r_ = r_.iloc[0]
                    concl = (f"<b style='color:{GREEN}'>HET GELD VOLGEN WERKTE</b>" if r_["t"] > 2.4 else
                             f"<b style='color:{RED}'>TEGEN HET GELD IN WERKTE</b>" if r_["t"] < -2.4 else f"<b style='color:{AMBER}'>GEEN AANTOONBAAR VERBAND</b>")
                    lines.append(f"<b>Stroom over {L} dagen → rendement in de {h} dagen erna</b><br>verschil {r_['spread']:+.2f}% · t = {r_['t']:+.1f} "
                                 f"(per startmoment {r_['t_min']:+.1f} tot {r_['t_max']:+.1f}) · {int(r_['n'])} perioden · {concl}")
                tr_ = rt[rt["kind"] == "Koerstrend"]
                trend_txt = " · ".join(f"{int(r['h'])}D vooruit {r['spread']:+.2f}% (t = {r['t']:+.1f})" for _, r in tr_.iterrows())
                big = fl_[(fl_["t"].abs() > 3) & ~fl_.apply(lambda r: (r["L"], r["h"]) in ROT_HYPOTHESES, axis=1)]
                more = ("<b>Opvallend buiten de twee vaste toetsen</b> (|t| boven 3): " + ", ".join(
                    f"stroom {int(r['L'])}D → {int(r['h'])}D ({r['spread']:+.2f}%, t = {r['t']:+.1f})" for _, r in big.iterrows())
                        if len(big) else "Buiten de twee vaste toetsen haalt geen enkele cel |t| boven 3.")
                st.markdown(f"<div class='kpi' style='font-family:{MONO};font-size:12px;line-height:1.75'>" + "<br><br>".join(lines) +
                            f"<br><br><b>Ter vergelijking, gewone koerstrend</b> (12 maanden, laatste maand overgeslagen):<br>{trend_txt}<br><br>{more}"
                            f"<br><br><span style='color:{DIM}'>Groen = fondsen met instroom deden het daarna beter dan fondsen met uitstroom; rood = slechter. "
                            "Twee toetsen (★) lagen vooraf vast en tellen vanaf |t| 2,4; de rest is verkennend en telt pas vanaf 3. "
                            "Bovenste derde min onderste derde, instap op de slotkoers van de dag erna, zonder kosten.</span></div>", unsafe_allow_html=True)

        sec("Short-posities · waar wordt het zwaarst tegen gewed? (FINRA, tweemaal per maand)")
        us_ = tuple(c for c in P["Close"].columns if c in META.index and "." not in c and "=" not in c and "^" not in c and not c.endswith("-USD"))
        if not (CACHE_DIR / "short.pkl").exists() and not st.button("Short-posities laden (eenmalig, enkele minuten en ±450 MB download)"):
            st.caption("Nog niet opgehaald. Dit gebeurt ook vanzelf de eerste keer dat het model traint (VOORSPELLING of ANALIST).")
        else:
            with st.spinner("Short-posities ophalen…"):
                si_ = load_short_interest(us_)
            if si_ is None or si_.empty:
                st.info("Geen short-gegevens beschikbaar.")
            else:
                d_last = si_["date"].max()
                prev_dates = sorted(si_["date"].unique())
                cur = si_[si_["date"] == d_last].set_index("symbol")
                prv = si_[si_["date"] == prev_dates[-2]].set_index("symbol")["si"] if len(prev_dates) > 1 else pd.Series(dtype=float)
                bd = pd.DataFrame({"Naam": [META.loc[t, "name"] if t in META.index else t for t in cur.index],
                                   "Dagen tot dekking": cur["dtc"].values, "Short (mln stuks)": cur["si"].values / 1e6,
                                   "Verandering %": ((cur["si"] / prv.reindex(cur.index) - 1) * 100).values}, index=cur.index)
                bd = bd[bd["Short (mln stuks)"] > 0.05]
                bd.index.name = "Ticker"
                cfg_ = {"Dagen tot dekking": st.column_config.NumberColumn(format="%.1f", help="Shortpositie gedeeld door de gemiddelde dagomzet: hoeveel dagen kopen nodig is om alles terug te kopen"),
                        "Short (mln stuks)": st.column_config.NumberColumn(format="%.1f"), "Verandering %": st.column_config.NumberColumn(format="%+.0f%%")}
                s1_, s2_, s3_ = st.columns(3)
                with s1_:
                    st.caption("Hoogste dagen tot dekking")
                    st.dataframe(bd.nlargest(15, "Dagen tot dekking"), width="stretch", height=420, column_config=cfg_)
                with s2_:
                    st.caption("Grootste toename van de shortpositie")
                    st.dataframe(bd.nlargest(15, "Verandering %"), width="stretch", height=420, column_config=cfg_)
                with s3_:
                    st.caption("Grootste afname van de shortpositie")
                    st.dataframe(bd.nsmallest(15, "Verandering %"), width="stretch", height=420, column_config=cfg_)
                st.markdown(f"<div class='note'>Stand per {d_last:%d-%m-%Y} ({si_['date'].nunique()} rapporten in het geheugen). FINRA publiceert ongeveer acht "
                            "werkdagen na de peildatum. Alleen in de VS genoteerde aandelen en fondsen. In onderzoek gaat een hoge shortpositie gemiddeld samen "
                            "met een lager rendement daarna; het model krijgt deze gegevens als invoer.</div>", unsafe_allow_html=True)

elif view == "GEHEUGEN":
    sec("Data-archief · wat de verzamelaar elke nacht vastlegt en later nergens meer te krijgen is")
    arch = store.archive_status()
    cl = collector_last()
    a_, b_ = st.columns([2.2, 1])
    with a_:
        if len(arch):
            NAMES_ = {"intraday_15m": "Kwartierkoersen, alle instrumenten", "options_summary": "Optiemarkt: put/call, impliciete volatiliteit, scheefheid",
                      "news_headlines": "Nieuwskoppen per instrument", "crypto_funding": "Financieringsrente doorlopende crypto-futures"}
            ar = arch.assign(Dataset=arch["dataset"].map(NAMES_).fillna(arch["dataset"])).rename(
                columns={"eerste": "Eerste dag", "laatste": "Laatste dag", "dagen": "Dagen", "rijen": "Rijen opgehaald"})
            st.dataframe(ar[["Dataset", "Eerste dag", "Laatste dag", "Dagen", "Rijen opgehaald", "MB"]], width="stretch", hide_index=True,
                         column_config={"MB": st.column_config.NumberColumn("MB", format="%.1f")})
        else:
            st.markdown("<div class='note'>Nog niets gearchiveerd. De eerste run van de verzamelaar vult dit.</div>", unsafe_allow_html=True)
    with b_:
        st.markdown(f"<div class='kpi' style='font-family:{MONO};font-size:12px;line-height:1.7'><b>Verzamelaar</b><br>"
                    f"laatste run: {cl.get('at', 'nog niet')}<br>duur: {cl.get('seconden', '—')} s<br>"
                    f"patronen actief: {', '.join(cl.get('actief', [])) or '—'}</div>", unsafe_allow_html=True)
        if st.button("Nu verzamelen", key="run_coll", width="stretch", disabled=demo):
            st.toast("Verzamelaar gestart op de achtergrond; dit duurt enkele minuten." if ensure_collector(force=True) else "De verzamelaar draait al.")
    st.markdown("<div class='note'>Yahoo bewaart kwartierkoersen maar 60 dagen en historische optie- en nieuwsdata zijn nergens gratis te koop. "
                "Door ze dagelijks vast te leggen ontstaat een eigen dataset waarop nieuwe ideeën later getoetst kunnen worden. "
                "Bestanden staan per maand in <code>cache/archive/</code> en zijn met pandas te openen.</div>", unsafe_allow_html=True)
    sec("Geheugen · wat de app op deze pc onthoudt")
    cnt = mem_read("SELECT COUNT(DISTINCT date) AS dagen, MIN(date) AS eerste, MAX(date) AS laatste, COUNT(*) AS rijen FROM snapshots")
    n_an = mem_read("SELECT COUNT(DISTINCT date) AS n FROM analyst_log")
    size_mb = sum(f_.stat().st_size for f_ in CACHE_DIR.glob("*") if f_.is_file()) / 1e6 if CACHE_DIR.exists() else 0.0
    dagen = int(cnt["dagen"].iloc[0]) if len(cnt) else 0
    k_ = st.columns(5)
    with k_[0]:
        kpi("Dagen vastgelegd", f"{dagen}", f"{cnt['eerste'].iloc[0] or '—'} t/m {cnt['laatste'].iloc[0] or '—'}" if dagen else "nog niets")
    with k_[1]:
        kpi("Signaalregels", f"{int(cnt['rijen'].iloc[0]) if len(cnt) else 0:,}".replace(",", "."), "instrument × dag")
    with k_[2]:
        kpi("Analistadviezen", f"{int(n_an['n'].iloc[0]) if len(n_an) else 0}", "dagen met vastgelegde selectie")
    with k_[3]:
        pf_ = pf_load()
        kpi("Portefeuille", f"{len(pf_['positions'])} posities", f"{len(pf_['trades'])} transacties")
    with k_[4]:
        kpi("Schijfruimte", f"{size_mb:,.0f} MB", "map cache")
    st.markdown("<div class='note'>Elke dag dat je de app opent, legt hij de stand van dat moment vast: per instrument de scores, het signaal en de "
                "modelverwachting, de selectie van de analist per regio, het oordeel over het model en de verkoopsignalen van je portefeuille. "
                "Ook je instellingen (gewichten, vastgepinde instrumenten, termijn) en je portefeuille blijven bewaard. Koersen hoeven niet te worden "
                "onthouden; die levert Yahoo altijd opnieuw. Dagen waarop de app niet geopend is, ontbreken in dit geheugen. "
                "Demo-data wordt nooit vastgelegd.</div>", unsafe_allow_html=True)

    sec("Trackrecord van de analist · hoe deden zijn eerdere selecties het sindsdien?")
    al = mem_read("SELECT * FROM analyst_log ORDER BY date, scope, rank")
    rows_ = []
    Cc = P["Close"]
    for (dt_, sc_), g_ in (al.groupby(["date", "scope"]) if len(al) else []):
        after = Cc.index[Cc.index > pd.Timestamp(dt_)]
        if len(after) < 2:
            continue                                            # needs an entry close (next day) and at least one later close
        ent = after[0]
        tk = [t_ for t_ in g_["ticker"] if t_ in Cc.columns]
        if not tk:
            continue
        ret = (Cc[tk].iloc[-1] / Cc.loc[ent, tk] - 1) * 100
        w_ = g_.set_index("ticker")["weight"].reindex(tk)
        scope_code = SCOPES.get(sc_)
        uni_cols = [c for c in Cc.columns if c in META.index and (scope_code is None or (scope_code == "core" and META.loc[c, "core"]) or META.loc[c, "cls"] == scope_code)
                    and META.loc[c, "cls"] not in ("Cash", "Futures & Vol", "Indices")]
        bench = float(((Cc[uni_cols].iloc[-1] / Cc.loc[ent, uni_cols] - 1) * 100).median())
        mine = float((ret * w_).sum() / w_.sum())
        rows_.append({"Datum advies": dt_, "Selectie": sc_, "Instrumenten": ", ".join(tk), "Handelsdagen": len(after) - 1, "Selectie %": mine,
                      "Mediaan universum %": bench, "Verschil %": mine - bench, "Met model": "ja" if g_["with_model"].iloc[0] else "nee"})
    if rows_:
        tr_ = pd.DataFrame(rows_)
        w1, w2, w3 = st.columns(3)
        with w1:
            kpi("Beoordeelde selecties", f"{len(tr_)}", "elk vanaf de slotkoers van de dag erna")
        with w2:
            kpi("Gemiddeld verschil", f"{tr_['Verschil %'].mean():+.2f}%", "selectie min mediaan van het universum", col(tr_["Verschil %"].mean() * 20))
        with w3:
            kpi("Beter dan universum", f"{(tr_['Verschil %'] > 0).mean() * 100:.0f}%", "van de selecties", col((tr_["Verschil %"] > 0).mean() * 100 - 50))
        st.dataframe(tr_.sort_values("Datum advies", ascending=False).style.format({"Selectie %": "{:+.2f}", "Mediaan universum %": "{:+.2f}", "Verschil %": "{:+.2f}"})
                     .map(lambda v: f"color:{GREEN}" if v > 0 else f"color:{RED}" if v < 0 else "", subset=["Selectie %", "Verschil %"]),
                     width="stretch", hide_index=True, height=min(420, 38 * len(tr_) + 42))
        st.markdown("<div class='note'>Selecties van opeenvolgende dagen overlappen sterk en zijn dus geen onafhankelijke waarnemingen. "
                    "Rendement in lokale valuta, zonder kosten. Dit is de eerlijkste toets van de app: hij gebruikt alleen koersen van ná het advies.</div>",
                    unsafe_allow_html=True)
    else:
        st.info("Nog geen selectie die oud genoeg is om te beoordelen. Een advies telt mee zodra er minstens twee handelsdagen aan koersen na de adviesdatum zijn. "
                "Open de app regelmatig; het trackrecord bouwt zich vanzelf op.")

    m1, m2 = st.columns(2)
    with m1:
        sec("Oordeel over het model door de tijd")
        ml_hist = mem_read("SELECT date AS Datum, verdict AS Oordeel, horizon AS Horizon, hold_ic AS IC, hold_t AS t, hold_n AS Perioden, spread AS 'Top−bodem %' FROM model_log ORDER BY date DESC")
        if len(ml_hist):
            st.dataframe(ml_hist.style.format({"IC": "{:+.3f}", "t": "{:+.1f}", "Top−bodem %": "{:+.2f}"}), width="stretch", hide_index=True, height=240)
        else:
            st.caption("Wordt gevuld zodra het scherm VOORSPELLING of de ANALIST is geopend.")
    with m2:
        sec("Verkoop- en herbeoordeelsignalen van je portefeuille")
        sl = mem_read("SELECT date AS Datum, ticker AS Ticker, advies AS Advies, reden AS Reden FROM sell_log ORDER BY date DESC, ticker")
        if len(sl):
            st.dataframe(sl, width="stretch", hide_index=True, height=240)
        else:
            st.caption("Nog geen signalen vastgelegd.")

    sec("Vastgelegde geschiedenis van één instrument")
    hist_t = mem_read("SELECT date, totaal, model, s5, s20, s60, signaal FROM snapshots WHERE ticker=? ORDER BY date", (ss.ticker,))
    if len(hist_t) >= 2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist_t["date"], y=hist_t["totaal"], name="Totaalscore", line=dict(color=CYAN, width=1.8)))
        fig.add_trace(go.Scatter(x=hist_t["date"], y=hist_t["model"], name="Modelverwachting", line=dict(color=AMBER, width=1.4, dash="dot")))
        lay(fig, 280, title=dict(text=f"{ss.ticker} · zoals vastgelegd op elke dag", font=dict(size=11, color=DIM)))
        fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.2, font=dict(size=10)))
        fig.update_yaxes(range=[-100, 100])
        show(fig)
    else:
        st.caption(f"Voor {ss.ticker} is nog minder dan twee dagen vastgelegd. Kies een ander instrument via het zoekveld of kom later terug.")

    e1, e2, e3 = st.columns(3)
    with e1:
        if MEM_FILE.exists():
            st.download_button("⬇ Geheugen downloaden (SQLite-bestand)", MEM_FILE.read_bytes(), "geheugen.db", width="stretch")
    with e2:
        snap_csv = mem_read("SELECT * FROM snapshots ORDER BY date, ticker")
        if len(snap_csv):
            st.download_button("⬇ Signaalhistorie als CSV", snap_csv.to_csv(index=False).encode(), "signaalhistorie.csv", "text/csv", width="stretch")
    with e3:
        with st.popover("Geheugen wissen", width="stretch"):
            st.write("Wist de vastgelegde signalen, adviezen en oordelen. Je portefeuille en instellingen blijven staan.")
            if st.button("Ja, wis de historie", type="primary"):
                for tb in ("snapshots", "analyst_log", "model_log", "sell_log"):
                    mem_write(f"DELETE FROM {tb}", [()])
                ss.pop("_remembered", None)
                st.rerun()

elif view == "HANDLEIDING":
    doc = Path(__file__).with_name("HANDLEIDING.md")
    if doc.exists():
        txt = "\n".join(l for l in doc.read_text(encoding="utf-8").splitlines() if not l.startswith("!["))
        st.markdown(txt)
    else:
        st.info("De handleiding van Qtron wordt geschreven zodra de definitieve versie vaststaat. Tot dan: het scherm COCKPIT legt de werkwijze uit, en elk patroon heeft zijn eigen uitvoeringsstappen onder PATRONEN.")

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
        why = ("LIVE 1D is alleen beschikbaar voor de kerninstrumenten; kies 5D of langer voor losse aandelen." if t in P["Close"].columns
               else "Yahoo returned no usable history for it (check the symbol, e.g. BMW.DE, ^N225, EURUSD=X).")
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

    # ── Qtron: levels, valuation, news ──
    dt_ = st.tabs(["NIVEAUS & POSITIEGROOTTE", "WAARDERING", "NIEUWS & AGENDA"])
    with dt_[0]:
        lv = risk.levels(P, t)
        if lv:
            dist = lambda x: f"{(x / lv['last'] - 1) * 100:+.1f}% van de koers" if pd.notna(x) else "te weinig historie"
            q_ = st.columns(6)
            with q_[0]:
                kpi("50-dagengemiddelde", f"{lv['ma50']:,.2f}" if pd.notna(lv["ma50"]) else "—", dist(lv["ma50"]), GREEN if lv["last"] > (lv["ma50"] or 0) else RED)
            with q_[1]:
                kpi("200-dagengemiddelde", f"{lv['ma200']:,.2f}" if pd.notna(lv["ma200"]) else "—", dist(lv["ma200"]), GREEN if pd.notna(lv["ma200"]) and lv["last"] > lv["ma200"] else RED)
            with q_[2]:
                kpi("Steun · 20 dagen", f"{lv['support']:,.2f}", dist(lv["support"]))
            with q_[3]:
                kpi("Weerstand · 20 dagen", f"{lv['resistance']:,.2f}", dist(lv["resistance"]))
            with q_[4]:
                kpi("52 weken", f"{lv['lo52']:,.0f} – {lv['hi52']:,.0f}", f"{(lv['last'] - lv['lo52']) / max(lv['hi52'] - lv['lo52'], 1e-9) * 100:.0f}% van laag naar hoog")
            with q_[5]:
                kpi("Stop op beweeglijkheid", f"{lv['stop']:,.2f}", f"{lv['stop_pct']:.1f}% onder de koers · ATR {lv['atr_pct']:.1f}%", AMBER)
            c_ = P["Close"][t].dropna().tail(260)
            fig = go.Figure(go.Scatter(x=c_.index, y=c_.values, line=dict(color=TXT, width=1.6), name="koers"))
            for nm_, ser_, cl_ in (("50 dagen", lv["ma50_series"], CYAN), ("200 dagen", lv["ma200_series"], AMBER)):
                fig.add_trace(go.Scatter(x=c_.index, y=ser_.reindex(c_.index).values, line=dict(color=cl_, width=1.1), name=nm_))
            for y_, cl_, tx_ in ((lv["support"], GREEN, "steun"), (lv["resistance"], RED, "weerstand"), (lv["stop"], AMBER, "stop")):
                fig.add_hline(y=y_, line=dict(color=cl_, dash="dot", width=1), annotation_text=tx_, annotation_font_color=cl_)
            lay(fig, 300)
            fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.12, x=0, font=dict(size=10)))
            show(fig, key="dd_levels")
            pf_ = pf_load()
            try:
                tot_ = pf_value(pf_)[2]
            except Exception:
                tot_ = pf_["cash"]
            amt_ = risk.size_by_risk(tot_, float(pf_.get("risk_pct", 1.0)), lv["stop_pct"], float(pf_.get("max_pos_pct", 15.0)))
            st.markdown(f"<div class='note'>Positiegrootte bij {pf_.get('risk_pct', 1.0):.2f}% risico op je papieren portefeuille van {tot_:,.0f} {pf_['base']}: "
                        f"<b style='color:{GREEN}'>{amt_:,.0f} {pf_['base']}</b>, met de stop op {lv['stop']:,.2f}. Deze niveaus zijn hulpmiddelen om in- en uitstap te kiezen; "
                        "dat ze koersen voorspellen is in onze toetsen niet gebleken.</div>", unsafe_allow_html=True)
        else:
            st.caption("Te weinig koershistorie voor niveaus.")
    with dt_[1]:
        inf = {} if demo else inst_info(t)
        if inf.get("trailingPE") or inf.get("priceToBook") or inf.get("marketCap"):
            pct = lambda k_: f"{inf[k_] * 100:.1f}%" if inf.get(k_) is not None else "—"
            num = lambda k_, f_="{:.1f}": f_.format(inf[k_]) if inf.get(k_) is not None else "—"
            fcf_y = inf["freeCashflow"] / inf["marketCap"] * 100 if inf.get("freeCashflow") and inf.get("marketCap") else None
            v_ = st.columns(6)
            with v_[0]:
                kpi("Koers / winst", num("trailingPE"), f"verwacht {num('forwardPE')}")
            with v_[1]:
                kpi("Koers / boekwaarde", num("priceToBook"), "onder 1,5 geldt als goedkoop")
            with v_[2]:
                kpi("Vrije kasstroom", f"{fcf_y:.1f}%" if fcf_y is not None else "—", "van de beurswaarde, per jaar")
            with v_[3]:
                kpi("Rendement eigen vermogen", pct("returnOnEquity"), f"winstmarge {pct('profitMargins')}")
            with v_[4]:
                kpi("Schuld / eigen vermogen", num("debtToEquity", "{:.0f}%"), "lager is veiliger")
            with v_[5]:
                kpi("Beurswaarde", fmt_usd(inf["marketCap"]) if inf.get("marketCap") else "—", f"{inf.get('sector', '')} · {inf.get('currency', '')}")
            if is_cheap(t) and r["Score"] > 25:
                st.markdown(f"<div class='banner'>Goedkoop volgens de balans én sterke instroom: in onze toets (2015–2026) deed deze combinatie het slechter dan de sector. "
                            "Niet bewezen, wel een reden om extra kritisch te zijn.</div>", unsafe_allow_html=True)
            st.markdown("<div class='note'>Cijfers zoals Yahoo ze vandaag opgeeft. Ter informatie: in onze toets op Amerikaanse aandelen (2015–2026) voorspelde "
                        "waardering het rendement over weken tot maanden niet.</div>", unsafe_allow_html=True)
        else:
            st.caption("Geen waarderingscijfers beschikbaar voor dit instrument (alleen voor aandelen).")
    with dt_[2]:
        de_ = days_to_earnings(t)
        if de_ is not None:
            st.markdown(f"<div class='banner'>Winstcijfers over {de_} dag{'en' if de_ != 1 else ''} ({inst_earnings(t):%d-%m-%Y}). Rond cijfers beweegt een koers vaak "
                        "veel sterker dan normaal.</div>" if de_ <= 7 else f"<div class='note'>Volgende winstcijfers: {inst_earnings(t):%d-%m-%Y} (over {de_} dagen).</div>",
                        unsafe_allow_html=True)
        nw = [] if demo else inst_news(t)
        if nw:
            st.markdown("<div style='font-family:%s;font-size:12.5px;line-height:1.9'>" % MONO + "".join(
                f"<div style='border-bottom:1px solid {BORDER};padding:3px 0'><span style='color:{DIM}'>{n_['time']} · {n_['publisher'] or ''}</span><br>"
                + (f"<a href='{n_['url']}' target='_blank' style='color:{TXT};text-decoration:none'>{n_['title']}</a>" if n_.get("url") else n_["title"]) + "</div>" for n_ in nw) + "</div>",
                unsafe_allow_html=True)
            st.markdown("<div class='note'>Koppen via Yahoo, enkele minuten vertraagd. Bedoeld om te begrijpen waarom iets beweegt, niet om op te handelen: "
                        "tegen de tijd dat een kop hier staat, zit het nieuws in de koers.</div>", unsafe_allow_html=True)
        else:
            st.caption("Geen recente koppen gevonden voor dit instrument.")

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

# ── memory: persist settings when they change, and record today's state once ──
try:
    _cur = {"pins": ss.pins, "weights": dict(zip(COMP_COLS, wt)), "stocks": bool(ss.get("stocks", True)), "auto": bool(ss.get("auto", False)),
            "tf": ss.get("tf", "20D"), "extra": list(ss.extra)}
    if _cur != ss.get("_mem_saved"):
        mem_write("INSERT OR REPLACE INTO settings VALUES (?,?)", [(k_, json.dumps(v_)) for k_, v_ in _cur.items()])
        ss["_mem_saved"] = _cur
    remember()
except Exception:
    pass

# ── optional auto-refresh: a timer fragment that reruns the whole app ─────────
ss["_last_run"] = time.time()
if ss.get("auto"):
    @st.fragment(run_every=300)
    def _tick():
        if time.time() - ss.get("_last_run", 0) > 290:
            st.rerun()
    _tick()
