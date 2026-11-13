exec(open('h1.py').read().split('if __name__')[0]); exec(open('h2.py').read().split('if __name__=="__main__"')[0].split('\n',1)[1])
f=H["fomc"]; 
for tk in ["ES=F","NQ=F","ZN=F","GC=F"]:
    P=checkpoints(tk); P["p16p"]=P["p16"].shift(1); F=P[P.index.isin(f)]
    print(tk,"FOMC n",len(F),"pre 16->14",tt(F["p14"]/F["p16p"]-1),"| 14->16",tt(F["p16"]/F["p14"]-1))
# intraday momentum / reversal ES,NQ at 1bp: sign(16prev->10) held 10->16 ; sign(16prev->15) held 15->16 ; sign overnight(16->9) held 10->16 reversed
for tk in ["ES=F","NQ=F"]:
    c=Cc[tk].dropna(); P=checkpoints(tk); P["p16p"]=P["p16"].shift(1)
    def strat(sig,enter_h,exit_h,sgn):
        pos=pd.Series(np.nan,index=c.index); td=(c.index+pd.Timedelta(hours=6)).normalize(); h=c.index.hour
        s=pd.Series(np.sign(sig).reindex(td).values,index=c.index).fillna(0)*sgn
        pos[h==enter_h]=s[h==enter_h]; pos[h==exit_h]=0.0
        return lib4.bar_strategy(pos.ffill().fillna(0).to_frame(tk),H,1.0)
    show(f"{tk} mom: sign(16p->10) hold 10->16",strat(P["p10"]/P["p16p"]-1,9,15,1))
    show(f"{tk} mom: sign(16p->15) hold 15->16",strat(P["p15"]/P["p16p"]-1,14,15,1))
    show(f"{tk} mom: sign(10->15) hold 15->16",strat(P["p15"]/P["p10"]-1,14,15,1))
    show(f"{tk} asia->eu: sign(18->02) hold 02->09",strat(P["p02"]/P["o18"]-1,1,8,1))
# hour-of-day ES: mean, t, sign share
for tk in ["ES=F","GC=F"]:
    r=Cc[tk].dropna().pct_change(); g=r.groupby(r.index.hour)
    print(tk," ".join(f"{h}:{m*1e4:.1f}({m/s*n**.5:.1f})" for h,m,s,n in zip(g.mean().index,g.mean(),g.std(),g.size())))
