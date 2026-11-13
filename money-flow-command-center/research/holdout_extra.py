"""One-shot hold-out checks (2024-01-02 onward) for the two 'closest miss' patterns that lib's close-to-close runner
cannot express. Definitions fixed from the discovery reports before running."""
import os, sys; os.environ["MFCC_HOLDOUT"] = "1"; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, lib
D = lib.load(); START = pd.Timestamp("2024-01-02")
def tstat(x): x = x.dropna(); return float(x.mean() / x.std(ddof=1) * np.sqrt(len(x))), len(x)
print("== 1. Overnight (close->open) vs intraday (open->close), gross, basis points per day")
for t in ["IWM", "SPY", "QQQ"]:
    O, C, V = D["O"][t], D["C"][t], D["V"][t]
    live = V > 0                                    # skip forward-filled holiday rows
    on = (O / C.shift(1) - 1)[live]; intra = (C / O - 1)[live]
    for lab, s in (("discovery", slice(None, lib.CUTOFF)), ("HOLD-OUT", slice(START, None))):
        a, b = on.loc[s], intra.loc[s]; ta, n = tstat(a); tb, _ = tstat(b)
        net1 = (a.mean() - 2e-4) * 252 * 100; net05 = (a.mean() - 1e-4) * 252 * 100
        print(f"  {t} {lab:9s} overnight {a.mean()*1e4:+.1f} bp (t={ta:+.2f}, n={n}) | intraday {b.mean()*1e4:+.1f} bp (t={tb:+.2f}) | overnight net/yr at 1bp per trade {net1:+.1f}%, at 0.5bp {net05:+.1f}% | buy&hold/yr {(a.mean()+b.mean())*252*100:+.1f}%")
print("== 2. Treasuries in the last 3 trading days of the month vs other days, gross bp/day")
for t in ["IEF", "TLT"]:
    C, V = D["C"][t], D["V"][t]; r = C.pct_change(fill_method=None)[V > 0]
    per = r.index.to_period("M"); rank_from_end = r.groupby(per).cumcount(ascending=False)
    inw = rank_from_end < 3
    for lab, s in (("discovery", r.index <= lib.CUTOFF), ("HOLD-OUT", r.index >= START)):
        a, b = r[inw & s], r[~inw & s]
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        print(f"  {t} {lab:9s} in-window {a.mean()*1e4:+.1f} bp (n={len(a)}) | other days {b.mean()*1e4:+.1f} bp | difference t={(a.mean()-b.mean())/se:+.2f} | gross per month {a.sum()/len(a)*3*1e2:+.3f}% vs round-trip cost at 2bp/trade 0.04%")
