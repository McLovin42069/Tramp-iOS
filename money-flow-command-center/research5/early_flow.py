"""Round 5: can a flow be detected EARLIER? Level of the flow score versus its rate of change ("debiet").
Definitions were fixed before looking at any result. Entry at the next close; returns are excess over the
same-day mean of the instrument's asset class. Discovery: to 2023-12-31. Hold-out: 2024-01-01 onward."""
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
S, CMF = {}, {}
for n in (5, 20, 60):
    fp = ns["flow_panels"](P, n, groups, classes)
    S[n], CMF[n] = ns["composite"](fp, W)[cols], fp["_cmf"][cols]
C = P["Close"][cols]
valid = C.notna() & S[60].notna() & (C.notna().cumsum() > 130)
tot = .3 * S[5] + .4 * S[20] + .3 * S[60]
cls = classes[cols]

def fwd(h):
    f = C.shift(-1 - h) / C.shift(-1) - 1
    return f - f.T.groupby(cls.values).transform("mean").T

def first(cond):
    cond = cond & valid
    return cond & ~cond.shift(1, fill_value=False)

EV = {
 "BEVESTIGD (analist: alle horizonten >10, totaal >35)": first((S[5] > 10) & (S[20] > 10) & (S[60] > 10) & (tot > 35)),
 "VROEG-1 omslag (5D van <0 naar >20 in 3 dagen, 60D nog <0)": first((S[5] > 20) & (S[5].shift(3) < 0) & (S[60] < 0)),
 "VROEG-2 puur debiet (CMF 5D >0,10; CMF 20D en 60D <0)": first((CMF[5] > .10) & (CMF[20] < 0) & (CMF[60] < 0)),
 "VROEG-3 versnelling (5D-score 25+ boven 20D, 20D nog <0)": first((S[5] - S[20] > 25) & (S[20] < 0) & (S[5] > 0)),
}
CUT = pd.Timestamp("2024-01-01")
def stat(mask, F, lo, hi, h):
    x = F.where(mask).stack().dropna()
    x = x[(x.index.get_level_values(0) >= lo) & (x.index.get_level_values(0) < hi)]
    if len(x) < 50:
        return None
    per = x.groupby(x.index.get_level_values(0).to_period("Q" if h > 20 else "M")).mean()
    return {"n": int(len(x)), "gem_pct": round(float(x.mean() * 100), 3), "t": round(float(per.mean() / per.std() * np.sqrt(len(per))), 2), "pos_pct": round(float((x > 0).mean() * 100), 1)}

out = {"events": {}, "ic": {}, "lead": {}}
F = {h: fwd(h) for h in (5, 10, 20, 60)}
for name, m in EV.items():
    out["events"][name] = {f"{h}d": {"zoek": stat(m, F[h], pd.Timestamp("2000"), CUT, h), "toets": stat(m, F[h], CUT, pd.Timestamp("2100"), h)} for h in F}

# rank correlation of level vs rate of change with forward excess returns (sampled every h days, no overlap)
SIG = {"niveau (totaalscore)": tot, "debiet (5D min 60D)": S[5] - S[60], "debiet (verandering 20D-score in 5 dagen)": S[20] - S[20].shift(5),
       "puur debiet (CMF 5D min CMF 60D)": CMF[5] - CMF[60]}
for name, sg in SIG.items():
    out["ic"][name] = {}
    for h in (5, 20, 60):
        ic = sg.where(valid).iloc[::h].rank(axis=1).corrwith(F[h].iloc[::h].rank(axis=1), axis=1).dropna()
        d = {}
        for lab, seg in (("zoek", ic[ic.index < CUT]), ("toets", ic[ic.index >= CUT])):
            d[lab] = {"ic": round(float(seg.mean()), 4), "t": round(float(seg.mean() / seg.std() * np.sqrt(len(seg))), 2), "n": int(len(seg))}
        out["ic"][name][f"{h}d"] = d

# how much earlier, and what was gained in between?
conf, early = EV["BEVESTIGD (analist: alle horizonten >10, totaal >35)"], EV["VROEG-1 omslag (5D van <0 naar >20 in 3 dagen, 60D nog <0)"]
raw = C.pct_change(fill_method=None)
xr = raw - raw.T.groupby(cls.values).transform("mean").T
leads, gains, n_conf, conv = [], [], 0, []
split = {True: [], False: []}
for c in cols:
    ci, ei = np.flatnonzero(conf[c].values), np.flatnonzero(early[c].values)
    n_conf += len(ci)
    for i in ci:
        prev = ei[(ei < i) & (ei >= i - 40)]
        if len(prev):
            e = prev[0]
            leads.append(i - e); gains.append(float(np.nansum(xr[c].values[e + 2:i + 2])))
    cx = np.nancumsum(np.nan_to_num(xr[c].values))
    for e in ei:
        ok = bool(((ci > e) & (ci <= e + 40)).any())
        conv.append(ok)
        if e + 42 < len(cx):
            split[ok].append(cx[e + 41] - cx[e + 1])
out["lead"] = {"bevestigingen": n_conf, "met_vroeg_signaal_in_40d_ervoor_pct": round(100 * len(leads) / max(n_conf, 1), 1), "mediaan_dagen_eerder": float(np.median(leads)),
               "gem_excess_tussen_vroeg_en_bevestigd_pct": round(100 * float(np.mean(gains)), 2),
               "vroege_signalen": int(len(conv)), "waarvan_later_bevestigd_pct": round(100 * float(np.mean(conv)), 1),
               "excess_40d_als_later_bevestigd_pct": round(100 * float(np.mean(split[True])), 2), "excess_40d_als_niet_bevestigd_pct": round(100 * float(np.mean(split[False])), 2)}
out["meta"] = {"instrumenten": len(cols), "van": str(C.index[0].date()), "tot": str(C.index[-1].date())}
json.dump(out, open("early_flow_results.json", "w"), indent=1, ensure_ascii=False)
for k, v in out["events"].items():
    print("\n" + k)
    for h, d in v.items():
        print("  ", h, "zoek", d["zoek"], "| toets", d["toets"])
print()
for k, v in out["ic"].items():
    print(k, {h: (d["zoek"]["ic"], d["zoek"]["t"], d["toets"]["ic"], d["toets"]["t"]) for h, d in v.items()})
print(out["lead"], out["meta"])
