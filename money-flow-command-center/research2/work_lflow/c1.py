from base import *
import warnings; warnings.filterwarnings("ignore")
A=C0.reindex(C.index).ffill(limit=3)
def ls(name, sig, longs, shorts, start="1999-03-01", rebal=5):
    """sig>0 -> long `longs` short `shorts`, total gross 1; reversed when sig<0"""
    s=np.sign(sig).loc[start:].dropna()
    keep=np.arange(len(s))%rebal==0; s=s.where(pd.Series(keep,index=s.index)).ffill()
    pos=pd.DataFrame(0.0,index=s.index,columns=longs+shorts)
    for c in longs: pos[c]=s*0.5/len(longs)
    for c in shorts: pos[c]=-s*0.5/len(shorts)
    return rep(name, run(pos))
tnx=A["^TNX"]; irx=A["^IRX"]; dxy=A["DX-Y.NYB"]
for N in (20,60):
    ls(f"dTNX{N} -> XLF vs XLU", tnx.diff(N), ["XLF"],["XLU"])
ls("d(slope 10y-3m)60 -> XLF vs XLU", (tnx-irx).diff(60), ["XLF"],["XLU"])
ls("dTNX60 -> cyc(XLF,XLI,XLB,XLE) vs def(XLU,XLP,XLV)", tnx.diff(60), ["XLF","XLI","XLB","XLE"],["XLU","XLP","XLV"])
ls("dDXY60 -> def(XLP,XLU,XLV) vs XLE,XLB", dxy.pct_change(60), ["XLP","XLU","XLV"],["XLE","XLB"])
cg=(A["HG=F"]/A["GC=F"])
ls("copper/gold 60d -> cyc vs def", cg.pct_change(60), ["XLI","XLB","XLY","XLF"],["XLU","XLP","XLV"], start="2001-01-01")
ls("copper/gold 20d -> cyc vs def", cg.pct_change(20), ["XLI","XLB","XLY","XLF"],["XLU","XLP","XLV"], start="2001-01-01")
ls("crude 60d -> XLE vs SPY", A["CL=F"].pct_change(60), ["XLE"],["SPY"], start="2001-01-01")
# SPY timing
spy=C["SPY"].pct_change()
def tim(name,w,start):
    r=run(w.loc[start:].rename("SPY").to_frame()); e=lib2.ts_eval(r,spy.reindex(r.index))
    x=r[(r.index.year!=2008)&(r.index.year!=2009)]; ex=lib2.ts_eval(x,spy.reindex(x.index))
    print(f"{name:40s} t={e['t']:5.2f} sh={e['sharpe']:5.2f} (bench {e['bench_sharpe']:.2f}) beta={e['beta']:.2f} alpha={e['alpha_ann_pct']:6.2f} alpha_t={e['alpha_t']:5.2f} ex0809={ex['alpha_t']:5.2f} h1={e['first_half_ann_pct']:.1f} h2={e['second_half_ann_pct']:.1f} mde={e['mde_ann_pct']:.1f}")
tim("SPY long unless TNX 20d rise > +0.25pt", (tnx.diff(20)<0.25).astype(float), "1993-06-01")
tim("SPY long when HYG/IEF 20d > 0", ((A["HYG"]/A["IEF"]).pct_change(20)>0).astype(float).where(A["HYG"].notna()).dropna(), "2007-06-01")
tim("SPY long when copper/gold 60d > 0", (cg.pct_change(60)>0).astype(float).where(cg.notna()).dropna(), "2001-01-01")
