import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research")
import lib, numpy as np, pandas as pd
D = lib.load()
S = D["spdr"]
so, nav, tna = S["so"], S["nav"], S["tna"]
# daily flow as fraction of assets; public next day -> shift(1)
fl_raw = so.pct_change(fill_method=None)
fl_raw = fl_raw.where(fl_raw.abs() < 0.5)          # guard against splits / data errors
FLP = fl_raw.shift(1)                               # usable at close t
FLD = (so.diff() * nav).shift(1)                    # dollar flow usable at close t
TNA = tna.shift(1)
NAVR = nav.pct_change(fill_method=None)
NAVR = NAVR.where(NAVR.abs() < 0.3)
# long-history D-like dict on NAV (price return)
navc = (1 + NAVR.fillna(0)).cumprod().where(nav.notna())
EQ = ['XLK','XLC','XLY','XLP','XLF','XLV','XLE','XLI','XLB','XLU','XLRE','XBI','XOP','XME','XHB','XRT','KRE','KBE','XSD','XAR','KIE','XES','XPH','XSW','XTN','SPY','DIA','MDY','SPYG','SPYV','SPMD','SPSM','SPYD','SDY','RWR','SPDW','SPEM','FEZ','GXC','SPEU','GNR']
SECT = ['XLK','XLY','XLP','XLF','XLV','XLE','XLI','XLB','XLU','XLC','XLRE']
IND = ['XBI','XOP','XME','XHB','XRT','KRE','KBE','XSD','XAR','KIE','XES','XPH','XSW','XTN']
BOND = ['BIL','SPTS','SPTI','SPTL','SPIP','SPAB','SPIB','SPSB','SPLB','JNK','SJNK','BWX','CWB','SPMB']
def mkD(cols, group=None):
    meta = pd.DataFrame({"cls": "X", "group": "X", "core": True}, index=cols)
    if group: meta["group"] = [group.get(c, "X") for c in cols]
    return {"C": navc[cols], "meta": meta}
DL = mkD(list(so.columns))
def pred(sig, tgt="SPY", hs=(5, 20, 60), start=None, end=None, C=None):
    """non-overlapping predictive test: corr of signal(t) with fwd return close t+1 -> t+1+h; returns {h:(t, n)}"""
    c = (navc if C is None else C)[tgt]
    out = {}
    for h in hs:
        f = c.shift(-h - 1) / c.shift(-1) - 1
        df = pd.concat([sig, f], axis=1).dropna()
        if start: df = df[df.index >= start]
        if end: df = df[df.index <= end]
        ts = []
        for off in range(0, h + 1, max(1, (h + 1) // 4)):   # average over offsets
            d = df.iloc[off::h + 1]
            r = np.corrcoef(d.iloc[:, 0], d.iloc[:, 1])[0, 1]
            ts.append(r * np.sqrt(len(d) - 2) / np.sqrt(1 - r * r))
        out[h] = (round(float(np.mean(ts)), 2), len(df) // (h + 1))
    return out
def z(x, w=250, mp=120):
    return (x - x.rolling(w, min_periods=mp).mean()) / x.rolling(w, min_periods=mp).std()
