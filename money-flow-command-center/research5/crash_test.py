"""Round 5f: does the Qtron market alarm (alarm.py, fixed rules) limit losses? S&P 500 since 1993.
Strategy: hold SPY, move to cash at the close after the alarm turns red, return when it leaves red. 5 bp per switch."""
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, "/home/user/Tramp-iOS/qtron")
import alarm, feeds
P = feeds.prices(alarm.TICKERS, period="max")
C = P["C"]
pd.to_pickle(C, "/home/user/Tramp-iOS/qtron/cache/alarm_px.pkl")
level, comp = alarm.state(C)
spy = C["SPY"].reindex(level.index)
r = spy.pct_change().fillna(0)
def dd(eq):
    return float((eq / eq.cummax() - 1).min() * 100)
def run(mask_out):
    pos = (~mask_out).shift(1, fill_value=True).astype(float)
    net = pos * r - pos.diff().abs().fillna(0) * 5e-4
    return net
res = {}
for name, out in (("altijd belegd", level < -1), ("uit bij ROOD", level == 2), ("uit bij ORANJE of ROOD", level >= 1)):
    net = run(out)
    eq = (1 + net).cumprod()
    yrs = len(net) / 252
    res[name] = {"rendement_per_jaar_pct": round(float(eq.iloc[-1] ** (1 / yrs) - 1) * 100, 2), "grootste_verlies_pct": round(dd(eq), 1),
                 "beweeglijkheid_pct": round(float(net.std() * np.sqrt(252) * 100), 1), "tijd_uit_markt_pct": round(float(out.mean() * 100), 1),
                 "wissels": int(out.astype(int).diff().abs().sum())}
    for lab, a, b in (("2000-2002", "2000-03-24", "2002-10-09"), ("2007-2009", "2007-10-09", "2009-03-09"), ("2020 corona", "2020-02-19", "2020-03-23"), ("2022", "2022-01-03", "2022-10-12")):
        seg = (1 + net[a:b]).prod() - 1
        res[name][lab] = round(float(seg * 100), 1)
    res[name]["sinds_2010_per_jaar_pct"] = round(float(((1 + net["2010":]).prod()) ** (252 / len(net["2010":])) - 1) * 100, 2)
fw = {}
for h in (20, 60):
    f = spy.shift(-h) / spy - 1
    fw[f"{h}d"] = {alarm.NAMES[k]: {"gem_pct": round(float(f[level == k].mean() * 100), 2), "slechtste_5pct": round(float(f[level == k].quantile(.05) * 100), 1),
                                    "kans_op_verlies_groter_dan_10pct": round(float((f[level == k] < -0.10).mean() * 100), 1), "dagen": int((level == k).sum())} for k in (0, 1, 2)}
out = {"strategie": res, "vooruit": fw, "nu": {"stand": alarm.NAMES[int(level.iloc[-1])], "datum": str(level.index[-1].date()), "onderdelen": comp.iloc[-1].to_dict()},
       "van": str(level.dropna().index[0].date())}
json.dump(out, open("/home/user/Tramp-iOS/money-flow-command-center/research5/crash_results.json", "w"), indent=1, ensure_ascii=False)
for k, v in res.items(): print(k, v)
for k, v in fw.items(): print(k, v)
print(out["nu"], out["van"])
