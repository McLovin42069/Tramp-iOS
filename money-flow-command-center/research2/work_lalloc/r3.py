from core import *
pd.set_option("display.width", 300); pd.set_option("display.max_columns", 40)
def ma(sym, m): return (Cf[sym] > Cf[sym].rolling(21 * m).mean()).astype(float).where(Cf[sym].rolling(21 * m).mean().notna())
dx = Cf["DX-Y.NYB"]
def fdx(d): return (dx < dx.shift(d)).astype(float)
def sub(r, bench=SPYr):
    o = {}
    for nm, (a, b) in {"93-99": ("1993", "1999"), "00-09": ("2000", "2009"), "10-18": ("2010", "2018"), "03-07": ("2003", "2007"), "09-18": ("2009-07", "2018")}.items():
        e = lib2.ts_eval(r, bench, start=a, end=b + "-12-31" if len(b) == 4 else None)
        o[nm] = f"sh{e['sharpe']:.2f}/b{e['bench_sharpe']:.2f} a{e['alpha_ann_pct']:.1f} t{e['alpha_t']:.2f}"
    x = r[~(((r.index >= "2000-01-01") & (r.index <= "2002-12-31")) | ((r.index >= "2007-10-01") & (r.index <= "2009-06-30")))]
    e = lib2.ts_eval(x, bench); o["ex-crises"] = f"sh{e['sharpe']:.2f}/b{e['bench_sharpe']:.2f} a{e['alpha_ann_pct']:.1f} t{e['alpha_t']:.2f}"
    return o
rows = []
main = {"SPY>MA10": monthly(ma("SPY", 10)).rename("SPY").dropna(),
        "MA ens": monthly(sum(ma("SPY", m) for m in (6, 8, 10, 12)) / 4).rename("SPY").dropna(),
        "DXY126 m": monthly(fdx(126)).rename("SPY"),
        "trend+dollar": monthly((ma("SPY", 10) + fdx(126)) / 2).rename("SPY").dropna()}
for k, p in main.items():
    r = run(p); print(k, sub(r)); 

print("grid trend+dollar: alpha_t vs SPY / sharpe / mdd")
for m in (8, 10, 12):
    for d in (63, 126, 189, 252):
        if (m, d) == (10, 126): continue
        r, o, e = ev(f"tr{m}+dx{d}", monthly((ma("SPY", m) + fdx(d)) / 2).rename("SPY").dropna(), show=False)
        print(o["name"], o["a_t"], o["a64_t"], o["sh"], o["mdd"], o["py"])
r, o, e = ev("trend+dollar same_close", monthly((ma("SPY", 10) + fdx(126)) / 2).rename("SPY").dropna(), exec="same_close", show=False); print(o)
# 3-sleeve vs its static mix: the proper benchmark
p = pd.concat([ma(s, 10) for s in ("SPY", "TLT", "GLD")], axis=1, keys=["SPY", "TLT", "GLD"]).dropna() / 3
r3 = run(monthly(p).dropna()); st = lib2.daily_strategy(pd.DataFrame(1 / 3, index=us, columns=["SPY", "TLT", "GLD"]).where(C["GLD"].notna()).dropna(), L)
e = lib2.ts_eval(r3, st); print("3sleeve MA10 vs static 1/3:", round(e["alpha_t"], 2), round(e["sharpe"], 2), round(e["bench_sharpe"], 2))
print("N", N[0])
