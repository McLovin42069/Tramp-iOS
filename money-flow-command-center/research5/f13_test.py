"""Round 5c: quarterly holdings of institutional managers (SEC 13F) on Qtron's US stocks.
Signals become usable 47 days after quarter end (filing deadline is 45 days); only filings made by then are used.
A. Do changes in institutional ownership predict excess returns?  B. Do they separate early inflows that continue?
Definitions fixed beforehand. Discovery: signals available before 2024-01-01. Hold-out: after."""
import ast, sys, json
import numpy as np, pandas as pd
Q = "/home/user/Tramp-iOS/qtron/"
sys.path.insert(0, Q)
from universe import META
src = open(Q + "app.py").read()
ns = {"np": np, "pd": pd, "RISK_ON_BASKET": ["SPY", "QQQ", "IWM", "EEM", "HYG", "CPER"],
      "COMP_COLS": ["CMF", "MFI", "RS vs Peers", "RS vs Risk-On", "Flow Momentum", "Volume Intensity"]}
for node in ast.parse(src).body:
    if isinstance(node, ast.FunctionDef) and node.name in ("_clean", "flow_panels", "composite"):
        exec(compile(ast.Module([node], []), "app", "exec"), ns)
W = dict(zip(ns["COMP_COLS"], (30, 20, 10, 10, 15, 15)))
core, st = pd.read_pickle(Q + "cache/core.pkl")["panels"], pd.read_pickle(Q + "cache/stocks.pkl")["panels"]
P = ns["_clean"]({k: pd.concat([core[k], st[k].reindex(core[k].index).astype(float)], axis=1) for k in core})
groups, classes = META["group"].reindex(P["Close"].columns), META["cls"].reindex(P["Close"].columns)
H = pd.read_pickle("sec/f13.pkl")
H = H[(H["filed"] - H["period"]).dt.days.between(0, 47) & (H["shares"] > 0)]
us = [c for c in P["Close"].columns if c in set(H["ticker"])]
S = {n: ns["composite"](ns["flow_panels"](P, n, groups, classes), W)[us] for n in (5, 20, 60)}
C = P["Close"][us]
idx = C.index
valid = C.notna() & S[60].notna() & (C.notna().cumsum() > 130)

periods = sorted(p for p in H["period"].unique() if pd.Timestamp(p).is_quarter_end)
npos = H.groupby(["period", "cik"])["ticker"].nunique()
sig = {"breedte: nieuwe houders min vertrekkers": {}, "aandeel fondsen dat bijkocht min afbouwde": {}, "geconcentreerde fondsen (10-60 posities): bijkopers min afbouwers": {}}
for p0, p1 in zip(periods[:-1], periods[1:]):
    if (pd.Timestamp(p1) - pd.Timestamp(p0)).days > 100:
        continue
    a = H[H["period"] == p0].pivot_table(index="cik", columns="ticker", values="shares", aggfunc="sum")
    b = H[H["period"] == p1].pivot_table(index="cik", columns="ticker", values="shares", aggfunc="sum")
    both = a.index.intersection(b.index)
    if len(both) < 500:
        continue
    a, b = a.reindex(index=both, columns=us).fillna(0), b.reindex(index=both, columns=us).fillna(0)
    held = (a > 0) & (b > 0)
    ratio = (b / a.where(a > 0)).where(held)
    split = (ratio.median() > 1.4) | (ratio.median() < 0.7)                    # share counts jump for everyone: a stock split
    n_prev = (a > 0).sum().where(lambda x: x >= 50)
    breadth = (((b > 0) & (a == 0)).sum() - ((a > 0) & (b == 0)).sum()) / n_prev
    inc = (((b > a * 1.02) & (a >= 0)).sum() - (b < a * 0.98).sum()) / n_prev
    conc = both[npos.reindex([(p1, c) for c in both]).between(10, 60).values]
    ac, bc = a.loc[conc], b.loc[conc]
    nc = ((ac > 0) | (bc > 0)).sum().where(lambda x: x >= 15)
    cinc = ((bc > ac * 1.02).sum() - (bc < ac * 0.98).sum()) / nc
    avail = idx[min(idx.searchsorted(pd.Timestamp(p1) + pd.Timedelta(days=47)), len(idx) - 1)]
    for k, v in zip(sig, (breadth, inc.mask(split), cinc.mask(split))):
        sig[k][avail] = v
SIG = {k: pd.DataFrame(v).T.sort_index() for k, v in sig.items()}

def fwd(h):
    f = C.shift(-1 - h) / C.shift(-1) - 1
    return f.sub(f.mean(axis=1), axis=0)
F = {h: fwd(h) for h in (20, 60)}
CUT = pd.Timestamp("2024-01-01")
out = {"A_rangschikking": {}, "B_vroege_instroom": {}}
for k, X in SIG.items():
    out["A_rangschikking"][k] = {}
    for h in F:
        f = F[h].reindex(X.index)
        ic = X.rank(axis=1).corrwith(f.rank(axis=1), axis=1)
        r = X.rank(axis=1, pct=True)
        spread = (f.where(r > 0.8).mean(axis=1) - f.where(r <= 0.2).mean(axis=1)) * 100
        d = {}
        for lab, m in (("zoek", X.index < CUT), ("toets", X.index >= CUT)):
            i_, s_ = ic[m].dropna(), spread[m].dropna()
            d[lab] = {"kwartalen": int(len(i_)), "ic": round(float(i_.mean()), 4), "ic_t": round(float(i_.mean() / i_.std() * np.sqrt(len(i_))), 2),
                      "top_min_bodem_pct": round(float(s_.mean()), 2), "spread_t": round(float(s_.mean() / s_.std() * np.sqrt(len(s_))), 2)}
        out["A_rangschikking"][k][f"{h}d"] = d

def stat(mask, h, lo, hi):
    x = F[h].where(mask & valid).stack().dropna()
    d0 = x.index.get_level_values(0)
    x = x[(d0 >= lo) & (d0 < hi)]
    if len(x) < 30:
        return {"n": int(len(x))}
    per = x.groupby(x.index.get_level_values(0).to_period("Q")).mean()
    return {"n": int(len(x)), "gem_pct": round(float(x.mean() * 100), 2), "t": round(float(per.mean() / per.std() * np.sqrt(len(per))), 2)}
early = (S[5] > 20) & (S[5].shift(3) < 0) & (S[60] < 0)
early = early & ~early.shift(1, fill_value=False)
X = SIG["aandeel fondsen dat bijkocht min afbouwde"]
rk = X.rank(axis=1, pct=True).reindex(idx).ffill(limit=70)
for lab, m in (("vroeg signaal, alle", early), ("vroeg signaal + fondsen kochten bij (bovenste derde)", early & (rk > 2 / 3)), ("vroeg signaal + fondsen bouwden af (onderste derde)", early & (rk < 1 / 3))):
    out["B_vroege_instroom"][lab] = {f"{h}d": {"zoek": stat(m, h, X.index[0], CUT), "toets": stat(m, h, CUT, pd.Timestamp("2100"))} for h in F}
out["meta"] = {"aandelen": len(us), "kwartalen": int(len(X)), "eerste_signaal": str(X.index[0].date()), "laatste_signaal": str(X.index[-1].date()), "fondsen": int(H["cik"].nunique())}
json.dump(out, open("f13_results.json", "w"), indent=1, ensure_ascii=False)
for sec in ("A_rangschikking", "B_vroege_instroom"):
    print("\n" + sec)
    for k, v in out[sec].items():
        print(" ", k)
        for h, d in v.items():
            print("     ", h, "zoek", d["zoek"], "| toets", d["toets"])
print(out["meta"])
