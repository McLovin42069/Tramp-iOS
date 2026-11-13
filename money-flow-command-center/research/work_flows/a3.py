from common import *
def panel(sig, cols, h, hedge="SPY", start=None, end=None):
    """per date: mean_i sig_i * fwd excess ret_i ; non-overlap t (avg over offsets)"""
    c = navc[cols]
    f = c.shift(-h-1)/c.shift(-1)-1
    if hedge: f = f.sub(navc[hedge].shift(-h-1)/navc[hedge].shift(-1)-1, axis=0)
    p = (sig[cols].clip(-3,3) * f).mean(axis=1).dropna()
    if start: p = p[p.index>=start]
    if end: p = p[p.index<=end]
    ts=[]
    for off in range(0,h+1,max(1,(h+1)//4)):
        d=p.iloc[off::h+1]; ts.append(d.mean()/d.std()*np.sqrt(len(d)))
    return round(float(np.mean(ts)),2), round(float(p.mean()*1e4),2)
def show(name, sig, cols, hedge="SPY"):
    print(f"{name:26s}", end=" ")
    for h in (5,20):
        print(f"h{h}: long {panel(sig,cols,h,hedge)} pre16 {panel(sig,cols,h,hedge,end='2016-11-01')} disc {panel(sig,cols,h,hedge,start='2016-11-14')}", end=" | ")
    print()
SI = SECT+IND
for w in (5,20,60):
    f = FLP.rolling(w, min_periods=w//2).sum()
    show(f"own zflow{w} sect", z(f), SECT)
    show(f"own zflow{w} ind", z(f), IND)
# extremes only
f5 = z(FLP.rolling(5).sum()); 
show("extreme |z5|>2 sect+ind", f5.where(f5.abs()>2, 0), SI)
f20 = z(FLP.rolling(20).sum())
show("extreme |z20|>2 sect+ind", f20.where(f20.abs()>2, 0), SI)
# short-vehicle funds (create-to-lend): XRT XOP KRE XBI XHB
SV = ['XRT','XOP','KRE','XBI','XHB']
show("own zflow20 shortveh", f20, SV)
show("own zflow5 shortveh", f5, SV)
# flow-return divergence, time-series version: sign(ret20) != sign(flow20)
r20 = navc/navc.shift(20)-1
dv = (np.sign(r20) * -np.sign(FLP.rolling(20).sum()))   # +1 when price and flow disagree; direction = price
show("diverg: follow price when flow disagrees", (np.sign(r20)).where(dv>0,0), SI)
show("agree: follow price when flow agrees", (np.sign(r20)).where(dv<0,0), SI)
# bond funds own flow (unhedged)
show("own zflow20 bonds unhedged", f20, [b for b in BOND if b!='BIL'], None)
show("own zflow60 bonds unhedged", z(FLP.rolling(60).sum()), [b for b in BOND if b!='BIL'], None)
# JNK flow -> JNK ; breadth of sector inflows -> SPY ; expiry-filtered SPY flow
print("jnk z5->JNK", pred(f5["JNK"], "JNK"), "disc", pred(f5["JNK"], "JNK", start="2016-11-14"))
print("jnk z20->JNK", pred(f20["JNK"], "JNK"), "disc", pred(f20["JNK"], "JNK", start="2016-11-14"))
br = (FLP[SECT].rolling(20).sum()>0).where(FLP[SECT].notna()).mean(axis=1)
print("sector inflow breadth20 -> SPY", pred(br), "disc", pred(br, start="2016-11-14"))
# SPY flow ex expiry weeks (3rd Friday +-3 trading days)
idx = FLP.index; third = pd.Series(((idx.day>=15)&(idx.day<=21)&(idx.dayofweek==4)), index=idx)
near = third.rolling(7, center=True, min_periods=1).max().astype(bool)
sx = FLP["SPY"].where(~near, 0).rolling(60).sum()
print("spy flow60 ex-expiry -> SPY", pred(sx), "pre16", pred(sx, end="2016-11-01"), "disc", pred(sx, start="2016-11-14"))
sx = FLP["SPY"].where(near, 0).rolling(60).sum()
print("spy flow60 expiry-only -> SPY", pred(sx), "pre16", pred(sx, end="2016-11-01"), "disc", pred(sx, start="2016-11-14"))
s120 = FLP["SPY"].rolling(120).sum()
print("spy flow120 -> SPY", pred(s120), "pre16", pred(s120, end="2016-11-01"), "disc", pred(s120, start="2016-11-14"))
