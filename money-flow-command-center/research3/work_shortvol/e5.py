from base import *
SV=D["shortvol"]; C=D["C"]
agg = (Ss.sum(axis=1)/Ts.sum(axis=1))
def run(sig_ser, etf, name):
    pos = pd.Series(sig_ser.astype(float), index=sig_ser.index).where(sig_ser.notna()).rename(etf)
    r = lib3.daily_strategy(pos.to_frame(), D, cost_bps=2.0)
    b = C[etf].pct_change(fill_method=None)
    r = r[r.index>="2019-09-01"]
    e = lib3.ts_eval(r, bench=b)
    print(f"{name:28s} {etf} t={e['t']:+.2f} alpha_t={e['alpha_t']:+.2f} ann={e['ann_return_pct']:+.1f} bench={e['bench_ann_pct']:+.1f} beta={e['beta']:.2f} sharpe={e['sharpe']:.2f}/{e['bench_sharpe']:.2f} yrs {e['positive_years']} act={e['active_days_pct']:.0f}%")
for etf in ["SPY","QQQ","IWM","HYG","TLT"]:
    if etf not in SV["short"].columns: print(etf,"missing"); continue
    own = (SV["short"][etf]/SV["total"][etf]).reindex(sess)
    zo = z(own.rolling(5).mean(),250)
    run((zo>0), etf, "own r5 above 250d mean")
    run((zo<0), etf, "own r5 below 250d mean")
    za = z(agg.rolling(5).mean(),250)
    run((za>0), etf, "agg stock r5 above 250d mean")
    run((za<0), etf, "agg stock r5 below 250d mean")
