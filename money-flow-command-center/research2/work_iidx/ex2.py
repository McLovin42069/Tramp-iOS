import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research2"); import lib2
import numpy as np, pandas as pd
pd.set_option("display.width",250); pd.set_option("display.max_columns",40)
I=lib2.load_intra(); C=I["C"]
ETF="SPY QQQ IWM DIA XLK XLF XLE XLV XLI XLY XLP XLU XLB XLRE XLC SMH XBI KRE GDX XOP TLT IEF HYG LQD GLD SLV USO UUP EEM EFA FXI EWJ EWZ VNQ RSP".split()
G={"eq":"SPY QQQ IWM DIA RSP".split(),"sec":"XLK XLF XLE XLV XLI XLY XLP XLU XLB XLRE XLC SMH XBI KRE XOP VNQ".split(),"intl":"EEM EFA FXI EWJ EWZ".split(),"bond":"TLT IEF HYG LQD".split(),"cmd":"GLD SLV GDX USO UUP".split()}
r=C[ETF].pct_change(fill_method=None)
times=sorted(set(r.index.time)); 
R={i:r[r.index.time==t].set_axis(r.index[r.index.time==t].normalize()) for i,t in enumerate(times)}
days=R[0].index
full=pd.Series(C.index.normalize()).value_counts(); full=full[full==7].index
R={i:x.reindex(days) for i,x in R.items()}
O0=I["O"][ETF]; O0=O0[O0.index.time==times[0]]; O0=O0.set_axis(O0.index.normalize())
C0=C[ETF][C.index.time==times[0]]; C0=C0.set_axis(C0.index.normalize())
gap=(1+R[0])/(C0/O0)-1; fh=C0/O0-1
def cum(a,b): 
    x=1
    for i in range(a,b+1): x=x*(1+R[i])
    return x-1
def corr_t(x,y):
    out={}
    for g,m in G.items():
        cs=[]; 
        for e in m:
            d=pd.concat([x[e],y[e]],axis=1).dropna(); cs.append(np.corrcoef(d.iloc[:,0],d.iloc[:,1])[0,1])
            h=len(d)//2
        out[g]=round(float(np.mean(cs)),3)
    for e in ["SPY","QQQ","IWM","TLT","GLD"]:
        d=pd.concat([x[e],y[e]],axis=1).dropna(); h=len(d)//2
        out[e]="%.2f(%.2f/%.2f)"%(np.corrcoef(d.iloc[:,0],d.iloc[:,1])[0,1],np.corrcoef(d.iloc[:h,0],d.iloc[:h,1])[0,1],np.corrcoef(d.iloc[h:,0],d.iloc[h:,1])[0,1])
    return out
tests={"r1->last":(R[0],R[6]),"r1->last2":(R[0],cum(5,6)),"gap->last":(gap,R[6]),"fh->last":(fh,R[6]),"fh->last2":(fh,cum(5,6)),
"morn(1-3)->aft(4-7)":(cum(0,2),cum(3,6)),"r1-2->rest":(cum(0,1),cum(2,6)),"r1->r2":(R[0],R[1]),"fh->r2":(fh,R[1]),"gap->fh":(gap,fh),"1-6->last":(cum(0,5),R[6]),"1-5->last2":(cum(0,4),cum(5,6)),
"r6->r7":(R[5],R[6]),"mid(3-5)->last":(cum(2,4),R[6]),"last->nextr1":(R[6],R[0].shift(-1)),"last->nextgap":(R[6],gap.shift(-1)),"day->nextr1":(cum(0,6),R[0].shift(-1)),"last2->nextr1":(cum(5,6),R[0].shift(-1)),
"r2->r3":(R[1],R[2]),"r3->r4":(R[2],R[3]),"r4->r5":(R[3],R[4]),"r5->r6":(R[4],R[5])}
print("corr 1se ~ 0.046")
print(pd.DataFrame({k:corr_t(*v) for k,v in tests.items()}).T)
import pickle; pickle.dump((R,gap,fh,ETF,G),open("R.pkl","wb"))
