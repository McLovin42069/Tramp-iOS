"""Qtron data feeds that do not depend on Streamlit: prices, crypto funding, share counts, earnings, and the
daily archive of data that cannot be bought back later (15-minute bars, option-market summaries, headlines)."""
import io, time, zipfile
import numpy as np, pandas as pd, requests
import store

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}


def prices(tickers, period="3y", interval="1d"):
    """Daily (or intraday) OHLCV panels {O,H,L,C,V} of [time x ticker]; tickers that fail are simply absent."""
    import yfinance as yf
    frames, tick = {}, list(dict.fromkeys(tickers))
    for i in range(0, len(tick), 40):
        ch = tick[i:i + 40]
        try:
            raw = yf.download(ch, period=period, interval=interval, auto_adjust=True, group_by="ticker", threads=True, progress=False)
        except Exception:
            continue
        for t in ch:
            try:
                d = (raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw).dropna(subset=["Close"])
                if len(d) > 5:
                    frames[t] = d
            except Exception:
                pass
    if not frames:
        return None
    P = {}
    for f, k in (("Open", "O"), ("High", "H"), ("Low", "L"), ("Close", "C"), ("Volume", "V")):
        df = pd.DataFrame({t: d[f] for t, d in frames.items()})
        ix = pd.to_datetime(df.index)
        if interval == "1d":
            df.index = (ix.tz_localize(None) if ix.tz is not None else ix).normalize()
        else:
            df.index = ix.tz_convert("America/New_York").tz_localize(None) if ix.tz is not None else ix
        P[k] = df[~df.index.duplicated(keep="last")].sort_index()
    return P


def fetch_funding(symbols=("BTCUSDT", "ETHUSDT"), max_age_h=20):
    """Perpetual-futures funding rates (Binance public data dumps, monthly files; the running month via the live API
    when reachable). Kept in cache/funding.pkl and extended incrementally. Returns [timestamp x symbol] or None."""
    old = store.disk("funding.pkl")
    if old is not None and store.disk("funding.pkl", max_age_h) is not None:
        return old
    have = old if old is not None else pd.DataFrame()
    out = {}
    for sym in symbols:
        s_old = have[sym].dropna() if sym in getattr(have, "columns", []) else pd.Series(dtype=float)
        start = (s_old.index[-1].to_period("M") if len(s_old) else pd.Period("2020-01", "M"))
        rows = [s_old]
        for m in pd.period_range(start, pd.Timestamp.today().to_period("M"), freq="M"):
            try:
                r = requests.get(f"https://data.binance.vision/data/futures/um/monthly/fundingRate/{sym}/{sym}-fundingRate-{m}.zip", timeout=40, headers=UA)
                if r.status_code != 200:
                    continue
                z = zipfile.ZipFile(io.BytesIO(r.content))
                x = pd.read_csv(z.open(z.namelist()[0]))
                tc = [c for c in x.columns if "time" in c.lower()][0]
                rc = [c for c in x.columns if "rate" in c.lower()][0]
                rows.append(pd.Series(pd.to_numeric(x[rc], errors="coerce").values, index=pd.to_datetime(pd.to_numeric(x[tc], errors="coerce"), unit="ms")))
            except Exception:
                continue
        try:                                    # running month: live endpoint (not reachable everywhere)
            last = max([r_.index[-1] for r_ in rows if len(r_)], default=pd.Timestamp("2020-01-01"))
            r = requests.get("https://fapi.binance.com/fapi/v1/fundingRate", params={"symbol": sym, "startTime": int(last.timestamp() * 1000) + 1, "limit": 1000}, timeout=20, headers=UA)
            if r.status_code == 200 and r.json():
                j = pd.DataFrame(r.json())
                rows.append(pd.Series(pd.to_numeric(j["fundingRate"]).values, index=pd.to_datetime(j["fundingTime"], unit="ms")))
        except Exception:
            pass
        s = pd.concat([r_ for r_ in rows if len(r_)]) if any(len(r_) for r_ in rows) else pd.Series(dtype=float)
        out[sym] = s[~s.index.duplicated(keep="last")].sort_index()
    F = pd.DataFrame(out)
    if len(F):
        store.disk_save("funding.pkl", F)
        return F
    return old


def fetch_shares(tickers, max_age_h=7 * 24):
    """Cumulative log net share issuance per company (Yahoo share counts; jumps > 40% treated as splits)."""
    got = store.disk("shares.pkl", max_age_h)
    if got is not None and len(got) >= 0.5 * len(tickers):
        return got
    import yfinance as yf
    out, miss = {}, 0
    for t in tickers:
        try:
            s = yf.Ticker(t).get_shares_full(start="2014-01-01")
            if s is None or len(s) < 8:
                continue
            s = s[~s.index.duplicated(keep="last")].astype(float)
            s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
            d = np.log(s.where(s > 0)).diff()
            d[d.abs() > np.log(1.4)] = 0.0
            out[t] = d.cumsum().groupby(level=0).last()
            miss = 0
        except Exception:
            miss += 1
            if miss > 25:
                break
    if len(out) < 0.3 * len(tickers):
        return store.disk("shares.pkl")
    store.disk_save("shares.pkl", out)
    return out


def fetch_earnings(tickers, max_age_h=7 * 24):
    """Earnings announcement times with estimate, reported EPS and surprise %, long frame. Cached weekly."""
    got = store.disk("earnings.pkl", max_age_h)
    if got is not None and got["ticker"].nunique() >= 0.5 * len(tickers):
        return got
    import yfinance as yf
    rows = []
    for t in tickers:
        try:
            e = yf.Ticker(t).get_earnings_dates(limit=40)
            if e is None or e.empty:
                continue
            e = e.reset_index()
            e.columns = ["ts", "eps_est", "eps_rep", "surprise_pct"]
            e["ticker"] = t
            e["ts"] = pd.to_datetime(e["ts"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
            rows.append(e)
        except Exception:
            continue
    if not rows:
        return store.disk("earnings.pkl")
    E = pd.concat(rows, ignore_index=True)
    store.disk_save("earnings.pkl", E)
    return E


# ── daily archive: things Yahoo does not keep for you ────────────────────────────────────────────
def archive_intraday(tickers, day=None):
    """15-minute bars of the last 5 sessions. Yahoo only serves 60 days back; archiving daily builds a permanent history."""
    P = prices(tickers, period="5d", interval="15m")
    if P is None:
        return 0
    long = pd.concat({k: P[k].stack() for k in "OHLCV"}, axis=1).reset_index()
    long.columns = ["ts", "ticker", "o", "h", "l", "c", "v"]
    return store.archive_append("intraday_15m", long, ["ts", "ticker"], day or pd.Timestamp.today())


def archive_options(underlyings, day=None, n_exp=3):
    """Per underlying and expiry: put/call volume and open interest, at-the-money implied volatility and a skew measure.
    Historical option data is not free anywhere; this snapshot, taken daily, becomes a dataset of its own."""
    import yfinance as yf
    day = pd.Timestamp(day or pd.Timestamp.today()).normalize()
    rows = []
    for u in underlyings:
        try:
            tk = yf.Ticker(u)
            spot = float(tk.fast_info["last_price"])
            for ex in list(tk.options)[:n_exp]:
                ch = tk.option_chain(ex)
                c, p = ch.calls, ch.puts
                def iv_at(df, k):
                    d = df.iloc[(df["strike"] - k).abs().argsort()[:1]]
                    return float(d["impliedVolatility"].iloc[0]) if len(d) else np.nan
                rows.append({"date": day, "ticker": u, "expiry": ex, "spot": spot,
                             "call_vol": float(c["volume"].fillna(0).sum()), "put_vol": float(p["volume"].fillna(0).sum()),
                             "call_oi": float(c["openInterest"].fillna(0).sum()), "put_oi": float(p["openInterest"].fillna(0).sum()),
                             "atm_iv": np.nanmean([iv_at(c, spot), iv_at(p, spot)]),
                             "put95_iv": iv_at(p, spot * 0.95), "call105_iv": iv_at(c, spot * 1.05)})
        except Exception:
            continue
    return store.archive_append("options_summary", pd.DataFrame(rows), ["date", "ticker", "expiry"], day)


def archive_news(tickers, day=None):
    """Latest headlines per ticker (title, publisher, time). Kept so that news can be tested against prices later."""
    import yfinance as yf
    day = pd.Timestamp(day or pd.Timestamp.today()).normalize()
    rows = []
    for t in tickers:
        try:
            for n in (yf.Ticker(t).news or [])[:15]:
                c = n.get("content", n)
                prov = c.get("provider", {})
                rows.append({"ticker": t, "title": c.get("title"), "publisher": prov.get("displayName") if isinstance(prov, dict) else n.get("publisher"),
                             "published": str(c.get("pubDate") or n.get("providerPublishTime") or ""), "id": str(n.get("id") or c.get("id") or c.get("title")),
                             "collected": day})
        except Exception:
            continue
    df = pd.DataFrame(rows)
    return store.archive_append("news_headlines", df[df["title"].notna()] if len(df) else df, ["ticker", "id"], day)
