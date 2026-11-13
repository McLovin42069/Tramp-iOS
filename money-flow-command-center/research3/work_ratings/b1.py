from core import *
# benchmarks (not counted as variants of mine, but count anyway)
for L in (5,20,250):
    for h in (5,20): ev(f"BENCH past ret {L}",C/C.shift(L)-1,h)
for W in (5,20,60):
    for h in (5,20):
        ev(f"net up-down count W{W}",rsum(r,"ud",W),h)
for W in (5,20,60):
    for h in (5,20):
        ev(f"PT rev mean W{W}",rmean(r,"ptrev",W),h)
for W in (20,60):
    for h in (5,20):
        ev(f"PT breadth sum W{W}",rsum(r,"ptdir",W),h)
print("variants",N[0])
