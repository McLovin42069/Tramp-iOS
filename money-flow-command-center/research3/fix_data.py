"""Post-build corrections: (1) events before the price window must not be mapped onto the first row;
(2) SPDR premium: Yahoo closes are split-adjusted, State Street NAVs are not -> divide out the split factor."""
import pickle, numpy as np, pandas as pd
from pathlib import Path
HERE = Path(__file__).resolve().parent
for f in ("stocks_full.pkl", "stocks_discovery.pkl"):
    D = pickle.load(open(HERE / f, "rb")); first = D["C"].index[0]
    for k in ("earnings", "ratings"):
        e = D[k]
        if len(e):
            e.loc[e["ts"].dt.normalize() < first, "usable_date"] = pd.NaT
    pickle.dump(D, open(HERE / f, "wb"))
    print(f, "earnings usable:", int(D["earnings"]["usable_date"].notna().sum()), "ratings usable:", int(D["ratings"]["usable_date"].notna().sum()))
FACT = np.array([1/10, 1/8, 1/6, 1/5, 1/4, 1/3, 1/2, 1, 2, 3, 4, 5, 6, 8, 10])
for f in ("long_full.pkl", "long_discovery.pkl"):
    L = pickle.load(open(HERE / f, "rb"))
    uc = L["spdr_close_unadj"]; nav = L["spdr"]["nav"].reindex(uc.index)[uc.columns]
    r = uc / nav
    near = FACT[np.abs(np.log(r.values[..., None]) - np.log(FACT)[None, None, :]).argmin(axis=2)]
    prem = (r / near - 1) * 100
    prem = prem.where(prem.abs() < 8)                      # anything larger is a data error, not a premium
    L["spdr_premium_pct"] = prem
    pickle.dump(L, open(HERE / f, "wb"))
    print(f, "premium JNK:", prem["JNK"].dropna().describe().round(3).to_dict() if "JNK" in prem else None)
