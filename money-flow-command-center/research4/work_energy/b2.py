from common import *
T = L["temp_c"]; P = L["precip_mm"]
def anomaly(x):  # day-of-year norm from prior years only (smoothed +-7 days), expanding
    df = pd.DataFrame({'v':x.rolling(15,center=False,min_periods=5).mean()})  # trailing-15d mean per date
    doy = np.minimum(x.index.dayofyear,365)
    norm = df['v'].groupby(doy).transform(lambda g: g.shift(1).expanding(min_periods=5).mean())
    return x - norm
gas = ["Chicago","New_York","Boston","Detroit","Minneapolis","Philadelphia","Atlanta","Dallas","Houston","Denver"]
hdd = (18.3-T[gas]).clip(lower=0).mean(axis=1); cdd=(T[gas]-18.3).clip(lower=0).mean(axis=1)
dd = hdd+cdd; a = anomaly(dd)   # demand anomaly (cold in winter / hot in summer)
az = a/ a.rolling(365*3,min_periods=365).std().shift(1)
n=0
m = pd.Series(az.index.month, index=az.index); winter = m.isin([11,12,1,2,3]); summer=m.isin([6,7,8])
def toix(s): return s.reindex(IX, method='ffill')
for k in [1,5,15]:
    s = az.rolling(k).mean()
    ev(f"DD anomaly {k}d sign -> UNG L/S", toix(np.sign(s)).rename("UNG"), bench="UNG"); n+=1
ev("DD anom 5d >1 winter long UNG", toix(((az.rolling(5).mean()>1)&winter).astype(float)).rename("UNG"), bench="UNG"); n+=1
ev("DD anom 5d >1 summer long UNG", toix(((az.rolling(5).mean()>1)&summer).astype(float)).rename("UNG"), bench="UNG"); n+=1
ev("DD anom 5d sign -> XLU L/S", toix(np.sign(az.rolling(5).mean())).rename("XLU"), bench="XLU"); n+=1
ev("DD anom 5d >1 long XLU", toix((az.rolling(5).mean()>1).astype(float)).rename("XLU"), bench="XLU"); n+=1
ev("cold winter 5d sign -> USO (heating oil proxy)", toix((np.sign(az.rolling(5).mean())*winter)).rename("USO"), bench="USO"); n+=1
# change in anomaly (new info)
ch = az.rolling(3).mean()-az.rolling(3).mean().shift(3)
ev("DD anom change 3d sign -> UNG", toix(np.sign(ch)).rename("UNG"), bench="UNG"); n+=1
# Wed-before-storage report: week's anomaly (Sat-Fri) known by Fri; hold Fri close->Thu close
# corn belt
cb = ["Des_Moines","Springfield_IL","Lincoln_NE","Indianapolis"]
ta = anomaly(T[cb].mean(axis=1)); pr = P[cb].mean(axis=1).rolling(30).sum(); pa = anomaly(pr)
taz = ta.rolling(10).mean(); taz = taz/ta.rolling(10).mean().rolling(365*3,min_periods=365).std().shift(1)
paz = pa/pa.rolling(365*3,min_periods=365).std().shift(1)
jja = m.isin([6,7,8])
hotdry = (taz - paz)/2
for etf in ["CORN","SOYB"]:
    ev(f"corn belt hot&dry sign JJA -> {etf} L/S", toix(np.sign(hotdry)*jja).rename(etf), bench=etf); n+=1
    ev(f"corn belt hot&dry>1 JJA long {etf}", toix(((hotdry>1)&jja).astype(float)).rename(etf), bench=etf); n+=1
# futures check (signal only): next-day ZC=F return by hotdry tercile in JJA, since 2000, excluding nothing
r = R["ZC=F"].shift(-1); h = toix(hotdry); jj = pd.Series(IX.month,index=IX).isin([6,7,8])
d = pd.DataFrame({'r':r,'h':h})[jj].dropna(); 
print("ZC=F next-day ret JJA by hotdry sign:", d.groupby(np.sign(d.h))['r'].agg(['mean','std','count']).assign(t=lambda x:x['mean']/x['std']*np.sqrt(x['count'])))
r = R["NG=F"].shift(-1); d = pd.DataFrame({'r':r,'h':toix(az.rolling(5).mean())}).dropna()
print("NG=F next-day by DD anom sign:", d.groupby(np.sign(d.h))['r'].agg(['mean','std','count']).assign(t=lambda x:x['mean']/x['std']*np.sqrt(x['count'])))
print(n+2)
