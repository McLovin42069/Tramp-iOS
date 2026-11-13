from h import *
import warnings; warnings.filterwarnings('ignore')
def nxt(mask): return mask.shift(-1).fillna(False).astype(float)
print("== long-history yield check: -d(^TNX) in bp/day, last3 vs first3 vs other, by decade")
y=px('^TNX'); dy=-y.diff()*100; f,b=tdm(y.index)
for lab,m in [('last3',b>=-3),('first3',f<=3),('other',(b<-3)&(f>3))]:
    x=dy[m]; print(lab,' '.join(f"{k}:{v.mean():5.2f}({v.mean()/v.std()*np.sqrt(len(v)):4.1f})" for k,v in x.groupby((x.index.year//10)*10)))
print("== neighbours & other bond instruments")
for t in ['TLT','IEF','ZN=F','ZB=F','LQD','AGG','TIP','SHY','IEI']:
    d=px(t).index; f,b=tdm(d)
    for lab,m in [('last2',b>=-2),('last3',b>=-3),('last4',b>=-4)] if t in('TLT','IEF') else [('last3',b>=-3)]:
        r,e=ev(nxt(m),t,label=lab); print('    ',dec(r))
print("== TLT variants")
d=px('TLT').index; f,b=tdm(d)
r,e=ev(nxt(b>=-3)-nxt(f<=3),'TLT',label='L last3 / S first3'); print('    ',dec(r)); print(e['by_year_pct'])
r,e=ev(1-nxt(f<=3),'TLT',label='hold TLT except first3'); print('    ',dec(r))
r,e=ev(nxt(b>=-3),'TLT',label='last3 next_close-ish cost10',cost=10); print('    ',dec(r))
r1,e1=ev(nxt(b>=-3),'TLT',label='last3',show=False); print(e1['by_year_pct'])
# day-by-day profile
rr=bh('TLT'); print('TLT mean bp by days-remaining:',{k:round(rr[b==k].mean()*1e4,1) for k in range(-8,0)},' by day-of-month:',{k:round(rr[f==k].mean()*1e4,1) for k in range(1,9)})
rr=bh('IEF'); print('IEF mean bp by days-remaining:',{k:round(rr[b==k].mean()*1e4,1) for k in range(-8,0)},' by day-of-month:',{k:round(rr[f==k].mean()*1e4,1) for k in range(1,9)})
print("== combined rebal reversal SPY vs TLT")
s=px('SPY').reindex(d); tl=px('TLT'); ym=[d.year,d.month]
mtd=(s.pct_change().fillna(0).add(1).groupby(ym).cumprod())-(tl.pct_change().fillna(0).add(1).groupby(ym).cumprod())
for k in [-4,-5,-6]:
    sig=mtd.where(b==k).groupby(ym).transform('max'); hold=(b>=k)&(b<=-2)
    sg=-np.sign(sig).fillna(0)*hold
    pos=pd.DataFrame({'SPY':0.5*sg,'TLT':-0.5*sg},index=d)
    r=lib2.daily_strategy(pos,{"C":C[['SPY','TLT']].reindex(d)},exec='same_close'); e=lib2.ts_eval(r)
    print(f"signal at {k}: t={e['t']:.2f} ann={e['ann_return_pct']:.2f} sh={e['sharpe']:.2f} dd={e['max_drawdown_pct']:.1f} py={e['positive_years']} h1={e['first_half_ann_pct']:.1f} h2={e['second_half_ann_pct']:.1f} mde={e['mde_ann_pct']:.1f}",dec(r))
