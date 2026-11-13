"""Round 5d: within instruments that already show inflow (signal POSITIEF/STERK, as in the app), does the phase
(versnelt / stabiel / verzwakt) matter for the next 5, 20, 30, 60 days? Definitions are the app's own.
Entry at the next close; excess over the same-day mean of the asset class. Discovery to 2023, hold-out 2024+."""
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
cols = [c for c in P["Close"].columns if c in META.index and META.at[c, "cls"] not in ("Cash", "Futures & Vol") and META.at[c, "group"] not in ("Spot Pairs", "Volatility")]
groups, classes = META["group"].reindex(P["Close"].columns), META["cls"].reindex(P["Close"].columns)
S = {n: ns["composite"](ns["flow_panels"](P, n, groups, classes), W)[cols] for n in (5, 20, 60)}
C = P["Close"][cols]
cls = classes[cols]
valid = C.notna() & S[60].notna() & (C.notna().cumsum() > 130)
tot = .3 * S[5] + .4 * S[20] + .3 * S[60]
up = (S[5] > 10) & (S[20] > 10) & (S[60] > 10)
pos = (up | (tot > 25)) & valid                                  # the app's POSITIEF ▲ or STERK ▲
fase = {"versnelt": S[5] > S[20] + 10, "stabiel": (S[5] <= S[20] + 10) & (S[5] >= S[20] - 10), "verzwakt": S[5] < S[20] - 10}
top15 = tot.where(valid).rank(axis=1, ascending=False) <= 15     # the list shown under 'Sterkste instroom'
CUT = pd.Timestamp("2024-01-01")
def fwd(h):
    f = C.shift(-1 - h) / C.shift(-1) - 1
    return f - f.T.groupby(cls.values).transform("mean").T, f
def stat(mask, F, lo, hi, h):
    m = mask.iloc[::h]                                           # one decision every h days: no overlapping holding periods
    x = F.iloc[::h].where(m).stack().dropna()
    d0 = x.index.get_level_values(0)
    x = x[(d0 >= lo) & (d0 < hi)]
    per = x.groupby(level=0).mean()                              # one equal-weight basket per decision date
    return {"n": int(len(x)), "gem_pct": round(float(per.mean() * 100), 2), "t": round(float(per.mean() / per.std() * np.sqrt(len(per))), 2),
            "pos_pct": round(float((per > 0).mean() * 100)), "mandjes": int(len(per))}
out = {}
for h in (5, 20, 30, 60):
    FX, FR = fwd(h)
    for uni, base in (("alle met positief signaal", pos), ("top 15 instroom", top15 & pos)):
        for f, m in fase.items():
            out.setdefault(uni, {}).setdefault(f, {})[f"{h}d"] = {"zoek": stat(base & m, FX, pd.Timestamp("2000"), CUT, h), "toets": stat(base & m, FX, CUT, pd.Timestamp("2100"), h),
                                                                  "toets_ruw": stat(base & m, FR, CUT, pd.Timestamp("2100"), h)["gem_pct"]}
json.dump(out, open("fase_results.json", "w"), indent=1, ensure_ascii=False)
for u, d in out.items():
    print("\n" + u)
    for f, hh in d.items():
        for h, r in hh.items():
            print(f"  {f:9s} {h:4s} zoek {r['zoek']['gem_pct']:+.2f}% t{r['zoek']['t']:+.1f} (n={r['zoek']['n']}, {r['zoek']['mandjes']} mandjes) | toets {r['toets']['gem_pct']:+.2f}% t{r['toets']['t']:+.1f} win {r['toets']['pos_pct']}% (n={r['toets']['n']}) ruw {r['toets_ruw']:+.2f}%")
