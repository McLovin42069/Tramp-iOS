"""Round 4 data: macro events, energy, weather, liquidity, futures sessions, crypto carry."""
import io, re, sys, time, json, zipfile, pickle, numpy as np, pandas as pd, requests, yfinance as yf
from pathlib import Path
HERE = Path(__file__).resolve().parent; R3 = HERE.parent / "research3"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
LCUT, CCUT = pd.Timestamp("2018-12-31"), pd.Timestamp("2023-12-31")
def get(url, **kw):
    for a in range(3):
        try:
            r = requests.get(url, timeout=60, headers=UA, **kw)
            if r.status_code == 200: return r
        except Exception: time.sleep(2)
    return None
MONTHS = {m: i + 1 for i, m in enumerate(["January","February","March","April","May","June","July","August","September","October","November","December"])}
MS = {k[:3]: v for k, v in MONTHS.items()}

# 1. FOMC scheduled meeting decision dates -----------------------------------------------
fomc = []
for y in range(2000, 2021):
    r = get(f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{y}.htm")
    if r is None: print("fomc hist fail", y); continue
    for m in re.finditer(r"(January|February|March|April|May|June|July|August|September|October|November|December)(?:[/-](January|February|March|April|May|June|July|August|September|October|November|December))?\s+(\d{1,2})(?:\s*-\s*(\d{1,2}))?\s+Meeting\s*-\s*(\d{4})", r.text):
        m1, m2, d1, d2, yy = m.groups()
        mon = MONTHS[m2] if m2 else MONTHS[m1]; day = int(d2) if d2 else int(d1)
        fomc.append(pd.Timestamp(int(yy), mon, day))
r = get("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")
if r is not None:
    txt = r.text
    yrs = [(m.start(), int(m.group(1))) for m in re.finditer(r"(\d{4}) FOMC Meetings", txt)]
    for m in re.finditer(r"fomc-meeting__month[^>]*>\s*(?:<strong>)?([A-Za-z/]+)(?:</strong>)?\s*</div>\s*<div[^>]*fomc-meeting__date[^>]*>\s*([0-9\-\*]+)", txt):
        yy = max([y for p, y in yrs if p < m.start()], key=lambda v: [p for p, y in yrs if y == v][0], default=None) if yrs else None
        prev = [y for p, y in yrs if p < m.start()]
        if not prev: continue
        yy = prev[-1]; mons = m.group(1).split("/"); dd = m.group(2).replace("*", "").split("-")
        mon = mons[-1]; mon = MONTHS.get(mon) or MS.get(mon[:3]); day = int(dd[-1])
        if mon: fomc.append(pd.Timestamp(yy, mon, day))
fomc = sorted(set(fomc)); F = pd.Series(1, index=pd.DatetimeIndex(fomc))
print("FOMC meetings:", len(fomc), F.groupby(F.index.year).size().to_dict(), flush=True)

# 2. EIA weekly inventories ------------------------------------------------------------------
eia = {}
for nm, url in (("crude_stocks", "https://www.eia.gov/dnav/pet/hist_xls/WCESTUS1w.xls"), ("gasoline_stocks", "https://www.eia.gov/dnav/pet/hist_xls/WGTSTUS1w.xls"),
                ("distillate_stocks", "https://www.eia.gov/dnav/pet/hist_xls/WDISTUS1w.xls"), ("natgas_storage", "https://www.eia.gov/dnav/ng/hist_xls/NW2_EPG0_SWO_R48_BCFw.xls"),
                ("crude_production", "https://www.eia.gov/dnav/pet/hist_xls/WCRFPUS2w.xls")):
    r = get(url)
    try:
        x = pd.read_excel(io.BytesIO(r.content), sheet_name=1, skiprows=2, engine="xlrd")
        s = pd.Series(pd.to_numeric(x.iloc[:, 1], errors="coerce").values, index=pd.to_datetime(x.iloc[:, 0], errors="coerce")).dropna()
        eia[nm] = s[s.index.notna()]
    except Exception as e: print("EIA fail", nm, type(e).__name__, str(e)[:80])
EIA = pd.DataFrame(eia); print("EIA:", EIA.shape, {c: (str(EIA[c].first_valid_index())[:10], str(EIA[c].last_valid_index())[:10]) for c in EIA.columns}, flush=True)

# 3. weather (Open-Meteo archive): daily mean temperature and precipitation --------------------
CITIES = {"Chicago": (41.88, -87.63), "New_York": (40.71, -74.01), "Boston": (42.36, -71.06), "Detroit": (42.33, -83.05), "Minneapolis": (44.98, -93.27),
          "Philadelphia": (39.95, -75.17), "Atlanta": (33.75, -84.39), "Dallas": (32.78, -96.80), "Houston": (29.76, -95.37), "Denver": (39.74, -104.99),
          "Des_Moines": (41.59, -93.62), "Springfield_IL": (39.80, -89.64), "Lincoln_NE": (40.81, -96.70), "Indianapolis": (39.77, -86.16),
          "Amsterdam": (52.37, 4.90), "Frankfurt": (50.11, 8.68), "London": (51.51, -0.13)}
temp, prec = {}, {}
for c, (la, lo) in CITIES.items():
    r = get(f"https://archive-api.open-meteo.com/v1/archive?latitude={la}&longitude={lo}&start_date=1990-01-01&end_date={pd.Timestamp.today().date() - pd.Timedelta(days=3)}&daily=temperature_2m_mean,precipitation_sum&timezone=UTC")
    try:
        d = r.json()["daily"]; ix = pd.to_datetime(d["time"])
        temp[c] = pd.Series(d["temperature_2m_mean"], index=ix, dtype=float); prec[c] = pd.Series(d["precipitation_sum"], index=ix, dtype=float)
    except Exception as e: print("weather fail", c, type(e).__name__)
    time.sleep(1)
TEMP, PREC = pd.DataFrame(temp), pd.DataFrame(prec); print("weather:", TEMP.shape, TEMP.index[0].date(), TEMP.index[-1].date(), flush=True)

# 4. liquidity: Treasury General Account (daily) and Fed reverse repo --------------------------
tga = []
page = 1
while True:
    r = get("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance", params={"fields": "record_date,account_type,open_today_bal,close_today_bal", "page[size]": 10000, "page[number]": page, "sort": "record_date"})
    if r is None: break
    j = r.json(); tga += j["data"]
    if page >= j["meta"]["total-pages"]: break
    page += 1
T = pd.DataFrame(tga); T["record_date"] = pd.to_datetime(T["record_date"])
for c in ("open_today_bal", "close_today_bal"): T[c] = pd.to_numeric(T[c], errors="coerce")
old = T[T["account_type"].str.contains("Federal Reserve Account", na=False)].groupby("record_date")["close_today_bal"].last()
new = T[T["account_type"].str.contains("Closing Balance", na=False)].groupby("record_date")["open_today_bal"].last()
TGA = pd.concat([old, new]).sort_index(); TGA = TGA[~TGA.index.duplicated(keep="last")].dropna() / 1000.0      # $ billions
rr = []
for y in range(2013, pd.Timestamp.today().year + 1):
    r = get(f"https://markets.newyorkfed.org/api/rp/reverserepo/propositions/search.json?startDate={y}-01-01&endDate={y}-12-31")
    try:
        for op in r.json()["repo"]["operations"]: rr.append((op["operationDate"], op.get("totalAmtAccepted", 0)))
    except Exception: pass
RRP = pd.Series({pd.Timestamp(d): v for d, v in rr}).sort_index().groupby(level=0).sum() / 1e9 if rr else pd.Series(dtype=float)
auc = []
page = 1
while True:
    r = get("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query", params={"fields": "auction_date,issue_date,security_type,security_term,offering_amt,bid_to_cover_ratio,high_yield", "filter": "auction_date:gte:2000-01-01", "page[size]": 10000, "page[number]": page, "sort": "auction_date"})
    if r is None: break
    j = r.json(); auc += j["data"]
    if page >= j["meta"]["total-pages"]: break
    page += 1
AUC = pd.DataFrame(auc)
if len(AUC):
    AUC["auction_date"] = pd.to_datetime(AUC["auction_date"])
    for c in ("offering_amt", "bid_to_cover_ratio", "high_yield"): AUC[c] = pd.to_numeric(AUC[c], errors="coerce")
print("TGA:", len(TGA), str(TGA.index[0])[:10], str(TGA.index[-1])[:10], "| RRP:", len(RRP), "| auctions:", len(AUC), flush=True)

# 5. prices: long daily + extras, hourly futures -------------------------------------------------
L = pickle.load(open(R3 / "long_full.pkl", "rb"))
extra = ["HO=F", "RB=F", "BZ=F", "ZC=F", "ZS=F", "ZW=F", "KC=F", "SB=F", "CT=F", "LE=F", "UNG", "USO", "XOP", "XLE", "CORN", "WEAT", "SOYB", "DBA", "JETS", "XLU", "BTC=F", "ETH=F", "IBIT", "BITO", "RTY=F", "YM=F", "ZT=F", "ZF=F", "6E=F", "6J=F", "PPLT", "URA", "TAN", "ICLN", "AMLP", "XHB", "ITB"]
extra = [t for t in extra if t not in L["C"].columns]
raw = yf.download(extra, period="max", interval="1d", auto_adjust=True, group_by="ticker", progress=False)
for f, k in (("Open", "O"), ("High", "H"), ("Low", "L"), ("Close", "C"), ("Volume", "V")):
    add = pd.DataFrame({t: raw[t][f] for t in extra if t in raw.columns.get_level_values(0)}); add.index = pd.to_datetime(add.index).tz_localize(None).normalize()
    L[k] = pd.concat([L[k], add.reindex(L[k].index)], axis=1)
L["fomc"] = pd.DatetimeIndex(fomc); L["eia_weekly"] = EIA; L["temp_c"] = TEMP; L["precip_mm"] = PREC
L["tga_bn"] = TGA; L["rrp_bn"] = RRP; L["auctions"] = AUC
FUT = ["ES=F", "NQ=F", "RTY=F", "YM=F", "ZN=F", "ZB=F", "ZT=F", "GC=F", "SI=F", "HG=F", "CL=F", "NG=F", "BZ=F", "6E=F", "6J=F", "BTC=F", "ETH=F", "SPY", "QQQ", "TLT", "GLD", "USO", "UNG"]
rh = yf.download(FUT, period="730d", interval="1h", auto_adjust=True, group_by="ticker", progress=False, prepost=False)
H = {}
for f, k in (("Open", "O"), ("High", "H"), ("Low", "L"), ("Close", "C"), ("Volume", "V")):
    df = pd.DataFrame({t: rh[t][f] for t in FUT if t in rh.columns.get_level_values(0)})
    ix = pd.to_datetime(df.index); df.index = ix.tz_convert("America/New_York").tz_localize(None) if ix.tz is not None else ix
    H[k] = df.sort_index()
H["fomc"] = pd.DatetimeIndex(fomc)
print("hourly futures:", H["C"].shape, H["C"].index[0], H["C"].index[-1], "ES bars/day:", H["C"]["ES=F"].dropna().groupby(H["C"]["ES=F"].dropna().index.normalize()).size().median(), flush=True)

# 6. crypto: perpetual funding rates (Binance public dumps) + spot and CME futures daily ---------
fund = {}
for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"):
    rows = []
    for m in pd.period_range("2019-09", pd.Timestamp.today().to_period("M") - 1, freq="M"):
        r = get(f"https://data.binance.vision/data/futures/um/monthly/fundingRate/{sym}/{sym}-fundingRate-{m}.zip")
        if r is None: continue
        try:
            z = zipfile.ZipFile(io.BytesIO(r.content)); x = pd.read_csv(z.open(z.namelist()[0]))
            tcol = [c for c in x.columns if "time" in c.lower()][0]; rcol = [c for c in x.columns if "rate" in c.lower()][0]
            rows.append(pd.Series(pd.to_numeric(x[rcol], errors="coerce").values, index=pd.to_datetime(pd.to_numeric(x[tcol], errors="coerce"), unit="ms")))
        except Exception: pass
    if rows: fund[sym] = pd.concat(rows).sort_index()
FUND = pd.DataFrame({k: v[~v.index.duplicated()] for k, v in fund.items()})
cr = yf.download(["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "DOGE-USD", "BTC=F", "ETH=F"], period="max", interval="1d", auto_adjust=True, group_by="ticker", progress=False)
CR = pd.DataFrame({t: cr[t]["Close"] for t in cr.columns.get_level_values(0).unique()}); CR.index = pd.to_datetime(CR.index).tz_localize(None).normalize()
CRO = pd.DataFrame({t: cr[t]["Open"] for t in cr.columns.get_level_values(0).unique()}); CRO.index = CR.index
print("funding:", FUND.shape, str(FUND.index[0])[:10] if len(FUND) else None, str(FUND.index[-1])[:10] if len(FUND) else None, "| crypto daily:", CR.shape, flush=True)
X = {"funding": FUND, "C": CR, "O": CRO}

pickle.dump(L, open(HERE / "long_full.pkl", "wb")); pickle.dump(H, open(HERE / "fut_full.pkl", "wb")); pickle.dump(X, open(HERE / "crypto_full.pkl", "wb"))
def cut(obj, c):
    if isinstance(obj, (pd.DataFrame, pd.Series)): return obj.loc[:c] if isinstance(obj.index, pd.DatetimeIndex) else obj
    if isinstance(obj, pd.DatetimeIndex): return obj        # calendars (FOMC dates) are known in advance
    if isinstance(obj, dict): return {k: cut(v, c) for k, v in obj.items()}
    return obj
Ld = cut(L, LCUT)
if len(AUC): Ld["auctions"] = AUC[AUC["auction_date"] <= LCUT]
days = H["C"].index.normalize().unique(); HCUT = days[int(len(days) * 0.65)]
Hd = {k: (v.loc[:HCUT + pd.Timedelta(hours=23)] if isinstance(v, pd.DataFrame) else v) for k, v in H.items()}
Xd = cut(X, CCUT)
pickle.dump(Ld, open(HERE / "long_discovery.pkl", "wb")); pickle.dump(Hd, open(HERE / "fut_discovery.pkl", "wb")); pickle.dump(Xd, open(HERE / "crypto_discovery.pkl", "wb"))
pickle.dump({"LCUT": LCUT, "HCUT": HCUT, "CCUT": CCUT}, open(HERE / "cuts.pkl", "wb"))
print("cuts:", LCUT.date(), HCUT.date(), CCUT.date(), "DONE", flush=True)
