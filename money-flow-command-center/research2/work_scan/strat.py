"""Turn the scan's clusters into concrete rules. Definitions are fixed here on DISCOVERY data (<= 2018) with a single
a-priori threshold (|z| > 1); neighbours are reported for robustness only. Then holdout_scan.py runs them once on 2019+."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "/home/user/Tramp-iOS/money-flow-command-center/research2"); import lib2

def us(L):
    """Restrict every panel to US sessions (days on which SPY traded)."""
    ix = L["C"]["SPY"].dropna().index
    return {k: (v.loc[v.index.isin(ix)] if isinstance(v, pd.DataFrame) else v) for k, v in L.items()}

def zs(x, w=60):
    """Signal divided by its own trailing volatility (window ends the day before)."""
    return x / x.rolling(w, min_periods=30).std().shift(1)

def gap_to_session(L, sig_tickers, targets, thr=1.0, cost=2.0):
    """At the OPEN of day t: average overnight gap of the signal ETFs. If it is unusually large, hold the slow
    target ETFs from that open to the close, in the direction of the gap."""
    on, _ = lib2.session_returns(L, sig_tickers)
    z = zs(on.mean(axis=1))
    side = np.sign(z).where(z.abs() > thr, 0.0)
    pos_day = pd.DataFrame({t: side / len(targets) for t in targets})
    return lib2.segment_strategy(pos_day * 0, pos_day, L, cost_bps=cost)

def day_to_next_day(L, sig_ticker, targets, thr=1.0, cost=2.0, sign=1, long_only=False):
    """At the CLOSE of day t: today's return of the signal ETF. If unusually large, hold the slow target ETFs from
    this close to the next close, in the same direction (decided a few minutes before the close)."""
    z = zs(L["C"][sig_ticker].pct_change(fill_method=None))
    side = sign * np.sign(z).where(z.abs() > thr, 0.0)
    if long_only:
        side = side.clip(lower=0)
    pos = pd.DataFrame({t: side / len(targets) for t in targets})
    return lib2.daily_strategy(pos, L, cost_bps=cost, exec="same_close")

def day_to_overnight(L, sig_ticker, targets, thr=1.0, cost=2.0):
    """Same signal, but hold the targets only overnight (close t -> open t+1)."""
    z = zs(L["C"][sig_ticker].pct_change(fill_method=None))
    side = np.sign(z).where(z.abs() > thr, 0.0)
    pos = pd.DataFrame({t: side / len(targets) for t in targets})
    return lib2.segment_strategy(pos, pos * 0, L, cost_bps=cost)

RULES = {
    "A  equity gap -> HYG+JNK session":         lambda L, thr=1.0, c=2.0: gap_to_session(L, ["SPY", "IWM", "EFA", "EEM"], ["HYG", "JNK"], thr, c),
    "B  HYG day -> EMB next day":               lambda L, thr=1.0, c=2.0: day_to_next_day(L, "HYG", ["EMB"], thr, c),
    "C  SPY day -> EMB next day":               lambda L, thr=1.0, c=2.0: day_to_next_day(L, "SPY", ["EMB"], thr, c),
    "D  SPY day -> EWH+FXI+EWT next day":       lambda L, thr=1.0, c=2.0: day_to_next_day(L, "SPY", ["EWH", "FXI", "EWT"], thr, c),
    "E  SPY day -> EWH+FXI+EWT overnight only": lambda L, thr=1.0, c=2.0: day_to_overnight(L, "SPY", ["EWH", "FXI", "EWT"], thr, c),
    "D' SPY day -> EWH+FXI+EWT next day, REVERSED": lambda L, thr=1.0, c=2.0: day_to_next_day(L, "SPY", ["EWH", "FXI", "EWT"], thr, c, sign=-1),
    "D'' same, long side only (buy after SPY drop)": lambda L, thr=1.0, c=2.0: day_to_next_day(L, "SPY", ["EWH", "FXI", "EWT"], thr, c, sign=-1, long_only=True),
    "F  SPY day -> EWC next day":               lambda L, thr=1.0, c=2.0: day_to_next_day(L, "SPY", ["EWC"], thr, c),
    "G  treasury gap -> MUB session":           lambda L, thr=1.0, c=2.0: gap_to_session(L, ["TLT", "IEF"], ["MUB"], thr, c),
    "H  SPY day -> TIP+LQD next day":           lambda L, thr=1.0, c=2.0: day_to_next_day(L, "SPY", ["TIP", "LQD"], thr, c),
}
if __name__ == "__main__":
    L = us(lib2.load_long())
    print(f"{'rule':44s} {'thr':>4} {'cost':>4} {'ann%':>6} {'vol%':>5} {'t':>6} {'shrp':>5} {'act%':>5} {'maxDD':>6} {'yrs+':>6} {'H1%':>6} {'H2%':>6}  from")
    for name, f in RULES.items():
        for thr, c in ((1.0, 2.0), (0.5, 2.0), (1.5, 2.0), (1.0, 0.0), (1.0, 5.0)):
            e = lib2.ts_eval(f(L, thr, c))
            if "t" not in e: print(name, "n/a"); continue
            print(f"{name:44s} {thr:4.1f} {c:4.0f} {e['ann_return_pct']:6.2f} {e['ann_vol_pct']:5.1f} {e['t']:6.2f} {e['sharpe']:5.2f} {e['active_days_pct']:5.0f} {e['max_drawdown_pct']:6.1f} {e['positive_years']:>6} {e['first_half_ann_pct']:6.2f} {e['second_half_ann_pct']:6.2f}  {e['from']}")
        print()
