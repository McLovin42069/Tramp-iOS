"""Qtron collector. Runs once a day on its own (systemd timer) and can also be started from the app.

What it does, in order:
  1. refreshes the long price history the patterns need, and the world-wide stock panel (also warms the app's cache)
  2. evaluates every pattern, stores today's signal with a timestamp and appends realised returns to the forward log
  3. archives data that cannot be bought back later: 15-minute bars, option-market summaries, headlines, crypto funding

Usage:  python collector.py            (full run)
        python collector.py --quick    (patterns only, no archive)
"""
import sys, time, json
import numpy as np, pandas as pd
import store, feeds, patterns
from universe import META

PATTERN_TICKERS = ["SPY", "QQQ", "TLT", "EWH", "FXI", "EWT", "XLE"]
OPTION_UNDERLYINGS = ["SPY", "QQQ", "IWM", "TLT", "GLD", "SLV", "USO", "HYG", "EEM", "FXI", "XLE", "XLF", "XLK", "SMH", "NVDA", "AAPL", "MSFT", "AMZN",
                      "META", "GOOGL", "TSLA", "AMD", "JPM", "XOM", "COIN", "MSTR", "IBIT"]


def _stock_panels(max_age_h=20.0):
    """World-wide stock panel in the app's own cache format (cache/stocks.pkl), so the app starts from disk."""
    tick = tuple(META.index[~META["core"]])
    got = store.disk("stocks.pkl", max_age_h)
    if got is not None and got.get("tickers") == tick:
        return got["panels"]
    P = feeds.prices(list(tick), period="10y")
    if P is None or P["C"].shape[1] < 0.8 * len(tick):
        old = store.disk("stocks.pkl")
        return old["panels"] if old is not None else None
    panels = {n: P[k].astype("float32") for n, k in (("Open", "O"), ("High", "H"), ("Low", "L"), ("Close", "C"), ("Volume", "V"))}
    store.disk_save("stocks.pkl", {"tickers": tick, "panels": panels, "failed": [t for t in tick if t not in P["C"].columns]})
    return panels


def build_D(max_age_h=6.0, offline=False, heavy=True):
    """Everything the patterns need. Each part falls back to the last copy on disk.
    heavy=False (the app): only the seven index series are refreshed; stocks, share counts, earnings and funding come
    from disk, where the collector keeps them up to date."""
    px = store.disk("pattern_px.pkl", 1e9 if offline else max_age_h)
    if px is None:
        px = feeds.prices(PATTERN_TICKERS, period="max")
        if px is not None and "SPY" in px["C"].columns:
            store.disk_save("pattern_px.pkl", px)
        else:
            px = store.disk("pattern_px.pkl")
    if px is None:
        return None
    D = {k: px[k].astype(float) for k in ("O", "C", "V")}
    disk_only = offline or not heavy
    sp = (store.disk("stocks.pkl") or {}).get("panels") if disk_only else _stock_panels()
    if sp is not None:
        reg = [t for t in META.index[META["cls"].isin(["Asia Stocks", "Europe Stocks"])] if t in sp["Close"].columns]
        sc = sp["Close"][reg].astype(float).ffill(limit=5)
        D["C"] = pd.concat([D["C"], sc], axis=1).sort_index()
        D["O"], D["V"] = D["O"].reindex(D["C"].index), D["V"].reindex(D["C"].index)
        asia = [t for t in reg if META.at[t, "cls"] == "Asia Stocks"]
        D["shares"] = store.disk("shares.pkl") if disk_only else feeds.fetch_shares(reg)
        D["earnings"] = store.disk("earnings.pkl") if disk_only else feeds.fetch_earnings(asia)
    D["funding"] = store.disk("funding.pkl") if disk_only else feeds.fetch_funding()
    D["meta"] = META
    return D


def golive_dates():
    m = store.read("SELECT pattern, golive FROM pattern_meta")
    return dict(zip(m["pattern"], m["golive"])) if len(m) else {}


def log_patterns(D, now=None, res=None):
    """Freeze today's signals and append realised returns since go-live. Rows already logged are never rewritten,
    so the live record cannot be changed afterwards by revised data or by a changed rule."""
    now = pd.Timestamp(now or pd.Timestamp.now())
    res = res or patterns.evaluate(D)
    live = golive_dates()
    today = str(now.date())
    new = [(p["id"], today, patterns.VERSION) for p in patterns.PATTERNS if p["id"] not in live and len(res[p["id"]]["ret"])]
    if new:
        store.write("INSERT OR IGNORE INTO pattern_meta VALUES (?,?,?)", new)
        live = golive_dates()
    rows, sig = [], []
    for p in patterns.PATTERNS:
        r, st = res[p["id"]]["ret"], res[p["id"]]["state"]
        if p["id"] in live and len(r):
            seg = r[r.index > pd.Timestamp(live[p["id"]])]
            seg = seg[seg.index.normalize() < now.normalize()]      # only completed days
            rows += [(str(d.date()), p["id"], float(v != 0), float(v)) for d, v in seg.items()]
        sig.append((today, p["id"], int(bool(st.get("active"))), (st.get("action", "") + " — " + st.get("detail", ""))[:600], now.strftime("%Y-%m-%d %H:%M")))
    if rows:
        store.write("INSERT OR IGNORE INTO pattern_log VALUES (?,?,?,?)", rows)
    store.write("INSERT OR REPLACE INTO pattern_signal VALUES (?,?,?,?,?)", sig)
    return res


def run(quick=False):
    t0, note = time.time(), {}
    D = build_D(max_age_h=0.5)
    if D is not None:
        res = log_patterns(D)
        note["patronen"] = sum(1 for v in res.values() if len(v["ret"]))
        note["actief"] = [k for k, v in res.items() if v["state"].get("active")]
    if not quick:
        day = pd.Timestamp.today()
        for name, fn, arg in (("intraday_15m", feeds.archive_intraday, list(META.index)),
                              ("options_summary", feeds.archive_options, OPTION_UNDERLYINGS),
                              ("news_headlines", feeds.archive_news, list(META.index[META["core"]])[:80] + OPTION_UNDERLYINGS)):
            try:
                note[name] = int(fn(arg, day))
            except Exception as e:
                note[name] = f"fout: {type(e).__name__}"
        f = D.get("funding") if D else None
        if f is not None and len(f):
            fl = f.stack().reset_index()
            fl.columns = ["ts", "symbol", "rate"]
            note["funding"] = int(store.archive_append("crypto_funding", fl[fl["ts"] >= day - pd.Timedelta(days=40)], ["ts", "symbol"], day))
    try:
        (store.CACHE_DIR / "collector.lock").unlink(missing_ok=True)
    except Exception:
        pass
    note["seconden"] = round(time.time() - t0)
    store.write("INSERT OR REPLACE INTO settings VALUES (?,?)", [("collector_last", json.dumps({"at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), **note}))])
    return note


if __name__ == "__main__":
    print(json.dumps(run(quick="--quick" in sys.argv), ensure_ascii=False, default=str))
