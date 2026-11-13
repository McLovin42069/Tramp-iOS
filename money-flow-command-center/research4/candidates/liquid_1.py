NAME = "TLT long for 2 days after every Treasury coupon auction day (flat on auction days), else cash"
RATIONALE = ("Dealers and investors cheapen long bonds into coupon supply (auction concession) and yields fall back once the supply is absorbed; on 2002-2018 all of TLT's return was earned on the 1-3 sessions after coupon auction days. The auction calendar is announced in advance, so the rule is calendar-only. It subsumes the month-end Treasury effect: month-end days that are not post-auction days earned zero.")
VARIANTS_TRIED = 85
DATA = "long"
BENCH = "TLT"
TERMS = None     # original maturity classes (years) whose auction days count; None = every non-bill auction
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
 "active_days_pct": 35.38945331398162,
 "ann_return_pct": 6.92529202748158,
 "ann_vol_pct": 6.170595081782625,
 "sharpe": 1.1223053750402516,
 "t": 4.5456501590811325,
 "max_drawdown_pct": -8.228384753409902,
 "positive_years": "14/17",
 "first_half_ann_pct": 7.360500929688847,
 "second_half_ann_pct": 6.490083125274316,
 "mde_ann_pct": 3.8087467057085815,
 "by_year_pct": {
  "2002": 7.24,
  "2003": 2.46,
  "2004": 9.67,
  "2005": -0.41,
  "2006": -0.4,
  "2007": 7.6,
  "2008": 17.89,
  "2009": 8.54,
  "2010": 10.22,
  "2011": 12.16,
  "2012": 16.52,
  "2013": 1.98,
  "2014": 14.46,
  "2015": 3.5,
  "2016": -3.43,
  "2017": 4.68,
  "2018": 4.28
 },
 "from": "2002-07-31",
 "to": "2018-12-31",
 "beta": 0.20901330481751687,
 "alpha_ann_pct": 5.428243703062879,
 "alpha_t": 3.9723619175128158,
 "bench_ann_pct": 7.162454685483914,
 "bench_sharpe": 0.5487287267464943,
 "bench_max_drawdown_pct": -26.72490271563579,
 "worst_day_pct": -2.956479161506398,
 "worst_month_pct": -3.831661010343912,
 "ex_2008_09_t": 3.979966411543664,
 "ex_2008_09_alpha_t": 3.2652143071164677
}
