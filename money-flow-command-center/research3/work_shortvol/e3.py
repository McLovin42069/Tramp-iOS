from base import *
r1, r5, r20 = ratio(1), ratio(5), ratio(20)
z1 = z(r1,60); d5 = r5 - r1.rolling(60,min_periods=30).mean()
rr = lib3.residual(ret, D); rr5 = lib3.residual(Cs.pct_change(5, fill_method=None), D)
xz = lambda x: x.sub(x.mean(axis=1),axis=0).div(x.std(axis=1),axis=0)
aT = np.log(Ts.rolling(5).mean()/Ts.rolling(60,min_periods=30).mean())
aS = np.log(Ss.rolling(5).mean()/Ss.rolling(60,min_periods=30).mean())
offsh = (Ts/Vs.replace(0,np.nan)).clip(upper=1)
aOff = offsh.rolling(5).mean() - offsh.rolling(60,min_periods=30).mean()
# short interest
sh = D["short"]; sh = sh[sh.symbol.isin(cols)].sort_values(["symbol","date"]).copy()
sh["dsi"] = sh.groupby("symbol").si.diff() / sh.adv
P = sh.pivot_table(index="pub_date", columns="symbol", values="dsi", aggfunc="last")
P = P.reindex(P.index.union(sess)).ffill(limit=12).reindex(sess).reindex(columns=cols)
z250 = r20 - r1.rolling(250,min_periods=120).mean()
tests = {
 "z60r1_updays": z1.where(rr>0), "z60r1_downdays": z1.where(rr<0),
 "d5_up5": d5.where(rr5>0), "d5_down5": d5.where(rr5<0),
 "z1_x_ret": xz(z1)*xz(rr), "d5_x_ret5": xz(d5)*xz(rr5),
 "abnT5": aT, "abnS5": aS, "abnOffshare5": aOff, "offshare20": offsh.rolling(20).mean(),
 "dSI": P, "z250_dSIpos": z250.where(P>0), "z250_dSIneg": z250.where(P<0), "z250_x_dSI": xz(z250)*xz(P.clip(-5,5)),
}
import sys
hs = (1,5,20)
for k,v in tests.items():
    for h in hs:
        if k.startswith(("dSI","z250","offshare20")) and h==1: continue
        ev(out(v), h, k)
