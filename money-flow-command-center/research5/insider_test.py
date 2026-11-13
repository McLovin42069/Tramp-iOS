"""Round 5b: insider purchases (SEC Form 4) on Qtron's US stock universe.
A. Do purchases predict excess returns on their own?   B. Do they separate early inflows that continue from those that reverse?
Definitions fixed beforehand. Signal date = filing date (public); entry at the next close. Excess = minus same-day mean of US stocks.
Discovery to 2023-12-31, hold-out 2024-01-01 .. 2026-03-31 (end of the SEC data)."""
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
us = [c for c in P["Close"].columns if c in META.index and META.at[c, "cls"] == "US Stocks"]
S = {n: ns["composite"](ns["flow_panels"](P, n, groups, classes), W)[us] for n in (5, 20, 60)}
C = P["Close"][us]
END = pd.Timestamp("2026-03-31")
valid = C.notna() & S[60].notna() & (C.notna().cumsum() > 130)
idx = C.index

I = pd.read_pickle("sec/insider.pkl")
I = I[I["symbol"].isin(us) & I["filed"].notna() & (I["value"] > 0) & (I["value"] < 2e9)]
I = I[I["role"].astype(str).str.contains("Officer|Director", case=False)]          # executives and board, not 10% holders alone
I = I[(I["filed"] - I["traded"]).dt.days.between(0, 10)]                             # timely filings only
I["day"] = idx[np.clip(idx.searchsorted(I["filed"].values), 0, len(idx) - 1)]
def panel(code, col, fn):
    return I[I["code"] == code].pivot_table(index="day", columns="symbol", values=col, aggfunc=fn).reindex(index=idx, columns=us)
buy_val = panel("P", "value", "sum").fillna(0)
sell_val = panel("S", "value", "sum").fillna(0)
buyers30 = pd.DataFrame(0.0, index=idx, columns=us)
b = I[I["code"] == "P"]
for sym, g in b.groupby("symbol"):                                                   # distinct buyers in the trailing 30 trading days
    d = g.drop_duplicates(["day", "owner"])
    for t in d["day"].unique():
        w = d[(d["day"] <= t) & (d["day"] > t - pd.Timedelta(days=45))]
        buyers30.at[t, sym] = w["owner"].nunique()

def fwd(h):
    f = C.shift(-1 - h) / C.shift(-1) - 1
    return f.sub(f.mean(axis=1), axis=0)
F = {h: fwd(h) for h in (5, 20, 60)}
CUT = pd.Timestamp("2024-01-01")
def stat(mask, h, lo, hi):
    x = F[h].where(mask & valid).stack().dropna()
    d0 = x.index.get_level_values(0)
    x = x[(d0 >= lo) & (d0 < hi) & (d0 <= END)]
    if len(x) < 30:
        return {"n": int(len(x))}
    per = x.groupby(x.index.get_level_values(0).to_period("Q")).mean()
    return {"n": int(len(x)), "gem_pct": round(float(x.mean() * 100), 2), "t": round(float(per.mean() / per.std() * np.sqrt(len(per))), 2), "pos_pct": round(float((x > 0).mean() * 100), 1)}
def both(mask):
    return {f"{h}d": {"zoek": stat(mask, h, pd.Timestamp("2000"), CUT), "toets": stat(mask, h, CUT, pd.Timestamp("2100"))} for h in F}

buy90 = buy_val.rolling(63, min_periods=1).sum()
sell90 = sell_val.rolling(63, min_periods=1).sum()
early = (S[5] > 20) & (S[5].shift(3) < 0) & (S[60] < 0)
early = early & ~early.shift(1, fill_value=False)
out = {"A_standalone": {
          "aankoop >= $100k gemeld": both(buy_val >= 1e5),
          "aankoop >= $1 mln gemeld": both(buy_val >= 1e6),
          "cluster: 2+ bestuurders kopen binnen 30 dagen": both((buyers30 >= 2) & (buy_val > 0)),
          "verkoop >= $10 mln gemeld": both(sell_val >= 1e7)},
       "B_vroege_instroom": {
          "vroeg signaal, alle (VS-aandelen)": both(early),
          "vroeg signaal + aankoop bestuurders in 3 maanden ervoor": both(early & (buy90 >= 1e5)),
          "vroeg signaal, geen aankoop": both(early & (buy90 < 1e5)),
          "vroeg signaal + zware verkoop (>= $10 mln) in 3 maanden ervoor": both(early & (sell90 >= 1e7)),
          "vroeg signaal, geen enkele verkoop": both(early & (sell90 == 0))},
       "meta": {"vs_aandelen": len(us), "transacties_in_universum": int(len(I)), "aankopen": int((I["code"] == "P").sum()), "verkopen": int((I["code"] == "S").sum())}}
json.dump(out, open("insider_results.json", "w"), indent=1, ensure_ascii=False)
for sec in ("A_standalone", "B_vroege_instroom"):
    print("\n" + sec)
    for k, v in out[sec].items():
        print(" ", k)
        for h, d in v.items():
            print("     ", h, "zoek", d["zoek"], "| toets", d["toets"])
print(out["meta"])
