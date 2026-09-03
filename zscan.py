"""
zscan.py — thin wrapper around zone_core for the Streamlit app.
"""
from __future__ import annotations

import pandas as pd
import zone_core
import zdata


def scan(symbol, timeframe="2h", min_score=40, recommended=False,
         strict=False, lookback_months=None, start=None):
    """Return (zones, df, summary_dict) for a symbol / timeframe.

    - zones:       list of Zone objects (VALID only; scans already filter).
    - df:          the zone-ready frame (for realistic_roi).
    - summary:     computed forward-quality summary via zone_core.backtest_summary.
    """
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
        # apply the recommended SL buffer / RR for the target/TP in the Zone objects
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
                        strict=False, active_only=False):
    """Scan ALL NSE futures stocks across EVERY timeframe and return ONE flat list
    of every VALID zone with its details (the true 'zone scan' across the universe).

    Each row: {symbol, tf, pattern, dir, entry, sl, tp, score, hq, state,
               touches, dist_pct, last, chain}
    """
    import options as _opt
    all_zones = []
    for sym in zdata.FUT_STOCKS:
        for tf in timeframes:
            try:
                zones, df, extra = scan(sym, tf, min_score=min_score,
                                        recommended=recommended, strict=strict)
                last = float(df["close"].iloc[-1]) if df is not None and len(df) else None
                links = _opt.deep_links(sym)
                chain = links[0]["url"] if links else ""
                for z in zones:
                    if active_only and z.state not in ("Fresh", "Tested"):
                        continue
                    if recommended and z.patternType not in ["DBD"]:
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
                    })
            except Exception:
                continue
    # sort by score descending
    all_zones.sort(key=lambda z: (-z["score"], z["symbol"]))
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
                  strict=False):
    """Scan ALL NSE futures stocks across BOTH timeframes at once.

    Returns a list of rows (one per stock-timeframe) with zone count, best active
    zone, last price, and recommended ROI, so the app can show the whole universe
    in a single table (each row also links to that stock's option chain).

    Each row: {symbol, tf, zones, active, best_score, best_dir, last,
               roi_n, roi_pct, chain_url_frag}
    """
    import options as _opt
    rows = []
    for sym in zdata.FUT_STOCKS:
        for tf in timeframes:
            try:
                zones, df, extra = scan(sym, tf, min_score=min_score,
                                        recommended=recommended, strict=strict)
                last = float(df["close"].iloc[-1]) if df is not None and len(df) else None
                active = [z for z in zones if z.state in ("Fresh", "Tested")]
                best = max(active, key=lambda z: z.densityScore) if active else None
                roi = extra.get("roi", {}) if isinstance(extra, dict) else {}
                # a short label for the option-chain deep link (first one)
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
                })
            except Exception as e:
                rows.append({"symbol": sym, "tf": tf, "zones": 0, "active": 0,
                             "best_score": None, "best_dir": None, "best_pat": None,
                             "last": None, "roi_n": None, "roi_pct": None,
                             "chain": "", "error": str(e)[:60]})
    return rows
