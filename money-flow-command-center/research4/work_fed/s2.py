from base import *
on,dy = lib4.session_returns(L)
s=slice("2000",None)
fm=flag(Fc)[s]
# alignment check on a hand example: 2008-12-16 FOMC (ZIRP), SPY rose ~+4.6-5%
d=pd.Timestamp("2008-12-16"); r=hold(flag(Fc),"SPY",0.0)
print("align:", R["SPY"][d], r[d], r[idx[idx.get_loc(d)-1]], r[idx[idx.get_loc(d)+1]])
print("\n== A. FOMC day")
for tk in ["SPY","QQQ","IWM","XLF","XLU","XHB","TLT","GLD","UUP","EFA","EEM"]:
    r=R[tk][s]; print(tk, cmp(r,fm), subs(r.dropna(),fm.reindex(r.dropna().index)))
for nm,x in [("SPY overnight",on["SPY"]),("SPY daysession",dy["SPY"]),("QQQ overnight",on["QQQ"]),("QQQ day",dy["QQQ"])]:
    r=x[s]; print(nm, cmp(r,fm), subs(r,fm))
for k in [-3,-2,-1,1,2,3,4,5]:
    m=flag(Fc,k)[s]; print("SPY day",k, cmp(R["SPY"][s],m), " TLT",cmp(R["TLT"][s],m)["mean_in_bp"],cmp(R["TLT"][s],m)["t_diff"], " GLD",cmp(R["GLD"][s],m)["mean_in_bp"],cmp(R["GLD"][s],m)["t_diff"]," UUP",cmp(R["UUP"][s],m)["mean_in_bp"],cmp(R["UUP"][s],m)["t_diff"])
print("\n== strategies")
b=R["SPY"][s]
for c in (2.0,1.0):
    print("SPY cc fomc day",c, ev(hold(flag(Fc),"SPY",c), b))
    pn=flag(Fc).shift(-1,fill_value=False).astype(float).rename("SPY"); z=pn*0
    print("SPY overnight into fomc",c, ev(lib4.segment_strategy(pn,z,L,c)[s], b))
    pdy=flag(Fc).astype(float).rename("SPY")
    print("SPY day session fomc",c, ev(lib4.segment_strategy(z,pdy,L,c)[s], b))
print("uncorrected cal:", ev(hold(flag(Fd),"SPY",2.0), b))
