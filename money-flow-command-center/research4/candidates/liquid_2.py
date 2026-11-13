NAME = "TLT long for 2 days after 2/5/7-year note auction days (month-end supply cluster), else cash"
RATIONALE = ("The 2/5/7-year notes are auctioned in the last week of each month and settle at month-end, when index duration extension adds demand; the earlier-round month-end TLT effect is concentrated entirely on the sessions after these auctions. Calendar-only rule.")
VARIANTS_TRIED = 85
DATA = "long"
BENCH = "TLT"
TERMS = [2, 5, 7]     # original maturity classes (years) whose auction days count; None = every non-bill auction
HOLD = 2

def strategy(D):
    import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research4")
    import lib4, re, numpy as np, pandas as pd
    L = lib4.us_calendar(D)
    ix = L["C"]["TLT"].dropna().index
    a = L["auctions"]; a = a[a.security_type != "Bill"].copy()
    def mat(s):
        m = re.search(r"(\d+)-Year", s); m2 = re.search(r"(\d+)-Month", s)
        return (int(m.group(1)) if m else 0) + (int(m2.group(1)) / 12 if m2 else 0)
    y = a.security_term.map(mat)
    cls = np.where(y > 19, 30, np.where(y > 8, 10, np.where(y > 6, 7, np.where(y > 4, 5, np.where(y > 2.5, 3, 2)))))
    if TERMS is not None:
        a = a[np.isin(cls, TERMS)]
    d = pd.DatetimeIndex(sorted(set(pd.to_datetime(a.auction_date)))); d = d[(d >= ix[0]) & (d <= ix[-1])]
    f = pd.Series(0.0, ix); f.iloc[np.unique(ix.searchsorted(d))] = 1.0        # auction days (calendar announced in advance)
    since = pd.Series(np.arange(len(ix)), ix) - pd.Series(np.where(f > 0, np.arange(len(ix)), np.nan), ix).ffill()
    pos = ((since >= 0) & (since <= HOLD - 1)).astype(float)                  # buy at the close of an auction day, hold HOLD days
    pos = pos * (1 - f.shift(-1).fillna(0))                                   # but be flat over the next auction day (known ahead)
    # calendar-only rule: position for tomorrow is known today -> trade at today's close (exec="same_close")
    return lib4.daily_strategy(pos.rename("TLT"), L, 2.0, "same_close")

DISCOVERY = {
 "days": 4134,
 "active_days_pct": 18.9163038219642,
 "ann_return_pct": 4.87798956688104,
 "ann_vol_pct": 4.521685368173392,
 "sharpe": 1.078798980843637,
 "t": 4.369437113951774,
 "max_drawdown_pct": -5.055934788841321,
 "positive_years": "17/17",
 "first_half_ann_pct": 4.986289311699879,
 "second_half_ann_pct": 4.769689822062199,
 "mde_ann_pct": 2.7909713766708295,
 "by_year_pct": {
  "2002": 7.73,
  "2003": 7.11,
  "2004": 3.1,
  "2005": 3.95,
  "2006": 2.1,
  "2007": 6.31,
  "2008": 6.2,
  "2009": 2.67,
  "2010": 5.79,
  "2011": 13.92,
  "2012": 5.93,
  "2013": 0.52,
  "2014": 4.38,
  "2015": 3.34,
  "2016": 3.99,
  "2017": 0.35,
  "2018": 3.52
 },
 "from": "2002-07-31",
 "to": "2018-12-31",
 "beta": 0.11130505679293586,
 "alpha_ann_pct": 4.080772141336422,
 "alpha_t": 3.8600084298512725,
 "bench_ann_pct": 7.162454685483914,
 "bench_sharpe": 0.5487287267464943,
 "bench_max_drawdown_pct": -26.72490271563579,
 "worst_day_pct": -2.956479161506398,
 "worst_month_pct": -3.831661010343912,
 "ex_2008_09_t": 4.332554976433948,
 "ex_2008_09_alpha_t": 3.770517577350661
}
