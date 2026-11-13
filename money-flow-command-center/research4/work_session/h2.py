exec(open('h1.py').read().split('if __name__')[0])
def show(name,r,bench=None):
    e=lib4.ts_eval(r,bench)
    if "t" not in e: print(name,e); return e
    q=r.groupby([r.index.year,r.index.quarter]).sum(); m=r.groupby([r.index.year,r.index.month]).apply(lambda g:(1+g).prod()-1)
    print(f"{name:44s} n={e['days']} act={e['active_days_pct']:.0f}% ann={e['ann_return_pct']:6.2f} t={e['t']:5.2f} h1={e['first_half_ann_pct']:6.1f} h2={e['second_half_ann_pct']:6.1f} posQ={(q>0).sum()}/{len(q)} dd={e['max_drawdown_pct']:.1f} wd={r.min()*100:.1f} wm={m.min()*100:.1f} mde={e['mde_ann_pct']:.1f}")
    return e
def window_pos(tk, enter_h, exit_h, cond=None):
    """position 1 from close of bar starting enter_h until close of bar starting exit_h. cond: Series by trade date of the ENTRY bar's calendar... evaluated at entry bar (bool by entry timestamp)."""
    c=Cc[tk].dropna(); h=c.index.hour
    pos=pd.Series(np.nan,index=c.index)
    ent=(h==enter_h)
    if cond is not None: ent=ent & (cond.reindex(c.index)==True).values
    pos[ent]=1.0; pos[(h==exit_h)]=0.0
    if cond is not None: pos[(h==enter_h)&~ent]=0.0
    return pos.ffill().fillna(0.0)
def downday(tk):
    c=Cc[tk].dropna(); c15=c[c.index.hour==15]
    return (c15<c15.shift(1))
if __name__=="__main__":
  for tk in ["ES=F","NQ=F","RTY=F","YM=F"]:
    for c_ in [0.5,1.0]:
        for ex in [8,9]:
            show(f"{tk} always ON 16->{ex+1} c={c_}",lib4.bar_strategy(window_pos(tk,15,ex).to_frame(tk),H,c_))
            show(f"{tk} downday ON 16->{ex+1} c={c_}",lib4.bar_strategy(window_pos(tk,15,ex,downday(tk)).to_frame(tk),H,c_))
    show(f"{tk} asia+eu 18->04 c=1",lib4.bar_strategy(window_pos(tk,17 if False else 16,3).to_frame(tk),H,1.0))
    d=downday(tk); c=Cc[tk].dropna()
    P=checkpoints(tk); on_=(P["p10"]/P["p16"].shift(1)-1); dn=(P["p16"]<P["p16"].shift(1)).shift(1)
    x=on_[dn==True]; y=on_[dn==False]
    print("   gross night 16->10 after down %.2fbp (n%d, t%.2f) after up %.2fbp (n%d, t%.2f)"%(x.mean()*1e4,len(x),x.mean()/x.std()*len(x)**.5,y.mean()*1e4,len(y),y.mean()/y.std()*len(y)**.5))
