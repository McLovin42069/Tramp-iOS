from h import *
# alignment check: position set on day d (same_close) earns return of next trading day
d=px('SPY').index; p=pd.Series(0.0,index=d); p[d[10]]=1
r=run(p,'SPY'); print(d[10],d[11],bh('SPY')[d[11]]); print(r[r!=0])
print("=== TOM: hold days -1..+3 (pos set on day -2 through +2)")
for t in ['SPY','QQQ','IWM','EFA','EEM','^GSPC']:
    d=px(t).index; f,b=tdm(d)
    # day being earned = next day; want next day in {last, 1,2,3}: position at day t set if (b==-2) or f<=2 or b==-1
    pos=((b==-2)|(b==-1)|(f<=2)).astype(float)
    if t=='^GSPC':
        r=bh(t).shift(-1)*pos; r=r.shift(1).dropna(); rest=(bh(t).shift(-1)*(1-pos)).shift(1).dropna()
        print('GSPC gross tom',dec(r,10)); print('GSPC gross rest',dec(rest,10)); continue
    r,e=ev(pos,t,label='TOM -1..+3'); print('   ',dec(r))
    r,e=ev(1-pos,t,label='rest'); print('   ',dec(r))
