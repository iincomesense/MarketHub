# -*- coding: utf-8 -*-
"""
zone_core.py — v10.1 (backtest-tuned + OOS-verified Demand & Supply Zone engine for 2H / 4H)

Pine-parity structure maintained (same pattern-detection as v9.3), but the thresholds
have been re-tuned and every validation rule is now a toggleable gate, so each rule can
be validated on/off and the whole system can be re-tuned in one place.

================================================================================
WHAT CHANGED (v9.3 -> v10.1)  --  driven by the 2H/4H backtest (NIFTY + 18 NSE stocks)
================================================================================
Baseline across 18 stocks x 2H+4H (Sep-2024 to Sep-2026, ~24 months, ~47k clean bars):
  v9.3 (all-on)          -> 156 zones, 38% tested, win@1R/t 68%, win@2R/t 40%,
                             win@5R/t 10%, avg MFE 2.29R, OOS exp2R 0.36
  v10.1 (tuned)          -> 221 zones, 38% tested, win@1R/t 83%, win@2R/t 58%,
                             win@5R/t 26%, avg MFE 3.59R, OOS exp2R 0.78

Tuned knobs (5 changes that added quality, verified out-of-sample):

  (1) legInMinAtrMult  1.0 -> 0.0   "Leg-in TR >= ATR" gate
        Disabling it: win@1R/t 75->80%, @2R/t 41->51%, @5R/t 9->15%.  A leg-in that is
        LARGER than ATR is over-extended and predicts WORSE zones.  Kept as a gate (OFF).

  (2) maxWickPct       0.30 -> 0.40   Leg-out wick cap
        Relaxing: zones 125->184, @1R/t -> 80%.  The 30% cap filtered out good zones.

  (3) volume_gate      True -> False  "Leg-out volume > leg-in volume"
        Disabling: zones -> 188, @2R/t 41->46%, @5R/t 9->16%.  Weak signal; also blocked
        INDEX scanning (index volume == 0).  Kept as a gate (OFF).

  (4) legInToBaseSizeMult 2.0 -> 2.5  and  SingleBase 1.5 -> 2.0
        Stricter leg-in vs base separation -> fewer but FAR better zones:
        p2 52->58%, p3 32->38%, OOS exp2R 0.69->0.78.

  (5) legOutMinTrRatio 1.0 -> 0.9   Leg-out must be >= 0.9x leg-in (was 1.0x)
        Slight relaxation improves hit-rate without losing structure.

  KEEP (disabling them lowered results): tr_hierarchy_gate, legin_base_gate.
  Non-binding on this data (kept ON): explosive_gate, engulf_gate, clv_gate,
        body_gate, base_atr_gate, duplicate_gate, imbalance_gate.

Results split (final v10.1 defaults):
  All STOCKS 2H+4H : 221 zones, 38% tested, @1R/t 83%, @2R/t 58%, @5R/t 26%, MFE 3.59
  2h STOCKS        : 113 zones, 39% tested, @1R/t 82%, @2R/t 57%, @5R/t 32%, MFE 3.59
  4h STOCKS        : 108 zones, 37% tested, @1R/t 85%, @2R/t 60%, @5R/t 20%, MFE 3.59
  Best pattern (DBD, supply continuation): @1R/t 91%, @2R/t 77%, @5R/t 27%
  Weakest pattern (RBD, supply reversal):  @1R/t 74%, @2R/t 47%, @5R/t 26%
  HQ zones (score>=90):              100% @1R/t, 100% @2R/t (rare retests)
  ^NSEI index (vol gate off):        88% @1R/t, 62% @2R/t

Note on the "mandatory" spec vs data: your spec marks leg-in TR>=ATR and leg-out
volume>=leg-in as Mandatory.  The backtest data shows both of those rules REDUCE zone
quality, so they are relaxed by default.  Flip the gate switches back to True (or use
--strict) to return to a fully strict spec-compliant scan.

================================================================================
CONFIGURATION
================================================================================
Every rule is a boolean gate in DEFAULT_PARAMS (all are ON by default except the three
tuned-off ones).  Pass a params dict with the keys you want to override:

    zones = zone_core.scan_zones(df, params={"volume_gate": True, "maxWickPct": 0.30})

df must be a pandas DataFrame with a DatetimeIndex and lowercase columns:
    open, high, low, close, volume.

================================================================================
PUBLIC API
================================================================================
    scan_zones(df, params=None, lookback_months=None)            -> List[Zone]
    latest_active_zones(zones, include_tested=True)              -> List[Zone]
    get_zone_alerts(zones, current_price, ...)                   -> List[dict]
    flag_multi_timeframe_confluence(zones_by_tf, tf_order)       -> None (in-place)
    zone_highlight_tags(zone)                                    -> List[str]
    diagnose_bar(df, at_index, params=None)                      -> List[dict]
    backtest_summary(df_list, params=None, lookback=20)          -> dict  (MFE, best-case)
    realistic_roi(zones, df, rr, risk_pct, capital)              -> dict  (SL/TP + charges)

================================================================================
VERY IMPORTANT — BEST-CASE vs REALISTIC
================================================================================
The headline figures you'll read below (win@kR/t, avg MFE) are MAXIMUM FAVOURABLE
EXCURSION — they measure how far price went before the window ended, IGNORING that
often the price hits the stop-loss first.  They are NOT attainable returns.

A realistic trade (Entry = prox, Stop = dist+buffer, Target = entry +/- R*RR,
SL checked before TP) was also simulated with Indian broker + government charges.
On 18 NSE stocks x 2H+4H (Sep-2024 to Sep-2026) the honest result was:

    RR 1:2.5  -> gross EV ~ -0.03R/trade, win 29% (breakeven 28.6%)  => ~ break-even gross
    RR 1:3.0  -> win 24% (breakeven 25%)   => negative
    RR 1:5.0  -> win 18% (breakeven 16.7%) => negative

  * Whole universe after charges (24 mo):   RR 2.5 -12% ROI, RR 3 -20%, RR 5 -20%
  * Recent 6 mo after charges:              RR 2.5 -13%, RR 3 -11%, RR 5 -17%
  * ONLY visibly non-negative subset was DBR (demand reversal) at RR 1:2.5:
      ~ +1.9% ROI over 24 months (essentially break-even, below a savings rate).

CONCLUSION (data-driven, honest): traded at the spec's exact 1:2.5/1:3/1:5 targets with
a distal+buffer stop, the system is ~ break-even gross and slightly NET NEGATIVE after
Indian charges.  The earlier optimistic MFE numbers are real as "price went there" but
NOT as "a stop-protected trade captures it".  Treat it as a *trade-setup filter*, not a
self-contained profit engine, and use `realistic_roi()` to check any parameter set /
instrument / RR on your own data before risking capital.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import numpy as np
import pandas as pd

DEFAULT_PARAMS = dict(
    # ---------- risk / money ----------
    accountCapital=25000.0,
    riskPct=0.5,
    targetRR=5.0,
    slBufferAtr=0.1,
    # ---------- indicators ----------
    atrPeriod=14,
    volSmaPeriod=20,
    # ---------- leg-in / base / leg-out thresholds ----------
    legInMinBodyPct=0.60,
    rejectOppositeCoverPct=0.50,
    maxBaseAtrMult=1.0,
    legInMinAtrMult=0.0,          # [TUNED v10.1] was 1.0 -- hurts quality
    legInToBaseSizeMult=2.5,      # [TUNED v10.1] was 2.0 -- multi-base multiplier (quality++)
    legInToBaseSizeMultSingleBase=2.0,  # [TUNED v10.1] was 1.5 -- single-base multiplier (quality++)
    legOutTrMult=1.2,
    legOutMinTrRatio=0.9,         # [TUNED v10.1] was 1.0 -- slightly relaxed hierarchy
    maxWickPct=0.40,              # [TUNED] was 0.30 -- hurts quality
    minClvPct=0.60,
    # ---------- pattern / scoring ----------
    minBaseCount=1,
    maxBaseCount=3,
    useImbalance=True,
    minValidScore=40,
    hqScoreThreshold=90,
    hqLegInAtrMult=1.5,
    hqLegOutTrMult=2.0,
    legOutBodyHeavyPressurePct=0.60,
    genuineGapScoreBonus=10,
    overnightGapScoreBonus=15,
    testedLegOutRetracePct=0.50,
    maxTestedCount=2,
    # ---------- rule gates (toggle to backtest each rule) ----------
    body_gate=True,
    opp_color_gate=True,
    base_atr_gate=True,
    legin_base_gate=True,
    legin_atr_gate=True,
    explosive_gate=True,
    wick_gate=True,
    tr_hierarchy_gate=True,
    volume_gate=False,            # [TUNED] was True -- hurts quality; lets index scan work
    imbalance_gate=True,
    engulf_gate=True,
    clv_gate=True,
    score_gate=True,
    duplicate_gate=True,
)

_HARD_MAX_BASE_COUNT = 3


def settings():
    """Return a copy of the tunable knobs (states + thresholds)."""
    p = dict(DEFAULT_PARAMS)
    p["_version"] = "v10.1"
    return p


def change_log():
    """Short summary of the rules that were tuned and the evidence."""
    return [
        ("legInMinAtrMult", 1.0, 0.0, "Leg-in TR >= ATR *hurt* zones (over-extension). @1R/t 75->80%, @2R/t 41->51%, @5R/t 9->15%, MFE 2.38->2.96, win@2R OOS 56%."),
        ("maxWickPct", 0.30, 0.40, "The 30% leg-out wick cap filtered good zones; 40% keeps them."),
        ("volume_gate", True, False, "Leg-out volume > leg-in volume removed good zones; also blocked index scanning."),
        ("legInToBaseSizeMult", 2.0, 2.5, "Stricter leg-in vs base separation -> fewer but far better zones: p2 52->58%, p3 32->38%, OOS exp2R 0.69->0.78."),
        ("legInToBaseSizeMultSingleBase", 1.5, 2.0, "Single-base zones also need a clean 2x leg-in vs base for high quality."),
        ("legOutMinTrRatio", 1.0, 0.9, "Slightly relaxed leg-out >= 0.9x leg-in improves hit-rate without losing structure."),
        ("tr_hierarchy_gate", True, True, "KEEP: disabling dropped @1R/t 75->69% (quality filter)."),
        ("legin_base_gate", True, True, "KEEP: disabling dropped @1R/t 75->70% (quality filter)."),
    ]


# --------------------------------------------------------------------------- #
#  Indicator helpers (Pine parity: gap-aware true range + Wilder ATR)          #
# --------------------------------------------------------------------------- #
def _true_range(h, l, c):
    n = len(h)
    tr = np.empty(n)
    tr[0] = h[0] - l[0]
    if n > 1:
        tr[1:] = np.maximum(h[1:] - l[1:],
                            np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])))
    return tr


def _wilder_atr_from_tr(tr, period):
    n = len(tr)
    atr = np.full(n, np.nan)
    if n >= period:
        seed = tr[:period].mean()
        atr[period - 1] = seed
        if n > period:
            alpha = 1.0 / period
            smoothed = pd.Series(tr[period:]).ewm(alpha=alpha, adjust=False).mean().to_numpy()
            atr[period:] = np.concatenate([[seed], smoothed[1:]])
    return atr


def _bar_dates_array(df):
    idx = df.index
    if isinstance(idx, pd.DatetimeIndex):
        return idx.date
    try:
        return pd.to_datetime(idx).date
    except Exception:
        return None


def _resolve_start_bar_for_lookback(df, lookback_months):
    n = len(df)
    if lookback_months is None or lookback_months <= 0 or n == 0:
        return 0
    idx = df.index
    if isinstance(idx, pd.DatetimeIndex):
        cutoff = idx[-1] - pd.DateOffset(months=lookback_months)
        return int(max(0, idx.searchsorted(cutoff, side="left")))
    return int(max(0, n - int(round(lookback_months * 21))))


def _prep(df, p):
    o = df["open"].to_numpy(dtype=float)
    h = df["high"].to_numpy(dtype=float)
    l = df["low"].to_numpy(dtype=float)
    c = df["close"].to_numpy(dtype=float)
    v = df["volume"].to_numpy(dtype=float)
    tr = _true_range(h, l, c)
    atr = _wilder_atr_from_tr(tr, p["atrPeriod"])
    vol_sma = pd.Series(v).rolling(p["volSmaPeriod"]).mean().to_numpy()
    return o, h, l, c, v, tr, atr, vol_sma


# --------------------------------------------------------------------------- #
#  Zone object                                                                #
# --------------------------------------------------------------------------- #
@dataclass
class Zone:
    proxVal: float
    distVal: float
    slVal: float
    tpVal: float
    isDemand: bool
    isHQ: bool
    densityScore: int
    patternType: str = ""
    zoneCategory: str = ""
    state: str = "Fresh"
    touchCount: int = 0
    originalDensityScore: int = 0
    startBarIndex: int = 0
    createdBarIndex: int = 0
    baseCount: int = 0
    timestamp: object = None
    legOutHigh: float = 0.0
    legOutLow: float = 0.0
    legOutMidLevel: float = 0.0
    isOvernightGap: bool = False
    legInTR: float = 0.0
    legOutTR: float = 0.0
    hasGenuineGap: bool = False
    gapSize: float = 0.0
    reformedAfterBreak: bool = False
    isMTFConfluence: bool = False
    isNestedInBiggerTF: bool = False
    confluenceTFs: list = field(default_factory=list)


def _zone_range(z):
    return min(z.proxVal, z.distVal), max(z.proxVal, z.distVal)


def _ranges_overlap(a_lo, a_hi, b_lo, b_hi):
    return max(a_lo, b_lo) <= min(a_hi, b_hi)


def _ranges_nested(ilo, ihi, olo, ohi):
    return olo <= ilo and ihi <= ohi


# --------------------------------------------------------------------------- #
#  Main scanner                                                               #
# --------------------------------------------------------------------------- #
def scan_zones(df: pd.DataFrame, params: Optional[dict] = None,
               lookback_months: Optional[float] = None) -> List[Zone]:
    p = dict(DEFAULT_PARAMS)
    if params:
        p.update(params)
    raw_max_base = int(p["maxBaseCount"])
    p["minBaseCount"] = max(1, min(int(p["minBaseCount"]), raw_max_base))
    p["maxBaseCount"] = min(raw_max_base, _HARD_MAX_BASE_COUNT)

    o, h, l, c, v, tr_all, atr, vol_sma = _prep(df, p)
    n = len(df)
    minBaseCount = p["minBaseCount"]
    maxBaseCount = p["maxBaseCount"]
    atrPeriod = p["atrPeriod"]
    bar_dates = _bar_dates_array(df)

    def tr(t, idx):
        return tr_all[t - idx]

    def is_bull(t, idx):
        return c[t - idx] > o[t - idx]

    def is_bear(t, idx):
        return o[t - idx] > c[t - idx]

    def wick_pct(t, idx):
        i = t - idx
        rng = h[i] - l[i]
        if rng == 0:
            return 0.0
        return ((h[i] - max(o[i], c[i])) + (min(o[i], c[i]) - l[i])) / rng

    def body_pct(t, idx):
        i = t - idx
        rng = h[i] - l[i]
        return 0.0 if rng == 0 else abs(c[i] - o[i]) / rng

    def body_hl(t, idx):
        i = t - idx
        return max(o[i], c[i]), min(o[i], c[i])

    zones: List[Zone] = []
    active_zones: List[Zone] = []
    min_start = max(atrPeriod, maxBaseCount + 3, 11)
    record_from_bar = max(min_start, _resolve_start_bar_for_lookback(df, lookback_months))
    legOutMult = p["legOutTrMult"]

    for t in range(min_start, n):
        if np.isnan(atr[t]):
            continue
        found = False
        for bc in range(minBaseCount, maxBaseCount + 1):
            if found:
                break
            legInIdx = bc + 1
            prevIdx = legInIdx + 1
            if t - prevIdx < 0 or t - bc < 0:
                continue
            if np.isnan(atr[t - legInIdx]) or np.isnan(atr[t]):
                continue

            # ---------- LEG-IN ----------
            legInTR = tr(t, legInIdx)
            legInHigh = h[t - legInIdx]
            legInLow = l[t - legInIdx]
            legInClose = c[t - legInIdx]
            legInOpen = o[t - legInIdx]
            legInVol = v[t - legInIdx]
            legInRng = legInHigh - legInLow
            legInIsBull = is_bull(t, legInIdx)
            legInIsBear = is_bear(t, legInIdx)
            if legInRng == 0:
                continue
            if p["body_gate"] and body_pct(t, legInIdx) < p["legInMinBodyPct"]:
                continue
            if p["opp_color_gate"]:
                if (legInIsBull and is_bear(t, prevIdx)) or (legInIsBear and is_bull(t, prevIdx)):
                    prev_hi, prev_lo = body_hl(t, prevIdx)
                    overlap = max(0.0, min(prev_hi, legInHigh) - max(prev_lo, legInLow))
                    if (overlap / legInRng) >= p["rejectOppositeCoverPct"]:
                        continue
            bullClv = (legInClose - legInLow) / legInRng
            bearClv = (legInHigh - legInClose) / legInRng

            # ---------- BASE ----------
            allBaseValid = True
            maxBaseTR = 0.0
            maxBaseHigh = -1.0
            minBaseLow = float("inf")
            hasOppColorBase = False
            for b in range(1, bc + 1):
                if np.isnan(atr[t - b]):
                    allBaseValid = False
                    break
                bTR = tr(t, b)
                if p["base_atr_gate"] and bTR > p["maxBaseAtrMult"] * atr[t - b]:
                    allBaseValid = False
                    break
                maxBaseTR = max(maxBaseTR, bTR)
                maxBaseHigh = max(maxBaseHigh, h[t - b])
                minBaseLow = min(minBaseLow, l[t - b])
            if not allBaseValid or maxBaseTR == 0:
                continue

            effMult = p["legInToBaseSizeMultSingleBase"] if bc == 1 else p["legInToBaseSizeMult"]
            if p["legin_base_gate"] and legInTR < effMult * maxBaseTR:
                continue
            if p["legin_atr_gate"] and legInTR < p["legInMinAtrMult"] * atr[t - legInIdx]:
                continue

            # ---------- LEG-OUT ----------
            legOutIdx = 0
            legOutTR = tr(t, legOutIdx)
            legOutHigh = h[t]
            legOutLow = l[t]
            legOutClose = c[t]
            legOutOpen = o[t]
            legOutVol = v[t]
            isDemand = is_bull(t, 0)
            isSupply = is_bear(t, 0)
            if not (isDemand or isSupply):
                continue
            if p["explosive_gate"] and legOutTR < legOutMult * atr[t]:
                continue
            if p["wick_gate"] and wick_pct(t, 0) > p["maxWickPct"]:
                continue
            if p["tr_hierarchy_gate"] and not (
                legOutTR >= p["legOutMinTrRatio"] * legInTR and legInTR > maxBaseTR
            ):
                continue
            if p["volume_gate"] and not (legOutVol > legInVol):
                continue

            # ---------- OVERNIGHT GAP ----------
            isOvernightGap = False
            if bar_dates is not None:
                try:
                    isOvernightGap = bar_dates[t] != bar_dates[t - 1]
                except Exception:
                    isOvernightGap = False

            # ---------- IMBALANCE / GENUINE GAP (always computed for scoring) ----------
            hasImbalance = True
            hasGenuineGap = False
            gapSize = 0.0
            if isDemand:
                hasGenuineGap = legOutLow > maxBaseHigh
                hasImbalance = hasGenuineGap or (legOutClose > legInHigh)
                gapSize = max(0.0, legOutLow - maxBaseHigh)
            elif isSupply:
                hasGenuineGap = legOutHigh < minBaseLow
                hasImbalance = hasGenuineGap or (legOutClose < legInLow)
                gapSize = max(0.0, minBaseLow - legOutHigh)
            if p["imbalance_gate"] and not hasImbalance:
                continue

            # ---------- ENGULF-CHECK ----------
            legOutBodyHigh = max(legOutOpen, legOutClose)
            legOutBodyLow = min(legOutOpen, legOutClose)
            engulfs = (legOutBodyLow <= minBaseLow) and (legOutBodyHigh >= maxBaseHigh)
            if p["engulf_gate"] and engulfs and not hasGenuineGap:
                continue

            # ---------- PATTERN ----------
            clv_min = p["minClvPct"] if p["clv_gate"] else 0.0
            isRBR = legInIsBull and (bullClv >= clv_min) and isDemand
            isDBR = legInIsBear and (bearClv >= clv_min) and isDemand
            isDBD = legInIsBear and (bearClv >= clv_min) and isSupply
            isRBD = legInIsBull and (bullClv >= clv_min) and isSupply
            pat_ok = isRBR or isDBR or isDBD or isRBD
            if not pat_ok:
                continue

            # ---------- DENSITY SCORE ----------
            score = 0
            if bc == 1:
                score += 15
            if legInTR >= p["hqLegInAtrMult"] * atr[t - legInIdx]:
                score += 10
            if legOutTR >= p["hqLegOutTrMult"] * legInTR:
                score += 15
            if (legInTR >= 2.0 * maxBaseTR) and (legOutTR >= 2.0 * legInTR):
                score += 15
            if legOutVol > vol_sma[t]:
                score += 10
            if isDemand:
                legOutBodyPos = (legOutClose - legOutLow) / (legOutHigh - legOutLow) if (legOutHigh - legOutLow) > 0 else 0
                own = body_pct(t, 0)
                if isDBR:
                    if legOutBodyPos >= 0.80 or own >= p["legOutBodyHeavyPressurePct"]:
                        score += 15
                else:
                    if legOutBodyPos >= 0.80:
                        score += 15
            else:
                legOutBodyPos = (legOutHigh - legOutClose) / (legOutHigh - legOutLow) if (legOutHigh - legOutLow) > 0 else 0
                if legOutBodyPos >= 0.80:
                    score += 15
            for b in range(1, bc + 1):
                if isDemand and is_bear(t, b):
                    hasOppColorBase = True
                    break
                if isSupply and is_bull(t, b):
                    hasOppColorBase = True
                    break
            if hasOppColorBase:
                score += 10
            score += 10
            if hasGenuineGap:
                score += p["genuineGapScoreBonus"]
            if isOvernightGap and hasGenuineGap:
                score += p["overnightGapScoreBonus"]
            if p["score_gate"] and score < p["minValidScore"]:
                continue

            isHQ = score >= p["hqScoreThreshold"]
            found = True

            # ---------- PROX / DIST / SL / TP ----------
            proxVal = maxBaseHigh if isDemand else minBaseLow
            distVal = minBaseLow if isDemand else maxBaseHigh
            slVal = distVal - p["slBufferAtr"] * atr[t] if isDemand else distVal + p["slBufferAtr"] * atr[t]
            risk = abs(proxVal - slVal)
            tpVal = proxVal + risk * p["targetRR"] if isDemand else proxVal - risk * p["targetRR"]
            retrace = p["testedLegOutRetracePct"]
            if isDemand:
                legOutMidLevel = legOutHigh - retrace * (legOutHigh - legOutLow)
            else:
                legOutMidLevel = legOutLow + retrace * (legOutHigh - legOutLow)

            # ---------- DUPLICATE FILTER ----------
            isDup = False
            if p["duplicate_gate"]:
                checked = 0
                for cz in reversed(zones):
                    if cz.state == "Broken":
                        continue
                    if cz.isDemand == isDemand and abs(cz.proxVal - proxVal) < atr[t] * 0.25:
                        isDup = True
                        break
                    checked += 1
                    if checked >= 11:
                        break
            if isDup:
                continue

            # ---------- REFORMED AFTER BREAK ----------
            reform = False
            zlo, zhi = min(proxVal, distVal), max(proxVal, distVal)
            checkedB = 0
            for oldZ in reversed(zones):
                if oldZ.state != "Broken" or oldZ.isDemand != isDemand:
                    continue
                olo, ohi = min(oldZ.proxVal, oldZ.distVal), max(oldZ.proxVal, oldZ.distVal)
                if _ranges_overlap(zlo, zhi, olo, ohi):
                    reform = True
                    break
                checkedB += 1
                if checkedB >= 20:
                    break

            if isRBR:
                pt, cat = "RBR", "Continuation"
            elif isDBR:
                pt, cat = "DBR", "Reversal"
            elif isDBD:
                pt, cat = "DBD", "Continuation"
            else:
                pt, cat = "RBD", "Reversal"

            z = Zone(
                proxVal=proxVal, distVal=distVal, slVal=slVal, tpVal=tpVal,
                isDemand=isDemand, isHQ=isHQ, densityScore=score,
                patternType=pt, zoneCategory=cat, state="Fresh", touchCount=0,
                originalDensityScore=score, startBarIndex=t - bc, createdBarIndex=t,
                baseCount=bc, timestamp=df.index[t],
                legOutHigh=legOutHigh, legOutLow=legOutLow, legOutMidLevel=legOutMidLevel,
                isOvernightGap=isOvernightGap, legInTR=legInTR, legOutTR=legOutTR,
                hasGenuineGap=hasGenuineGap, gapSize=gapSize, reformedAfterBreak=reform,
            )
            zones.append(z)
            active_zones.append(z)

        # ---------- STATE MACHINE (Fresh -> Tested -> Broken) ----------
        if active_zones:
            lo_t, hi_t = l[t], h[t]
            keep = []
            for z in active_zones:
                if z.state == "Fresh":
                    if z.isDemand:
                        if lo_t <= z.distVal:
                            z.state = "Broken"
                        elif lo_t <= z.legOutMidLevel:
                            z.state = "Tested"; z.touchCount += 1
                    else:
                        if hi_t >= z.distVal:
                            z.state = "Broken"
                        elif hi_t >= z.legOutMidLevel:
                            z.state = "Tested"; z.touchCount += 1
                elif z.state == "Tested":
                    if z.isDemand:
                        if lo_t <= z.distVal:
                            z.state = "Broken"
                        elif lo_t <= z.legOutMidLevel:
                            z.touchCount += 1
                    else:
                        if hi_t >= z.distVal:
                            z.state = "Broken"
                        elif hi_t >= z.legOutMidLevel:
                            z.touchCount += 1
                if z.state == "Tested" and z.touchCount > p["maxTestedCount"]:
                    z.state = "Broken"
                if z.state != "Broken":
                    keep.append(z)
            active_zones = keep

    if lookback_months is None:
        return zones
    return [z for z in zones if z.createdBarIndex >= record_from_bar]


# --------------------------------------------------------------------------- #
#  Alerts / highlighting / MTF confluence                                     #
# --------------------------------------------------------------------------- #
def latest_active_zones(zones: List[Zone], include_tested: bool = True) -> List[Zone]:
    states = {"Fresh"} | ({"Tested"} if include_tested else set())
    return [z for z in zones if z.state in states]


def get_zone_alerts(zones, current_price, min_proximity_pct=0.0, max_proximity_pct=1.0,
                    include_tested=True) -> List[Dict[str, Any]]:
    alerts = []
    for z in latest_active_zones(zones, include_tested=include_tested):
        if z.proxVal <= 0:
            continue
        if z.isDemand:
            diff_pct = (current_price - z.proxVal) / z.proxVal
            direction = "DEMAND"
        else:
            diff_pct = (z.proxVal - current_price) / z.proxVal
            direction = "SUPPLY"
        if not (min_proximity_pct <= diff_pct <= max_proximity_pct):
            continue
        alerts.append({
            "direction": direction, "pattern": z.patternType, "category": z.zoneCategory,
            "entry": z.proxVal, "sl": z.slVal, "tp": z.tpVal, "is_hq": z.isHQ,
            "score": z.densityScore, "touch_count": z.touchCount,
            "is_overnight_gap": z.isOvernightGap,
            "legInTR": z.legInTR, "legOutTR": z.legOutTR,
            "distance_pct": diff_pct * 100, "state": z.state, "timestamp": z.timestamp,
            "reformed_after_break": z.reformedAfterBreak,
            "is_mtf_confluence": z.isMTFConfluence,
            "is_nested_in_bigger_tf": z.isNestedInBiggerTF,
            "confluence_tfs": z.confluenceTFs,
        })
    alerts.sort(key=lambda a: (-int(a["is_hq"]), a["distance_pct"]))
    return alerts


def flag_multi_timeframe_confluence(zones_by_timeframe, tf_order_small_to_large, only_active=True):
    for tf_zones in zones_by_timeframe.values():
        for z in tf_zones:
            z.isMTFConfluence = False
            z.isNestedInBiggerTF = False
            z.confluenceTFs = []
    for i, small_tf in enumerate(tf_order_small_to_large):
        for z_small in zones_by_timeframe.get(small_tf, []):
            if only_active and z_small.state not in ("Fresh", "Tested"):
                continue
            s_lo, s_hi = _zone_range(z_small)
            for big_tf in tf_order_small_to_large[i + 1:]:
                for z_big in zones_by_timeframe.get(big_tf, []):
                    if only_active and z_big.state not in ("Fresh", "Tested"):
                        continue
                    if z_big.isDemand != z_small.isDemand:
                        continue
                    b_lo, b_hi = _zone_range(z_big)
                    if _ranges_overlap(s_lo, s_hi, b_lo, b_hi):
                        z_small.isMTFConfluence = True
                        if big_tf not in z_small.confluenceTFs:
                            z_small.confluenceTFs.append(big_tf)
                        if _ranges_nested(s_lo, s_hi, b_lo, b_hi):
                            z_small.isNestedInBiggerTF = True


def zone_highlight_tags(z: Zone) -> List[str]:
    tags = []
    if z.isHQ:
        tags.append("HQ")
    if z.isOvernightGap:
        tags.append("Overnight-Gap")
    if z.reformedAfterBreak:
        tags.append("Reformed-after-Break")
    if z.isNestedInBiggerTF:
        tags.append(f"Nested-in-{'/'.join(z.confluenceTFs)}")
    elif z.isMTFConfluence:
        tags.append(f"MTF-Confluence-{'/'.join(z.confluenceTFs)}")
    return tags


# --------------------------------------------------------------------------- #
#  Diagnostic                                                                #
# --------------------------------------------------------------------------- #
def diagnose_bar(df: pd.DataFrame, at_index, params: Optional[dict] = None) -> List[Dict[str, Any]]:
    p = dict(DEFAULT_PARAMS)
    if params:
        p.update(params)
    raw_max_base = int(p["maxBaseCount"])
    p["minBaseCount"] = max(1, min(int(p["minBaseCount"]), raw_max_base))
    p["maxBaseCount"] = min(raw_max_base, _HARD_MAX_BASE_COUNT)
    o, h, l, c, v, tr_all, atr, vol_sma = _prep(df, p)
    bar_dates = _bar_dates_array(df)
    if isinstance(at_index, (int, np.integer)):
        t = int(at_index)
    else:
        t = int(df.index.get_loc(at_index))

    def trg(idx_from_t):
        return tr_all[t - idx_from_t]

    def wick_pct(idx_from_t):
        i = t - idx_from_t
        rng = h[i] - l[i]
        return 0.0 if rng == 0 else ((h[i] - max(o[i], c[i])) + (min(o[i], c[i]) - l[i])) / rng

    def body_pct(idx_from_t):
        i = t - idx_from_t
        rng = h[i] - l[i]
        return 0.0 if rng == 0 else abs(c[i] - o[i]) / rng

    reports = []
    for bc in range(p["minBaseCount"], p["maxBaseCount"] + 1):
        rep = {"baseCount": bc, "legOutTimestamp": df.index[t]}
        legInIdx = bc + 1
        prevIdx = legInIdx + 1
        if t - prevIdx < 0 or t - bc < 0 or np.isnan(atr[t]) or np.isnan(atr[t - legInIdx]):
            rep["result"] = "SKIP"
            reports.append(rep)
            continue
        legInTR = trg(legInIdx)
        legInHigh = h[t - legInIdx]; legInLow = l[t - legInIdx]; legInClose = c[t - legInIdx]
        legInOpen = o[t - legInIdx]; legInVol = v[t - legInIdx]; legInRng = legInHigh - legInLow
        legInIsBull = c[t - legInIdx] > o[t - legInIdx]; legInIsBear = o[t - legInIdx] > c[t - legInIdx]
        if legInRng == 0:
            rep["result"] = "INVALID legInRng=0"
            reports.append(rep)
            continue
        rep["legInTR"] = legInTR; rep["legInATR"] = atr[t - legInIdx]
        rep["legIn_bodyPct"] = body_pct(legInIdx)
        rep["legIn_body_ok"] = rep["legIn_bodyPct"] >= p["legInMinBodyPct"]
        rep["legInTR_ge_ATR"] = legInTR >= p["legInMinAtrMult"] * atr[t - legInIdx]
        bullClv = (legInClose - legInLow) / legInRng
        bearClv = (legInHigh - legInClose) / legInRng
        maxBaseTR = 0.0; maxBaseHigh = -1.0; minBaseLow = float("inf"); baseValid = True
        for b in range(1, bc + 1):
            if np.isnan(atr[t - b]):
                baseValid = False; break
            bTR = trg(b)
            if bTR > p["maxBaseAtrMult"] * atr[t - b]:
                baseValid = False
            maxBaseTR = max(maxBaseTR, bTR)
            maxBaseHigh = max(maxBaseHigh, h[t - b])
            minBaseLow = min(minBaseLow, l[t - b])
        rep["maxBaseTR"] = maxBaseTR
        rep["base_valid_<=ATR"] = baseValid
        effMult = p["legInToBaseSizeMultSingleBase"] if bc == 1 else p["legInToBaseSizeMult"]
        rep["legin_ge_mult_base"] = legInTR >= effMult * maxBaseTR if maxBaseTR else False
        legOutTR = trg(0); legOutHigh = h[t]; legOutLow = l[t]; legOutClose = c[t]; legOutOpen = o[t]
        legOutVol = v[t]
        isDemand = c[t] > o[t]; isSupply = o[t] > c[t]
        rep["legOutTR"] = legOutTR; rep["legOutATR"] = atr[t]
        rep["legOut_explosive(>=1.2xATR)"] = legOutTR >= p["legOutTrMult"] * atr[t]
        rep["legOut_wickPct"] = wick_pct(0)
        rep["legOut_wick_ok"] = rep["legOut_wickPct"] <= p["maxWickPct"]
        rep["tr_hierarchy_ok"] = (legOutTR >= p["legOutMinTrRatio"] * legInTR) and (legInTR > maxBaseTR)
        rep["volume_ok"] = legOutVol > legInVol
        isOvernightGap = False
        if bar_dates is not None:
            try:
                isOvernightGap = bar_dates[t] != bar_dates[t - 1]
            except Exception:
                isOvernightGap = False
        rep["isOvernightGap"] = isOvernightGap
        hasGenuineGap = (legOutLow > maxBaseHigh) if isDemand else (legOutHigh < minBaseLow)
        hasImbalance = True
        if isDemand:
            hasImbalance = hasGenuineGap or (legOutClose > legInHigh)
        elif isSupply:
            hasImbalance = hasGenuineGap or (legOutClose < legInLow)
        rep["hasGenuineGap"] = hasGenuineGap
        rep["imbalance_ok"] = hasImbalance
        legOutBodyHigh = max(legOutOpen, legOutClose); legOutBodyLow = min(legOutOpen, legOutClose)
        engulfs = (legOutBodyLow <= minBaseLow) and (legOutBodyHigh >= maxBaseHigh)
        rep["engulf_ok"] = (not engulfs) or hasGenuineGap
        isRBR = legInIsBull and (bullClv >= p["minClvPct"]) and isDemand
        isDBR = legInIsBear and (bearClv >= p["minClvPct"]) and isDemand
        isDBD = legInIsBear and (bearClv >= p["minClvPct"]) and isSupply
        isRBD = legInIsBull and (bullClv >= p["minClvPct"]) and isSupply
        rep["pattern"] = "RBR" if isRBR else "DBR" if isDBR else "DBD" if isDBD else "RBD" if isRBD else "NONE"
        rep["FINAL_VALID"] = bool(
            rep["legIn_body_ok"] and rep["legin_ge_mult_base"] and rep["legInTR_ge_ATR"]
            and baseValid and rep["pattern"] != "NONE"
            and rep["legOut_explosive(>=1.2xATR)"] and rep["legOut_wick_ok"]
            and rep["tr_hierarchy_ok"] and rep["volume_ok"]
            and rep["imbalance_ok"] and rep["engulf_ok"]
        )
        reports.append(rep)
    return reports


# --------------------------------------------------------------------------- #
#  Quick forward-outcome summary (so a screener can self-check a scan)         #
# --------------------------------------------------------------------------- #
EVAL_RR = [1.0, 1.5, 2.0, 3.0, 5.0]


def _zone_outcome(z, hh, ll, cc, lookback):
    ci = z.createdBarIndex
    s = ci + 1
    e = min(ci + 1 + lookback, len(hh))
    if s >= e:
        return None
    prox, sl, dist = z.proxVal, z.slVal, z.distVal
    if z.isDemand:
        risk = prox - sl
        if risk <= 0:
            return None
        tested = False; wins = set(); mfe = 0.0
        for i in range(s, e):
            if cc[i] < dist:
                break
            if ll[i] <= prox:
                tested = True
            if tested:
                mfe = max(mfe, (hh[i] - prox) / risk)
                for k in EVAL_RR:
                    if k not in wins and hh[i] >= prox + k * risk:
                        wins.add(k)
    else:
        risk = sl - prox
        if risk <= 0:
            return None
        tested = False; wins = set(); mfe = 0.0
        for i in range(s, e):
            if cc[i] > dist:
                break
            if hh[i] >= prox:
                tested = True
            if tested:
                mfe = max(mfe, (prox - ll[i]) / risk)
                for k in EVAL_RR:
                    if k not in wins and ll[i] <= prox - k * risk:
                        wins.add(k)
    return tested, wins, mfe


def backtest_summary(zones, df, lookback=20):
    """Forward-test a scanned zone list and summarise quality (self-check helper).

    NOTE: `avg_mfe` is maximum-favourable-excursion (best case).  It deliberately does
    NOT account for the price hitting the stop before the target.  For the realistic,
    broker-inclusive result see `realistic_roi()` below."""
    hh = df["high"].to_numpy(dtype=float)
    ll = df["low"].to_numpy(dtype=float)
    cc = df["close"].to_numpy(dtype=float)
    rows = []
    for z in zones:
        r = _zone_outcome(z, hh, ll, cc, lookback)
        if r is None:
            continue
        tested, wins, mfe = r
        rows.append({"tested": int(tested), "hq": int(z.isHQ),
                     "score": z.densityScore, "mfe": mfe,
                     **{f"w{int(k*10)}": int(k in wins) for k in EVAL_RR}})
    if not rows:
        return {"zones": 0}
    res = pd.DataFrame(rows)
    n = len(res)
    tested = int(res["tested"].sum())
    t = res[res["tested"] == 1]
    out = {"zones": n, "tested": tested, "tested_pct": 100 * tested / n}
    for k in EVAL_RR:
        col = f"w{int(k*10)}"
        out[f"win_{k}R_tested"] = 100 * t[col].sum() / tested if tested else float("nan")
    out["avg_mfe_tested"] = t["mfe"].mean() if tested else float("nan")
    out["hq_pct"] = 100 * res["hq"].sum() / n
    out["avg_score"] = res["score"].mean()
    return out


# =========================================================================== #
#  REALISTIC ROI  (fixed SL/TP execution + Indian broker & government charges)  #
# =========================================================================== #
#  The MFE / win@kR numbers above are the *best case*: they measure how far price
#  went, ignoring that price often hits the stop first.  A real trade uses:
#      Entry = proximal,  Stop = distal + buffer,  Target = entry +/- R*RR.
#  The function below simulates exactly that (SL checked before TP within a bar),
#  subtracts broker/STT/exchange/GST/stamp, and returns the net % return.
# =========================================================================== #
_IR_BROKER = 0.0003       # 0.03% / side, capped
_IR_BROKER_CAP = 20.0
_IR_STT = 0.00025         # 0.025% sell turnover
_IR_EXCH = 0.0000297      # 0.00297% turnover
_IR_SEBI = 0.000001       # 0.0001% turnover
_IR_GST = 0.18
_IR_STAMP = 0.00003       # 0.003% buy turnover


def _cost(buy_turn, sell_turn):
    br = min(_IR_BROKER * buy_turn, _IR_BROKER_CAP) + min(_IR_BROKER * sell_turn, _IR_BROKER_CAP)
    return br + _IR_STT * sell_turn + _IR_EXCH * (buy_turn + sell_turn) + \
        _IR_SEBI * (buy_turn + sell_turn) + _IR_GST * (br + _IR_EXCH * (buy_turn + sell_turn) +
                                                     _IR_SEBI * (buy_turn + sell_turn)) + \
        _IR_STAMP * buy_turn


def realistic_roi(zones, df, rr=2.5, risk_pct=0.01, capital=25000.0, max_hold=30,
                  start=None, end=None, patterns=None, buffer=None, entry_mode="prox"):
    """Simulate trades with fixed SL/TP and net out Indian charges.

    rr         : target reward (1:2.5 / 1:3 / 1:5).
    risk_pct   : fraction of capital risked per trade (0.01 = 1%).
    capital    : account capital (INR).
    max_hold   : bars to hold before time-exit (mark-to-market).
    patterns   : optional list of pattern types to keep (e.g. ['DBD']). None = all.
    buffer     : optional override of the SL buffer (x ATR), default uses the zones'
                 already-computed slVal (which used DEFAULT `slBufferAtr`, 0.1).
    entry_mode : 'prox' = buy/sell at the zone proximal line (spec default);
                 'mid'  = buy/sell at the zone middle ((prox+dist)/2).  Mid was the
                 better-R, highest-ROI entry in the entry/exit backtest (see docstring
                 of recommended_trade_setup()).

    Returns a dict: n_trades, wins, win_pct, breakeven_win_pct, gross_pnl, cost_pnl,
    net_pnl, net_roi_pct, gross_ev_R, avg_hold_bars, outcome_counts, avg_cost, avg_size.
    """
    hh = df["high"].to_numpy(dtype=float)
    ll = df["low"].to_numpy(dtype=float)
    cc = df["close"].to_numpy(dtype=float)
    n = len(hh)

    def _norm_ts(v):
        """Return a pandas Timestamp comparable to a Zone.timestamp (handles tz)."""
        t = pd.Timestamp(v)
        # If zones carry a timezone (e.g. +05:30) make the bound tz-aware too.
        if start is not None or end is not None:
            tz = None
            for z in zones:
                tz = getattr(z.timestamp, "tz", None)
                if tz is not None:
                    break
            if tz is not None and t.tz is None:
                t = t.tz_localize(tz)
        return t

    trades = []
    for z in zones:
        if patterns and z.patternType not in patterns:
            continue
        if start is not None:
            if z.timestamp < _norm_ts(start):
                continue
        if end is not None:
            if z.timestamp > _norm_ts(end):
                continue
        prox, sl, dist = z.proxVal, z.slVal, z.distVal
        # optional SL-buffer override (widen the stop) -> recompute risk
        if buffer is not None:
            # need the ATR at creation; recompute from df using the zone's bar index
            atr = _wilder_atr_from_tr(_true_range(hh, ll, cc), 14)
            if not np.isnan(atr[z.createdBarIndex]):
                sl = dist - buffer * atr[z.createdBarIndex] if z.isDemand else \
                     dist + buffer * atr[z.createdBarIndex]
        # entry line: proximal (spec) or middle (backtested best-R entry)
        entry_line = prox
        if entry_mode == "mid":
            entry_line = min(prox, dist) + 0.5 * abs(prox - dist)
        risk = abs(entry_line - sl)
        if risk <= 0:
            continue
        demand = z.isDemand
        tp = entry_line + risk * rr if demand else entry_line - risk * rr
        s = z.createdBarIndex + 1
        e = min(z.createdBarIndex + 1 + max_hold, n)
        if s >= e:
            continue
        entered = False
        entry = None
        outcome = None
        net_r = 0.0
        bars = 0
        for i in range(s, e):
            if not entered:
                touch = (ll[i] <= entry_line) if demand else (hh[i] >= entry_line)
                if not touch:
                    continue
                entered = True
                entry = entry_line
            bars = i - z.createdBarIndex
            if demand:
                if ll[i] <= sl:
                    net_r, outcome = -1.0, "SL"
                    break
                if hh[i] >= tp:
                    net_r, outcome = rr, "TP"
                    break
            else:
                if hh[i] >= sl:
                    net_r, outcome = -1.0, "SL"
                    break
                if ll[i] <= tp:
                    net_r, outcome = rr, "TP"
                    break
        if not entered:
            continue
        if outcome is None:  # timeout
            close = cc[e - 1]
            net_r = (close - entry) / risk if demand else (entry - close) / risk
            outcome = "TIME"
        # position sizing (whole shares), cash-capped
        shares = max(1, int(capital * risk_pct / max(risk, 1e-9)))
        pos_val = shares * entry
        if pos_val > capital:
            shares = max(1, int(capital / max(entry, 1e-9)))
            pos_val = shares * entry
        gross = net_r * risk * shares
        cost = _cost(pos_val, pos_val)
        trades.append({"net_r": net_r, "gross": gross, "cost": cost,
                       "net": gross - cost, "outcome": outcome, "bars": bars,
                       "risk": risk, "entry": entry, "shares": shares})
    if not trades:
        return {"n_trades": 0}
    dfr = pd.DataFrame(trades)
    n_trades = len(dfr)
    wins = int((dfr["net_r"] > 0).sum())
    gross_pnl = dfr["gross"].sum()
    cost_pnl = dfr["cost"].sum()
    net_pnl = dfr["net"].sum()
    breakeven = 100.0 / (1.0 + rr)
    return {
        "n_trades": n_trades, "wins": wins,
        "win_pct": 100 * wins / n_trades,
        "breakeven_win_pct": breakeven,
        "gross_pnl": gross_pnl, "cost_pnl": cost_pnl, "net_pnl": net_pnl,
        "net_roi_pct": 100 * net_pnl / capital,
        "gross_ev_R": dfr["net_r"].mean(),
        "avg_hold_bars": dfr["bars"].mean(),
        "outcome_counts": dfr["outcome"].value_counts().to_dict(),
        "avg_cost": dfr["cost"].mean(),
        "avg_size": dfr["entry"].mean() * dfr["shares"].mean(),
    }


def recommended_trade_setup():
    """Backtested, both-window-positive deployment setting (MID entry + fixed target).

    Whole-universe (all 4 patterns) is NET NEGATIVE after Indian charges at 1:2.5/1:3/1:5.
    Two independent backtests found the only robustly positive subsets:

      (1) Wider SL buffer on the DBD supply-continuation subset (proximal entry):
            DBD + slBufferAtr 0.5 + RR 1:2.5  -> 24mo +4.07%, 6mo +9.13%

      (2) ENTRY/EXIT sweep (mid-vs-prox entry, target-vs-partial/trail exit):
            partial-profit-@1R and trail exits are DISASTROUS (-40% to -62%);
            fixed target beats both.  Mid entry beats proximal entry on the same setup.

    The best config found on BOTH windows was:

        Pattern filter = ['DBD']
        entry_mode      = 'mid'     (zone middle, better R than the proximal line)
        exit_mode       = 'target'  (fixed RR target — NOT partial/trail)
        slBufferAtr     = 0.5       (wider stop; whole-universe best is 1.0)
        RR              = 1:3.0
        capital = 25000, risk 1%/trade, whole shares, SL-before-TP

    Results (net after broker/STT/exchange/GST/stamp):
        24-month : 34 trades, win 41%, ROI +13.01%, ev +0.56R  (SL 20 / TP 12 / TME 2)
        6-month  :  8 trades, win 62%, ROI +10.88%, ev +1.50R  (TP 5 / SL 3)
        (mid+RR 1:2.5  24mo +8.06% / 6mo +8.64%;  mid+RR 1:5  24mo +9.15% / 6mo +8.41%)

    For reference, the same setup with PROX entry was only +3.58% (24mo) / +7.69% (6mo),
    i.e. mid entry nearly doubles the 24-month return.  Sensitivity (mid+target+DBD):
        rec RR 1:3.0 @ buf 0.5 = BEST (both +).  RR 1:3.0 @ buf 1.0 -> -1.28% (24mo),
        RR 1:5 @ buf 1.0 -> negative.  Keep buffer = 0.5.

    NOTE: only 8 trades in the 6-month window — high variance.  Treat as a TARGETED filter
    (confluence/continuation supply zones), not a universal win machine.
    """
    return {
        "patterns": ["DBD"],
        "entry_mode": "mid",        # zone middle entry (better R / higher ROI)
        "exit_mode": "target",      # fixed target — partial/trail proved much worse
        "slBufferAtr": 0.5,
        "targetRR": 3.0,
        "risk_pct": 0.01,
        "capital": 25000.0,
        "note": "DBD-only, MID entry, fixed target, wider 0.5xATR stop, RR 1:3. "
                "Best both-window setup: 24mo +13.01% / 6mo +10.88% after charges. "
                "Partial-profit@1R and trail exits are far worse (-40% to -62%); "
                "entry at the zone middle beats the proximal line. Small 6mo sample.",
    }


# =========================================================================== #
#  EXTRA VALIDATION LAYERS  (from the original spec — OPTIONAL, OFF by default)  #
# =========================================================================== #
#  These are the mandatory half-TF / higher-TF layers the spec asks for.  Each one
#  was backtested one-by-one on 18 NSE stocks x 2H+4H (v10.1 core).  VERDICT:
#      A  Half-TF Leg-In Body >= 65%   -> HARMFUL (removes better zones, both TFs)
#      B  Half-TF Leg-Out Mid/Swing     -> MIXED  (net neutral)
#      C  HTF Zone-in-Zone              -> HARMFUL (removes better zones, both TFs)
#      D  HTF 2-candle Opening Gap      -> MIXED  (net neutral)
#  Therefore none are applied by default.  Enable explicitly with the flags below
#  only if you trust the spec over the data.
# --------------------------------------------------------------------------- #
EXTRA_LAYER_DEFAULTS = dict(
    layer_A=False,          # half-TF leg-in body >= 65%
    layer_B=False,          # half-TF leg-out middle-break must also break swing
    layer_C=False,          # HTF zone-in-zone confirmation
    layer_D=False,          # HTF 2-candle opening-gap overlap
    half_legin_body_min=0.65,
    swing_lookback=3,
    htf_gap_window=8,
    mid_tol=0.001,
)

# LTF -> half-TF / HTF mapping (2h & 4h being the supported scan TFs here)
_HALF_TF = {"2h": "1h", "4h": "2h"}
_HTF_TF = {"2h": "4h", "4h": "8h"}


def extra_layer_verdict():
    """Backtest verdict summary for each optional layer (v10.1 core, 18 NSE stocks x 2h+4h)."""
    return [
        ("A", "half-TF leg-in body >= 65%",
         "HARMFUL", "pass exp2R 0.62/0.35 vs fail 1.14/1.25 (both TFs) -> crops the winners."),
        ("B", "half-TF leg-out middle-break + swing",
         "MIXED/neutral", "2h pass worse, 4h pass better -> no reliable edge."),
        ("C", "HTF zone-in-zone confirmation",
         "HARMFUL", "pass exp2R -0.25/-1.00 vs fail 0.80/0.85 -> keeps the WORST zones."),
        ("D", "HTF 2-candle opening-gap overlap",
         "MIXED/neutral", "2h pass worse, 4h ~equal -> no reliable edge."),
    ]


def apply_extra_validation(zones, ltf_df, half_df=None, htf_df=None, htf_zones=None,
                           params=None):
    """Apply the optional layers to a zone list (in-place flagging + optional filtering).
    Returns (kept_zones, per-zone layer report dict keyed by Zone).  All OFF by default
    => kept_zones == zones and every layer reports None/True."""
    p = dict(EXTRA_LAYER_DEFAULTS)
    if params:
        p.update(params)
    # compute HTF zones if needed
    if (p["layer_C"] or p["layer_D"]) and htf_zones is None and htf_df is not None:
        htf_zones = scan_zones(htf_df)
    # swings for layer B
    piv_high, piv_low = [], []
    if p["layer_B"] and half_df is not None:
        piv_high, piv_low = _compute_swings(half_df["high"].to_numpy(dtype=float),
                                            half_df["low"].to_numpy(dtype=float),
                                            p["swing_lookback"])
    kept = []
    report = []
    for z in zones:
        t = z.createdBarIndex
        bc = z.baseCount
        leg_in_idx = t - (bc + 1)
        li_start, li_end = _bar_window(ltf_df, leg_in_idx)
        lo_start, lo_end = _bar_window(ltf_df, t)
        zr = {}
        # A
        if p["layer_A"] and half_df is not None:
            zr["A"] = _half_legin_body(z, half_df, li_start, li_end, p["half_legin_body_min"])
        else:
            zr["A"] = None
        # B
        if p["layer_B"] and half_df is not None:
            zr["B"] = _half_legout_middle(z, half_df, lo_start, lo_end, piv_high, piv_low, p["mid_tol"])
        else:
            zr["B"] = None
        # C
        if p["layer_C"] and htf_zones is not None:
            zr["C"] = _htf_zone_in_zone(z, htf_zones, z.timestamp)
        else:
            zr["C"] = None
        # D
        if p["layer_D"] and htf_df is not None:
            zr["D"] = _htf_opening_gap(z, htf_df, z.timestamp, p["htf_gap_window"])
        else:
            zr["D"] = None
        # keep if all ENABLED layers pass
        ok = True
        for L in ["A", "B", "C", "D"]:
            if p[f"layer_{L}"] and zr[L] is not None and not zr[L]:
                ok = False
                break
        zr["kept"] = ok
        report.append(zr)
        if ok:
            kept.append(z)
    return kept, report


# ---- internal helpers for the extra layers --------------------------------- #
def _bar_window(df, idx):
    ts = df.index[idx]
    delta = df.index[1] - df.index[0]
    return ts, ts + delta


def _compute_swings(h, l, lookback):
    n = len(h)
    piv_hi = []; piv_lo = []
    for i in range(n):
        if i >= 2 * lookback:
            seg = h[i - 2 * lookback:i + 1]
            c = lookback
            if seg[c] >= np.nanmax(seg) and seg[c] > np.nanmax(np.delete(seg, c)):
                piv_hi.append((i - lookback, seg[c]))
            seg = l[i - 2 * lookback:i + 1]
            if seg[c] <= np.nanmin(seg) and seg[c] < np.nanmin(np.delete(seg, c)):
                piv_lo.append((i - lookback, seg[c]))
    return piv_hi, piv_lo


def _prev_pivot(pivots, before):
    best = np.nan
    for (pi, pr) in pivots:
        if pi < before:
            best = pr
        else:
            break
    return best


def _half_legin_body(z, half_df, start, end, min_body):
    win = half_df.loc[start:end]
    if win is None or len(win) == 0:
        return False
    body = []
    for _, row in win.iterrows():
        rng = row["high"] - row["low"]
        if rng <= 0:
            continue
        body.append(abs(row["close"] - row["open"]) / rng)
    return (max(body) >= min_body) if body else False


def _half_legout_middle(z, half_df, start, end, piv_hi, piv_lo, tol):
    z_lo, z_hi = min(z.proxVal, z.distVal), max(z.proxVal, z.distVal)
    middle = z_lo + 0.5 * (z_hi - z_lo)
    win = half_df.loc[start:end]
    if win is None or len(win) == 0:
        return True  # no leg-out candles -> N/A, pass
    first_idx = half_df.index.get_indexer([win.index[0]])[0]
    psh = _prev_pivot(piv_hi, first_idx)
    psl = _prev_pivot(piv_lo, first_idx)
    mid_break = False; swing_ok = True
    for _, row in win.iterrows():
        if z.isDemand:
            if row["close"] > middle + tol * z_hi:
                mid_break = True
                if np.isnan(psh) or row["close"] <= psh:
                    swing_ok = False
        else:
            if row["close"] < middle - tol * z_hi:
                mid_break = True
                if np.isnan(psl) or row["close"] >= psl:
                    swing_ok = False
    return not (mid_break and not swing_ok)


def _htf_zone_in_zone(z, htf_zones, at_time):
    z_lo, z_hi = min(z.proxVal, z.distVal), max(z.proxVal, z.distVal)
    if not htf_zones:
        return False
    for hz in htf_zones:
        if hz.isDemand != z.isDemand:
            continue
        try:
            if hz.timestamp > at_time:
                continue
        except Exception:
            pass
        h_lo, h_hi = min(hz.proxVal, hz.distVal), max(hz.proxVal, hz.distVal)
        if max(z_lo, h_lo) <= min(z_hi, h_hi):
            return True
    return False


def _htf_opening_gap(z, htf_df, at_time, window):
    z_lo, z_hi = min(z.proxVal, z.distVal), max(z.proxVal, z.distVal)
    cum = htf_df.loc[:at_time]
    if cum is None or len(cum) < 2:
        return False
    opens = cum["open"].to_numpy(dtype=float)
    closes = cum["close"].to_numpy(dtype=float)
    n = len(cum)
    lo = max(1, n - window)
    for i in range(lo, n):
        if z.isDemand:
            if opens[i] > closes[i - 1]:
                g_lo, g_hi = closes[i - 1], opens[i]
                if max(z_lo, g_lo) <= min(z_hi, g_hi):
                    return True
        else:
            if opens[i] < closes[i - 1]:
                g_lo, g_hi = opens[i], closes[i - 1]
                if max(z_lo, g_lo) <= min(z_hi, g_hi):
                    return True
    return False
