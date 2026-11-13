from h import *
import warnings; warnings.filterwarnings('ignore')
def nxt(mask):  # position today so that we hold over the NEXT trading day when mask(next day) is true (calendar known in advance)
    return mask.shift(-1).fillna(False).astype(float)
print("=== bonds: last N days of month / first days")
for t in ['TLT','IEF']:
    d=px(t).index; f,b=tdm(d)
    for lab,m in [('last3',b>=-3),('last5',b>=-5),('last1',b==-1),('first3',f<=3),('days 4-9',(f>=4)&(f<=9))]:
        r,e=ev(nxt(m),t,label=lab); print('    ',dec(r))
    q=pd.Series(d.month.isin([3,6,9,12]),index=d)
    r,e=ev(nxt((b>=-3)&q),t,label='last3 quarter-end'); print('    ',dec(r))
    r,e=ev(nxt((b>=-3)&~q),t,label='last3 non-quarter'); print('    ',dec(r))
print("=== rebalancing reversal: SPY-TLT in last 4 days conditional on month-to-date spread")
s=px('SPY'); tl=px('TLT'); d=tl.index; s=s.reindex(d); f,b=tdm(d)
ym=[d.year,d.month]
mtd_s=s.pct_change().fillna(0).add(1).groupby(ym).cumprod()-1; mtd_t=tl.pct_change().fillna(0).add(1).groupby(ym).cumprod()-1
spread=(mtd_s-mtd_t)
for thr in [0.0,0.03]:
    sig=spread.where(b==-5).groupby(ym).transform('max')  # spread measured at close of day -5, hold days -4..-1
    hold=(b>=-5)&(b<=-2)   # positions set at closes -5..-2 earn days -4..-1
    for lab,w in [('stk won -> long TLT short SPY',(sig>thr)),('stk lost -> long SPY short TLT',(sig<-thr))]:
        sgn = 1 if 'lost' in lab else -1
        pos=pd.DataFrame({'SPY':0.5*sgn*(w&hold),'TLT':-0.5*sgn*(w&hold)},index=d).astype(float)
        Ls={"C":C[['SPY','TLT']].reindex(d)}
        r=lib2.daily_strategy(pos,Ls,exec='same_close'); e=lib2.ts_eval(r)
        print(f"{lab} thr={thr}: t={e['t']:.2f} ann={e['ann_return_pct']:.2f} py={e['positive_years']} h1={e['first_half_ann_pct']:.1f} h2={e['second_half_ann_pct']:.1f} mde={e['mde_ann_pct']:.1f}",dec(r))
print("=== equities calendar (SPY unless noted)")
for t in ['SPY','IWM']:
    d=px(t).index; f,b=tdm(d); idx=pd.Series(d,index=d)
    gap_next=(idx.shift(-1)-idx).dt.days; 
    # pre-holiday day = day whose next trading day is >1 calendar day away on a weekday gap (not normal weekend): gap>3 or (gap>1 and not Friday) 
    prehol=((gap_next>3)|((gap_next>1)&(d.dayofweek!=4))|((gap_next==3)&(d.dayofweek!=4)))
    r,e=ev(nxt(prehol),t,label='pre-holiday day'); print('    ',dec(r))
    for k,nm in enumerate(['Mon','Tue','Wed','Thu','Fri']):
        r,e=ev(nxt(pd.Series(d.dayofweek==k,index=d)),t,label='DOW '+nm); print('    ',dec(r))
    r,e=ev(nxt(f==1),t,label='first day of month'); print('    ',dec(r))
    win=pd.Series(d.month.isin([11,12,1,2,3,4]),index=d)
    r,e=ev(nxt(win),t,label='Halloween Nov-Apr'); print('    ',dec(r))
    # opex week: week containing third Friday
    third=pd.Series([(x.day-1)//7==2 if True else 0 for x in (d + pd.offsets.Week(weekday=4)) ],index=d)  # the Friday on/after this date is the 3rd Friday
    fr=d + pd.to_timedelta((4-d.dayofweek)%7,unit='D'); opx=pd.Series((fr.day>=15)&(fr.day<=21),index=d)
    r,e=ev(nxt(opx),t,label='opex week'); print('    ',dec(r))
    wk_after=opx.shift(5).fillna(False)
    r,e=ev(nxt(wk_after),t,label='week after opex'); print('    ',dec(r))
    santa=pd.Series(((d.month==12)&(d.day>=22))|((d.month==1)&(d.day<=4)),index=d)
    r,e=ev(nxt(santa),t,label='santa Dec22-Jan4'); print('    ',dec(r))
g=px('^GSPC'); r=g.pct_change(); print('GSPC Nov-Apr gross',dec(r[r.index.month.isin([11,12,1,2,3,4])],10)); print('GSPC May-Oct gross',dec(r[~r.index.month.isin([11,12,1,2,3,4])],10))
