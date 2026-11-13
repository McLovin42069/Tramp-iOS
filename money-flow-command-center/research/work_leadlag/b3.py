import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research"); import lib
import pandas as pd, numpy as np
D = lib.load(); C=D["C"]; m=D["meta"]
r1=C.pct_change(fill_method=None)
def show(name, W, bench=None):
    ret=lib.weights_to_returns(W, D); ret=ret[ret.index>=C.index[280]]
    r=lib.ts_eval(ret, r1[bench] if bench else None)
    by=r["by_year_pct"]; pos=sum(v>0 for v in by.values())
    print(f"{name:40s} ann={r['ann_return_pct']:+.2f} vol={r['ann_vol_pct']:.1f} SR={r['sharpe']:+.2f} t={r['t']:+.2f} a_t={r.get('alpha_t',float('nan')):+.2f} beta={r.get('beta',float('nan')):+.2f} bSR={r.get('bench_sharpe',float('nan')):+.2f} yrs+={pos}/{len(by)} dd={r['max_drawdown_pct']:.0f}")
    return r
n=0
# credit leads equity: HYG vs IEF relative return over L days >0 -> long SPY else cash
for L in [5,20,60]:
    s=(C['HYG'].pct_change(L)-C['IEF'].pct_change(L))
    W=pd.DataFrame({'SPY':(s>0).astype(float)}); show(f"credit HYG-IEF {L}d >0 -> SPY",W,'SPY'); n+=1
# pure long-short version to isolate: sign
s=(C['HYG'].pct_change(20)-C['IEF'].pct_change(20)); W=pd.DataFrame({'SPY':np.sign(s)}); show("credit20 sign L/S SPY",W,'SPY'); n+=1
# equity leads credit: SPY 5/20d -> HYG long/flat
for L in [5,20]:
    W=pd.DataFrame({'HYG':(C['SPY'].pct_change(L)>0).astype(float)}); show(f"SPY {L}d>0 -> HYG",W,'HYG'); n+=1
# copper/gold -> EEM ; dollar -> EEM
for L in [20,60]:
    s=C['CPER'].pct_change(L)-C['GLD'].pct_change(L)
    W=pd.DataFrame({'EEM':(s>0).astype(float)}); show(f"Cu/Au {L}d>0 -> EEM",W,'EEM'); n+=1
    s=-C['UUP'].pct_change(L)
    W=pd.DataFrame({'EEM':(s>0).astype(float)}); show(f"USD down {L}d -> EEM",W,'EEM'); n+=1
# COT pooled
cot=D['cot']; MAP={'SP500':'SPY','NASDAQ':'QQQ','UST10Y':'IEF','UST30Y':'TLT','GOLD':'GLD','SILVER':'SLV','COPPER':'CPER','WTI':'USO','EUR':'FXE','JPY':'FXY','USD':'UUP','BTC':'BTC-USD'}
for col in ['spec_net_pct_oi','comm_net_pct_oi']:
    P=cot.pivot_table(index='date',columns='contract',values=col)
    Z=(P-P.rolling(156,min_periods=104).mean())/P.rolling(156,min_periods=104).std()
    Zd=Z.reindex(C.index.union(Z.index)).ffill().reindex(C.index).rename(columns=MAP)
    Zd=Zd[[c for c in Zd.columns if c in C.columns]]
    k=Zd.shape[1]
    for thr in [1.0,1.5]:
        W=(-(Zd>thr).astype(float)+(Zd<-thr).astype(float))/k
        show(f"COT {col[:4]} contrarian |z|>{thr} L/S pooled",W); n+=1
    W=np.sign(Zd).fillna(0)/k; show(f"COT {col[:4]} sign(z) trend pooled",W); n+=1
    # 13w change in positioning
    dP=(P-P.shift(13)); dz=dP/dP.rolling(156,min_periods=104).std()
    dzd=dz.reindex(C.index.union(dz.index)).ffill().reindex(C.index).rename(columns=MAP); dzd=dzd[[c for c in dzd.columns if c in C.columns]]
    W=np.sign(dzd).fillna(0)/k; show(f"COT {col[:4]} 13w chg sign pooled",W); n+=1
print("variants",n)
