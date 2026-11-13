from cal import *
D = lib.load(); C = D["C"]; V = D["V"]
US=lib.tickers(D,cls="US Stocks",core=False); ALL=lib.tickers(D,cls=["US Stocks","Europe Stocks","Asia Stocks"],core=False)
R=C[ALL].pct_change(fill_method=None); R=R.where(V[ALL]>0)   # ignore holiday/ffilled rows
RR=lib.residual(R,D)
vol=RR.rolling(60,min_periods=40).std().shift(1); z=RR/vol
relv=V[ALL].where(V[ALL]>0)/V[ALL].where(V[ALL]>0).rolling(60,min_periods=40).median().shift(1)
N=[0]
def x(name,sig,h,cols=US,**k):
    N[0]+=1; e=lib.xs_eval(sig,D,h,cols=cols,**k)
    print(f"{name:38s} h={h:2d} spread={e['spread_pct']:6.3f} t={e['t']:5.2f} n={e['n_eff']} ic_t={e['ic_t']:5.2f} net={e['net_spread_pct']:6.3f} turn={e['turnover']:.2f} h1={e['first_half_pct']:.3f} h2={e['second_half_pct']:.3f} nps={e['names_per_side']:.0f} yrs={list(e['by_year_pct'].values())}")
    return e
for un,cols in [("US",US),("ALL",ALL)]:
    print("=====",un)
    for h in [1,5,20]:
        x("1d resid z",z,h,cols,step=1 if h==1 else 5)
    for h in [5,20]:
        x("1d z * relvol",z*relv.clip(upper=5),h,cols)
    # biggest move in last 20d, signed, on high volume
    zz=(z*np.sqrt(relv.clip(0.2,5)))
    a=zz.abs().rolling(20,min_periods=10).max(); big=zz.where(zz.abs()>=a-1e-12).ffill(limit=19)
    x("signed max|z*sqrt(rv)| 20d",big,20,cols); x("signed max|z*sqrt(rv)| 20d",big,5,cols)
    hi=C[ALL]/C[ALL].rolling(250,min_periods=200).max()
    x("52w-high proximity",hi,20,cols); x("52w-high proximity",hi,5,cols)
    lo=C[ALL]/C[ALL].rolling(250,min_periods=200).min()
    x("52w-low distance",lo,20,cols)
    N[0]+=1
    seas=sum(C[ALL].shift(250*k-21)/C[ALL].shift(250*k)-1 for k in [1])  ; x("same-month 1y ago",seas,20,cols)
    seas=sum((C[ALL].shift(250*k-21)/C[ALL].shift(250*k)-1) for k in [1,2,3])/3 ; x("same-month avg 1-3y",seas,20,cols)
print("N",N[0])
