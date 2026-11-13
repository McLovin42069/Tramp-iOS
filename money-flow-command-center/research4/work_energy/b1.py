from common import *
E_ = L["eia_weekly"]
def hold(sig, h):  # sig on release days; hold h trading days (None = until next release)
    p = sig.reindex(IX)
    return (p.fillna(0) if h==1 else p.ffill(limit=h-1).fillna(0)) if h else p.ffill().fillna(0)
n=0
for col,etfs in [("crude_stocks",["USO","XLE"]),("gasoline_stocks",["USO"]),("distillate_stocks",["USO"]),("natgas_storage",["UNG"])]:
    s = E_[col].dropna(); sur = seas_surprise(s)
    z = sur/ sur.rolling(104,min_periods=52).std().shift(1)
    sg = rel(-np.sign(z), col)      # draw larger than normal -> long
    for etf in etfs:
        for h in [1,None]:
            ev(f"{col[:8]} surprise sign -> {etf} h={h}", hold(sg,h).rename(etf), bench=etf); n+=1
    # long-only on big draw
    sb = rel((z<-1).astype(float), col)
    ev(f"{col[:8]} big draw long-only {etfs[0]} h=5", hold(sb,5).rename(etfs[0]), bench=etfs[0]); n+=1
# total petroleum
tot = E_[["crude_stocks","gasoline_stocks","distillate_stocks"]].dropna().sum(axis=1)
sg = rel(-np.sign(seas_surprise(tot)),"crude_stocks")
ev("total petroleum surprise -> USO weekly", hold(sg,None).rename("USO"), bench="USO"); n+=1
ev("total petroleum surprise -> XLE weekly", hold(sg,None).rename("XLE"), bench="XLE"); n+=1
# levels
for col,etf in [("crude_stocks","USO"),("crude_stocks","XLE"),("natgas_storage","UNG"),("distillate_stocks","USO")]:
    lv = seas_level(E_[col].dropna())
    ev(f"{col[:8]} level<0.5 of 5y range long {etf}", hold(rel((lv<0.5).astype(float),col),None).rename(etf), bench=etf); n+=1
    ev(f"{col[:8]} level L/S around 0.5 {etf}", hold(rel(np.sign(0.5-lv),col),None).rename(etf), bench=etf); n+=1
print(n)
