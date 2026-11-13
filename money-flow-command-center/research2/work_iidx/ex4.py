import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research2"); import lib2
import numpy as np, pandas as pd, pickle
pd.set_option("display.width",250); pd.set_option("display.max_columns",40)
I=lib2.load_intra(); C=I["C"]; V=I["V"]
R,gap,fh,ETF,G=pickle.load(open("R.pkl","rb"))
times=sorted(set(C.index.time)); dn=C.index.normalize(); tm=np.array(C.index.time)
def cum(a,b):
    x=1
    for i in range(a,b+1): x=x*(1+R[i])
    return x-1
def run(sig, hold, cols, name, bench=None):
    """sig: DataFrame day x ETF of desired position (-1/0/1), known before first hold bar. hold: list of bar idx (same day; idx>=1)."""
    sig=sig[cols].fillna(0)/len(cols)
    pos=pd.DataFrame(0.0,index=C.index,columns=cols)
    for j in hold:
        m=tm==times[j-1]
        pos.loc[m]=sig.reindex(dn[m]).values
    ret=lib2.bar_strategy(pos,I)
    e=lib2.ts_eval(ret,bench)
    q=ret.groupby(ret.index.to_period("Q")).sum(); 
    print("%-38s t=%5.2f ann=%6.2f vol=%5.2f 1h=%6.2f 2h=%6.2f Q+=%d/%d act=%3.0f%% mde=%.1f"%(name,e["t"],e["ann_return_pct"],e["ann_vol_pct"],e["first_half_ann_pct"],e["second_half_ann_pct"],(q>0).sum(),len(q),e["active_days_pct"],e["mde_ann_pct"]))
    return ret
def big(x,k,w=60):  # |x| > k * trailing std (prior days only)
    return x.abs()>k*x.rolling(w,min_periods=20).std().shift(1)
sg=np.sign
eq=G["eq"]; n=0
r1=R[0]
for cols,nm in [(["SPY"],"SPY"),(eq,"eq5"),(["TLT","IEF"],"bond"),(["GLD","SLV"],"metal")]:
    run(sg(r1),[6],cols,f"mom r1->last {nm}"); run(sg(r1),[5,6],cols,f"mom r1->last2 {nm}"); n+=2
run(sg(r1)*big(r1,1),[6],eq,"mom r1(big1)->last eq5"); run(sg(fh)*big(fh,1),[6],eq,"mom fh(big1)->last eq5"); n+=2
# high first-hour volume
V0=V[ETF][tm==times[0]]; V0=V0.set_axis(V0.index.normalize()); hv=V0>V0.rolling(20).median().shift(1)*1.3
run(sg(r1)*hv,[6],eq,"mom r1->last hiVol eq5"); n+=1
run(-sg(r1),[1],eq,"rev r1->r2 eq5"); run(-sg(r1)*big(r1,1),[1],eq,"rev r1(big)->r2 eq5"); n+=2
run(sg(R[1]),[2],eq,"mom r2->r3 eq5"); run(sg(R[3]),[4],eq,"mom r4->r5 eq5"); n+=2
run(-sg(R[5]),[6],eq,"rev r6->r7 eq5"); run(-sg(R[5])*big(R[5],1),[6],eq,"rev r6(big)->r7 eq5"); n+=2
d6=cum(0,5)
run(-sg(d6),[6],eq,"rev day(1-6)->last eq5"); run(-sg(d6)*big(d6,1),[6],eq,"rev day(big)->last eq5"); run(-sg(d6)*big(d6,1),[6],G["intl"],"rev day(big)->last intl"); n+=3
m2=cum(0,1)
run(sg(m2)*big(m2,1),[2,3,4,5,6],eq,"trend-day r1-2 big ->rest eq5"); run(sg(m2)*big(m2,1.5),[2,3,4,5,6],G["eq"]+G["sec"],"trend-day big1.5 ->rest eq+sec"); n+=2
m3=cum(0,2); run(sg(m3),[3,4,5,6],eq,"morn->aft eq5"); n+=1
# seasonality
one=pd.DataFrame(1.0,index=r1.index,columns=ETF)
run(one,[5],["USO"],"long USO 14:30 bar"); run(one,[4],["GLD","SLV"],"long GLD/SLV 13:30 bar"); run(one,[6],["TLT","IEF"],"long TLT/IEF 15:30 bar"); n+=3
run(-one,[6],["XLE","XOP","KRE"],"short XLE/XOP/KRE 15:30 bar"); n+=1
# overnight+first hour: pos at bar 6 held into next day's bar 0
def on(sigfn,cols,name):
    pos=pd.DataFrame(0.0,index=C.index,columns=cols); m=tm==times[6]
    pos.loc[m]=sigfn.reindex(dn[m])[cols].fillna(0).values/len(cols)
    ret=lib2.bar_strategy(pos,I); e=lib2.ts_eval(ret); q=ret.groupby(ret.index.to_period("Q")).sum()
    print("%-38s t=%5.2f ann=%6.2f vol=%5.2f 1h=%6.2f 2h=%6.2f Q+=%d/%d mde=%.1f"%(name,e["t"],e["ann_return_pct"],e["ann_vol_pct"],e["first_half_ann_pct"],e["second_half_ann_pct"],(q>0).sum(),len(q),e["mde_ann_pct"]))
on(one,["SPY","QQQ"],"long ON+1h SPY/QQQ"); on(one,["GLD"],"long ON+1h GLD"); n+=2
on(-sg(R[6]),G["intl"],"rev last->next ON intl"); on(-sg(R[6])*big(R[6],1),eq,"rev last(big)->next ON eq5"); n+=2
day=cum(0,6); on(sg(day),eq,"mom day->next ON eq5"); n+=1
# SPY leads others by one bar
r=C[ETF].pct_change(fill_method=None)
others=[e for e in G["sec"]+G["intl"] ]
lead=r["SPY"]; nxt=r[others].shift(-1); own=r[others]
intr=tm!=times[6]
resid_corr={e:np.corrcoef(*pd.concat([lead-own[e],nxt[e]],axis=1)[intr].dropna().values.T)[0,1] for e in others}
print("corr(SPY_b - X_b, X_b+1) intraday:",pd.Series(resid_corr).round(3).to_dict())
gapx=(lead-own[others].T).T if False else own.rsub(lead,axis=0)
sgn=np.sign(gapx)*(gapx.abs()>gapx.abs().rolling(140).quantile(0.9).shift(1))
pos=(sgn/len(others)).where(pd.Series(intr,index=C.index),0.0).fillna(0)
ret=lib2.bar_strategy(pos,I); e=lib2.ts_eval(ret); print("SPY-lead catch-up top-decile gaps: t=%.2f ann=%.2f mde=%.1f"%(e["t"],e["ann_return_pct"],e["mde_ann_pct"])); n+=1
print("variants",n)
