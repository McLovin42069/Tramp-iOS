from common import *
tga = L["tga_bn"].reindex(ix).ffill().shift(1)   # known at close of t (published t ~16:00 for t-1) -> with next_close exec safe
rrp = L["rrp_bn"].reindex(ix).ffill()
n=0
for nm,s in [("TGA",tga),("RRP",rrp),("TGA+RRP",tga+rrp)]:
    for h in (5,20,60):
        d = s.diff(h)
        for a in ["SPY","QQQ","IWM","HYG","GLD","BTC-USD"]:
            if nm!="TGA" and a in("IWM","GLD"): continue
            st = d.dropna().index[0]
            pos = (d<0).astype(float).where(d.notna())
            mir = (d>0).astype(float).where(d.notna())
            b = bh(a)
            r = lib4.daily_strategy(pos.rename(a).dropna(), L, 2.0, "next_close"); rm = lib4.daily_strategy(mir.rename(a).dropna(), L, 2.0, "next_close")
            r=r[r.index>=st]; rm=rm[rm.index>=st]
            n+=1
            print(line(f"{nm} d{h} fall->long {a}", r, b)); print(line(f"   mirror (rise->long)", rm, b))
print("variants",n)
