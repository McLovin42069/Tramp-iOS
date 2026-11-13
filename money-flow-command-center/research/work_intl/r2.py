from h import *
import pickle; S = pickle.load(open("S.pkl","rb"))
rk = lambda X: X.rank(axis=1, pct=True)
m = D["meta"]
# beta within country vs country median return
cm = r - rr
def rbeta(y, x, w=250):
    return (y.rolling(w, min_periods=150).cov(x)) / x.rolling(w, min_periods=150).var()
beta = pd.DataFrame({c: rbeta(r[c], cm[c]) for c in ALL})
ev("lowbeta250", -z(beta), 20); ev("lowbeta250", -z(beta), 60)
V = D["V"][ALL].replace(0, np.nan)
abv = np.log(V.rolling(20, min_periods=10).mean() / V.rolling(250, min_periods=120).mean())
ev("abnvol20_250", z(abv), 20)
# seasonality: mean residual return in same calendar month in prior years (approx via 20d windows lagged 250,500,..)
mret = rr.rolling(20).sum()
seas = pd.concat([mret.shift(250*k - 20) for k in (1,2,3)]).groupby(level=0).mean()  # the 20d window starting ~ same date k years ago
ev("season_next20", seas.reindex(C.index), 20)
# combos (equal weights, stated up front)
ev("combo resmom+issu", rk(S["resmom12_1"]) + rk(S["issu12"]), 20); ev("combo resmom+issu", rk(S["resmom12_1"]) + rk(S["issu12"]), 60)
c3 = rk(S["resmom12_1"]) + rk(S["issu12"]) + rk(S["str20"])
ev("combo resmom+issu+str20", c3, 20)
# US lead: stock's sensitivity to prior-day SPY return, times latest SPY return(s)
spy = D["C"]["SPY"].pct_change(fill_method=None)
for k in (1,5):
    x = spy.rolling(k).sum()
    b = pd.DataFrame({c: rbeta(rr[c], spy.shift(1)) for c in ALL})   # resid stock return on day t vs SPY on t-1
    sig = b.mul(x, axis=0)
    ev(f"USlead spy{k}d", z(sig), 1); ev(f"USlead spy{k}d", z(sig), 5)
# per-country diagnostics for resmom, h=20 (min_names lowered)
for g in m.loc[ALL,"group"].unique():
    cols = [c for c in ALL if m.loc[c,"group"]==g]
    for k in ("resmom12_1","str20"):
        e = lib.xs_eval(S[k], D, 20, cols=cols, min_names=10)
        print(f"{g:22s} {k:11s} sp={e['spread_pct']:+.2f} t={e['t']:+.2f} n={e['names_per_side']:.0f} yrs+={sum(v>0 for v in e['by_year_pct'].values())}")
