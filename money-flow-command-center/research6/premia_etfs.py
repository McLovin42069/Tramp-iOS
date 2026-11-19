"""Round 6a: what did arbitrage- and derivative-based strategies actually deliver in investable form?
Listed funds that run each strategy, after their own costs, from Yahoo total-return prices. Excess = over T-bills (BIL)."""
import json
import numpy as np, pandas as pd, yfinance as yf
F = {"SPY": "S&P 500 (ter vergelijking)", "BIL": "Schatkistpapier (spaarrente)",
     "MNA": "Fusie-arbitrage", "MERFX": "Fusie-arbitrage (fonds sinds 1989)", "ARB": "Fusie-arbitrage",
     "PUTW": "Putopties schrijven op S&P 500", "XYLD": "Gedekte calls op S&P 500", "QYLD": "Gedekte calls op Nasdaq", "JEPI": "Gedekte calls + aandelenselectie",
     "SVXY": "Short volatiliteit (VIX-futures)", "VXX": "Long volatiliteit (VIX-futures)",
     "DBMF": "Trendvolgen met futures", "KMLM": "Trendvolgen met futures", "WTMF": "Trendvolgen met futures", "CTA": "Trendvolgen met futures",
     "BTAL": "Long defensief, short beweeglijk", "QAI": "Hedgefonds-replicatie", "CCOR": "Aandelen + optie-afdekking", "TAIL": "Staartrisico-verzekering",
     "DBV": "Valuta-carry", "PDBC": "Grondstoffen met geoptimaliseerde doorrol", "CEFS": "Korting op gesloten fondsen"}
raw = yf.download(list(F), period="max", auto_adjust=True, progress=False)["Close"]
bil = raw["BIL"].pct_change()
rows = []
def stats(t, start=None):
    p = raw[t].dropna()
    if start is not None:
        p = p[p.index >= start]
    if len(p) < 400:
        return None
    r = p.pct_change().dropna()
    yrs = len(r) / 252
    ex = (r - bil.reindex(r.index).fillna(0))
    eq = (1 + r).cumprod()
    return {"van": str(p.index[0].date()), "jaren": round(yrs, 1), "rendement_pj": round(float(eq.iloc[-1] ** (1 / yrs) - 1) * 100, 1),
            "boven_spaarrente_pj": round(float(ex.mean() * 252 * 100), 1), "beweeglijkheid": round(float(r.std() * np.sqrt(252) * 100), 1),
            "sharpe": round(float(ex.mean() / ex.std() * np.sqrt(252)), 2), "t": round(float(ex.mean() / ex.std() * np.sqrt(len(ex))), 1),
            "grootste_verlies": round(float((eq / eq.cummax() - 1).min() * 100), 0), "slechtste_dag": round(float(r.min() * 100), 1)}
out = {}
for t, lab in F.items():
    if t in raw:
        s = stats(t)
        if s:
            s["wat"] = lab
            spy_same = stats("SPY", pd.Timestamp(s["van"]))
            s["sp500_zelfde_periode_pj"] = spy_same["rendement_pj"] if spy_same else None
            out[t] = s
json.dump(out, open("premia_etfs.json", "w"), indent=1, ensure_ascii=False)
print(pd.DataFrame(out).T[["wat", "van", "rendement_pj", "sp500_zelfde_periode_pj", "boven_spaarrente_pj", "sharpe", "t", "grootste_verlies", "slechtste_dag"]].to_string())
