exec(open('a2.py').read().split('if __name__')[0])
def tt(x): x=x.dropna(); return "%.2fbp(t%.1f,n%d)"%(x.mean()*1e4,x.mean()/x.std()*len(x)**.5,len(x))
for tk in ["SPY","QQQ","IWM"]:
    r=C[tk].pct_change(); nx=on[tk].shift(-1); nd=day[tk].shift(-1)
    for a,b in [("1993","2004"),("2005","2018"),("2010","2018")]:
        s=slice(a,b)
        print(tk,a,b,"night after down",tt(nx[s][r[s]<0]),"after up",tt(nx[s][r[s]>=0]),"| next day sess after down",tt(nd[s][r[s]<0]),"after up",tt(nd[s][r[s]>=0]))
        g=on[tk][s]; d=day[tk][s]
        print("     day sess after gap>0.3%",tt(d[g>0.003]),"gap<-0.3%",tt(d[g<-0.003]), "small", tt(d[g.abs()<=0.003]))
# magnitude of down day
tk="SPY"; r=C[tk].pct_change(); nx=on[tk].shift(-1)
for lo,hi in [(-1,-0.01),(-0.01,-0.005),(-0.005,0),(0,0.005),(0.005,0.01),(0.01,1)]:
    m=(r>=lo)&(r<hi); print(lo,hi,"all",tt(nx[m]),"2005+",tt(nx["2005":][m["2005":]]))
