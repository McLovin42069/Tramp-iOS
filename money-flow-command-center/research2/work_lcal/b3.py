from h import *
from mr import rsi, state
import warnings; warnings.filterwarnings('ignore')
s=px('SPY'); ma200=s.rolling(200).mean(); ma5=s.rolling(5).mean(); R=rsi(s)
for th in [5,10,15,25]:
    p=state((R<th)&(s>ma200), s>ma5)
    for ex in ['same_close','next_close']:
        r,e=ev(p,'SPY',exec=ex,label=f'rsi2<{th}&up {ex[:4]}'); print('    ',dec(r))
        r,e=ev(p,'SPY',exec=ex,start='2005-01-01',label=f'  2005+',)
v=px('^VIX').reindex(s.index).ffill()
p=state((R<10)&(s>ma200)&(v>v.rolling(10).mean()), s>ma5); r,e=ev(p,'SPY',label='rsi2<10&up&vix>ma10'); print('    ',dec(r))
