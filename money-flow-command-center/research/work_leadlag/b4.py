import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research"); import lib
import pandas as pd, numpy as np
D = lib.load(); C=D["C"]; m=D["meta"]; r1=C.pct_change(fill_method=None)
cot=D['cot']; MAP={'SP500':'SPY','NASDAQ':'QQQ','UST10Y':'IEF','UST30Y':'TLT','GOLD':'GLD','SILVER':'SLV','COPPER':'CPER','WTI':'USO','EUR':'FXE','JPY':'FXY','USD':'UUP','BTC':'BTC-USD'}
P=cot.pivot_table(index='date',columns='contract',values='comm_net_pct_oi')
Z=(P-P.rolling(156,min_periods=104).mean())/P.rolling(156,min_periods=104).std()
Zd=Z.reindex(C.index.union(Z.index)).ffill().reindex(C.index).rename(columns=MAP)
vol=r1[Zd.columns].rolling(60).std()
raw=np.sign(Zd).fillna(0)/vol; W=raw.div(raw.abs().sum(axis=1),axis=0).fillna(0)
ret=lib.weights_to_returns(W,D); ret=ret[ret.index>=C.index[280]]
r=lib.ts_eval(ret, r1['SPY']); print("COT comm sign(z) inv-vol", {k:r[k] for k in ['ann_return_pct','ann_vol_pct','sharpe','t','alpha_t','beta','by_year_pct']})
# per-contract contribution
Wl=W.reindex(r1.index).ffill().shift(2); pc=(Wl*r1[W.columns]).loc[ret.index]
print((pc.mean()/pc.std()*np.sqrt(len(pc))).round(2).to_dict())
cols=lib.tickers(D, cls="US Stocks", core=False); g=m["group"].reindex(cols).values
r=r1[cols]; peer=r.T.groupby(g).transform("mean").T
x=lib.xs_eval(peer-r, D, 5, cols=cols); print("US gap1d h5", round(x['spread_pct'],3), round(x['t'],2), round(x['net_spread_pct'],3), x['by_year_pct'])
