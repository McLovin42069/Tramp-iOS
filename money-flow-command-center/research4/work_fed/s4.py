from base import *
s=slice("2000",None); b=R["SPY"][s]
k=k_since(Fc)
def evenmask(sh=0, L5=5):
    # days relative to FOMC (day 0). even weeks start at -1+sh
    rel=k.copy()
    m=pd.Series(False,index=idx)
    for w in (0,2,4,6):
        for d in range(-1+sh+5*w, -1+sh+5*w+5):
            m |= (rel==d) if d>=0 else flag(Fc,d)
    return m
for sh in (-2,-1,0,1,2):
    m=evenmask(sh)
    print("shift",sh, cmp(R["SPY"][s],m[s])["t_diff"], ev(hold(m,"SPY",2.0),b,keys=("t","alpha_t","ann_return_pct","positive_years","first_half_ann_pct","second_half_ann_pct")))
m=evenmask(0)
e=lib4.ts_eval(hold(m,"SPY",2.0),b); print(e["by_year_pct"]); 
# long even / short odd
pos=(m.astype(float)*2-1).shift(-1).fillna(0).rename("SPY")
for c in (2.0,1.0):
    r=lib4.daily_strategy(pos,L,c,exec="same_close")[s]; print("L/S",c,ev(r,b)); 
print(lib4.ts_eval(r,b)["by_year_pct"])
# other assets even weeks
for tk in ["QQQ","IWM","EFA","EEM","TLT","GLD"]:
    r=R[tk][s].dropna(); print(tk, cmp(r,m.reindex(r.index)), subs(r,m.reindex(r.index)))
# pre-2000 not available in calendar. trades per year
print("switches/yr", m[s].astype(int).diff().abs().sum()/19)
# day-of-cycle profile
r=R["SPY"][s]; prof=r.groupby(k[s]).agg(["mean","count"]); print((prof["mean"]*1e4).round(1).iloc[:36].to_dict())
