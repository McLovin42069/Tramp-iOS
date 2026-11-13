from core import *
pd.set_option("display.width", 300); pd.set_option("display.max_columns", 40)
rows = []; R = {}
def E(name, *a, **k):
    r, o, e = ev(name, *a, show=False, **k); rows.append(o); R[name] = r; return r
spy = Cf["SPY"]
def ma(sym, m): return (Cf[sym] > Cf[sym].rolling(21 * m).mean()).astype(float).where(Cf[sym].rolling(21 * m).mean().notna())
# ensemble of MA lookbacks
E("SPY MA ensemble 6/8/10/12", monthly(sum(ma("SPY", m) for m in (6, 8, 10, 12)) / 4).rename("SPY"))
# dual momentum SPY/EFA -> IEF
for m in (6, 9, 12):
    mom = Cf[["SPY", "EFA", "SHY"]] / Cf[["SPY", "EFA", "SHY"]].shift(21 * m) - 1
    mom = mom.dropna()
    best = mom[["SPY", "EFA"]].idxmax(axis=1); ok = mom[["SPY", "EFA"]].max(axis=1) > mom["SHY"]
    pos = pd.DataFrame(0.0, index=mom.index, columns=["SPY", "EFA", "IEF"])
    for c in ("SPY", "EFA"): pos[c] = ((best == c) & ok).astype(float)
    pos["IEF"] = (~ok).astype(float)
    E(f"dualmom SPY/EFA/IEF {m}m", monthly(pos).dropna(), cash=None, risk=["SPY", "EFA"])
# sector rotation
sec = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB"]
for m in (3, 6, 12):
    mom = (Cf[sec] / Cf[sec].shift(21 * m) - 1).dropna()
    top = (mom.rank(axis=1, ascending=False) <= 3).astype(float) / 3
    E(f"sector top3 {m}m", monthly(top).dropna())
    E(f"sector top3 {m}m + SPY>MA10 filter", monthly(top.mul(ma("SPY", 10).reindex(top.index), axis=0)).dropna())
allsec = pd.DataFrame(1 / 9, index=us, columns=sec).where(C[sec].notna().all(axis=1)).dropna()
E("sectors equal weight (ref)", allsec)
E("sectors each > own MA10 (1/9 each)", monthly(pd.concat([ma(s, 10) for s in sec], axis=1, keys=sec).dropna() / 9).dropna())
# three sleeve trend
for m in (6, 10, 12):
    p = pd.concat([ma(s, m) for s in ("SPY", "TLT", "GLD")], axis=1, keys=["SPY", "TLT", "GLD"]).dropna() / 3
    E(f"3-sleeve SPY/TLT/GLD MA{m}", monthly(p).dropna(), risk=["SPY", "TLT", "GLD"])
E("3-sleeve static 1/3 (ref)", pd.DataFrame(1 / 3, index=us, columns=["SPY", "TLT", "GLD"]).where(C["GLD"].notna()).dropna(), risk=["SPY", "TLT", "GLD"])
g5 = ["SPY", "EFA", "IEF", "GLD", "VNQ"]
E("GTAA5 MA10", monthly(pd.concat([ma(s, 10) for s in g5], axis=1, keys=g5).dropna() / 5).dropna(), risk=g5)
E("GTAA5 static (ref)", pd.DataFrame(0.2, index=us, columns=g5).where(C["GLD"].notna()).dropna(), risk=g5)
# country trend basket (1996 ETFs)
cty = ["SPY", "EWJ", "EWG", "EWU", "EWA", "EWC", "EWH", "EWW"]
E("8-country each>MA10 (1/8)", monthly(pd.concat([ma(s, 10) for s in cty], axis=1, keys=cty).dropna() / 8).dropna())
E("8-country static (ref)", pd.DataFrame(1 / 8, index=us, columns=cty).where(C["EWJ"].notna()).dropna())
# combos
dx = Cf["DX-Y.NYB"]; f_dx = (dx < dx.shift(126)).astype(float)
cr = Cf["LQD"] / Cf["IEF"]; f_cr = (cr > cr.shift(126)).astype(float).where(cr.shift(126).notna())
f_tr = ma("SPY", 10)
E("vote trend+dollar (avg)", monthly((f_tr + f_dx) / 2).rename("SPY").dropna())
E("vote trend+dollar+credit (avg)", monthly((f_tr + f_dx + f_cr) / 3).rename("SPY").dropna())
E("vote trend+dollar+credit (2of3)", monthly(((f_tr + f_dx + f_cr) >= 2).astype(float).where(f_cr.notna())).rename("SPY").dropna())
E("vote trend+credit (avg)", monthly((f_tr + f_cr) / 2).rename("SPY").dropna())
E("trend OR dollar", monthly(((f_tr + f_dx) >= 1).astype(float).where(f_tr.notna())).rename("SPY").dropna())
rsp = C["SPY"].pct_change(); vol = rsp.rolling(21).std() * np.sqrt(252)
E("MA10 x voltarget .15", monthly(f_tr * (0.15 / vol).clip(upper=1)).rename("SPY").dropna())
# off-asset IEF instead of SHY for trend (2002+)
p = monthly(f_tr).rename("SPY").to_frame(); p["IEF"] = (1 - p["SPY"]); E("SPY>MA10 else IEF (2002+)", p.where(C["IEF"].notna()).dropna(), cash=None, risk=["SPY"])
E("SPY>MA10 (2002-08+ for 60/40 compare)", monthly(f_tr).rename("SPY").dropna(), start="2002-08-01")
df = pd.DataFrame(rows); print(df.to_string()); df.to_pickle("r2.pkl"); print("N", N[0])
pd.to_pickle(R, "R2.pkl")
