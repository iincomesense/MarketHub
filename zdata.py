"""
zdata.py — self-contained live data loader for the zone screener.

Fetches 1h bars from Yahoo Finance and resamples to 2h/4h, exactly the way the
backtest path did (prep_data.resample).  Being self-contained, the app deploys
standalone on Streamlit Cloud without the cached CSV set.
"""
from __future__ import annotations

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


def fetch_1h(sym, start=None, end=None, period="2y"):
    """Return a clean 1h DataFrame (lowercase columns).

    Yahoo caps 1h history to the last 730 days, so we fetch by `period` only
    (start/end as explicit timestamps fail for intraday).  We then trim to `start`
    if supplied (pandas-level), which keeps the resampled window tight for scans.
    """
    df = yf.download(sym, interval="1h", progress=False, auto_adjust=False,
                     period=period)
    if df is None or df.empty:
        raise RuntimeError(f"no data for {sym}")
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
    # optional trim to an explicit start (guarded; timestamps already tz-aware)
    if start is not None:
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


def load_zone_frame(symbol, rule, **kw):
    """Return a DatetimeIndex + lowercase-ohlcv DataFrame ready for zone_core.scan_zones."""
    df1 = fetch_1h(symbol, **kw)
    return resample(df1, rule)


if __name__ == "__main__":
    df = load_zone_frame("RELIANCE.NS", "2h")
    print("RELIANCE 2h bars:", len(df), df.index.min(), "->", df.index.max())
