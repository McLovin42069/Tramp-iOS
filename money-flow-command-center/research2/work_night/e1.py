from base import *
print(C.shape, C.index[0], C.index[-1])
print(list(C.columns))
T=[c for c in C.columns if not c.startswith("^")]
rows=[]
for c in T:
    s=C[c].dropna()
    if len(s)<500: continue
    o=on[c].dropna(); d=day[c].reindex(o.index)
    dec=(o.index.year//5)*5
    z=(o==0).groupby(dec).mean().round(2).to_dict()
    rows.append(dict(t=c,start=s.index[0].date(),n=len(o),on_ann=o.mean()*252*100,on_t=o.mean()/o.std()*np.sqrt(len(o)),day_ann=d.mean()*252*100,day_t=d.mean()/d.std()*np.sqrt(len(d)),be_bps=o.mean()/2*1e4,zero=z))
print(pd.DataFrame(rows).round(2).to_string())
