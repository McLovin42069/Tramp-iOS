from feat import *
E = events()
print("== pre-announcement")
dte = dte_panel(); print(dte.stack().describe())
for reg in ["US","EU","AS"]:
    ev(-dte.where(dte <= 70), reg, 5, "-dte")
    d = (dte - 6).abs(); cyc = np.minimum(d, 65 - d).where(dte <= 70)
    ev(-cyc, reg, 10, "-cyclic dist to dte=6")
print("== run-up reversal")
for reg in ["US","EU","AS"]:
    ev(panel(E, "pre10", 20), reg, 20, "pre10 hold20")
print("== muted reaction")
E["mut"] = np.sign(E["diff"]) * (E.ar1z.abs() < 1) 
E["sue_minus_ar"] = E.groupby("usable_date").sue_p.rank(pct=True) - E.groupby("usable_date").ar1.rank(pct=True)
for reg in ["US","EU","AS"]:
    E["m2"] = np.where(E.ar1z.abs() < 1, E.sue_p, np.nan)
    ev(panel(E, "m2", 60), reg, 20, "sue_p | muted |ar1z|<1")
print("variants", N[0])
