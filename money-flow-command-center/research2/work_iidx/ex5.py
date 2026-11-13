exec(open("ex4.py").read().split("sg=np.sign")[0])
sg=np.sign; eq=G["eq"]; r1=R[0]; d6=cum(0,5); m2=cum(0,1); day=cum(0,6)
run(sg(r1)*big(r1,2),[6],eq,"mom r1(2s)->last eq5")
run(sg(r1)*big(r1,2),[5,6],eq,"mom r1(2s)->last2 eq5")
run(-sg(d6)*big(d6,2),[6],eq,"rev day(2s)->last eq5")
run(-sg(R[5])*big(R[5],2),[6],eq,"rev r6(2s)->r7 eq5")
run(sg(m2)*big(m2,2),[2,3,4,5,6],eq,"trend-day 2s ->rest eq5")
run(-sg(m2)*big(m2,2),[2,3,4,5,6],eq,"fade 2s morning ->rest eq5")
run(sg(R[5])*big(R[5],1),[6],["TLT","IEF"],"mom r6(big)->r7 bond")
def on(sig,cols,name):
    pos=pd.DataFrame(0.0,index=C.index,columns=cols); m=tm==times[6]
    pos.loc[m]=sig.reindex(dn[m])[cols].fillna(0).values/len(cols)
    ret=lib2.bar_strategy(pos,I); e=lib2.ts_eval(ret); q=ret.groupby(ret.index.to_period("Q")).sum()
    print("%-38s t=%5.2f ann=%6.2f vol=%5.2f 1h=%6.2f 2h=%6.2f Q+=%d/%d mde=%.1f"%(name,e["t"],e["ann_return_pct"],e["ann_vol_pct"],e["first_half_ann_pct"],e["second_half_ann_pct"],(q>0).sum(),len(q),e["mde_ann_pct"]))
on((day<0)&big(day,1.5),eq,"buy ON+1h after big down day eq5")
on(sg(day)*big(day,1.5),eq,"mom ON+1h after big day eq5")
# gross reference: mean per-trade bps of unconditional sign rules
for nm,s,y in [("mom r1->last",sg(r1),R[6]),("rev r6->r7",-sg(R[5]),R[6]),("rev day->last",-sg(d6),R[6]),("rev r1->r2",-sg(r1),R[1]),("mom r2->r3",sg(R[1]),R[2])]:
    g=(s[eq]*y[eq]).mean(axis=1).dropna(); print(nm,"gross bps/trade %.2f t=%.2f"%(g.mean()*1e4,g.mean()/g.std()*len(g)**.5))
