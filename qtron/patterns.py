"""Qtron pattern engine.

Each pattern is a FIXED rule that came out of the four research rounds (2,300 variants, 161k lead-lag pairs).
None of them is statistically proven on unseen data; each kept the same sign after its search period. From the
go-live date onward the rules are frozen, so everything they earn afterwards is a genuine forward test.

A pattern provides
    returns(D)  -> daily net return Series over the whole history in D (costs included)
    state(D)    -> dict(active: bool, action: str, detail: str) for the latest bar
D is a dict of daily panels {"O","C","V"} [date x ticker] plus optional "funding", "shares", "earnings".
Pure pandas/numpy: used by both the app and the nightly collector.
"""
import numpy as np
import pandas as pd
from pandas.tseries.holiday import (AbstractHolidayCalendar, GoodFriday, Holiday, USLaborDay, USMartinLutherKingJr, USMemorialDay,
                                    USPresidentsDay, USThanksgivingDay, nearest_workday)
from pandas.tseries.offsets import CustomBusinessDay

VERSION = 1


class _NYSE(AbstractHolidayCalendar):
    rules = [Holiday("NewYear", month=1, day=1, observance=nearest_workday), USMartinLutherKingJr, USPresidentsDay, GoodFriday, USMemorialDay,
             Holiday("Juneteenth", month=6, day=19, start_date="2022-06-19", observance=nearest_workday),
             Holiday("July4", month=7, day=4, observance=nearest_workday), USLaborDay, USThanksgivingDay,
             Holiday("Christmas", month=12, day=25, observance=nearest_workday)]


NYSE_DAY = CustomBusinessDay(calendar=_NYSE())


def nyse_days(start, end):
    return pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq=NYSE_DAY)


def _sessions(D, ticker="SPY"):
    """Rows on which the US market really traded (the app's panels also contain forward-filled holiday rows)."""
    if ticker not in D["C"].columns:
        return D["C"].index[:0]
    c = D["C"][ticker]
    ok = c.notna()
    if "V" in D and ticker in D["V"].columns:
        ok &= D["V"][ticker].fillna(0) > 0
    return c.index[ok]


def _have(D, tickers):
    return [t for t in tickers if t in D["C"].columns and D["C"][t].notna().sum() > 300]


# ── 1. overnight after a down day (index futures) ────────────────────────────────────────────────
NACHT_T, NACHT_COST = ["SPY", "QQQ"], 0.5e-4          # per trade; micro E-mini cost level


def nacht_returns(D):
    tk = _have(D, NACHT_T)
    if not tk or "O" not in D:
        return pd.Series(dtype=float)
    ix = _sessions(D)
    C, O = D["C"].loc[ix, tk], D["O"].loc[ix, tk]
    down = C < C.shift(1)                              # known at the close
    night = O / C.shift(1) - 1                         # realised at this row's open, decided at the previous close
    r = (night - 2 * NACHT_COST).where(down.shift(1, fill_value=False), 0.0)
    return r.mean(axis=1).dropna()


def nacht_state(D):
    tk = _have(D, NACHT_T)
    ix = _sessions(D)
    if not tk or len(ix) < 3:
        return {"active": False, "action": "geen data", "detail": ""}
    C = D["C"].loc[ix, tk]
    chg = (C.iloc[-1] / C.iloc[-2] - 1) * 100
    names = {"SPY": "S&P 500 (micro-future MES)", "QQQ": "Nasdaq 100 (micro-future MNQ)"}
    act = [names[t] for t in tk if chg[t] < 0]
    det = " · ".join(f"{t} {chg[t]:+.2f}%" for t in tk) + f" op {ix[-1]:%d-%m}"
    if act:
        return {"active": True, "action": "Long van slot (16:00 New York) tot opening (09:30): " + " en ".join(act), "detail": det}
    return {"active": False, "action": "Geen positie vannacht: de index sloot hoger", "detail": det}


# ── 2. long Treasuries in the last three trading days of the month ───────────────────────────────
MAAND_T, MAAND_COST, MAAND_N = "TLT", 2e-4, 3


def _days_left_in_month(dates):
    """Trading days remaining in the month AFTER each date (0 on the last trading day), from the exchange calendar."""
    out = []
    cache = {}
    for d in dates:
        key = (d.year, d.month)
        if key not in cache:
            cache[key] = nyse_days(d.replace(day=1), d + pd.offsets.MonthEnd(0))
        out.append(int((cache[key] > d).sum()))
    return pd.Series(out, index=dates)


def maand_returns(D):
    if MAAND_T not in D["C"].columns:
        return pd.Series(dtype=float)
    ix = _sessions(D, MAAND_T)
    r = D["C"].loc[ix, MAAND_T].pct_change()
    left = _days_left_in_month(ix)
    inwin = left < MAAND_N                              # held on the last 3 sessions (entered at the close before)
    out = r.where(inwin, 0.0)
    first, last = inwin & ~inwin.shift(1, fill_value=False), inwin & (left == 0)
    return (out - MAAND_COST * first - MAAND_COST * last).dropna()


def maand_state(D):
    ix = _sessions(D, MAAND_T)
    if len(ix) < 3:
        return {"active": False, "action": "geen data", "detail": ""}
    today = ix[-1]
    month = nyse_days(today.replace(day=1), today + pd.offsets.MonthEnd(0))
    left = int((month > today).sum())
    last_day = month[-1]
    if left == MAAND_N:
        return {"active": True, "action": f"KOOP lange staatsobligaties (TLT of UCITS-variant) bij het slot van {today:%d-%m}; verkoop bij het slot van {last_day:%d-%m}",
                "detail": f"nog {left} handelsdagen in de maand"}
    if left < MAAND_N:
        return {"active": True, "action": f"In positie houden; VERKOOP bij het slot van {last_day:%d-%m}", "detail": f"nog {left} handelsdagen in de maand"}
    entry = month[-(MAAND_N + 1)] if len(month) > MAAND_N else month[0]
    return {"active": False, "action": f"Wachten; instap bij het slot van {entry:%d-%m}", "detail": f"nog {left} handelsdagen in de maand"}


# ── 3. buy Asian country funds after a sharp US down day ─────────────────────────────────────────
DIP_T, DIP_COST, DIP_Z = ["EWH", "FXI", "EWT"], 2e-4, -1.0


def _spy_z(D):
    ix = _sessions(D)
    r = D["C"].loc[ix, "SPY"].pct_change()
    return r / r.rolling(60, min_periods=30).std().shift(1)


def dip_returns(D):
    tk = _have(D, DIP_T)
    if not tk or "SPY" not in D["C"].columns:
        return pd.Series(dtype=float)
    z = _spy_z(D)
    sig = (z < DIP_Z).shift(1, fill_value=False)        # decided at yesterday's close, earned today close-to-close
    r = D["C"].loc[z.index, tk].pct_change().mean(axis=1)
    return (r - 2 * DIP_COST).where(sig, 0.0).dropna()


def dip_state(D):
    if "SPY" not in D["C"].columns:
        return {"active": False, "action": "geen data", "detail": ""}
    z = _spy_z(D).dropna()
    if z.empty:
        return {"active": False, "action": "geen data", "detail": ""}
    zl = float(z.iloc[-1])
    det = f"S&P 500 dagbeweging {zl:+.1f} standaardafwijkingen op {z.index[-1]:%d-%m} (drempel {DIP_Z:+.1f})"
    if zl < DIP_Z:
        return {"active": True, "action": "KOOP Hongkong, China en Taiwan (EWH, FXI, EWT of UCITS-varianten) bij het slot; verkoop bij het volgende slot", "detail": det}
    return {"active": False, "action": "Geen positie: geen scherpe Amerikaanse daling", "detail": det}


# ── 4. energy equities February–April ────────────────────────────────────────────────────────────
XLE_T, XLE_COST, XLE_MONTHS = "XLE", 2e-4, (2, 3, 4)


def xle_returns(D):
    if XLE_T not in D["C"].columns:
        return pd.Series(dtype=float)
    ix = _sessions(D, XLE_T)
    r = D["C"].loc[ix, XLE_T].pct_change()
    inwin = pd.Series(ix.month.isin(XLE_MONTHS), index=ix)
    edge = inwin != inwin.shift(1, fill_value=False)
    return (r.where(inwin, 0.0) - XLE_COST * edge).dropna()


def xle_state(D):
    ix = _sessions(D, XLE_T)
    if len(ix) < 3:
        return {"active": False, "action": "geen data", "detail": ""}
    m = ix[-1].month
    if m in XLE_MONTHS:
        return {"active": True, "action": "In positie: energieaandelen (XLE of UCITS-variant) aanhouden tot eind april", "detail": "seizoensvenster februari–april"}
    nxt = "eind januari" if m in (11, 12, 1) else "eind januari van volgend jaar"
    return {"active": False, "action": f"Buiten het venster; instap {nxt}", "detail": "seizoensvenster februari–april"}


# ── 5. crypto cash-and-carry on bitcoin ──────────────────────────────────────────────────────────
CARRY_SYM, CARRY_N, CARRY_DRAG = "BTCUSDT", 0.5, 0.004 / 365      # half the capital hedged; ~0.4%/yr rebalancing cost


def carry_returns(D):
    f = D.get("funding")
    if f is None or CARRY_SYM not in getattr(f, "columns", []):
        return pd.Series(dtype=float)
    s = f[CARRY_SYM].dropna()
    daily = s.groupby(s.index.normalize()).sum()
    return (CARRY_N * daily - CARRY_DRAG).dropna()


def carry_state(D):
    r = carry_returns(D)
    if r.empty:
        return {"active": False, "action": "financieringsrente nog niet opgehaald", "detail": ""}
    a7, a30 = r.tail(7).mean() * 365 * 100, r.tail(30).mean() * 365 * 100
    det = f"netto op totaal kapitaal, op jaarbasis: laatste 7 dagen {a7:+.1f}%, laatste 30 dagen {a30:+.1f}% (data t/m {r.index[-1]:%d-%m})"
    if a30 > 0:
        return {"active": True, "action": "Carry is positief: spot bitcoin aanhouden met een even grote short in de doorlopende future", "detail": det}
    return {"active": False, "action": "Carry is negatief: de handel kost nu geld", "detail": det}


# ── cross-sectional monthly long/short helper (Asian stocks) ─────────────────────────────────────
def _country_neutral(X, groups):
    g = groups.reindex(X.columns)
    return X - X.T.groupby(g.values).transform("median").T.values


def _xs_monthly(sig, D, cols, cost_bps=15.0, q=0.2, min_side=10):
    """Rebalance on the first trading day of each month using the signal of the day before; equal-weight top
    quintile long and bottom quintile short (0.5 each side). Returns (daily net returns, latest long list, latest short list)."""
    cols = [c for c in cols if c in D["C"].columns and c in sig.columns]
    C = _panel(D, cols)
    sig = sig.reindex(C.index)
    r = C.pct_change(fill_method=None)
    s = sig[cols].shift(1)
    first = pd.Series(C.index, index=C.index).groupby([C.index.year, C.index.month]).first().values
    W = pd.DataFrame(np.nan, index=C.index, columns=cols)
    longs, shorts = [], []
    for d in first:
        row = s.loc[d].dropna()
        if len(row) < 2 * min_side / q * q + 20:
            continue
        rk = row.rank(pct=True)
        lg, sh = rk.index[rk > 1 - q], rk.index[rk <= q]
        if len(lg) < min_side or len(sh) < min_side:
            continue
        w = pd.Series(0.0, index=cols)
        w[lg], w[sh] = 0.5 / len(lg), -0.5 / len(sh)
        W.loc[d] = w
        longs, shorts = list(row[lg].sort_values(ascending=False).index), list(row[sh].sort_values().index)
    W = W.ffill()
    held = W.shift(1)                                   # traded at the close of the rebalance day
    gross = (held * r).sum(axis=1, min_count=1)
    cost = held.diff().abs().sum(axis=1) * cost_bps / 1e4
    return (gross - cost).dropna(), longs, shorts


def _panel(D, cols):
    """Closes of a stock group on the days at least one of them has a price (the joint panel also holds decades of index-only rows)."""
    return D["C"][cols].dropna(how="all")


def _asia(D):
    m = D.get("meta")
    if m is None:
        return [], []
    base = m["base"] if "base" in m.columns else True                      # the patterns stay on the list they were frozen on
    asia = [t for t in m.index[(m["cls"] == "Asia Stocks") & base] if t in D["C"].columns]
    eur = [t for t in m.index[(m["cls"] == "Europe Stocks") & base] if t in D["C"].columns]
    return asia, eur


# ── 6. Asia: residual momentum + buybacks ────────────────────────────────────────────────────────
def _mom_signal(D):
    asia, eur = _asia(D)
    sh = D.get("shares")
    if len(asia) < 60 or sh is None:
        return None, asia
    cols = asia + eur
    C = _panel(D, cols)
    r = C.pct_change(fill_method=None)
    g = D["meta"]["group"]
    rr = _country_neutral(r, g)
    resmom = rr.shift(20).rolling(230, min_periods=150).sum() / rr.rolling(250, min_periods=150).std()
    cum = pd.DataFrame({t: sh[t] for t in cols if t in sh}) if isinstance(sh, dict) else sh
    cum = cum.reindex(columns=cols)
    cum = cum.set_axis(cum.index + pd.Timedelta(days=5)).reindex(C.index.union(cum.index + pd.Timedelta(days=5))).ffill().reindex(C.index)
    issu = -_country_neutral(cum - cum.shift(250), g)
    rk = lambda X: X.rank(axis=1, pct=True)
    return (rk(resmom) + rk(issu)), asia


def azmom_returns(D):
    sig, asia = _mom_signal(D)
    return pd.Series(dtype=float) if sig is None else _xs_monthly(sig, D, asia)[0]


def azmom_state(D):
    sig, asia = _mom_signal(D)
    if sig is None:
        return {"active": False, "action": "aandelenaantallen nog niet opgehaald (de nachtelijke verzamelaar doet dit)", "detail": ""}
    _, lg, sh = _xs_monthly(sig, D, asia)
    return {"active": bool(lg), "action": "Maandelijks herschikken op de eerste handelsdag: koop de bovenste groep, mijd de onderste",
            "detail": "Bovenaan nu: " + ", ".join(lg[:12]) + ("  |  Onderaan: " + ", ".join(sh[:8]) if sh else ""), "longs": lg, "shorts": sh}


# ── 7. Asia: drift after earnings ────────────────────────────────────────────────────────────────
def _earn_signal(D):
    asia, _ = _asia(D)
    E = D.get("earnings")
    if len(asia) < 60 or E is None or len(E) == 0:
        return None, asia
    C = _panel(D, asia)
    idx = C.index
    e = E[E["ticker"].isin(asia) & E["eps_rep"].notna()].copy()
    if e.empty:
        return None, asia
    ts = pd.to_datetime(e["ts"])
    day = ts.dt.normalize() + pd.to_timedelta((ts.dt.hour >= 3).astype(int), unit="D")      # Asian markets close before 03:00 New York
    pos = idx.searchsorted(day.values)
    e = e[(pos < len(idx)) & (day.values >= idx[0])]
    e["use"] = idx[pos[(pos < len(idx)) & (day.values >= idx[0])]]
    rr = _country_neutral(C.pct_change(fill_method=None), D["meta"]["group"])
    ar2 = (rr + rr.shift(-1)).shift(2)                   # two-day announcement return, usable two rows after the event row
    surp = e.assign(v=e["surprise_pct"].clip(-100, 100)).pivot_table(index="use", columns="ticker", values="v", aggfunc="last").reindex(index=idx, columns=asia)
    ev = surp.notna()
    ar_at = ar2.shift(-2).where(ev)                      # announcement return of the event, placed on the event row
    carry = lambda X, lag: X.shift(lag).ffill(limit=60)
    a, s_ = carry(ar_at, 2), carry(surp, 0)
    rk = lambda X: X.rank(axis=1, pct=True)
    return (rk(a) + rk(s_)), asia


def azearn_returns(D):
    sig, asia = _earn_signal(D)
    return pd.Series(dtype=float) if sig is None else _xs_monthly(sig, D, asia, min_side=6)[0]


def azearn_state(D):
    sig, asia = _earn_signal(D)
    if sig is None:
        return {"active": False, "action": "winstpublicaties nog niet opgehaald (de nachtelijke verzamelaar doet dit)", "detail": ""}
    _, lg, sh = _xs_monthly(sig, D, asia, min_side=6)
    return {"active": bool(lg), "action": "Maandelijks herschikken: koop aandelen met een positieve verrassing én koersreactie, mijd het omgekeerde",
            "detail": "Bovenaan nu: " + ", ".join(lg[:12]) + ("  |  Onderaan: " + ", ".join(sh[:8]) if sh else ""), "longs": lg, "shorts": sh}


# ── registry ─────────────────────────────────────────────────────────────────────────────────────
PATTERNS = [
    {"id": "nacht", "naam": "Nacht na een daldag", "soort": "Indexfutures", "fn": nacht_returns, "state": nacht_state,
     "disc_end": "2018-12-31", "hold_start": "2019-01-01", "hold_end": "2026-11-12",
     "kern": "Amerikaanse indices verdienen hun rendement 's nachts, en sinds 2005 vrijwel alleen in de nacht ná een dag waarop de index daalde.",
     "zoek": "1993–2018: +6,7% per jaar, t = 4,3 (S&P 500 + Nasdaq, 0,5 basispunt kosten)",
     "toets": "2019–2026: +5,0% per jaar, t = 1,4, positief in 6 van 8 jaren; geen voordeel boven het gelopen marktrisico",
     "uitbuiten": ["Alleen uitvoerbaar met futures: micro E-mini S&P 500 (MES) en Nasdaq (MNQ). Met indexfondsen eten de kosten alles op.",
                   "Bepaal één minuut voor het Amerikaanse slot (22:00 onze tijd) of de index lager staat dan het slot van gisteren.",
                   "Zo ja: koop de future bij het slot en verkoop bij de Amerikaanse opening (15:30 onze tijd). Zo nee: geen positie.",
                   "Ongeveer 115 keer per jaar een nacht in positie; reken op hooguit 0,5 tot 1 basispunt kosten per transactie."],
     "risico": ["Volledig blootgesteld aan nachtelijke koerssprongen: slechtste nacht in de toetsperiode −7%.",
                "Vereist een futuresrekening met onderpand; verlies kan groter zijn dan de inleg op de positie.",
                "Het voordeel is sinds 2010 kleiner dan daarvoor."]},
    {"id": "maand", "naam": "Staatsobligaties aan het maandeinde", "soort": "Kalender", "fn": maand_returns, "state": maand_state,
     "disc_end": "2018-12-31", "hold_start": "2019-01-01", "hold_end": "2026-11-12",
     "kern": "Lange Amerikaanse staatsobligaties stijgen in de laatste handelsdagen van de maand, wanneer indexvolgers hun looptijd verlengen en de maandeinde-veilingen achter de rug zijn.",
     "zoek": "2002–2018: +4,5% per jaar, t = 3,7, positief in 16 van 17 jaren (2 basispunten kosten)",
     "toets": "2019–2026: +2,5% per jaar, t = 1,4, positief in 7 van 8 jaren; drie agenten vonden dit patroon los van elkaar",
     "uitbuiten": ["Koop een fonds in lange Amerikaanse staatsobligaties (TLT; in de EU een UCITS-variant zoals een 20+ jaar Treasury-fonds) bij het slot van de vierde-laatste handelsdag van de maand.",
                   "Verkoop bij het slot van de laatste handelsdag. Twaalf keer per jaar, drie dagen in positie.",
                   "Qtron toont de instap- en uitstapdatum van de lopende maand."],
     "risico": ["Het effect is ongeveer gehalveerd sinds publicatie rond 2019.",
                "Europese varianten sluiten om 17:30, vóór het Amerikaanse slot; een deel van de beweging kan dan gemist worden.",
                "Transactiebelasting of hoge kosten per order kunnen het voordeel (ongeveer 0,2% per maand) volledig opeten."]},
    {"id": "dip", "naam": "Azië kopen na een Amerikaanse daling", "soort": "Voorlopen/achterlopen", "fn": dip_returns, "state": dip_state,
     "disc_end": "2018-12-31", "hold_start": "2019-01-01", "hold_end": "2026-11-12",
     "kern": "Na een scherpe daling van de S&P 500 schieten in New York verhandelde Aziatische landenfondsen door naar beneden; de dag erna herstellen ze deels.",
     "zoek": "1996–2018: +9,3% per jaar, t = 4,0 (alleen de koopkant, 2 basispunten kosten)",
     "toets": "2019–2026: +3,6% per jaar, t = 1,1, positief in 5 van 8 jaren",
     "uitbuiten": ["Meet bij het Amerikaanse slot de dagbeweging van de S&P 500 ten opzichte van de laatste 60 dagen.",
                   "Is de daling groter dan één standaardafwijking: koop Hongkong, China en Taiwan (EWH, FXI, EWT) bij het slot, elk een derde.",
                   "Verkoop bij het volgende Amerikaanse slot. Gemiddeld ruim 40 keer per jaar."],
     "risico": ["Je koopt in een dalende markt: in een aanhoudende crash stapelen de verliezen zich op.",
                "In de EU zijn deze Amerikaanse fondsen voor particulieren meestal niet te koop; UCITS-varianten handelen op andere uren."]},
    {"id": "xle", "naam": "Energieaandelen februari–april", "soort": "Seizoen", "fn": xle_returns, "state": xle_state,
     "disc_end": "2018-12-31", "hold_start": "2019-01-01", "hold_end": "2026-11-12",
     "kern": "Energieaandelen deden het historisch het best van februari tot en met april, in aanloop naar het Amerikaanse rijseizoen.",
     "zoek": "1999–2018: +7,6% per jaar, t = 2,8, positief in 16 van 20 jaren; voordeel boven vasthouden t = 2,3",
     "toets": "2019–2026: +5,6% per jaar, t = 0,7 (één waarneming per jaar; zegt nog weinig)",
     "uitbuiten": ["Koop een energiesectorfonds (XLE of een UCITS-variant) op de laatste handelsdag van januari.",
                   "Verkoop op de laatste handelsdag van april. Eén keer per jaar."],
     "risico": ["Eén waarneming per jaar: het duurt vele jaren voordat dit bewezen of weerlegd is.",
                "Haalde de lat van het onderzoek net niet."]},
    {"id": "carry", "naam": "Crypto-carry op bitcoin", "soort": "Premie", "fn": carry_returns, "state": carry_state,
     "disc_end": "2023-12-31", "hold_start": "2024-01-01", "hold_end": "2026-10-31",
     "kern": "Wie long zit in doorlopende bitcoin-futures betaalt elke acht uur rente aan wie short zit. Met spot bitcoin plus een even grote short ontvang je die rente zonder koersrisico.",
     "zoek": "2020–2023: +8,5% / +15,9% / +1,7% / +3,6% per jaar op het totale kapitaal",
     "toets": "2024: +5,8%, 2025: +2,3%, 2026 (t/m okt): +1,1%; elk jaar positief, nu onder de spaarrente",
     "uitbuiten": ["Zet de helft van het bedrag in spot bitcoin en de andere helft als onderpand voor een even grote short in de doorlopende future.",
                   "Stap één keer in en blijf zitten; herverdeel alleen het onderpand. In- en uitstappen kost meer dan het oplevert.",
                   "Qtron toont de actuele rente op jaarbasis. Onder de spaarrente loont het niet."],
     "risico": ["Het grootste risico staat niet in de cijfers: de beurs zelf. FTX ging in 2022 failliet en klanten verloren alles.",
                "Doorlopende crypto-futures zijn voor particulieren in de EU bij veel aanbieders beperkt of niet beschikbaar.",
                "Bij een snelle koersstijging moet het onderpand van de short tijdig worden aangevuld."]},
    {"id": "azmom", "naam": "Azië: momentum en inkoop van eigen aandelen", "soort": "Aandelenselectie", "fn": azmom_returns, "state": azmom_state,
     "needs": "shares", "disc_end": "2023-12-29", "hold_start": "2024-01-01", "hold_end": "2026-11-12",
     "kern": "Aziatische aandelen die het een jaar lang beter deden dan hun land én eigen aandelen inkochten, bleven beter presteren dan het omgekeerde.",
     "zoek": "2017–2023: +1,9% per 60 dagen verschil tussen beste en slechtste groep, t = 2,1",
     "toets": "2024–2026: +1,9% per 60 dagen, t = 1,3, positief in alle drie de jaren",
     "uitbuiten": ["Qtron rangschikt maandelijks de 142 gevolgde Aziatische aandelen en toont de bovenste en onderste groep.",
                   "Koop een gespreid mandje uit de bovenste groep (minstens 15 tot 20 namen) en mijd de onderste groep.",
                   "Herschik op de eerste handelsdag van de maand."],
     "risico": ["Het gemeten verschil is beste groep min slechtste groep; wie alleen koopt, houdt ongeveer de helft over.",
                "De aandelenlijst bevat alleen bedrijven die nu groot zijn, wat het verleden te rooskleurig maakt.",
                "Handel op Aziatische beurzen is duurder; gerekend is met 15 basispunten per transactie."]},
    {"id": "azearn", "naam": "Azië: doorloop na winstcijfers", "soort": "Aandelenselectie", "fn": azearn_returns, "state": azearn_state,
     "needs": "earnings", "disc_end": "2023-12-29", "hold_start": "2024-01-01", "hold_end": "2026-11-12",
     "kern": "Bij Aziatische aandelen liep de koers na een positieve winstverrassing met een sterke eerste reactie nog weken door; in de VS en Europa is dat effect verdwenen.",
     "zoek": "2017–2023: +0,8% per 20 dagen verschil, t = 2,8, positief in 6 van 7 jaren",
     "toets": "2024–2026 in de verhandelbare maandversie: −1,6% per jaar, t = −0,4. Niet bevestigd; blijft in observatie",
     "uitbuiten": ["Qtron combineert per aandeel de winstverrassing en de koersreactie van de twee dagen erna, en houdt dat 60 dagen vast.",
                   "Koop een mandje uit de bovenste groep, mijd de onderste groep, herschik maandelijks."],
     "risico": ["Was de beste van 45 geprobeerde varianten en haalde de lat net niet; de kans op toeval is reëel.",
                "Weinig namen per kant (ongeveer 20); één aandeel kan het resultaat sterk kleuren."]},
]
BY_ID = {p["id"]: p for p in PATTERNS}

# Patterns that were real and are gone: kept for the record, not tracked.
GRAVEYARD = [
    ("Aandelen stijgen op de dag van het rentebesluit", "2000–2013: +28 basispunt per vergadering, t = 2,6", "sinds 2014: +2 basispunt", "gepubliceerd in 2015, daarna weggehandeld"),
    ("Aandelen rond de maandwisseling", "1940–1999: t = 2,3 tot 6,7 per decennium", "sinds 2000: t ≤ 1,2", "zestig jaar sterk, sinds 2000 afwezig"),
    ("Trage obligatiefondsen volgen aandelen (hoogrentend, opkomende markten)", "2007–2018: +8% per jaar, t ≈ 4", "2019–2026: −2% tot −5% per jaar", "prijsvorming in obligatiefondsen is sneller geworden"),
    ("Staatsobligaties in de twee dagen na een veiling", "2002–2018: +6,9% per jaar, t = 4,6", "2019–2026: +1,2% per jaar, t = 0,4", "alleen het maandeinde-deel leeft nog zwak voort"),
    ("Canada volgt de S&P 500 een dag later", "1996–2018: +12,7% per jaar, t = 4,7", "2019–2026: +0,7% per jaar", "verdween al binnen de zoekperiode"),
    ("Het eerste handelsuur voorspelt het laatste", "literatuur tot 2013", "2023–2025: afwezig, ook zonder kosten", "niet teruggevonden"),
    ("Volg het geld: fondsen met instroom presteren beter", "nooit aangetoond", "licht omgekeerd, enkele honderdsten van een procent per week", "echte stromen zijn eerder een tegendraads signaal"),
]


def zone_stats(r, start=None, end=None, ann=252):
    """Annualised return, t-statistic, share of positive years and active days for a slice of a daily return series."""
    r = r.dropna()
    if start is not None:
        r = r[r.index >= pd.Timestamp(start)]
    if end is not None:
        r = r[r.index <= pd.Timestamp(end)]
    act = r[r != 0]
    if len(r) < 5 or r.std() == 0:
        return {"days": len(r), "active": len(act), "ann_pct": float(r.mean() * ann * 100) if len(r) else 0.0, "t": 0.0, "total_pct": float(((1 + r).prod() - 1) * 100) if len(r) else 0.0}
    return {"days": len(r), "active": len(act), "ann_pct": float(r.mean() * ann * 100), "t": float(r.mean() / r.std() * np.sqrt(len(r))),
            "total_pct": float(((1 + r).prod() - 1) * 100), "worst_day_pct": float(r.min() * 100)}


def evaluate(D, golive=None):
    """Run every pattern on D. Returns {id: {"ret": Series, "state": dict, "zones": {...}}}."""
    out = {}
    for p in PATTERNS:
        try:
            r = p["fn"](D)
            st = p["state"](D)
        except Exception as e:                          # one broken pattern must not take the others down
            r, st = pd.Series(dtype=float), {"active": False, "action": f"fout: {type(e).__name__}", "detail": str(e)[:120]}
        ann = 365 if p["id"] == "carry" else 252
        z = {"zoek": zone_stats(r, None, p["disc_end"], ann), "toets": zone_stats(r, p["hold_start"], p["hold_end"], ann)}
        if golive is not None:
            z["live"] = zone_stats(r, golive, None, ann)
        out[p["id"]] = {"ret": r, "state": st, "zones": z}
    return out
