"""Build the research datasets from the app's disk cache.
  data_full.pkl       everything (used ONLY by holdout.py)
  data_discovery.pkl  truncated at CUTOFF: the only file research agents may use
"""
import re, sys, pickle, numpy as np, pandas as pd, requests
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
CUTOFF = pd.Timestamp("2023-12-29")
src = (ROOT / "app.py").read_text()
ns = {}
exec(re.search(r"^U = \[.*?^\]\n", src, re.S | re.M).group(0), ns)
exec(re.search(r"^STOCKS = \{.*?^\}\n", src, re.S | re.M).group(0), ns)
rows = [(t, n, c, g, True) for t, n, c, g in ns["U"]]
core = {r[0] for r in rows}
for (c, g), txt in ns["STOCKS"].items():
    for tok in txt.split():
        t, _, n = tok.partition("=")
        if t not in core:
            rows.append((t, n.replace("_", " ") or t, c, g, False))
meta = pd.DataFrame(rows, columns=["ticker", "name", "cls", "group", "core"]).drop_duplicates("ticker").set_index("ticker")
corep = pd.read_pickle(ROOT / "cache/core.pkl")["panels"]
stk = pd.read_pickle(ROOT / "cache/stocks.pkl")["panels"]
D = {}
for k in ["Open", "High", "Low", "Close", "Volume"]:
    a = corep[k].astype(float)
    df = pd.concat([a, stk[k].reindex(a.index).astype(float)], axis=1)
    df = df.loc[df.index.dayofweek < 5].sort_index()
    df = df.loc[:, [c for c in df.columns if c in meta.index]]
    D[k[0]] = df.fillna(0.0) if k == "Volume" else df.ffill(limit=5)
good = D["C"].columns[D["C"].notna().sum() >= 130]
for k in "OHLCV":
    D[k] = D[k][good]
D["meta"] = meta.loc[good]
sp = pd.read_pickle(ROOT / "cache/spdr.pkl")
D["spdr"] = {k: v.sort_index() for k, v in sp.items()}
sh = pd.read_pickle(ROOT / "cache/short.pkl")
si = pd.DataFrame(sh["rows"], columns=["date", "symbol", "si", "adv", "dtc"])
si["pub_date"] = si["date"] + pd.offsets.BDay(12)          # usable from this date (publication lag)
D["short"] = si
shares = pd.DataFrame(pd.read_pickle(ROOT / "cache/shares.pkl"))
shares.index = shares.index + pd.Timedelta(days=5)          # reporting lag
D["shares"] = shares.reindex(D["C"].index.union(shares.index)).ffill().reindex(D["C"].index)   # cumulative log net issuance
try:
    want = {"13874A": "SP500", "209742": "NASDAQ", "043602": "UST10Y", "020601": "UST30Y", "088691": "GOLD", "084691": "SILVER",
            "085692": "COPPER", "067651": "WTI", "099741": "EUR", "097741": "JPY", "098662": "USD", "133741": "BTC"}
    r = requests.get("https://publicreporting.cftc.gov/resource/6dca-aqww.json", timeout=30, params={
        "$select": "cftc_contract_market_code,report_date_as_yyyy_mm_dd,open_interest_all,noncomm_positions_long_all,noncomm_positions_short_all,comm_positions_long_all,comm_positions_short_all",
        "$where": "cftc_contract_market_code in (" + ",".join(f"'{c}'" for c in want) + ") AND report_date_as_yyyy_mm_dd > '2014-01-01'", "$limit": 20000})
    c = pd.DataFrame(r.json()); c["date"] = pd.to_datetime(c["report_date_as_yyyy_mm_dd"]) + pd.Timedelta(days=4)   # Tuesday data, public Friday
    for col in c.columns[2:7]: c[col] = pd.to_numeric(c[col], errors="coerce")
    c["spec_net_pct_oi"] = 100 * (c["noncomm_positions_long_all"] - c["noncomm_positions_short_all"]) / c["open_interest_all"]
    c["comm_net_pct_oi"] = 100 * (c["comm_positions_long_all"] - c["comm_positions_short_all"]) / c["open_interest_all"]
    c["contract"] = c["cftc_contract_market_code"].map(want)
    D["cot"] = c[["date", "contract", "spec_net_pct_oi", "comm_net_pct_oi", "open_interest_all"]].sort_values("date")
except Exception as e:
    print("COT failed:", e); D["cot"] = pd.DataFrame(columns=["date", "contract", "spec_net_pct_oi", "comm_net_pct_oi", "open_interest_all"])
pickle.dump(D, open(Path(__file__).parent / "data_full.pkl", "wb"))
T = {k: D[k].loc[:CUTOFF] for k in "OHLCV"}
T["meta"] = D["meta"]
T["spdr"] = {k: v.loc[:CUTOFF] for k, v in D["spdr"].items()}
T["short"] = si[si["pub_date"] <= CUTOFF]
T["shares"] = D["shares"].loc[:CUTOFF]
T["cot"] = D["cot"][D["cot"]["date"] <= CUTOFF]
pickle.dump(T, open(Path(__file__).parent / "data_discovery.pkl", "wb"))
print("full", D["C"].shape, D["C"].index[0].date(), D["C"].index[-1].date(), "| discovery ends", T["C"].index[-1].date(), "| spdr", D["spdr"]["so"].shape,
      "| short rows", len(si), "| shares cols", D["shares"].shape[1], "| cot rows", len(D["cot"]), "| classes", D["meta"]["cls"].value_counts().to_dict())
