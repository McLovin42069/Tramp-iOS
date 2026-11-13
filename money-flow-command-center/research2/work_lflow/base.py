import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research2"); import lib2
import numpy as np, pandas as pd
L = lib2.load_long()
C=L["C"]; S=L["spdr"]
SEC=["XLK","XLF","XLE","XLV","XLI","XLY","XLP","XLU","XLB"]
def flows(L, tick):
    S=L["spdr"]; so=S["so"][tick]; nav=S["nav"][tick]
    f=(so.diff()*nav); tna=S["tna"][tick]
    return f.reindex(L["C"].index).shift(1), tna.reindex(L["C"].index).shift(1)   # public next day
def ev(ret,bench=None,**k):
    e=lib2.ts_eval(ret,bench,**k); return e
def short(e): 
    return {k:(round(v,2) if isinstance(v,float) else v) for k,v in e.items() if k in("t","sharpe","ann_return_pct","positive_years","first_half_ann_pct","second_half_ann_pct","mde_ann_pct","alpha_t","max_drawdown_pct","from")}
