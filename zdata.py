"""
zdata.py — self-contained live data loader for the zone screener.

Fetches base bars from Yahoo Finance and resamples to the requested timeframe
exactly the way the backtest path did (prep_data.resample).  Being
self-contained, the app deploys standalone on Streamlit Cloud without the cached
CSV set.

Supported timeframes: 15m · 30m · 75m · 1h · 2h · 4h · 6h · 8h · 1D · 1W · 1M
"""
from __future__ import annotations

import threading
import pandas as pd
import yfinance as yf

FUT_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "BHARTIARTL.NS", "HINDUNILVR.NS", "ITC.NS", "LT.NS",
    "BAJFINANCE.NS", "KOTAKBANK.NS", "AXISBANK.NS", "NESTLEIND.NS",
    "WIPRO.NS", "TITAN.NS", "ULTRACEMCO.NS", "ASIANPAINT.NS",
]
INDEX_INSTR = ["^NSEI"]
NIFTY_FUT_STOCKS = FUT_STOCKS  # alias
STOCK_CHOICES = FUT_STOCKS + ["^NSEI"]

# --------------------------------------------------------------------------- #
#  Timeframe config — (base yfinance interval, base period, pandas resample    #
#  rule).  Base intervals are fetched once per symbol and reused across the    #
#  timeframes that share them (e.g. 2h/4h/6h/8h all derive from 60m).          #
# --------------------------------------------------------------------------- #
TIMEFRAMES = ["15m", "30m", "75m", "1h", "2h", "4h", "6h", "8h", "1D", "1W", "1M"]

TF_CONFIG = {
    "15m": dict(interval="15m", period="60d", rule="15min"),
    "30m": dict(interval="30m", period="60d", rule="30min"),
    "75m": dict(interval="15m", period="60d", rule="75min"),
    "1h":  dict(interval="60m", period="2y",  rule="60min"),
    "2h":  dict(interval="60m", period="2y",  rule="2h"),
    "4h":  dict(interval="60m", period="2y",  rule="4h"),
    "6h":  dict(interval="60m", period="2y",  rule="6h"),
    "8h":  dict(interval="60m", period="2y",  rule="8h"),
    "1D":  dict(interval="1d",  period="2y",  rule="1D"),
    "1W":  dict(interval="1d",  period="2y",  rule="1W"),
    "1M":  dict(interval="1d",  period="2y",  rule="1ME"),
}

# small process-level cache so a universe scan reuses base bars across TFs
_BASE_CACHE = {}
_BASE_LOCK = threading.Lock()


def _fetch_base(sym, interval, period):
    """Fetch + normalise base OHLCV bars, cached per (sym, interval, period)."""
    key = (sym, interval, period)
    with _BASE_LOCK:
        if key in _BASE_CACHE:
            return _BASE_CACHE[key].copy()
    df = yf.download(sym, interval=interval, progress=False, auto_adjust=False,
                     period=period)
    if df is None or len(df) == 0:
        raise RuntimeError(f"no data for {sym} @ {interval}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.reset_index()
    ts_col = "Datetime" if "Datetime" in df.columns else "Date"
    df["timestamp"] = pd.to_datetime(df[ts_col])
    df = df[["timestamp", "Open", "High", "Low", "Close", "Volume"]].copy()
    df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"]).sort_values("timestamp")
    with _BASE_LOCK:
        _BASE_CACHE[key] = df.copy()
    return df


def fetch_1h(sym, start=None, end=None, period="2y"):
    """Back-compat alias: 1h bars (lowercase ohlcv)."""
    df = _fetch_base(sym, "60m", period)
    if start is not None:
        df = _trim(df, start)
    return df


def _trim(df, start):
    try:
        st = pd.Timestamp(start)
        if df["timestamp"].dt.tz is not None and st.tz is None:
            st = st.tz_localize(df["timestamp"].dt.tz)
        df = df[df["timestamp"] >= st]
    except Exception:
        pass
    return df


def resample(df, rule):
    s = df.set_index("timestamp")
    agg = s.resample(rule).agg({"open": "first", "high": "max", "low": "min",
                                "close": "last", "volume": "sum"})
    agg = agg.dropna(subset=["open", "high", "low", "close"])
    agg.index = pd.to_datetime(agg.index)
    agg.index.name = "timestamp"
    return agg.sort_index()


def load_zone_frame(symbol, timeframe, **kw):
    """Return a DatetimeIndex + lowercase-ohlcv DataFrame ready for zone_core.scan_zones.

    Supports all TIMEFRAMES.  ``kw`` may carry ``start`` / ``lookback_months``.
    """
    if timeframe not in TF_CONFIG:
        timeframe = normalize_tf(timeframe)
    cfg = TF_CONFIG[timeframe]
    df = _fetch_base(symbol, cfg["interval"], cfg["period"])
    if kw.get("start") is not None:
        df = _trim(df, kw["start"])
    rule = cfg["rule"]
    # if the base is already the requested granularity, avoid a redundant resample
    if rule in ("1D", "1W", "1ME") and cfg["interval"] == "1d":
        # daily base -> resample daily/weekly/monthly
        return resample(df, rule)
    return resample(df, rule)


def normalize_tf(tf):
    m = {"daily": "1D", "day": "1D", "d": "1D", "weekly": "1W", "week": "1W",
         "w": "1W", "monthly": "1M", "month": "1M", "m": "1M",
         "1h": "1h", "60m": "1h", "60min": "1h",
         "75m": "75m", "75min": "75m", "2h": "2h", "4h": "4h", "6h": "6h", "8h": "8h"}
    tf = str(tf).lower().replace(" ", "")
    return m.get(tf, tf)


def daily_hl(symbol, period="1y"):
    """Return (high, low) of the most recent daily (EOD) candle for the band filter."""
    try:
        df = _fetch_base(symbol, "1d", period)
        last = df.iloc[-1]
        return float(last["high"]), float(last["low"])
    except Exception:
        return None, None


if __name__ == "__main__":
    for tf in TIMEFRAMES:
        try:
            d = load_zone_frame("RELIANCE.NS", tf)
            print(f"{tf:5s} bars={len(d)}")
        except Exception as e:
            print(f"{tf:5s} ERR {str(e)[:70]}")
    print("daily_hl:", daily_hl("RELIANCE.NS"))
