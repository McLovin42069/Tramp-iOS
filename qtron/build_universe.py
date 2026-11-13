"""Refresh universe_extra.tsv: every US-listed stock above a market-value threshold, from Yahoo's screener.
Run occasionally (python build_universe.py) so new listings are picked up. Thresholds: $10 bn for all sectors,
$3 bn for Technology and Communication."""
import re, time
import pandas as pd, yfinance as yf
from yfinance import EquityQuery as Q
SEC = {"Technology": "Technology", "Communication Services": "Communication", "Consumer Cyclical": "Cons. Discretionary", "Consumer Defensive": "Cons. Staples",
       "Financial Services": "Financials", "Healthcare": "Health Care", "Energy": "Energy", "Industrials": "Industrials", "Basic Materials": "Materials",
       "Utilities": "Utilities", "Real Estate": "Real Estate"}
SKIP = {"GOOG", "BRK-A", "FOX", "NWS"}                    # second share classes of companies already listed
rows = []
for sector, group in SEC.items():
    floor = 3e9 if group in ("Technology", "Communication") else 1e10
    off = 0
    while True:
        q = Q("and", [Q("eq", ["region", "us"]), Q("is-in", ["exchange", "NMS", "NYQ"]), Q("eq", ["sector", sector]), Q("gt", ["intradaymarketcap", floor])])
        qs = yf.screen(q, offset=off, size=250, sortField="intradaymarketcap", sortAsc=False).get("quotes", [])
        for x in qs:
            s = str(x.get("symbol", ""))
            if re.fullmatch(r"[A-Z]{1,5}(-[A-Z])?", s) and s not in SKIP and (x.get("regularMarketVolume") or 0) > 0:
                name = re.sub(r"[\t=]", " ", str(x.get("shortName") or x.get("longName") or s)).strip()
                rows.append((s, name[:28], "US Stocks", group, float(x.get("marketCap") or 0)))
        if len(qs) < 250:
            break
        off += 250
        time.sleep(0.5)
D = pd.DataFrame(rows, columns=["ticker", "name", "cls", "group", "mcap"]).sort_values("mcap", ascending=False).drop_duplicates("ticker")
if len(D) > 300:                                          # never overwrite the list with a failed download
    D[["ticker", "name", "cls", "group"]].to_csv("universe_extra.tsv", sep="\t", index=False)
print(len(D), D.groupby("group").size().to_dict())


# ── Europe and Asia: home-exchange listings above a size floor (local currency, Europe roughly USD 3 bn, Asia USD 5 bn, mainland China USD 14 bn) ──
WORLD = {  # region: (class, group, allowed suffixes, market-value floor in local currency, required currency or None)
    "gb": ("Europe Stocks", "United Kingdom", (".L",), 2.4e11, "GBp"), "fr": ("Europe Stocks", "France", (".PA",), 2.8e9, None),
    "nl": ("Europe Stocks", "Netherlands", (".AS",), 2.8e9, None), "be": ("Europe Stocks", "Belgium", (".BR",), 1.0e9, None),
    "ch": ("Europe Stocks", "Switzerland", (".SW",), 2.6e9, None), "es": ("Europe Stocks", "Spain & Italy", (".MC",), 2.8e9, None),
    "it": ("Europe Stocks", "Spain & Italy", (".MI",), 2.8e9, None), "se": ("Europe Stocks", "Nordics", (".ST",), 3.2e10, None),
    "dk": ("Europe Stocks", "Nordics", (".CO",), 2.0e10, None), "no": ("Europe Stocks", "Nordics", (".OL",), 3.2e10, None),
    "fi": ("Europe Stocks", "Nordics", (".HE",), 2.8e9, None), "ie": ("Europe Stocks", "Overig Europa", (".IR",), 2.8e9, None),
    "pt": ("Europe Stocks", "Overig Europa", (".LS",), 2.8e9, None),
    "jp": ("Asia Stocks", "Japan", (".T",), 7.5e11, None), "hk": ("Asia Stocks", "China & Hong Kong", (".HK",), 3.9e10, "HKD"),
    "cn": ("Asia Stocks", "China & Hong Kong", (".SS", ".SZ"), 1.0e11, "CNY"), "kr": ("Asia Stocks", "Korea & Taiwan", (".KS", ".KQ"), 7.0e12, None),
    "tw": ("Asia Stocks", "Korea & Taiwan", (".TW", ".TWO"), 1.6e11, None), "in": ("Asia Stocks", "India", (".NS",), 4.2e11, None),
    "au": ("Asia Stocks", "Australia & Singapore", (".AX",), 7.5e9, None), "sg": ("Asia Stocks", "Australia & Singapore", (".SI",), 6.5e9, "SGD")}
# Germany and Austria: Yahoo's screener mixes in thousands of foreign cross-listings there, so these are listed by hand.
MANUAL = {("Europe Stocks", "Germany"): "AIXA AT1 BC8 BOSS DHER EVK EVT FRA FNTN FPE3 G1A GXI HAG HFG HLE HOT JUN3 KGX KBX LEG LXS NDA NEM PUM RAA RRTL SDF G24 TEG TKA TLX UTDI WCH "
                                        "KRN TUI1 NDX1 LHA HLAG DWS EVD BNR CBK DTG ENR SHL SY1 QIA P911 PAH3 1COV FME HNR1 MTX SRT3 ZAL BEI CON HEN3 FRE",
          ("Europe Stocks", "Overig Europa"): "EBS.VI OMV.VI VER.VI RBI.VI ANDR.VI VOE.VI BG.VI WIE.VI"}
norm = lambda s: re.sub(r"[^A-Z0-9]", "", str(s).upper())[:14]
wrows = []
for reg, (cls, group, suf, floor, ccy) in WORLD.items():
    off, got = 0, []
    while off < 3000:
        try:
            qs = yf.screen(Q("and", [Q("eq", ["region", reg]), Q("gt", ["intradaymarketcap", floor])]), offset=off, size=250,
                           sortField="intradaymarketcap", sortAsc=False).get("quotes", [])
        except Exception:
            break
        got += qs
        if len(qs) < 250:
            break
        off += 250
        time.sleep(0.4)
    for x in got:
        s = str(x.get("symbol", ""))
        if s.endswith(suf) and (ccy is None or x.get("currency") == ccy) and (x.get("averageDailyVolume3Month") or 0) > 0:
            name = re.sub(r"[\t=]", " ", str(x.get("shortName") or x.get("longName") or s)).strip().title()
            wrows.append((s, name[:28], cls, group, float(x.get("averageDailyVolume3Month") or 0) * float(x.get("regularMarketPrice") or 0), norm(name)))
    print(reg, len(got), flush=True)
Wd = pd.DataFrame(wrows, columns=["ticker", "name", "cls", "group", "turnover", "key"])
Wd = Wd.sort_values("turnover", ascending=False).drop_duplicates(["group", "key"])        # one share class per company: the most traded
for (cls, group), txt in MANUAL.items():
    Wd = pd.concat([Wd, pd.DataFrame([((t if "." in t else t + ".DE"), (t if "." in t else t + ".DE"), cls, group, 0.0, t) for t in txt.split()], columns=Wd.columns)])
if len(Wd) > 500:
    Wd.drop_duplicates("ticker")[["ticker", "name", "cls", "group"]].to_csv("universe_world.tsv", sep="\t", index=False)
print(len(Wd), Wd.groupby(["cls", "group"]).size().to_dict())
