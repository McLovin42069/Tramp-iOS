from feat import *
E = events()
print(E[["sue_h","sue_p","ar1","ar2","pre10","streak","surp_w"]].describe().T)
for reg in ["US","EU","AS"]:
    for col in ["surp_w","sue_h","sue_p","streak","ar1","ar1z"]:
        ev(panel(E, col, 60), reg, 20, f"{col} hold60")
    ev(panel(E, "ar2", 60, lag=1), reg, 20, "ar2 hold60 lag1")
print("variants", N[0])
