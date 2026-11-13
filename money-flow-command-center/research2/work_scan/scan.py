"""Systematic lead-lag correlation scan (lead researcher). Discovery data only.
Every signal series is paired with every tradable target at every lag; rank correlations, t = rho * sqrt(n).
Hits above a Bonferroni threshold are written to hits.json for a single hold-out replication (replicate.py)."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research2"); import lib2
from scipy.stats import norm

def zrank(df):
    r = df.rank(axis=0)
    return (r - r.mean()) / r.std()

def lagcorr(S, T, k):
    """corr(S[t], T[t+k]) for all column pairs; S, T standardized ranks with NaN. Returns rho, n."""
    A, B = S.iloc[:-k] if k else S, T.iloc[k:] if k else T
    a, b = np.nan_to_num(A.values), np.nan_to_num(B.values)
    ma, mb = (~np.isnan(A.values)).astype(float), (~np.isnan(B.values)).astype(float)
    n = ma.T @ mb
    return (a.T @ b) / np.maximum(n, 1), n

hits, ntests = [], 0
def collect(kind, S, T, lags, min_n, desc):
    global ntests
    out = []
    for k in lags:
        rho, n = lagcorr(S, T, k)
        ok = n >= min_n
        ntests += int(ok.sum())
        t = rho * np.sqrt(np.maximum(n, 1))
        for i, j in zip(*np.where(ok)):
            if S.columns[i] == T.columns[j] and kind in ("d_cc",) and False: continue
            out.append((kind, S.columns[i], T.columns[j], k, float(rho[i, j]), float(t[i, j]), int(n[i, j])))
    print(f"{desc}: {len(out)} tests, max |t| = {max(abs(o[5]) for o in out):.1f}", flush=True)
    return out

# ---------------- daily, long history ----------------
L = lib2.load_long(); C, O = L["C"], L["O"]
etf = [c for c in C.columns if not c.startswith("^") and not c.endswith("=F") and not c.endswith("=X") and not c.endswith("-USD") and c != "DX-Y.NYB"]
us_idx = ["^GSPC", "^NDX", "^RUT", "^DJI"]
yld = ["^IRX", "^FVX", "^TNX", "^TYX"]
cc = C.pct_change(fill_method=None)
ych = C[yld].diff()                                   # yield changes in percentage points
on, intra = O / C.shift(1) - 1, C / O - 1
live = (L["V"][etf].fillna(0) > 0)
cc_e, on_e, in_e = cc[etf].where(live), on[etf].where(live), intra[etf].where(live)
sig_cc = pd.concat([cc_e, cc[us_idx], ych], axis=1)
allres = []
allres += collect("d_cc", zrank(sig_cc), zrank(cc_e), [1, 2, 3, 4, 5], 1500, "daily close-to-close lead-lag (signal day t -> target day t+k)")
allres += collect("d_on_in", zrank(on_e), zrank(in_e), [0], 1500, "daily overnight gap of i -> same-day session return of j")
allres += collect("d_in_on", zrank(in_e), zrank(on_e), [1], 1500, "daily session return of i -> next overnight return of j")
asia = cc[["^N225", "^HSI"]]
allres += collect("d_asia_in", zrank(asia), zrank(in_e), [0], 1500, "Asian index day t (closed before US open) -> US session return day t")
allres += collect("d_asia_cc", zrank(asia), zrank(cc_e), [0], 1500, "Asian index day t -> US close-to-close day t (includes the gap: reference only)")
# multi-day horizons: past L-day return of i -> next h-day return of j (non-overlap adjusted t)
for Lb, h in ((5, 5), (20, 20), (60, 20), (120, 20), (250, 20)):
    past = C[etf] / C[etf].shift(Lb) - 1
    fut = C[etf].shift(-h - 1) / C[etf].shift(-1) - 1
    rho, n = lagcorr(zrank(past), zrank(fut), 0)
    t = rho * np.sqrt(np.maximum(n, 1) / h)             # credit non-overlapping periods only
    ok = n >= 1500; ntests += int(ok.sum())
    res = [("d_h%d_%d" % (Lb, h), past.columns[i], fut.columns[j], h, float(rho[i, j]), float(t[i, j]), int(n[i, j] / h)) for i, j in zip(*np.where(ok))]
    print(f"daily past {Lb}d of i -> next {h}d of j: {len(res)} tests, max |t| = {max(abs(o[5]) for o in res):.1f}", flush=True)
    allres += res
nd = ntests
# ---------------- hourly ----------------
I = lib2.load_intra(); Ch = I["C"]
rh = Ch.pct_change(fill_method=None)
first = Ch.index.strftime("%H:%M") == "09:30"
rh_intraday = rh.where(np.broadcast_to(~first[:, None], rh.shape))                # drop the bar that contains the overnight gap
allres += collect("h_cc", zrank(rh_intraday), zrank(rh_intraday), [1, 2, 3], 1500, "hourly bar b of i -> bar b+k of j (overnight excluded)")
gap = (I["O"] / Ch.shift(1) - 1)[first]          # overnight gap per day
day_ix = gap.index.normalize()
bars = {hh: (Ch / I["O"] - 1)[Ch.index.strftime("%H:%M") == hh].set_axis(Ch.index[Ch.index.strftime("%H:%M") == hh].normalize()) for hh in ["09:30", "10:30", "11:30", "12:30", "13:30", "14:30", "15:30"]}
g = gap.set_axis(day_ix)
am = (bars["09:30"] + 1) * (bars["10:30"] + 1) - 1
pm = (bars["14:30"] + 1) * (bars["15:30"] + 1) - 1
for nm, S_, T_ in (("h_gap_first", g, bars["09:30"]), ("h_gap_rest", g, sum(np.log1p(bars[h]) for h in ["10:30", "11:30", "12:30", "13:30", "14:30", "15:30"])),
                   ("h_first_last", bars["09:30"], bars["15:30"]), ("h_am_pm", am, pm), ("h_first_mid", bars["09:30"], bars["11:30"] + bars["12:30"] + bars["13:30"])):
    ix = S_.index.intersection(T_.index)
    allres += collect(nm, zrank(S_.loc[ix]), zrank(T_.loc[ix]), [0], 300, f"hourly/daily: {nm}")
print("total tests:", ntests, "(daily", nd, ")")
thr = float(norm.isf(0.05 / ntests / 2))
print("Bonferroni threshold |t| >", round(thr, 2), "| expected false hits at that threshold: 0.05")
R = pd.DataFrame(allres, columns=["kind", "signal", "target", "lag", "rho", "t", "n"])
H = R[R["t"].abs() > thr].sort_values("t", key=abs, ascending=False)
print("HITS:", len(H)); print(H.groupby("kind").size().to_string())
print(H.head(40).round(3).to_string())
R.to_pickle("scan_all.pkl"); json.dump({"threshold": thr, "ntests": ntests, "hits": H.to_dict("records")}, open("hits.json", "w"), indent=0)
