import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research2"); import lib2
import numpy as np, pandas as pd
I=lib2.load_intra(); C=I["C"]
print(C.shape, C.index[:9], C.index[-3:])
ETF="SPY QQQ IWM DIA XLK XLF XLE XLV XLI XLY XLP XLU XLB XLRE XLC SMH XBI KRE GDX XOP TLT IEF HYG LQD GLD SLV USO UUP EEM EFA FXI EWJ EWZ VNQ RSP".split()
print([e for e in ETF if e not in C.columns])
E=[e for e in ETF if e in C.columns]
print(C[E].isna().sum().sort_values().tail(8))
d=C.index.normalize(); print(pd.Series(d).value_counts().value_counts())
print(pd.Series(C.index.time).value_counts())
r=C[E].pct_change(fill_method=None)
# seasonality by time-of-bar (return over bar ending: bar stamped t return = close(t)/close(prev)); 09:30 bar includes overnight gap
g=r.groupby(r.index.time)
m=g.mean()*1e4; s=g.apply(lambda x: x.mean()/x.std()*np.sqrt(x.count()))
pd.set_option("display.width",250); pd.set_option("display.max_columns",40)
print(m.round(1).T); print(s.round(1).T)
# open-to-close of first bar vs gap
O=I["O"][E]
