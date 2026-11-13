import sys; sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research"); import lib
import numpy as np, pandas as pd

def nyse_holidays(y0, y1):
    """Rule-based NYSE full-day holidays (calendar knowledge only)."""
    from pandas.tseries.holiday import (AbstractHolidayCalendar, Holiday, nearest_workday, USMartinLutherKingJr,
        USPresidentsDay, GoodFriday, USMemorialDay, USLaborDay, USThanksgivingDay, sunday_to_monday)
    class NYSE(AbstractHolidayCalendar):
        rules = [Holiday("NY", month=1, day=1, observance=sunday_to_monday), USMartinLutherKingJr, USPresidentsDay, GoodFriday,
                 USMemorialDay, Holiday("Juneteenth", month=6, day=19, start_date="2022-01-01", observance=nearest_workday),
                 Holiday("July4", month=7, day=4, observance=nearest_workday), USLaborDay, USThanksgivingDay,
                 Holiday("Xmas", month=12, day=25, observance=nearest_workday)]
    return NYSE().holidays(pd.Timestamp(y0, 1, 1), pd.Timestamp(y1, 12, 31))

def calendar(index, pad=15):
    """Calendar features on the business-day index extended `pad` rows into the future."""
    ext = index.union(pd.bdate_range(index[-1], periods=pad + 1))
    hol = nyse_holidays(ext[0].year, ext[-1].year + 1)
    # also need month boundaries beyond the pad -> build a wide trading-day list
    wide = pd.bdate_range(ext[0] - pd.Timedelta(days=40), ext[-1] + pd.Timedelta(days=40))
    td = wide[~wide.isin(hol)]
    s = pd.Series(1, index=td)
    ym = td.to_period("M")
    fwd = s.groupby(ym).cumsum()                       # 1 = first trading day of month
    bwd = -(s[::-1].groupby(ym[::-1]).cumsum()[::-1])  # -1 = last trading day of month
    cal = pd.DataFrame({"tdm": fwd, "tdm_rev": bwd}, index=td)
    cal["dow"] = td.dayofweek; cal["month"] = td.month
    nxt = pd.Series(td[1:], index=td[:-1]).reindex(td)
    cal["pre_hol"] = ((nxt - pd.Series(td, index=td)).dt.days.sub(1).clip(lower=0) > 0) & False
    # pre-holiday: next trading day is separated by a weekday holiday
    gap_has_hol = [len(pd.bdate_range(a, b)) > 2 if pd.notna(b) else False for a, b in zip(td, nxt)]
    cal["pre_hol"] = gap_has_hol
    prv = pd.Series(td[:-1], index=td[1:]).reindex(td)
    cal["post_hol"] = [len(pd.bdate_range(b, a)) > 2 if pd.notna(b) else False for a, b in zip(td, prv)]
    # third friday (opex): week containing it
    tf = pd.Series(td, index=td).groupby(ym).apply(lambda x: x[(x.dt.dayofweek == 4)].iloc[2] if (x.dt.dayofweek == 4).sum() >= 3 else pd.NaT)
    third_fri = {p: (pd.Timestamp(p.year, p.month, 15) + pd.offsets.Week(weekday=4)) for p in ym.unique()}
    tfw = pd.Series([third_fri[p].isocalendar()[1] for p in ym], index=td)
    cal["opex_week"] = (pd.Series(td.isocalendar().week.values, index=td) == tfw).values
    cal["trading"] = True
    cal = cal.reindex(ext); cal["trading"] = cal["trading"].fillna(False).astype(bool)
    return cal

def cal_weights(index, mask_fn, ticker, pad=15):
    """Weight 1 in `ticker` on rows where the day-after-tomorrow row (t+2) satisfies mask_fn(cal). Calendar-only."""
    cal = calendar(index, pad)
    want = mask_fn(cal).reindex(cal.index).fillna(False).astype(float)
    # holiday rows: carry the previous desired state (no trading on holidays, returns are 0 anyway)
    want = want.where(cal["trading"], np.nan).ffill().fillna(0.0)
    w = want.shift(-2).reindex(index).fillna(0.0)
    return pd.DataFrame({ticker: w})
