"""Download SEC insider-transaction data sets (Forms 3/4/5) and keep open-market purchases and sales.
The SEC requires a contact address in the User-Agent: set QTRON_SEC_EMAIL. Nothing else is sent."""
import io, os, sys, time, zipfile
import pandas as pd, requests
UA = {"User-Agent": f"Qtron research {os.environ['QTRON_SEC_EMAIL']}"}
rows = []
for q in pd.period_range("2016Q1", pd.Timestamp.today().to_period("Q"), freq="Q"):
    url = f"https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/{q.year}q{q.quarter}_form345.zip"
    for attempt in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=120)
            break
        except Exception:
            time.sleep(5)
    if r.status_code != 200:
        print(q, "http", r.status_code); continue
    z = zipfile.ZipFile(io.BytesIO(r.content))
    sub = pd.read_csv(z.open("SUBMISSION.tsv"), sep="\t", low_memory=False, usecols=lambda c: c in ("ACCESSION_NUMBER", "FILING_DATE", "DOCUMENT_TYPE", "ISSUERTRADINGSYMBOL", "AFF10B5ONE"))
    if "AFF10B5ONE" not in sub:
        sub["AFF10B5ONE"] = float("nan")
    tr = pd.read_csv(z.open("NONDERIV_TRANS.tsv"), sep="\t", low_memory=False, usecols=["ACCESSION_NUMBER", "TRANS_DATE", "TRANS_CODE", "TRANS_SHARES", "TRANS_PRICEPERSHARE"])
    ow = pd.read_csv(z.open("REPORTINGOWNER.tsv"), sep="\t", low_memory=False, usecols=["ACCESSION_NUMBER", "RPTOWNERCIK", "RPTOWNER_RELATIONSHIP"]).drop_duplicates("ACCESSION_NUMBER")
    tr = tr[tr["TRANS_CODE"].isin(["P", "S"])]
    d = tr.merge(sub[sub["DOCUMENT_TYPE"].astype(str) == "4"], on="ACCESSION_NUMBER").merge(ow, on="ACCESSION_NUMBER", how="left")
    d["value"] = pd.to_numeric(d["TRANS_SHARES"], errors="coerce") * pd.to_numeric(d["TRANS_PRICEPERSHARE"], errors="coerce")
    rows.append(d[["FILING_DATE", "TRANS_DATE", "ISSUERTRADINGSYMBOL", "TRANS_CODE", "value", "RPTOWNERCIK", "RPTOWNER_RELATIONSHIP", "AFF10B5ONE"]])
    print(q, len(d), flush=True)
    time.sleep(1.0)
D = pd.concat(rows, ignore_index=True)
D.columns = ["filed", "traded", "symbol", "code", "value", "owner", "role", "plan"]
D["filed"] = pd.to_datetime(D["filed"], format="%d-%b-%Y", errors="coerce")
D["traded"] = pd.to_datetime(D["traded"], format="%d-%b-%Y", errors="coerce")
D["symbol"] = D["symbol"].astype(str).str.upper().str.strip().str.replace(".", "-", regex=False)
D.to_pickle("sec/insider.pkl")
print(len(D), D["code"].value_counts().to_dict(), D["filed"].min(), D["filed"].max())
