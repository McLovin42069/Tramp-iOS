import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research2"); import lib2
import numpy as np, pandas as pd, pickle
from scipy.stats import spearmanr
pd.set_option("display.width",250); pd.set_option("display.max_columns",40)
I=lib2.load_intra(); C=I["C"]
R,gap,fh,ETF,G=pickle.load(open("R.pkl","rb"))
def cum(a,b):
    x=1
    for i in range(a,b+1): x=x*(1+R[i])
    return x-1
# spearman for key pairs
pairs={"r4->r5":(R[3],R[4]),"r1->r2":(R[0],R[1]),"r6->r7":(R[5],R[6]),"r2->r3":(R[1],R[2]),"r3->r4":(R[2],R[3]),"r5->r6":(R[4],R[5]),"1-6->last":(cum(0,5),R[6]),"gap->fh":(gap,fh),"r1->last":(R[0],R[6]),"fh->last":(fh,R[6]),"last->nr1":(R[6],R[0].shift(-1))}
out={}
for k,(x,y) in pairs.items():
    o={}
    for g,m in G.items():
        o[g]=round(np.mean([spearmanr(*pd.concat([x[e],y[e]],axis=1).dropna().values.T)[0] for e in m]),3)
    out[k]=o
print(pd.DataFrame(out).T)
print(R[3]["SPY"].abs().sort_values().tail(5)); print(R[4]["SPY"].abs().sort_values().tail(5))
