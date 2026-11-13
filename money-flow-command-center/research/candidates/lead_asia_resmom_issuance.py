"""Submitted by the lead researcher as a single pre-registered hold-out shot. Definition copied unchanged from the
`intl` agent's closest miss (discovery t = 2.07, below the 2.5 bar; selected after ~36 variants x 3 universes)."""
import numpy as np, pandas as pd, lib
NAME = "Asia: country-residual momentum 12-1 + low net issuance (equal ranks), 60 days"
KIND = "xs"
RATIONALE = "Momentum and buyback/issuance effects are documented to be stronger outside the US; both showed the textbook sign in Asia in 6-7 of 7 discovery years."
VARIANTS_TRIED = 108
H = 60
UNIVERSE = {"cls": ["Asia Stocks"], "core": False}
EXPECTED_SIGN = 1
DISCOVERY = {"t": 2.07, "spread_pct": 1.91}


def signal(D):
    cols = lib.tickers(D, cls=["Europe Stocks", "Asia Stocks"], core=False)
    C = D["C"][cols]
    r = C.pct_change(fill_method=None)
    rr = lib.residual(r, D)
    vol = rr.rolling(250, min_periods=150).std()
    resmom = rr.shift(20).rolling(230, min_periods=150).sum() / vol
    sh = D["shares"].reindex(columns=cols)
    issu = -lib.residual(sh - sh.shift(250), D)
    rk = lambda X: X.rank(axis=1, pct=True)
    return rk(resmom) + rk(issu)
