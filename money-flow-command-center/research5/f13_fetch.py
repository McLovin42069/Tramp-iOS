"""Download SEC Form 13F data sets and keep, per quarter and manager, the share positions in Qtron's US stocks.
Needs QTRON_SEC_EMAIL (the SEC requires a contact address in the User-Agent)."""
import io, os, re, sys, time, zipfile, json
import pandas as pd, requests
sys.path.insert(0, "/home/user/Tramp-iOS/qtron")
from universe import META
UA = {"User-Agent": f"Qtron research {os.environ['QTRON_SEC_EMAIL']}"}
us = [t for t in META.index if META.at[t, "cls"] == "US Stocks"]
STOP = r"\b(INC|CORP|CORPORATION|CO|COMPANY|COM|NEW|LTD|PLC|CL|CLASS|A|B|C|THE|HOLDINGS|HLDGS|HLDG|GROUP|GRP|DEL|N V|NV|SA|S A|COS|COMPANIES|LP|ORD|SHS|CAP STK|COMMON|STOCK|INCORPORATED|LIMITED|TR|TRUST|&|AND)\b"
norm = lambda s: re.sub(r"\s+", " ", re.sub(STOP, " ", re.sub(r"[^A-Z0-9& ]", " ", str(s).upper().replace("-", " ")))).strip()

def load(z):
    it = pd.read_csv(z.open("INFOTABLE.tsv"), sep="\t", low_memory=False, usecols=["ACCESSION_NUMBER", "NAMEOFISSUER", "CUSIP", "SSHPRNAMT", "SSHPRNAMTTYPE", "PUTCALL"])
    it = it[it["PUTCALL"].isna() & (it["SSHPRNAMTTYPE"] == "SH")]
    it["CUSIP"] = it["CUSIP"].astype(str).str.upper().str.strip()
    return it

def cusip_map(it):
    g = it.groupby("CUSIP").agg(n=("ACCESSION_NUMBER", "nunique"), name=("NAMEOFISSUER", lambda x: (x.dropna().mode().tolist() or [""])[0])).reset_index()
    g = g[g["n"] >= 20].sort_values("n", ascending=False)
    g["k"] = g["name"].map(norm)
    by = g.drop_duplicates("k").set_index("k")
    ct = pd.DataFrame(json.load(open("sec/ct.json")).values())
    ct["ticker"] = ct["ticker"].str.replace(".", "-", regex=False)
    ct = ct.drop_duplicates("ticker").set_index("ticker")
    m = {}
    for t in us:
        for k in ([norm(ct.title[t])] if t in ct.index else []) + [norm(META.at[t, "name"])]:
            hit = next((by.loc[kk, "CUSIP"] for kk in (k, k.replace("INTERNATIONAL", "INTL"), k.replace("FINANCIAL", "FINL"), k.replace("SERVICES", "SVCS")) if kk in by.index), None)
            if hit is None and len(" ".join(k.split()[:2])) > 5:
                w = " ".join(k.split()[:2])
                c = g[g["k"].str.startswith(w + " ") | (g["k"] == w)]
                hit = c["CUSIP"].iat[0] if len(c) else None
            if hit:
                m[hit] = t
                break
    return m

links = [l.strip() for l in open("sec/13f_links.txt") if l.strip()]
links = [l for l in links if not re.search(r"/201[345]q", l)]
CM, rows = None, []
for l in links:                                    # newest first: the map is built from the newest file
    for attempt in range(4):
        try:
            r = requests.get("https://www.sec.gov" + l, headers=UA, timeout=600)
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(10)
    if r.status_code != 200:
        print("skip", l, r.status_code, flush=True); continue
    z = zipfile.ZipFile(io.BytesIO(r.content))
    it = load(z)
    if CM is None and it["ACCESSION_NUMBER"].nunique() > 3000:
        CM = cusip_map(it)
        print("mapped", len(CM), flush=True)
    if CM is None:
        print("too small for map, skipped", l, flush=True); continue
    it = it[it["CUSIP"].isin(CM)]
    sub = pd.read_csv(z.open("SUBMISSION.tsv"), sep="\t", low_memory=False)
    sub = sub[sub["SUBMISSIONTYPE"] == "13F-HR"]
    d = it.merge(sub[["ACCESSION_NUMBER", "FILING_DATE", "CIK", "PERIODOFREPORT"]], on="ACCESSION_NUMBER")
    d["ticker"] = d["CUSIP"].map(CM)
    a = d.groupby(["PERIODOFREPORT", "FILING_DATE", "CIK", "ticker"], as_index=False)["SSHPRNAMT"].sum()
    rows.append(a)
    print(l.split("/")[-1], len(a), flush=True)
    del r, z, it, d
    time.sleep(1)
H = pd.concat(rows, ignore_index=True)
H.columns = ["period", "filed", "cik", "ticker", "shares"]
for c in ("period", "filed"):
    H[c] = pd.to_datetime(H[c], format="%d-%b-%Y", errors="coerce")
H = H.sort_values("filed").drop_duplicates(["period", "cik", "ticker"], keep="first")
H.to_pickle("sec/f13.pkl")
print(len(H), H["period"].min(), H["period"].max(), H["cik"].nunique(), H["ticker"].nunique())
