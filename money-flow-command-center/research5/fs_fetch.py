"""Download SEC Financial Statement Data Sets (all 10-K/10-Q figures as filed, with filing dates) and keep the
balance-sheet, earnings and cash-flow items of Qtron's US stocks. Needs QTRON_SEC_EMAIL for the User-Agent."""
import io, os, sys, time, zipfile, json
import pandas as pd, requests
sys.path.insert(0, "/home/user/Tramp-iOS/qtron")
from universe import META
UA = {"User-Agent": f"Qtron research {os.environ['QTRON_SEC_EMAIL']}"}
us = {t for t in META.index if META.at[t, "cls"] == "US Stocks"}
ct = pd.DataFrame(json.load(open("sec/ct.json")).values())
ct["ticker"] = ct["ticker"].str.replace(".", "-", regex=False)
cik2t = ct[ct["ticker"].isin(us)].drop_duplicates("cik_str").set_index("cik_str")["ticker"]
TAGS = ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest", "NetIncomeLoss", "Assets", "Liabilities", "AssetsCurrent",
        "LiabilitiesCurrent", "NetCashProvidedByUsedInOperatingActivities", "PaymentsToAcquirePropertyPlantAndEquipment",
        "WeightedAverageNumberOfDilutedSharesOutstanding", "WeightedAverageNumberOfSharesOutstandingBasic", "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax", "LongTermDebtNoncurrent", "LongTermDebt"]
rows = []
for q in pd.period_range("2015Q1", "2026Q3", freq="Q"):
    url = f"https://www.sec.gov/files/dera/data/financial-statement-data-sets/{q.year}q{q.quarter}.zip"
    r = None
    for attempt in range(4):
        try:
            r = requests.get(url, headers=UA, timeout=600)
            if r.status_code in (200, 404):
                break
        except Exception:
            pass
        time.sleep(10)
    if r is None or r.status_code != 200:
        print(q, "skip", getattr(r, "status_code", None), flush=True); continue
    z = zipfile.ZipFile(io.BytesIO(r.content))
    sub = pd.read_csv(z.open("sub.txt"), sep="\t", low_memory=False, usecols=["adsh", "cik", "form", "period", "fy", "fp", "filed"])
    sub = sub[sub["cik"].isin(cik2t.index) & sub["form"].isin(["10-K", "10-Q"])]
    keep = []
    for ch in pd.read_csv(z.open("num.txt"), sep="\t", low_memory=False, chunksize=2_000_000, usecols=["adsh", "tag", "ddate", "qtrs", "uom", "segments", "coreg", "value"],
                          encoding_errors="replace"):
        ch = ch[ch["adsh"].isin(sub["adsh"]) & ch["tag"].isin(TAGS) & ch["segments"].isna() & ch["coreg"].isna()]
        keep.append(ch)
    n = pd.concat(keep).merge(sub, on="adsh")
    n = n[n["ddate"] == n["period"]]                       # the filing's own period, not the comparative columns
    n["ticker"] = n["cik"].map(cik2t)
    rows.append(n[["ticker", "form", "filed", "period", "tag", "qtrs", "value"]])
    print(q, len(n), flush=True)
    del r, z
    time.sleep(1)
F = pd.concat(rows, ignore_index=True)
F["filed"], F["period"] = pd.to_datetime(F["filed"].astype(str), format="%Y%m%d"), pd.to_datetime(F["period"].astype(str).str[:8], format="%Y%m%d", errors="coerce")
F.to_pickle("sec/fundamentals.pkl")
print(len(F), F["ticker"].nunique(), F["filed"].min(), F["filed"].max())
