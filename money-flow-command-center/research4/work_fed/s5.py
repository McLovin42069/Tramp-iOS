from base import *
s=slice("2000",None); b=R["SPY"][s]
on,dy=lib4.session_returns(L)
def last_on_or_before(dates):  # map calendar dates to trading days (previous session if holiday)
    out=[]
    for d in dates:
        i=idx.searchsorted(d,side="right")-1
        if i>=0: out.append(idx[i])
    return pd.DatetimeIndex(sorted(set(out)))
months=pd.date_range("1993-01-01","2019-01-01",freq="MS")
ff=[]; of=[]
for m in months:
    d=m+pd.Timedelta(days=(4-m.dayofweek)%7); ff.append(d); of.append(d+pd.Timedelta(days=14))
# jobs: first Friday; if market closed (e.g. Good Friday -> report still released; July 4 -> Thursday), take previous session (approximation)
J=last_on_or_before(ff); OPX=last_on_or_before(of)
J=J[J>="2000"]; 
print("jobs approx n",len(J), "ES-day abs move check: TNX abs chg jobs vs other", C["^TNX"].diff().abs()[s][flag(J)[s]].mean(), C["^TNX"].diff().abs()[s][~flag(J)[s]].mean())
print("== D. jobs day (approx first Friday)")
for tk in ["SPY","TLT","GLD","UUP"]:
    for kk,nm in [(-1,"day before"),(0,"day"),(1,"day after")]:
        m=flag(J,kk); r=R[tk][s].dropna(); mm=m.reindex(r.index)
        print(tk,nm,cmp(r,mm),subs(r,mm))
m=flag(J)[s]; print("SPY overnight into jobs", cmp(on["SPY"][s],m), " day session", cmp(dy["SPY"][s],m))
print("TLT overnight into jobs", cmp(on["TLT"][s].dropna(),m.reindex(on["TLT"][s].dropna().index)))
print("== E. opex")
for tk in ["SPY","QQQ","IWM"]:
    r=R[tk][s].dropna()
    m=flag(OPX).reindex(r.index); print(tk,"opex friday",cmp(r,m),subs(r,m))
    wk=pd.Series(False,index=idx)
    for q in range(0,5): wk|=flag(OPX,-q)
    print(tk,"opex week (Mon-Fri)",cmp(r,wk.reindex(r.index)),subs(r,wk.reindex(r.index)))
    wb=pd.Series(False,index=idx)
    for q in range(5,10): wb|=flag(OPX,-q)
    print(tk,"week before opex",cmp(r,wb.reindex(r.index)),subs(r,wb.reindex(r.index)))
    wa=pd.Series(False,index=idx)
    for q in range(1,6): wa|=flag(OPX,q)
    print(tk,"week after opex",cmp(r,wa.reindex(r.index)),subs(r,wa.reindex(r.index)))
print("== month/quarter turn")
me=pd.Series(idx.month,index=idx); first=(me!=me.shift(1)); qfirst=first&me.isin([1,4,7,10]); last=(me!=me.shift(-1))
for tk in ["SPY","TLT","GLD","EFA"]:
    r=R[tk][s].dropna()
    for nm,m in [("first day of month",first),("first day of quarter",qfirst),("last day of month",last)]:
        mm=m.reindex(r.index); print(tk,nm,cmp(r,mm),subs(r,mm))
print("first day of month SPY strategy", ev(hold(first,"SPY",2.0),b))
print("== F. announcement days union (FOMC + approx jobs)")
U=flag(Fc)|flag(J); r=R["SPY"][s]
print(cmp(r,U[s]),subs(r,U[s]))
for c in (2.0,1.0): print("strategy",c,ev(hold(U,"SPY",c),b))
print("complement:", ev(hold(~U,"SPY",2.0),b,keys=("t","ann_return_pct","sharpe")))
print("== pre-FOMC conditional on VIX (prior close above 1y median, known day before)")
v=C["^VIX"]; hi=(v>v.rolling(252).median()).shift(1,fill_value=False)   # VIX two closes before FOMC close -> known at entry? entry is close t-1, uses VIX close t-1
hi1=(v>v.rolling(252).median()).shift(1,fill_value=False)
m=flag(Fc)&hi1; print("hiVIX",cmp(r,m[s]),subs(r,m[s])); m2=flag(Fc)&~hi1; print("loVIX",cmp(r,m2[s]),subs(r,m2[s]))
print("== EFA/EEM FOMC-day strategies")
for tk in ["EFA","EEM","IWM"]:
    print(tk, ev(hold(flag(Fc),tk,2.0), R[tk][s]))
