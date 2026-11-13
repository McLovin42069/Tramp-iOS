from cal import *
D = lib.load(); C = D["C"]; V = D["V"]
US=lib.tickers(D,cls="US Stocks",core=False); ALL=lib.tickers(D,cls=["US Stocks","Europe Stocks","Asia Stocks"],core=False)
EU=lib.tickers(D,cls="Europe Stocks",core=False); AS=lib.tickers(D,cls="Asia Stocks",core=False)
ok=V[ALL]>0
R=C[ALL].pct_change(fill_method=None).where(ok); RR=lib.residual(R,D)
vol=RR.rolling(60,min_periods=40).std().shift(1); z=RR/vol
N=[0]
def x(name,sig,h,cols=US,**k):
    N[0]+=1; e=lib.xs_eval(sig,D,h,cols=cols,**k)
    print(f"{name:30s} h={h:2d} spread={e['spread_pct']:6.3f} t={e['t']:5.2f} n={e['n_eff']} ic_t={e['ic_t']:5.2f} net={e['net_spread_pct']:6.3f} turn={e['turnover']:.2f} h1={e['first_half_pct']:.3f} h2={e['second_half_pct']:.3f} nps={e['names_per_side']:.0f} yrs={list(e['by_year_pct'].values())}")
    return e
x("min z 20d US",z.rolling(20,min_periods=15).min(),20,US)
x("min z 20d ALL",z.rolling(20,min_periods=15).min(),20,ALL)
x("min z 10d US",z.rolling(10,min_periods=8).min(),20,US)
x("min z 40d US",z.rolling(40,min_periods=30).min(),20,US)
x("min z 20d US h5",z.rolling(20,min_periods=15).min(),5,US)
x("min z 20d US q10",z.rolling(20,min_periods=15).min(),20,US,q=0.1)
x("min z 20d EU",z.rolling(20,min_periods=15).min(),20,EU)
x("min z 20d AS",z.rolling(20,min_periods=15).min(),20,AS)
x("max z 20d US",z.rolling(20,min_periods=15).max(),20,US)
