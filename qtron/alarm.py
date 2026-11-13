"""Qtron market alarm: four fixed measurements of market stress, combined into green / orange / red.
It does not predict a crash; it says whether the market is in the state in which large losses have occurred.
Pure pandas: used by the app, the collector and the historical test."""
import numpy as np
import pandas as pd

SECTORS = ["XLK", "XLF", "XLV", "XLY", "XLP", "XLE", "XLI", "XLB", "XLU"]
TICKERS = ["SPY", "HYG", "IEF", "^VIX", "^VIX3M"] + SECTORS
PARTS = {"trend": "S&P 500 onder zijn 200-dagengemiddelde", "krediet": "Hoogrentende obligaties verliezen terrein tegenover staatspapier",
         "paniek": "Volatiliteit op korte termijn hoger dan op drie maanden", "breedte": "Minder dan 40% van de sectoren boven hun 200-dagengemiddelde"}


def components(C):
    """C: daily closes [date x ticker]. Returns a boolean frame (NaN where a measurement did not exist yet)."""
    ix = C["SPY"].dropna().index
    C = C.reindex(ix).ffill(limit=3)
    out = pd.DataFrame(index=ix, dtype=float)
    out["trend"] = (C["SPY"] < C["SPY"].rolling(200).mean()).where(C["SPY"].rolling(200).mean().notna())
    if "HYG" in C and "IEF" in C:
        ratio = C["HYG"] / C["IEF"]
        out["krediet"] = (ratio < ratio.rolling(100).mean()).where(ratio.rolling(100).mean().notna())
    if "^VIX" in C and "^VIX3M" in C:
        out["paniek"] = (C["^VIX"] > C["^VIX3M"]).where(C["^VIX3M"].notna() & C["^VIX"].notna())
    sec = [s for s in SECTORS if s in C]
    if len(sec) >= 6:
        ma = C[sec].rolling(200).mean()
        above = (C[sec] > ma).where(ma.notna())
        out["breedte"] = (above.mean(axis=1) < 0.4).where(above.notna().sum(axis=1) >= 6)
    return out


def state(C):
    """Returns (level Series: 0 green / 1 orange / 2 red, component frame). Red = at least 3 of 4 (or all available when fewer exist)."""
    comp = components(C)
    n, k = comp.notna().sum(axis=1), comp.sum(axis=1)
    frac = k / n.where(n > 0)
    level = pd.Series(np.select([frac >= 0.75, frac >= 0.5], [2, 1], 0), index=comp.index).where(n > 0)
    return level, comp


NAMES = {0: "GROEN", 1: "ORANJE", 2: "ROOD"}
ADVICE = {0: "Geen verhoogd marktrisico gemeten. Normaal handelen.",
          1: "Verhoogd risico. Nieuwe aankopen kleiner maken en stops nalopen.",
          2: "Hoog risico: de kans op een verlies van meer dan 10% binnen een maand is ongeveer tien keer zo groot als normaal. Geen nieuwe aankopen; overweeg posities te verkleinen."}
