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
