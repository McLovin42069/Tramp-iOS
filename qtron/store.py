"""Qtron storage: one SQLite database (cache/geheugen.db) plus a file archive (cache/archive/).
No Streamlit here, so the nightly collector can use it too."""
import json, sqlite3, time
from contextlib import closing
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
CACHE_DIR = BASE / "cache"
ARCHIVE_DIR = CACHE_DIR / "archive"
MEM_FILE = CACHE_DIR / "geheugen.db"
SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS snapshots(date TEXT, ticker TEXT, last REAL, s5 REAL, s20 REAL, s60 REAL, totaal REAL, signaal TEXT, fase TEXT,
                                     model REAL, PRIMARY KEY(date, ticker));
CREATE TABLE IF NOT EXISTS analyst_log(date TEXT, scope TEXT, rank INTEGER, ticker TEXT, kans REAL, weight REAL, price REAL, with_model INTEGER,
                                       PRIMARY KEY(date, scope, rank));
CREATE TABLE IF NOT EXISTS model_log(date TEXT PRIMARY KEY, horizon INTEGER, depth INTEGER, val_t REAL, hold_ic REAL, hold_t REAL, hold_n INTEGER,
                                     spread REAL, verdict TEXT);
CREATE TABLE IF NOT EXISTS sell_log(date TEXT, ticker TEXT, advies TEXT, reden TEXT, PRIMARY KEY(date, ticker));
CREATE TABLE IF NOT EXISTS pattern_meta(pattern TEXT PRIMARY KEY, golive TEXT, version INTEGER);
CREATE TABLE IF NOT EXISTS pattern_log(date TEXT, pattern TEXT, position REAL, ret REAL, PRIMARY KEY(date, pattern));
CREATE TABLE IF NOT EXISTS pattern_signal(date TEXT, pattern TEXT, active INTEGER, action TEXT, logged_at TEXT, PRIMARY KEY(date, pattern));
CREATE TABLE IF NOT EXISTS archive_log(date TEXT, dataset TEXT, rows INTEGER, note TEXT, PRIMARY KEY(date, dataset));
"""


def db():
    CACHE_DIR.mkdir(exist_ok=True)
    con = sqlite3.connect(MEM_FILE, timeout=20)
    con.executescript(SCHEMA)
    return con


def write(sql, rows):
    """Best-effort write: storage problems must never break the app or the collector."""
    try:
        with closing(db()) as con, con:
            con.executemany(sql, rows)
        return True
    except Exception:
        return False


def read(sql, params=()):
    try:
        with closing(db()) as con:
            return pd.read_sql_query(sql, con, params=params)
    except Exception:
        return pd.DataFrame()


def disk(name, max_age_h=1e9):
    f = CACHE_DIR / name
    try:
        if f.exists() and time.time() - f.stat().st_mtime < max_age_h * 3600:
            return pd.read_pickle(f)
    except Exception:
        pass
    return None


def disk_save(name, obj):
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        pd.to_pickle(obj, CACHE_DIR / name)
    except Exception:
        pass


def archive_append(dataset, df, key_cols, day):
    """Append rows to this month's archive file of a dataset, dropping duplicates on key_cols.
    Files: cache/archive/<dataset>/<YYYY-MM>.pkl. Returns the number of rows the file now holds."""
    if df is None or len(df) == 0:
        return 0
    d = ARCHIVE_DIR / dataset
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{pd.Timestamp(day):%Y-%m}.pkl"
    try:
        old = pd.read_pickle(f) if f.exists() else None
        out = pd.concat([old, df], ignore_index=True) if old is not None else df.reset_index(drop=True)
        out = out.drop_duplicates(subset=key_cols, keep="last")
        out.to_pickle(f)
        write("INSERT OR REPLACE INTO archive_log VALUES (?,?,?,?)", [(str(pd.Timestamp(day).date()), dataset, int(len(df)), "")])
        return len(out)
    except Exception:
        return 0


def archive_status():
    """One row per dataset: files, size on disk, first and last collection day, days collected."""
    log = read("SELECT dataset, MIN(date) AS eerste, MAX(date) AS laatste, COUNT(*) AS dagen, SUM(rows) AS rijen FROM archive_log GROUP BY dataset")
    sizes = {}
    if ARCHIVE_DIR.exists():
        for d in ARCHIVE_DIR.iterdir():
            if d.is_dir():
                sizes[d.name] = sum(f.stat().st_size for f in d.glob("*.pkl")) / 1e6
    if len(log):
        log["MB"] = log["dataset"].map(sizes).fillna(0.0)
    return log
