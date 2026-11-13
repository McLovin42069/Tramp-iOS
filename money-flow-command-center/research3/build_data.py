"""Round 3 data: genuinely different information.
  stocks: round-1 panels + daily short-sale volume (FINRA), earnings dates & EPS surprises (Yahoo), analyst rating changes (Yahoo)
  long:   round-2 long panels + volatility family (VIX term structure, VVIX, SKEW, MOVE, vol ETPs) + SPDR premium/discount to NAV
"""
import io, sys, time, pickle, numpy as np, pandas as pd, requests, yfinance as yf
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
HERE = Path(__file__).resolve().parent; R1 = HERE.parent / "research"; R2 = HERE.parent / "research2"
SCUT, LCUT = pd.Timestamp("2023-12-29"), pd.Timestamp("2018-12-31")
D = pickle.load(open(R1 / "data_full.pkl", "rb"))
meta = D["meta"]; us = [t for t in D["C"].columns if "." not in t and "=" not in t and "^" not in t and not t.endswith("-USD")]
stocks = [t for t in D["C"].columns if not meta.loc[t, "core"]]
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/126.0 Safari/537.36"}

# 1. FINRA daily short-sale volume -------------------------------------------------
want = {t.replace("-", ""): t for t in us}
days = pd.bdate_range("2018-08-01", pd.Timestamp.today().normalize())
def one(d):
    for attempt in range(2):
        try:
            r = requests.get(f"https://cdn.finra.org/equity/regsho/daily/CNMSshvol{d:%Y%m%d}.txt", timeout=40, headers=UA)
            if r.status_code != 200 or len(r.content) < 5000: return None
            x = pd.read_csv(io.BytesIO(r.content), sep="|", dtype=str, usecols=["Symbol", "ShortVolume", "ShortExemptVolume", "TotalVolume"])
            x = x[x["Symbol"].isin(want)]
            return d, x
        except Exception: time.sleep(1)
    return None
t0 = time.time(); sv, tv = {}, {}
with ThreadPoolExecutor(8) as ex:
    for res in ex.map(one, days):
        if res is None: continue
        d, x = res
        sym = x["Symbol"].map(want)
        sv[d] = pd.Series(pd.to_numeric(x["ShortVolume"], errors="coerce").values, index=sym)
        tv[d] = pd.Series(pd.to_numeric(x["TotalVolume"], errors="coerce").values, index=sym)
SV, TV = pd.DataFrame(sv).T.sort_index(), pd.DataFrame(tv).T.sort_index()
print("shortvol", SV.shape, SV.index[0].date(), SV.index[-1].date(), round(time.time() - t0), "s", flush=True)

# 2. earnings and 3. ratings ---------------------------------------------------------
def earn(t):
    for attempt in range(2):
        try:
            e = yf.Ticker(t).get_earnings_dates(limit=100)
            if e is None or e.empty: return t, None
            e = e.reset_index(); e.columns = ["ts", "eps_est", "eps_rep", "surprise_pct"]; e["ticker"] = t
            return t, e
        except Exception: time.sleep(2)
    return t, None
def rate(t):
    for attempt in range(2):
        try:
            u = yf.Ticker(t).upgrades_downgrades
            if u is None or u.empty: return t, None
            u = u.reset_index().rename(columns={"GradeDate": "ts"}); u["ticker"] = t
            return t, u
        except Exception: time.sleep(2)
    return t, None
t0 = time.time(); E, Rr = [], []
with ThreadPoolExecutor(4) as ex:
    for t, e in ex.map(earn, stocks):
        if e is not None: E.append(e)
print("earnings tickers", len(E), "of", len(stocks), round(time.time() - t0), "s", flush=True)
t0 = time.time()
with ThreadPoolExecutor(4) as ex:
    for t, u in ex.map(rate, [t for t in stocks if t in us]):
        if u is not None: Rr.append(u)
print("ratings tickers", len(Rr), round(time.time() - t0), "s", flush=True)
idx = D["C"].index
def usable(ts, close_hour=16):
    """First trading row whose close is AFTER the timestamp (announcements at/after the close count for the next day)."""
    ts = pd.to_datetime(ts, utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    day = ts.dt.normalize() + pd.to_timedelta((ts.dt.hour >= close_hour).astype(int), unit="D")
    pos = idx.searchsorted(day.values)
    return pd.Series([idx[p] if p < len(idx) else pd.NaT for p in pos], index=ts.index), ts
EARN = pd.concat(E, ignore_index=True) if E else pd.DataFrame()
if len(EARN):
    # non-US exchanges close before 16:00 New York; use each market's rough closing hour in NY time
    hr = EARN["ticker"].map(lambda t: 16 if "." not in t else (3 if t.split(".")[-1] in ("T", "HK", "SS", "SZ", "KS", "TW", "AX", "SI", "NS") else 11))
    ts = pd.to_datetime(EARN["ts"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    day = ts.dt.normalize() + pd.to_timedelta((ts.dt.hour >= hr).astype(int), unit="D")
    pos = idx.searchsorted(day.values)
    EARN["usable_date"] = [idx[p] if p < len(idx) else pd.NaT for p in pos]; EARN["ts"] = ts
RATE = pd.concat(Rr, ignore_index=True) if Rr else pd.DataFrame()
if len(RATE):
    RATE["usable_date"], RATE["ts"] = usable(RATE["ts"])
D["shortvol"] = {"short": SV, "total": TV}; D["earnings"] = EARN; D["ratings"] = RATE
pickle.dump(D, open(HERE / "stocks_full.pkl", "wb"))
T = {k: D[k].loc[:SCUT] for k in "OHLCV"}; T["meta"] = meta
T["spdr"] = {k: v.loc[:SCUT] for k, v in D["spdr"].items()}; T["short"] = D["short"][D["short"]["pub_date"] <= SCUT]
T["shares"] = D["shares"].loc[:SCUT]; T["cot"] = D["cot"][D["cot"]["date"] <= SCUT]
T["shortvol"] = {"short": SV.loc[:SCUT], "total": TV.loc[:SCUT]}
T["earnings"] = EARN[EARN["ts"] <= SCUT] if len(EARN) else EARN          # future (scheduled) dates beyond the cut are removed
T["ratings"] = RATE[RATE["ts"] <= SCUT] if len(RATE) else RATE
pickle.dump(T, open(HERE / "stocks_discovery.pkl", "wb"))
print("earnings rows", len(EARN), "ratings rows", len(RATE), flush=True)

# 4. long side: volatility family + SPDR premium to NAV ---------------------------------
L = pickle.load(open(R2 / "long_full.pkl", "rb"))
vt = ["^VIX3M", "^VIX9D", "^VIX6M", "^VVIX", "^SKEW", "^VXN", "^OVX", "^GVZ", "^MOVE", "VXX", "SVXY", "UVXY", "VIXY", "VIXM"]
raw = yf.download(vt, period="max", interval="1d", auto_adjust=True, group_by="ticker", progress=False)
for f, k in (("Open", "O"), ("High", "H"), ("Low", "L"), ("Close", "C"), ("Volume", "V")):
    add = pd.DataFrame({t: raw[t][f] for t in vt if t in raw.columns.get_level_values(0)})
    add.index = pd.to_datetime(add.index).tz_localize(None).normalize()
    L[k] = pd.concat([L[k], add.reindex(L[k].index)], axis=1)
funds = list(L["spdr"]["nav"].columns)
ru = yf.download(funds, period="max", interval="1d", auto_adjust=False, group_by="ticker", progress=False)
uc = pd.DataFrame({t: ru[t]["Close"] for t in funds if t in ru.columns.get_level_values(0)})
uc.index = pd.to_datetime(uc.index).tz_localize(None).normalize()
nav = L["spdr"]["nav"].reindex(uc.index)
L["spdr_premium_pct"] = (uc / nav[uc.columns] - 1) * 100            # unadjusted close vs same-day NAV (NAV is published after the close)
L["spdr_close_unadj"] = uc
pickle.dump(L, open(HERE / "long_full.pkl", "wb"))
Ld = {k: (v.loc[:LCUT] if isinstance(v, pd.DataFrame) else v) for k, v in L.items() if k != "spdr"}; Ld["spdr"] = {k: v.loc[:LCUT] for k, v in L["spdr"].items()}
pickle.dump(Ld, open(HERE / "long_discovery.pkl", "wb"))
print("long", L["C"].shape, "premium", L["spdr_premium_pct"].shape, L["spdr_premium_pct"].dropna(how="all").index[0].date(), "DONE", flush=True)
