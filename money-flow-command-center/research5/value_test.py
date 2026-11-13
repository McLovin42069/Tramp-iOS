"""Round 5e: value investing (Graham/Buffett style) on Qtron's US stocks, from figures as filed with the SEC.
Every figure is used only from its filing date onward. Market value = diluted share count of the latest annual report
(brought to today's split basis) x split-adjusted price. Ranks are taken within the sector group.
A. cheap versus expensive   B. cheap + quality (Graham / Buffett style)   C. cheap combined with money flow.
Definitions fixed beforehand. Discovery to 2023-12-31, hold-out 2024+."""
import ast, sys, json, os
import numpy as np, pandas as pd
Q = "/home/user/Tramp-iOS/qtron/"
sys.path.insert(0, Q)
from universe import META
F = pd.read_pickle("sec/fundamentals.pkl")
A = F[(F["form"] == "10-K")]
us = sorted(set(A["ticker"]))
if not os.path.exists("sec/px_us.pkl"):
    import yfinance as yf
    raw = yf.download(us, start="2014-06-01", auto_adjust=False, actions=True, group_by="column", threads=True, progress=False)
    pd.to_pickle({"C": raw["Close"], "AC": raw["Adj Close"], "S": raw["Stock Splits"]}, "sec/px_us.pkl")
px = pd.read_pickle("sec/px_us.pkl")
C, AC, SPL = px["C"].ffill(limit=5), px["AC"].ffill(limit=5), px["S"].fillna(0)
us = [t for t in us if t in C.columns and C[t].notna().sum() > 500]
C, AC, SPL = C[us], AC[us], SPL[us]
idx = C.index
sf = SPL.where(SPL > 0, 1.0)
after = sf.iloc[::-1].cumprod().iloc[::-1].shift(-1).fillna(1.0)          # product of split ratios strictly after each date

def item(tags, qtrs):
    d = A[A["tag"].isin(tags) & (A["qtrs"] == qtrs) & A["ticker"].isin(us)].copy()
    d["prio"] = d["tag"].map({t: i for i, t in enumerate(tags)})
    d = d.sort_values(["filed", "prio"]).drop_duplicates(["ticker", "filed"], keep="first")
    d["day"] = idx[np.clip(idx.searchsorted(d["filed"].values), 0, len(idx) - 1)]
    return d.pivot_table(index="day", columns="ticker", values="value", aggfunc="last").reindex(index=idx, columns=us)
raw_items = {"eq": item(["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"], 0), "ni": item(["NetIncomeLoss"], 4),
             "assets": item(["Assets"], 0), "liab": item(["Liabilities"], 0), "cfo": item(["NetCashProvidedByUsedInOperatingActivities"], 4),
             "capex": item(["PaymentsToAcquirePropertyPlantAndEquipment"], 4),
             "sh": item(["WeightedAverageNumberOfDilutedSharesOutstanding", "WeightedAverageNumberOfSharesOutstandingBasic"], 4)}
sh_today = (raw_items["sh"] * after).ffill(limit=400)                      # share count on today's split basis
X = {k: v.ffill(limit=400) for k, v in raw_items.items() if k != "sh"}     # an annual report stays valid for at most ~19 months
ni_prev = raw_items["ni"].shift(1).ffill(limit=650).where(raw_items["ni"].ffill(limit=400).notna())
mcap = (sh_today * C).where(lambda m: m > 0)
liab = X["liab"].fillna(X["assets"] - X["eq"])
val = {"boekwaarde / beurswaarde": X["eq"] / mcap, "winst / beurswaarde": X["ni"] / mcap,
       "vrije kasstroom / beurswaarde": (X["cfo"] - X["capex"].fillna(0)) / mcap}
grp = META["group"].reindex(us)
def grank(D):
    return D.T.groupby(grp.values).rank(pct=True).T
vr = sum(grank(v) for v in val.values()) / 3
roe = X["ni"] / X["eq"].where(X["eq"] > 0)
lev = liab / X["assets"]
quality = (grank(roe) + grank(-lev)) / 2
SIG = dict(val)
SIG["WAARDE samengesteld (drie maatstaven)"] = vr
SIG["GRAHAM: goedkoop + lage schuld"] = (vr + grank(-lev)) / 2
SIG["BUFFETT: goedkoop + hoog rendement op eigen vermogen + lage schuld"] = (vr + quality) / 2

r = AC.pct_change(fill_method=None)
valid = mcap.notna() & AC.notna()
CUT = pd.Timestamp("2024-01-01")
def fwd(h):
    f = AC.shift(-1 - h) / AC.shift(-1) - 1
    return f - f.T.groupby(grp.values).transform("mean").T
out = {"A_B_rangschikking": {}, "C_met_geldstroom": {}}
for name, sg in SIG.items():
    out["A_B_rangschikking"][name] = {}
    for h in (20, 60, 250):
        f = fwd(h)
        for off in (0,):
            s_, f_ = sg.where(valid).iloc[off::h], f.iloc[off::h]
            rk = s_.rank(axis=1, pct=True)
            ic = s_.rank(axis=1).corrwith(f_.rank(axis=1), axis=1)
            spread = (f_.where(rk > 0.8).mean(axis=1) - f_.where(rk <= 0.2).mean(axis=1)) * 100
            top = f_.where(rk > 0.8).mean(axis=1) * 100
        d = {}
        for lab, m in (("zoek", ic.index < CUT), ("toets", ic.index >= CUT)):
            i_, s2, t2 = ic[m].dropna(), spread[m].dropna(), top[m].dropna()
            if len(s2) < 2:
                d[lab] = {"n": int(len(s2)), "top_min_bodem_pct": round(float(s2.mean()), 2) if len(s2) else None}
                continue
            d[lab] = {"n": int(len(s2)), "ic": round(float(i_.mean()), 3), "top_min_bodem_pct": round(float(s2.mean()), 2),
                      "t": round(float(s2.mean() / s2.std() * np.sqrt(len(s2))), 2), "alleen_goedkoopste_vijfde_pct": round(float(t2.mean()), 2),
                      "t_top": round(float(t2.mean() / t2.std() * np.sqrt(len(t2))), 2)}
        out["A_B_rangschikking"][name][f"{h}d"] = d

# C. value combined with the flow score of the app
src = open(Q + "app.py").read()
ns = {"np": np, "pd": pd, "RISK_ON_BASKET": ["SPY", "QQQ", "IWM", "EEM", "HYG", "CPER"],
      "COMP_COLS": ["CMF", "MFI", "RS vs Peers", "RS vs Risk-On", "Flow Momentum", "Volume Intensity"]}
for node in ast.parse(src).body:
    if isinstance(node, ast.FunctionDef) and node.name in ("_clean", "flow_panels", "composite"):
        exec(compile(ast.Module([node], []), "app", "exec"), ns)
W = dict(zip(ns["COMP_COLS"], (30, 20, 10, 10, 15, 15)))
core, st = pd.read_pickle(Q + "cache/core.pkl")["panels"], pd.read_pickle(Q + "cache/stocks.pkl")["panels"]
P = ns["_clean"]({k: pd.concat([core[k], st[k].reindex(core[k].index).astype(float)], axis=1) for k in core})
g2, c2 = META["group"].reindex(P["Close"].columns), META["cls"].reindex(P["Close"].columns)
S = {n: ns["composite"](ns["flow_panels"](P, n, g2, c2), W).reindex(index=idx, columns=us) for n in (5, 20, 60)}
tot = .3 * S[5] + .4 * S[20] + .3 * S[60]
cheap, dear = vr.rank(axis=1, pct=True) > 2 / 3, vr.rank(axis=1, pct=True) < 1 / 3
flow_pos = ((S[5] > 10) & (S[20] > 10) & (S[60] > 10)) | (tot > 25)
flow_neg = tot < -25
turn = (S[5] > 20) & (S[60] < 0)
def stat(mask, h, lo, hi):
    f = fwd(h)
    x = f.iloc[::h].where((mask & valid).iloc[::h])
    per = x.mean(axis=1).dropna() * 100
    per = per[(per.index >= lo) & (per.index < hi)]
    if len(per) < 3:
        return {"n": int(len(per))}
    return {"mandjes": int(len(per)), "gem_pct": round(float(per.mean()), 2), "t": round(float(per.mean() / per.std() * np.sqrt(len(per))), 2)}
for lab, m in (("goedkoop + positieve instroom", cheap & flow_pos), ("goedkoop + uitstroom", cheap & flow_neg), ("duur + positieve instroom", dear & flow_pos),
               ("goedkoop + instroom draait net bij (5D positief, 60D negatief)", cheap & turn), ("duur + instroom draait net bij", dear & turn)):
    out["C_met_geldstroom"][lab] = {f"{h}d": {"zoek": stat(m, h, pd.Timestamp("2000"), CUT), "toets": stat(m, h, CUT, pd.Timestamp("2100"))} for h in (20, 60)}
out["meta"] = {"aandelen": len(us), "van": str(mcap.dropna(how="all").index[0].date()), "tot": str(idx[-1].date()),
               "dekking_mediaan_per_dag": int(valid.sum(axis=1).median())}
json.dump(out, open("value_results.json", "w"), indent=1, ensure_ascii=False)
for sec in ("A_B_rangschikking", "C_met_geldstroom"):
    print("\n" + sec)
    for k, v in out[sec].items():
        print(" ", k)
        for h, d in v.items():
            print("     ", h, "zoek", d["zoek"], "| toets", d["toets"])
print(out["meta"])
