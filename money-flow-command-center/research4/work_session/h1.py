import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research4"); import lib4, numpy as np, pandas as pd
H=lib4.load_fut(); Cc=H["C"]; Oo=H["O"]
def checkpoints(tk):
    c=Cc[tk].dropna(); o=Oo[tk].reindex(c.index)
    td=(c.index+pd.Timedelta(hours=6)).normalize()
    df=pd.DataFrame({"c":c.values,"o":o.values,"h":c.index.hour,"td":td},index=c.index)
    out={}
    def at(h):  # close of bar starting at hour h
        return df[df.h==h].set_index("td")["c"]
    out["o18"]=df[df.h==18].set_index("td")["o"]
    for name,h in [("p20",19),("p22",21),("p00",23),("p02",1),("p03",2),("p04",3),("p06",5),("p08",7),("p09",8),("p10",9),("p11",10),("p12",11),("p13",12),("p14",13),("p15",14),("p16",15),("p17",16)]:
        out[name]=at(h)
    P=pd.DataFrame(out)
    P=P[P.index.dayofweek<5]
    return P
def tt(x):
    x=x.dropna(); n=len(x); h=n//2
    return "%6.2f (t%5.2f) h1 %6.2f h2 %6.2f"%(x.mean()*1e4,x.mean()/x.std()*n**.5,x.iloc[:h].mean()*1e4,x.iloc[h:].mean()*1e4)
segs=[("post 16-17","p16p","p17p"),("break 17-18","p17p","o18"),("asia 18-02","o18","p02"),("eu 02-04","p02","p04"),("preUS 04-09","p04","p09"),("open 09-10","p09","p10"),("cash 10-16","p10","p16"),("ON 16-09","p16p","p09"),("ON 16-10","p16p","p10"),("full 16-16","p16p","p16")]
if __name__=="__main__":
  for tk in ["ES=F","NQ=F","RTY=F","YM=F","ZN=F","ZB=F","ZT=F","GC=F","SI=F","HG=F","CL=F","NG=F","BZ=F","6E=F","6J=F","BTC=F","ETH=F"]:
    P=checkpoints(tk); P["p16p"]=P["p16"].shift(1); P["p17p"]=P["p17"].shift(1)
    print("==",tk,len(P),P.index[0].date(),P.index[-1].date())
    for n,a,b in segs:
        print("  %-12s"%n,tt(P[b]/P[a]-1))
    wk=P[P.index.dayofweek==0]; print("  weekend gap ",tt(wk["o18"]/wk["p17p"]-1), "n",len(wk))
