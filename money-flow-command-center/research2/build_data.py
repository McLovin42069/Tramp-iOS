"""Round 2 data: (a) long daily history for instruments without survivorship bias, (b) hourly bars for 2 years.
Writes long_full/long_discovery and intra_full/intra_discovery pickles."""
import pickle, time, sys, numpy as np, pandas as pd, yfinance as yf
from pathlib import Path
HERE = Path(__file__).resolve().parent
LONG = ["SPY","QQQ","IWM","DIA","MDY","EFA","EEM","VGK","EWJ","EWG","EWU","EWZ","FXI","EWA","EWC","EWH","EWT","EWY","EWW",
        "XLK","XLF","XLE","XLV","XLI","XLY","XLP","XLU","XLB","XLRE","XLC","SMH","XBI","KRE","XHB","XRT","XOP","GDX",
        "TLT","IEF","IEI","SHY","BIL","TIP","LQD","HYG","JNK","EMB","MUB","AGG","BND",
        "GLD","SLV","USO","UNG","DBC","DBA","CPER","UUP","FXE","FXY","FXB","FXA","VNQ","RSP","VTV","VUG","IWD","IWF","MTUM","USMV","QUAL",
        "^GSPC","^NDX","^RUT","^DJI","^VIX","^TNX","^IRX","^FVX","^TYX","^N225","^GDAXI","^FTSE","^FCHI","^STOXX50E","^HSI","^AEX","^BFX",
        "ES=F","NQ=F","ZN=F","ZB=F","GC=F","CL=F","HG=F","SI=F","NG=F","EURUSD=X","JPY=X","GBPUSD=X","DX-Y.NYB","BTC-USD","ETH-USD"]
INTRA = ["SPY","QQQ","IWM","DIA","XLK","XLF","XLE","XLV","XLI","XLY","XLP","XLU","XLB","XLRE","XLC","SMH","XBI","KRE","GDX","XOP",
         "TLT","IEF","HYG","LQD","GLD","SLV","USO","UUP","EEM","EFA","FXI","EWJ","EWZ","VNQ","RSP",
         "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","AVGO","BRK-B","JPM","LLY","V","UNH","XOM","MA","COST","HD","PG","JNJ","WMT",
         "NFLX","BAC","CRM","ORCL","ABBV","CVX","KO","MRK","AMD","PEP","ADBE","TMO","LIN","CSCO","ACN","MCD","ABT","WFC","GE","IBM",
         "DIS","QCOM","CAT","TXN","INTU","VZ","AMGN","PFE","GS","NOW","UBER","AXP","MS","BKNG","RTX","T","LOW","HON","NEE","UNP",
         "C","BA","INTC","MU","PLTR","COIN","SHOP","F","GM","NKE","SBUX","PYPL","SCHW","BLK","DE","LMT","MDT","GILD","COP","SLB"]
def dl(ticks, **kw):
    out = {}
    for i in range(0, len(ticks), 25):
        ch = ticks[i:i+25]
        for attempt in range(3):
            try:
                raw = yf.download(ch, group_by="ticker", auto_adjust=True, threads=True, progress=False, **kw)
                for t in ch:
                    try:
                        d = raw[t].dropna(subset=["Close"])
                        if len(d) > 200: out[t] = d
                    except Exception: pass
                break
            except Exception as e:
                time.sleep(5)
    return out
def panels(frames, intraday):
    P = {}
    for f, k in (("Open","O"),("High","H"),("Low","L"),("Close","C"),("Volume","V")):
        df = pd.DataFrame({t: d[f] for t, d in frames.items()})
        idx = pd.to_datetime(df.index)
        if intraday:
            df.index = idx.tz_convert("America/New_York").tz_localize(None) if idx.tz is not None else idx
        else:
            df.index = (idx.tz_localize(None) if idx.tz is not None else idx).normalize()
        P[k] = df[~df.index.duplicated(keep="last")].sort_index()
    return P
L = panels(dl(LONG, period="max", interval="1d"), False)
L = {k: v.loc[v.index.dayofweek < 5] for k, v in L.items()}
print("long", L["C"].shape, L["C"].index[0].date(), L["C"].index[-1].date(), "missing:", [t for t in LONG if t not in L["C"].columns])
print("first dates:", {t: str(L["C"][t].first_valid_index().date()) for t in ["SPY","QQQ","IWM","XLK","TLT","GLD","HYG","EEM","^GSPC","^VIX","^TNX","ES=F","UUP","BTC-USD"] if t in L["C"]})
I = panels(dl(INTRA, period="730d", interval="1h"), True)
print("intra", I["C"].shape, I["C"].index[0], I["C"].index[-1], "missing:", [t for t in INTRA if t not in I["C"].columns])
print("bars/day SPY:", I["C"]["SPY"].dropna().groupby(I["C"]["SPY"].dropna().index.normalize()).size().value_counts().head(4).to_dict(), "times:", sorted(set(I["C"]["SPY"].dropna().index.strftime("%H:%M")))[:10])
sp = pd.read_pickle(HERE.parent / "cache/spdr.pkl")
L["spdr"] = {k: sp[k].sort_index() for k in ("so","nav","tna")}
LCUT, ICUT = pd.Timestamp("2018-12-31"), I["C"].index[int(len(I["C"].index) * 0.65)].normalize()
pickle.dump(L, open(HERE / "long_full.pkl", "wb")); pickle.dump(I, open(HERE / "intra_full.pkl", "wb"))
Ld = {k: v.loc[:LCUT] for k, v in L.items() if k != "spdr"}; Ld["spdr"] = {k: v.loc[:LCUT] for k, v in L["spdr"].items()}
Id = {k: v.loc[:ICUT + pd.Timedelta(hours=23)] for k, v in I.items()}
pickle.dump(Ld, open(HERE / "long_discovery.pkl", "wb")); pickle.dump(Id, open(HERE / "intra_discovery.pkl", "wb"))
pickle.dump({"LCUT": LCUT, "ICUT": ICUT}, open(HERE / "cuts.pkl", "wb"))
print("cuts: long discovery ends", LCUT.date(), "| intraday discovery ends", ICUT.date(), "(", Id["C"].index.normalize().nunique(), "days ), hold-out days:", I["C"].index.normalize().nunique() - Id["C"].index.normalize().nunique())
