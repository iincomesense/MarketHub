"""
zscan.py — thin wrapper around zone_core for the Streamlit app.
"""
from __future__ import annotations

import threading

import pandas as pd
import zone_core
import zdata

# --------------------------------------------------------------------------- #
#  small process-level caches so a universe scan reuses base bars / OI / quotes #
# --------------------------------------------------------------------------- #
_oi_cache = {}
_oi_lock = threading.Lock()
_daily_hl_cache = {}
_dhl_lock = threading.Lock()


def _daily_hl(symbol):
    with _dhl_lock:
        if symbol in _daily_hl_cache:
            return _daily_hl_cache[symbol]
    v = zdata.daily_hl(symbol, period="1y")
    with _dhl_lock:
        _daily_hl_cache[symbol] = v
    return v


def _oi_snapshot(symbol):
    """Return (call_oi, put_oi) or (None, None).  Cached per symbol."""
    with _oi_lock:
        if symbol in _oi_cache:
            return _oi_cache[symbol]
    try:
        import options as _opt
        live = _opt.live_oi(symbol)
        call_oi = live.get("call_oi")
        put_oi = live.get("put_oi")
    except Exception:
        call_oi, put_oi = None, None
    with _oi_lock:
        _oi_cache[symbol] = (call_oi, put_oi)
    return call_oi, put_oi


def _fmt_oi(v):
    """Format an OI count the Indian way (Cr / L / raw)."""
    if v is None:
        return "—"
    v = float(v)
    if v >= 1e7:
        return f"{v/1e7:.2f}Cr"
    if v >= 1e5:
        return f"{v/1e5:.2f}L"
    return f"{v:,.0f}"


def oi_bias(symbol, is_demand):
    """Return a rich dict for the Put/Call OI bias of a zone direction.

    Demand (support) is bullish-leaning when Put OI > Call OI.
    Supply (resistance) is bearish-leaning when Call OI > Put OI.

    Returns {label, aligned, put, call} where `label` shows the actual numbers
    (e.g. 'P 4.5L > C 3.1L'), `aligned` is True when OI agrees with the zone
    direction.  Returns {} when the live OI is unavailable (blocked on cloud).
    """
    call_oi, put_oi = _oi_snapshot(symbol)
    if call_oi is None or put_oi is None or call_oi == 0:
        return {}
    p, c = _fmt_oi(put_oi), _fmt_oi(call_oi)
    if is_demand:
        aligned = put_oi > call_oi
        return {"label": f"P {p} {'>' if aligned else '<'} C {c}",
                "aligned": aligned, "put": put_oi, "call": call_oi}
    aligned = call_oi > put_oi
    return {"label": f"C {c} {'>' if aligned else '<'} P {p}",
            "aligned": aligned, "put": put_oi, "call": call_oi}


def eod_band(symbol):
    """Return the EOD (daily close candle) band dict:
       {hi, lo, eod_hi=hi*1.10, eod_lo=lo*0.90} or None if daily data unavailable.
    The zone scan is restricted to this band (daily high+10% .. low-10%)."""
    hi, lo = _daily_hl(symbol)
    if hi is None or lo is None:
        return None
    return {"hi": hi, "lo": lo, "eod_hi": hi * 1.10, "eod_lo": lo * 0.90}


def eod_zone_filter(zones, symbol):
    """Keep only zones that fall inside the EOD band (daily high+10% .. low-10%).

    Returns (kept_zones, band).  If band is None, returns zones unchanged.
    """
    band = eod_band(symbol)
    if band is None:
        return zones, None
    kept = []
    for z in zones:
        z_lo, z_hi = min(z.proxVal, z.distVal), max(z.proxVal, z.distVal)
        if z_hi >= band["eod_lo"] and z_lo <= band["eod_hi"]:
            kept.append(z)
    return kept, band


def scan(symbol, timeframe="2h", min_score=40, recommended=False,
         strict=False, lookback_months=None, start=None):
    """Return (zones, df, summary_dict) for a symbol / timeframe."""
    df = zdata.load_zone_frame(symbol, timeframe, start=start)
    params = zone_core.settings()
    if strict:
        params.update({"volume_gate": True, "legInMinAtrMult": 1.0,
                       "maxWickPct": 0.30, "legInToBaseSizeMult": 2.0,
                       "legInToBaseSizeMultSingleBase": 1.5,
                       "legOutMinTrRatio": 1.0})
    params["minValidScore"] = min_score
    zones = zone_core.scan_zones(df, params=params)
    if recommended:
        rec = zone_core.recommended_trade_setup()
        zones_all = zones
        zones = [z for z in zones_all if z.patternType in rec["patterns"]]
        for z in zones:
            pass
        roi = zone_core.realistic_roi(
            zones_all, df, rr=rec["targetRR"], risk_pct=rec["risk_pct"],
            capital=rec["capital"], patterns=rec["patterns"],
            buffer=rec["slBufferAtr"], entry_mode=rec.get("entry_mode", "prox"),
            max_hold=40)
        return zones, df, {"recommended": rec, "roi": roi}
    summary = zone_core.backtest_summary(zones, df)
    return zones, df, summary


def scan_universe_zones(timeframes=("2h", "4h"), min_score=40, recommended=True,
                        strict=False, active_only=False, eod_filter=False,
                        symbols=None):
    """Scan the full NSE futures universe across EVERY given timeframe and return
    one flat list of every VALID zone with its details.

    Each row: {symbol, tf, pattern, dir, entry, sl, tp, score, hq, state,
               touches, ts, last, chain, tv, oi, eod_lo, eod_hi, in_band,
               eod_band}

    ``eod_filter``  : keep only zones that fall inside the EOD candle band
                      (daily low -10% .. daily high +10%).  This is the
                      "scan only in the area around today's daily candle" rule.
    ``symbols``     : optional list of Yahoo symbols to scan (default = all F&O).
    """
    import options as _opt
    import tv as _tv
    all_zones = []
    universe = list(symbols) if symbols else list(zdata.FUT_STOCKS)
    for sym in universe:
        eod_lo = eod_hi = None
        if eod_filter:
            hi, lo = _daily_hl(sym)
            if hi is not None and lo is not None:
                eod_hi = hi * 1.10
                eod_lo = lo * 0.90
        for tf in timeframes:
            try:
                zones, df, extra = scan(sym, tf, min_score=min_score,
                                        recommended=recommended, strict=strict)
                last = float(df["close"].iloc[-1]) if df is not None and len(df) else None
                # option-chain + tradingview links (compute once per symbol/tf)
                links = _opt.deep_links(sym)
                chain = links[0]["url"] if links else ""
                tv_url = _tv.chart_url(sym, tf)
                for z in zones:
                    if active_only and z.state not in ("Fresh", "Tested"):
                        continue
                    if recommended and z.patternType not in ["DBD"]:
                        continue
                    z_lo, z_hi = min(z.proxVal, z.distVal), max(z.proxVal, z.distVal)
                    in_band = True
                    if eod_filter and eod_lo is not None:
                        in_band = (z_hi >= eod_lo) and (z_lo <= eod_hi)
                    if eod_filter and not in_band:
                        continue
                    all_zones.append({
                        "symbol": sym, "tf": tf,
                        "pattern": z.patternType,
                        "dir": "Demand" if z.isDemand else "Supply",
                        "entry": round(z.proxVal, 2),
                        "sl": round(z.slVal, 2),
                        "tp": round(z.tpVal, 2),
                        "score": z.densityScore,
                        "hq": bool(z.isHQ),
                        "state": z.state,
                        "touches": z.touchCount,
                        "last": last,
                        "ts": str(z.timestamp)[:16],
                        "chain": chain,
                        "tv": tv_url,
                        "oi": oi_bias(sym, z.isDemand),
                        "eod_lo": eod_lo,
                        "eod_hi": eod_hi,
                        "in_band": in_band,
                    })
            except Exception:
                continue
    all_zones.sort(key=lambda z: (-z["score"], z["symbol"], z["tf"]))
    return all_zones


def active_zones(zones):
    return zone_core.latest_active_zones(zones)


def alerts(zones, price):
    return zone_core.get_zone_alerts(zones, price)


def top_zones(zones, price, limit=10):
    cand = [z for z in zones if z.state in ("Fresh", "Tested")]
    cand.sort(key=lambda z: (-z.densityScore, abs(z.proxVal - price) / z.proxVal))
    return cand[:limit]


def zone_to_row(z, price):
    dist_pct = (price - z.proxVal) / z.proxVal * 100
    if not z.isDemand:
        dist_pct = (z.proxVal - price) / z.proxVal * 100
    return {
        "pattern": z.patternType,
        "cat": z.zoneCategory,
        "dir": "DEMAND" if z.isDemand else "SUPPLY",
        "entry": round(z.proxVal, 2),
        "sl": round(z.slVal, 2),
        "tp": round(z.tpVal, 2),
        "score": z.densityScore,
        "hq": z.isHQ,
        "touches": z.touchCount,
        "state": z.state,
        "dist%": round(dist_pct, 2),
        "ts": z.timestamp,
    }


def scan_universe(timeframes=("2h", "4h"), min_score=40, recommended=True,
                  strict=False, eod_filter=False, symbols=None):
    """Scan ALL NSE futures stocks across BOTH timeframes at once (summary rows).

    Returns a list of rows (one per stock-timeframe) with zone count, best active
    zone, last price, and recommended ROI, so the app can show the whole universe
    in a single table (each row also links to that stock's option chain).
    """
    import options as _opt
    import tv as _tv
    rows = []
    universe = list(symbols) if symbols else list(zdata.FUT_STOCKS)
    for sym in universe:
        for tf in timeframes:
            try:
                zones, df, extra = scan(sym, tf, min_score=min_score,
                                        recommended=recommended, strict=strict)
                last = float(df["close"].iloc[-1]) if df is not None and len(df) else None
                active = [z for z in zones if z.state in ("Fresh", "Tested")]
                best = max(active, key=lambda z: z.densityScore) if active else None
                roi = extra.get("roi", {}) if isinstance(extra, dict) else {}
                links = _opt.deep_links(sym)
                chain = links[0]["url"] if links else ""
                rows.append({
                    "symbol": sym, "tf": tf, "zones": len(zones),
                    "active": len(active),
                    "best_score": best.densityScore if best else None,
                    "best_dir": ("Demand" if best.isDemand else "Supply") if best else None,
                    "best_pat": best.patternType if best else None,
                    "last": last,
                    "roi_n": roi.get("n_trades"),
                    "roi_pct": roi.get("net_roi_pct"),
                    "chain": chain,
                    "tv": _tv.chart_url(sym, tf),
                })
            except Exception as e:
                rows.append({"symbol": sym, "tf": tf, "zones": 0, "active": 0,
                             "best_score": None, "best_dir": None, "best_pat": None,
                             "last": None, "roi_n": None, "roi_pct": None,
                             "chain": "", "tv": _tv.chart_url(sym, tf),
                             "error": str(e)[:60]})
    return rows
