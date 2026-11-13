from common import *
print("flow outliers", (fl_raw.abs()>0.2).sum().sum(), "so first rows SPY", so['SPY'].dropna().index[0])
sigs = {}
def agg(cols, w):  # aggregate dollar flow over w days / aggregate tna
    return FLD[cols].rolling(w, min_periods=w//2).sum().sum(axis=1, min_count=1) / TNA[cols].sum(axis=1, min_count=1)
for w in (5, 20, 60):
    sigs[f"spy_flow{w}"] = FLP["SPY"].rolling(w).sum()
    sigs[f"spy_flow{w}_z"] = z(FLP["SPY"].rolling(w).sum())
    sigs[f"eq_exspy_flow{w}_z"] = z(agg([c for c in EQ if c != "SPY"], w))
    sigs[f"sect_flow{w}_z"] = z(agg(SECT, w))
    sigs[f"bond_flow{w}_z"] = z(agg([b for b in BOND if b != "BIL"], w))
    sigs[f"bil_flow{w}_z"] = z(FLP["BIL"].rolling(w).sum())
    sigs[f"jnk_flow{w}_z"] = z(FLP["JNK"].rolling(w).sum())
    sigs[f"tsy_flow{w}_z"] = z(agg(["SPTS","SPTI","SPTL"], w))
    sigs[f"def_minus_cyc{w}_z"] = z(agg(["XLP","XLU","XLV"], w) - agg(["XLK","XLY","XLF","XLI","XLB","XLE"], w))
    sigs[f"bond_minus_eq{w}_z"] = z(agg([b for b in BOND if b != "BIL"], w) - agg(EQ, w))
for k, s in sigs.items():
    print(f"{k:24s} full06-23 {pred(s)}  pre2016 {pred(s, end='2016-11-01')}  disc {pred(s, start='2016-11-14')}")
