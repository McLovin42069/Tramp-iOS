from base import *
vix, v3 = C["^VIX"], C["^VIX3M"]
rv20 = R["SPY"].rolling(20).std()*np.sqrt(252)*100
sig = {"ts":vix/v3, "ts9":C["^VIX9D"]/vix, "ts36":v3/C["^VIX6M"], "vrp":vix-rv20, "vrp_rel":vix/rv20, "vix":vix, "vvix":C["^VVIX"], "skew":C["^SKEW"], "vvix/vix":C["^VVIX"]/vix, "rv20":rv20}
for tgt in ["SPY","SVXY"]:
    f = R[tgt].shift(-2)  # next_close exec
    f20 = (C[tgt].shift(-21)/C[tgt].shift(-1)-1)
    print("=====",tgt)
    for k,s in sig.items():
        for per in (["2006-07","2018-12"],) if tgt=="SVXY" else (["1993","2005"],["2006-07","2012"],["2013","2018"]):
            d = pd.DataFrame({"s":s,"f":f,"f20":f20}).loc[per[0]:per[1]].dropna()
            if len(d)<300: continue
            q = pd.qcut(d.s,5,labels=False,duplicates="drop")
            g = d.groupby(q)
            print(f"{k:9s} {per[0]}-{per[1]} n={len(d)} edges {np.round(d.s.quantile([.2,.4,.6,.8]).values,2)} ann% by quintile {np.round(g.f.mean().values*25200,1)}  vol {np.round(g.f.std().values*1587,0)} f20% {np.round(g.f20.mean().values*100,1)}")
