import warnings; warnings.filterwarnings("ignore")
from base import *; from e2 import z, pred
print("== intl premium -> region ETF (tradable lag)")
for f,tk in [("SPDW","EFA"),("SPEM","EEM"),("FEZ","VGK"),("SPEU","VGK"),("GXC","FXI"),("SPDW","EWJ"),("SPEM","SPY"),("SPDW","SPY")]:
    print(f,tk,"raw",pred(P[f],tk,hs=(1,5))); print(f,tk,"z60",pred(z(P[f],60),tk,hs=(1,5,20)))
print("== bond premia -> bond ETFs")
for f,tk in [("SPIB","LQD"),("SPAB","AGG"),("SPTL","TLT"),("SPMB","AGG"),("BWX","FXE"),("CWB","SPY"),("CWB","HYG"),("SJNK","HYG"),("SPIB","HYG"),("SPIP","TIP"),("SPSB","LQD")]:
    print(f,tk,"z60",pred(z(P[f],60),tk)); print(f,tk,"z250",pred(z(P[f],250),tk))
bonds=["JNK","SJNK","CWB","SPIB","SPSB","SPAB","SPTL","SPTI","SPIP","SPMB","BWX"]
credit=["JNK","SJNK","CWB","SPIB","SPSB"]
for nm,g in [("allbond",bonds),("credit",credit)]:
    for n in (60,250):
        a=pd.concat([z(P[f],n) for f in g],axis=1).mean(axis=1,skipna=True)
        for tk in ["HYG","LQD","SPY","AGG"]:
            print(nm,n,tk,pred(a,tk))
