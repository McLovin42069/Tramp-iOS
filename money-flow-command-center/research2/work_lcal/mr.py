from h import *
def rsi(s, n=2):
    d = s.diff(); up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100/(1+up/dn)
def state(entry, exit_):
    pos = np.zeros(len(entry)); on = False
    for i,(a,b) in enumerate(zip(entry.values, exit_.values)):
        if on and b: on = False
        elif (not on) and a: on = True
        pos[i] = on
    return pd.Series(pos, index=entry.index)
def sigs(t):
    s = px(t); r = s.pct_change(); out = {}
    up = r > 0; ma5 = s.rolling(5).mean(); ma200 = s.rolling(200).mean(); R = rsi(s)
    dn3 = (r<0)&(r.shift(1)<0)&(r.shift(2)<0)
    out['3down->firstup'] = state(dn3, up)
    out['rsi2<10->c>ma5'] = state(R<10, s>ma5)
    out['rsi2<10->firstup'] = state(R<10, up)
    out['rsi2<10&>ma200->c>ma5'] = state((R<10)&(s>ma200), s>ma5)
    out['rsi2<10&<ma200->c>ma5'] = state((R<10)&(s<ma200), s>ma5)
    vol = r.rolling(20).std().shift(1)
    out['drop<-1.5sig 1day'] = (r < -1.5*vol).astype(float)
    out['drop<-1.5sig->firstup'] = state(r < -1.5*vol, up)
    out['down day -> 1day'] = (r<0).astype(float)
    return out
if __name__ == "__main__":
    for t in ['SPY','QQQ','IWM']:
        for k,p in sigs(t).items():
            for ex in ['same_close','next_close']:
                r,e = ev(p,t,exec=ex,label=k+' '+ex[:4]); print('    ',dec(r))
