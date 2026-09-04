# -*- coding: utf-8 -*-
"""
MarketHub (हिंदी) — Zone Screener + Live Market Terminal
=========================================================
एक ही पेज पर:
  • ऊपर   : Live Market Board (छोटा) + Live Sector Indices (छोटा)
  • मध्य   : FII/DII (आज) + Options OI (छोटा)
  • मुख्य  : Demand/Supply Zone Scanner — हिंदी टेबल (TradingView + OI लिंक सहित)
  • नीचे   : महत्वपूर्ण समाचार + इवेंट (हिंदी हेडलाइन, touch = open)

Deploy:  streamlit run app.py   (Streamlit Cloud पर भी — सभी .py root में)
Data:    Yahoo Finance / TradingView / NSE / niftytrader / RSS (सब keyless)
"""
from __future__ import annotations

import os
import sys
import datetime
import requests
import streamlit as st

# ── ensure sibling modules importable regardless of launch dir ─────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

st.set_page_config(page_title="MarketHub · Zone Screener (हिंदी)", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

# ── Inline theme ────────────────────────────────────────────────────────────
st.markdown("""
<style>
:root{
  --bg:#0b1220; --line:#22304a; --txt:#e6edf7; --muted:#8ba1c0;
  --up:#1ecb6b; --down:#ff4b5c; --accent2:#22d3ee; --accent:#4f8cff;
}
.stApp{background-color:var(--bg); color:var(--txt);}
[data-testid="stSidebar"]{background-color:#0d1524;}
[data-testid="stSidebar"] *{color:var(--txt);}
[data-testid="stHeader"]{background:rgba(11,18,32,.35);}
[data-baseweb="select"] *{background-color:#121a2b; color:#e6edf7;}
[data-testid="stExpander"]{background-color:#121a2b;}
[data-testid="stExpander"] *{color:#e6edf7;}

/* compact board chips */
.strip{display:flex; gap:8px; flex-wrap:wrap; margin:2px 0 6px;}
.bchip{flex:0 1 auto; min-width:104px; background:linear-gradient(160deg,#141d31,#0e1626);
  border:1px solid var(--line); border-radius:10px; padding:7px 9px; font-size:12px;}
.bchip .sym{font-weight:700; color:#eaf1fb; font-size:12px;}
.bchip .px{font-size:14px; font-weight:700; font-variant-numeric:tabular-nums;}
.bchip .chg{font-size:10.5px; font-weight:600;}
.grplabel{font-size:10px; text-transform:uppercase; letter-spacing:1.2px;
  color:var(--accent2); font-weight:700; margin:7px 2px 3px;}
.up{color:var(--up);} .dn{color:var(--down);} .flat{color:var(--muted);}
.panel{background:#101828; border:1px solid var(--line); border-radius:14px;
  padding:10px 12px; margin-bottom:10px;}
.phead{display:flex; align-items:baseline; justify-content:space-between; flex-wrap:wrap;}
.phead .t{font-size:16px; font-weight:800; color:#eaf1fb;}
.phead .s{font-size:10.5px; color:var(--muted);}

/* summary bar (अंतिम स्कैन ...) */
.sumbar{display:flex; gap:8px; flex-wrap:wrap; background:#0e1626;
  border:1px solid var(--line); border-radius:12px; padding:8px 12px;
  margin:8px 0; font-size:12.5px;}
.sumbar .it{color:#cfe0ff; font-variant-numeric:tabular-nums;}
.sumbar .it b{color:#eaf1fb;}
.sumbar .sep{color:var(--muted);}
.sumbar .lbl{color:var(--muted); font-size:10.5px;}

/* Hindi zone table — horizontally scrollable, screenshot style */
.zwrap{overflow-x:auto; border:1px solid var(--line); border-radius:12px;
  background:#0e1626;}
.zhin{width:100%; border-collapse:collapse; font-size:12px; min-width:980px;}
.zhin th{text-align:left; color:var(--muted); font-size:10.5px; text-transform:uppercase;
  letter-spacing:.4px; padding:7px 8px; border-bottom:1px solid var(--line);
  background:#0c1422; white-space:nowrap;}
.zhin td{padding:6px 8px; border-bottom:1px solid #18233a; color:#d9e5f6;
  font-variant-numeric:tabular-nums; white-space:nowrap;}
.zhin tr:hover{background:#131d31;}
.zhin .sym{font-weight:700; color:#eaf1fb;}
.zhin a{color:var(--accent2); text-decoration:none; font-weight:600;}
.zhin a.sym{color:#eaf1fb; font-weight:700;}
.zhin a.sym:hover{color:var(--accent2); text-decoration:underline;}
.zhin .dot{font-size:9px; vertical-align:middle;}
.dot.dem{color:var(--up);} .dot.sup{color:var(--down);}
.zhin .hq{color:#f5c542;}
.zhin .st-fresh{color:var(--up);} .zhin .st-tested{color:var(--accent2);}
.zhin .st-broken{color:var(--muted);}
.zscore{font-size:11px; padding:1px 7px; border-radius:12px; border:1px solid var(--line);}
.zscore.hi{color:var(--up); border-color:rgba(30,203,107,.4);}
.zscore.md{color:var(--accent2); border-color:rgba(34,211,238,.4);}
.zscore.lo{color:var(--muted);}
.oi{font-size:11px; padding:1px 7px; border-radius:10px; border:1px solid var(--line);
  white-space:nowrap; font-weight:600;}
.oi.plus{color:var(--up); border-color:rgba(30,203,107,.4);}
.oi.minus{color:var(--down); border-color:rgba(255,75,92,.35);}
.oi.none{color:var(--muted);}
.fdbx{background:#0e1626; border:1px solid var(--line); border-radius:10px;
  padding:8px 10px; margin-bottom:6px;}
.fdbx .lab{font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:.5px;}
.fdbx .val{font-size:19px; font-weight:800; font-variant-numeric:tabular-nums;}
.fdbx .sub{font-size:10px; color:var(--muted);}
.fdrow{display:flex; gap:12px; flex-wrap:wrap;}
.fdrow .fdbx{flex:1 1 120px;}
.news-item{display:flex; gap:9px; padding:7px 4px; border-bottom:1px solid #18233a;}
.news-item:hover{background:#131d31;}
.news-time{color:var(--muted); font-size:11px; width:44px; flex:0 0 44px;}
.news-body{flex:1; min-width:0;}
.news-title{color:#dbeeef; font-size:13px; font-weight:600; text-decoration:none;}
.news-body a{color:#dbeeef; text-decoration:none; word-break:break-word;}
.news-src{color:var(--muted); font-size:10px;}
.chip{font-size:11px; background:#152036; border:1px solid var(--line);
  color:#cfe0ff; border-radius:20px; padding:2px 9px; display:inline-block;}
.chip.t{background:#1a2740; color:var(--accent2);}
.chips{display:flex; gap:6px; flex-wrap:wrap; margin:3px 0;}
</style>
""", unsafe_allow_html=True)


# ── Hindi translation (best-effort Google, keyless) ─────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def _hi(text):
    """Translate English text to Hindi (best-effort; falls back to original)."""
    if not text or not str(text).strip():
        return str(text)
    try:
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "auto", "tl": "hi", "dt": "t", "q": str(text)},
            timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            out = "".join(x[0] for x in r.json()[0]).strip()
            if out:
                return out
    except Exception:
        pass
    return str(text)


def _cat_hi(cat):
    return {"Reversal": "उलटाव (Reversal)", "Continuation": "जारी (Continuation)"}.get(cat, cat)


def _dir_hi(d):
    return {"Demand": "DEMAND", "Supply": "SUPPLY"}.get(d, d)


def _state_hi(s):
    return {"Fresh": "ताज़ा", "Tested": "परीक्षित", "Broken": "टूटा"}.get(s, s)


def _score_cls(sc):
    if sc >= 90:
        return "hi"
    if sc >= 60:
        return "md"
    return "lo"


# Timeframe label -> as shown in the screenshot ("4 Hours", "1 Hour", "15 Min").
TF_LABEL = {
    "15m": "15 Min", "30m": "30 Min", "75m": "75 Min", "1h": "1 Hour",
    "2h": "2 Hours", "4h": "4 Hours", "6h": "6 Hours", "8h": "8 Hours",
    "1D": "Daily", "1W": "Weekly", "1M": "Monthly",
}


def _tf_hi(tf):
    return TF_LABEL.get(str(tf), str(tf))


# ── Cached data helpers ─────────────────────────────────────────────────────
@st.cache_data(ttl=30, show_spinner=False)
def load_market():
    import marketdata as md
    return md.fetch_all()


@st.cache_data(ttl=30, show_spinner=False)
def load_sectors():
    import sectors as sc
    return sc.fetch_sectors()


@st.cache_data(ttl=300, show_spinner=False)
def load_news():
    import news as n
    return n.fetch_latest(26)


@st.cache_data(ttl=600, show_spinner=False)
def load_news_body(url):
    import news as n
    return n.fetch_article(url)


@st.cache_data(ttl=300, show_spinner=False)
def load_events():
    import events as e
    return e.fetch_events(24)


@st.cache_data(ttl=90, show_spinner=False)
def load_fiidii():
    import fiidii as f
    return f.fetch(6), f.monthly()


@st.cache_data(ttl=60, show_spinner=False)
def load_options(symbol):
    import options as o
    return o.live_oi(symbol), o.top_strikes(symbol, n=7), o.deep_links(symbol)


@st.cache_data(ttl=30, show_spinner=False)
def load_scan(symbol, timeframe, min_score, strict, lookback, recommended):
    import zscan
    return zscan.scan(symbol, timeframe, min_score=min_score, strict=strict,
                      lookback_months=lookback, recommended=recommended)


@st.cache_data(ttl=90, show_spinner=False)
def load_universe_zones(tf_tuple, min_score, recommended, strict, active_only,
                        eod_filter, symbols_tuple):
    import zscan
    syms = list(symbols_tuple) if symbols_tuple else None
    return zscan.scan_universe_zones(timeframes=tf_tuple, min_score=min_score,
                                     recommended=recommended, strict=strict,
                                     active_only=active_only, eod_filter=eod_filter,
                                     symbols=syms)


def fmt_cr(x):
    if x is None:
        return "—"
    x = float(x)
    cls = "up" if x > 0 else ("dn" if x < 0 else "flat")
    return f'<span class="{cls}">{x:+,.0f}</span>'


def _chg_html(c):
    if c is None:
        return '<span class="chg flat">—</span>'
    cls = "up" if c > 0 else ("dn" if c < 0 else "flat")
    sign = "+" if c > 0 else ("−" if c < 0 else "")
    return f'<span class="{cls}">{sign}{c:.2f}%</span>'


# ── Compact Live Market Board ──────────────────────────────────────────────
GRP_HI = {"dollar": "💵 मुद्राएँ", "rates": "🏛️ दरें और बॉन्ड",
          "commodities": "🥇 धातु और ऊर्जा", "indices": "📈 ग्लोबल इंडेक्स",
          "other": "अन्य"}


def render_board():
    import marketdata as md
    data = load_market()
    st.markdown('<div class="phead"><span class="t">🌍 Live Market Board '
                '<span style="color:#1ecb6b;font-size:11px;">● LIVE</span></span>'
                '<span class="s">30s auto-refresh · छोटा</span></div>', unsafe_allow_html=True)
    chips = []
    for grp, tiles in md.TILES:
        chips.append(f'<span class="grplabel">{GRP_HI.get(grp, grp)}</span>')
        for t in tiles:
            q = data[t["label"]]
            px = f"{q['price']:,.2f}" if q["price"] is not None else "—"
            chips.append(
                f'<div class="bchip"><div class="sym">{t["label"]}</div>'
                f'<div class="px">{px}</div><div class="chg">{_chg_html(q["chg_pct"])}</div></div>')
    st.markdown('<div class="strip">' + "".join(chips) + '</div>', unsafe_allow_html=True)


# ── Compact Live Sector Indices ────────────────────────────────────────────
def render_sectors():
    sec = load_sectors()
    if not sec:
        return
    st.markdown('<div class="phead"><span class="t">🧱 Live Sector Indices '
                '<span style="color:#1ecb6b;font-size:11px;">● LIVE</span></span>'
                '<span class="s">NSE · 30s</span></div>', unsafe_allow_html=True)
    chips = []
    for s in sec:
        cls = "up" if s["chg_pct"] >= 0 else "dn"
        px = f"{s['price']:,.1f}"
        sign = "+" if s["chg_pct"] >= 0 else "−"
        chips.append(
            f'<div class="bchip"><div class="sym">{s["label"]}</div>'
            f'<div class="px">{px}</div><div class="chg {cls}">{sign}{s["chg_pct"]:.2f}%</div></div>')
    st.markdown('<div class="strip">' + "".join(chips) + '</div>', unsafe_allow_html=True)


# ── FII/DII (आज + and-dino ke liye expander) ───────────────────────────────
def render_fiidii():
    st.markdown('<div class="phead"><span class="t">🏛️ FII / DII आज</span>'
                '<span class="s">live · 90s</span></div>', unsafe_allow_html=True)
    try:
        days, monthly = load_fiidii()
    except Exception:
        days, monthly = [], {}
    if not days:
        st.caption("आज का FII/DII अभी उपलब्ध नहीं।")
        return
    today = days[0]
    fii = today.get("fii_net")
    dii = today.get("dii_net")
    d = today.get("date", "")
    try:
        dome = d.strftime("%d-%b") if hasattr(d, "strftime") else str(d)
    except Exception:
        dome = str(d)
    st.markdown(
        f'<div class="fdrow">'
        f'<div class="fdbx"><div class="lab">FII / FPI &nbsp;{dome}</div>'
        f'<div class="val">{fmt_cr(fii)}</div>'
        f'<div class="sub">खरीद {today.get("fii_buy","—")} · बिक्री {today.get("fii_sell","—")} Cr</div></div>'
        f'<div class="fdbx"><div class="lab">DII &nbsp;{dome}</div>'
        f'<div class="val">{fmt_cr(dii)}</div>'
        f'<div class="sub">खरीद {today.get("dii_buy","—")} · बिक्री {today.get("dii_sell","—")} Cr</div></div>'
        f'<div class="fdbx"><div class="lab">NIFTY 50</div>'
        f'<div class="val">{today.get("nifty","—")}</div>'
        f'<div class="sub">chg {fmt_cr(today.get("chg",""))} pts</div></div>'
        f'</div>', unsafe_allow_html=True)
    # और दिन — touch = expand
    if len(days) > 1:
        with st.expander(f"📅 पिछले {min(len(days)-1, 5)} दिन देखें (touch = expand)"):
            for rec in days[1:6]:
                st.markdown(
                    f'<div class="fdbx"><div class="lab">{rec.get("date","")}</div>'
                    f'<div class="val">FII {fmt_cr(rec.get("fii_net"))} · '
                    f'DII {fmt_cr(rec.get("dii_net"))} · NIFTY {rec.get("nifty","—")}</div></div>',
                    unsafe_allow_html=True)


# ── Options OI (छोटा) ──────────────────────────────────────────────────────
def _oi_badge(oi, is_demand):
    if not oi:
        return '<span class="oi none">—</span>'
    aligned = (oi.startswith("P>") if is_demand else oi.startswith("C>"))
    cls = "plus" if aligned else "minus"
    return f'<span class="oi {cls}">{oi}</span>'


def render_options(symbol):
    live, strikes, links = load_options(symbol)
    st.markdown(f'<div class="phead"><span class="t">🎯 Options OI</span>'
                f'<span class="s">{symbol.upper()}</span></div>', unsafe_allow_html=True)
    if live:
        st.markdown(
            f'<div class="fdrow">'
            f'<div class="fdbx"><div class="lab">CALL OI</div>'
            f'<div class="val">{live["call_oi"]:,.0f}</div></div>'
            f'<div class="fdbx"><div class="lab">PUT OI</div>'
            f'<div class="val">{live["put_oi"]:,.0f}</div></div>'
            f'<div class="fdbx"><div class="lab">PCR</div>'
            f'<div class="val">{live["pcr"]:.2f}</div></div>'
            f'</div>', unsafe_allow_html=True)
    else:
        st.caption("Live OI cloud पर सीमित है — नीचे लिंक से browser में देखें।")
    links_html = "".join(
        f'<a class="chip" href="{l["url"]}" target="_blank" '
        f'style="text-decoration:none;">↗ {l["label"]}</a>' for l in links)
    st.markdown(f'<div class="chips">{links_html}</div>', unsafe_allow_html=True)


# ── स्टॉक / यूनिवर्स हिंदी table ──────────────────────────────────────────
def zone_table_heading(rows, lookback_hi="सभी"):
    fresh = sum(1 for r in rows if r["state"] == "Fresh")
    tested = sum(1 for r in rows if r["state"] == "Tested")
    hq = sum(1 for r in rows if r["hq"])
    now = datetime.datetime.now().strftime("%H:%M:%S")
    return (f'<div class="sumbar">'
            f'<span class="it"><span class="lbl">अंतिम स्कैन</span> {now}</span>'
            f'<span class="sep">|</span>'
            f'<span class="it"><b>{len(rows)}</b> <span class="lbl">कुल Zones</span></span>'
            f'<span class="sep">|</span>'
            f'<span class="it"><b>{fresh}</b> <span class="lbl">Fresh</span></span>'
            f'<span class="sep">|</span>'
            f'<span class="it"><b>{tested}</b> <span class="lbl">Tested</span></span>'
            f'<span class="sep">|</span>'
            f'<span class="it"><span style="color:#f5c542;">⭐ {hq}</span> <span class="lbl">HQ</span></span>'
            f'<span class="sep">|</span>'
            f'<span class="it"><span class="lbl">Lookback</span> {lookback_hi}</span>'
            f'</div>')


def render_zone_table(rows, title, subtitle, lookback_hi="सभी"):
    """Renders the screenshot-style Hindi zone table (exact column set + links)."""
    st.markdown(f'<div class="phead"><span class="t">{title}</span>'
                f'<span class="s">{subtitle}</span></div>', unsafe_allow_html=True)
    if not rows:
        st.info("कोई VALID zone नहीं मिला। कृपया फ़िल्टर/स्कोर बदलें।")
        return
    st.markdown(zone_table_heading(rows, lookback_hi), unsafe_allow_html=True)
    html = ['<div class="zwrap"><table class="zhin"><thead><tr>'
            '<th>एससेट</th><th>✓ चार्ट खोलें</th><th>टाइमफ्रेम</th><th>दिशा</th>'
            '<th>पैटर्न</th><th>टाइप</th><th>स्टेट</th><th>HQ</th>'
            '<th>स्कोर</th><th>Entry</th><th>SL</th><th>OI</th><th>चेन</th>'
            '</tr></thead><tbody>']
    for r in rows:
        disp = r["symbol"].replace(".NS", "")
        is_dem = r["dir"] == "Demand"
        dot = ('<span class="dot dem">●</span>' if is_dem else '<span class="dot sup">●</span>')
        tv = (f'<a href="{r["tv"]}" target="_blank">✓ Open</a>' if r.get("tv") else "—")
        cat = (_cat_hi(r.get("cat", "")) if r.get("cat")
               else _cat_hi("Continuation" if r.get("pattern", "").endswith(("D", "R")) else "Reversal"))
        st_map = {"Fresh": "st-fresh", "Tested": "st-tested", "Broken": "st-broken"}
        st_cls = st_map.get(r["state"], "")
        state_txt = f'{_state_hi(r["state"])} (#{r.get("touches", 0)})'
        hq = '<span class="hq">⭐</span>' if r.get("hq") else ""
        sc = r["score"]
        score = f'<span class="zscore {_score_cls(sc)}">{sc}</span>'
        chain = (f'<a href="{r["chain"]}" target="_blank">चेन ↗</a>' if r.get("chain") else "—")
        oi = _oi_badge(r.get("oi"), is_dem)
        symlink = (f'<a class="sym" href="{r["tv"]}" target="_blank" title="TradingView '
                   f'{r["tf"]}">📈 {disp}</a>' if r.get("tv") else f'<span class="sym">{disp}</span>')
        html.append(
            f'<tr><td>{symlink}</td><td>{tv}</td><td>{_tf_hi(r["tf"])}</td>'
            f'<td>{dot} {_dir_hi(r["dir"])}</td><td>{r["pattern"]}</td><td>{cat}</td>'
            f'<td class="{st_cls}">{state_txt}</td><td>{hq}</td><td>{score}</td>'
            f'<td>{r["entry"]:,.2f}</td><td>{r["sl"]:,.2f}</td>'
            f'<td>{oi}</td><td>{chain}</td></tr>')
    html.append('</tbody></table></div>')
    st.markdown("".join(html), unsafe_allow_html=True)
    st.caption("✓ चार्ट खोलें = उसी टायमफ्रेम का TradingView चार्ट; OI में Demand=P>C (bullish), "
               "Supply=C>P (bearish); चेन = NSE option chain. टाइप: Reversal=उलटाव, "
               "Continuation=जारी. स्कोर ≥90 = HQ.")



# ── Sidebar (हिंदी) ─────────────────────────────────────────────────────────
import zdata

st.sidebar.markdown("## ⚙️ Scan Settings")
scan_all = st.sidebar.toggle("Universe + Timeframes से स्कैन करें", value=False,
                             help="पूरे F&O universe को चुने हुए timeframes में स्कैन करें.")

if scan_all:
    st.sidebar.markdown("<b>Universe चुनें</b><br><span style='font-size:10px;color:#8ba1c0;'>(NSE फ्यूचर स्टॉक्स चुनें — डिफ़ॉल्ट: सभी)</span>", unsafe_allow_html=True)
    sel_universe = st.sidebar.multiselect(
        "Universe", zdata.FUT_STOCKS, default=list(zdata.FUT_STOCKS),
        format_func=lambda x: x.replace(".NS", ""),
        help="सिर्फ़ चुने स्टॉक स्कैन होंगे।")
    if not sel_universe:
        sel_universe = list(zdata.FUT_STOCKS)
    st.sidebar.markdown("<b>Timeframes चुनें</b>", unsafe_allow_html=True)
    univ_tfs = st.sidebar.multiselect(
        "Timeframes", zdata.TIMEFRAMES, default=list(zdata.TIMEFRAMES),
        format_func=_tf_hi,
        help="Ctrl/Cmd से add/remove. 15m–8h = intraday, 1D/1W/1M = daily.")
    if not univ_tfs:
        univ_tfs = ["2h", "4h"]
    eod_filter = st.sidebar.toggle(
        "सिर्फ़ आज की candle band (low−10% … high+10%) में", value=True,
        help="सिर्फ़ उन zones को दिखाएँ जो आज के daily candle range ±10% के भीतर हैं।")
    symbol = "RELIANCE.NS"
    timeframe = "4h"
else:
    sel_universe = None
    univ_tfs = ["4h"]
    symbol = st.sidebar.text_input("स्टॉक / प्रतीक", value="RELIANCE.NS",
                                   help="^NSEI = Nifty, ^NSEBANK = Bank Nifty।")
    timeframe = st.sidebar.selectbox("टाइमफ्रेम", zdata.TIMEFRAMES,
                                     index=zdata.TIMEFRAMES.index("4h"))
    eod_filter = st.sidebar.toggle(
        "सिर्फ़ EOD candle band (high+10% … low−10%) में स्कैन", value=True,
        help="आज के daily close-candle high+10% से low−10% के भीतर ही zones स्कैन करें।")

min_score = st.sidebar.slider("न्यूनतम स्कोर", 20, 90, 40, step=5)
strict = st.sidebar.toggle("सख्त (spec-strict) नियम", value=False)
recommended = st.sidebar.toggle("सुझाव सेटअप (DBD · mid · RR 1:3)", value=True)
lookback = st.sidebar.selectbox("कितना पीछे देखें", ["सभी", "24", "12", "6", "3"])
lookback_months = None if lookback == "सभी" else int(lookback)
st.sidebar.markdown("---")
st.sidebar.caption("Live data: Yahoo/TradingView/NSE/niftytrader (keyless). आज की तारीख·समय "
                   f"{datetime.datetime.now().strftime('%d-%b %H:%M')} IST")


# ── MAIN LAYOUT ─────────────────────────────────────────────────────────────
st.markdown("## 📊 Demand & Supply Zone Scanner")
st.caption("DBR/RBR/RBD/DBD — सभी 4 पैटर्न करें। हर row: ✓ चार्ट खोलें (TradingView) + OI + चेन लिंक।")

render_board()
render_sectors()
st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)

r1, r2 = st.columns([1.0, 1.0], gap="small")
with r1:
    render_fiidii()
with r2:
    render_options(symbol)

st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)


# ── Zone Scanner table (मुख्य / screenshot style) ──────────────────────────
if scan_all:
    tf_tuple = tuple(univ_tfs)
    rows = load_universe_zones(tf_tuple, min_score, recommended, strict,
                               active_only=False, eod_filter=eod_filter,
                               symbols_tuple=tuple(sel_universe))
    st.markdown('<div class="phead"><span class="t">🧭 Zone स्कैन — सभी NSE फ्यूचर '
                f'स्टॉक्स <span style="color:#4f8cff;">({len(sel_universe)} × '
                f'{" · ".join(tf_tuple)})</span></span>'
                f'<span class="s">live · cached 90s</span></div>', unsafe_allow_html=True)
    if eod_filter:
        st.caption("📌 EOD band ON: सिर्फ़ आज के daily close-candle "
                   "**high+10% … low−10%** के भीतर के zones।")
    # filters
    f1, f2, f3 = st.columns([1, 1, 1])
    dir_opt = f1.selectbox("दिशा", ["सभी", "Demand", "Supply"], index=0)
    sort_opt = f2.selectbox("क्रम", ["स्कोर ↓", "एससेट", "दूरी"], index=0)
    st_opt = f3.selectbox("स्टेट", ["सभी", "ताज़ा (Fresh)", "परीक्षित (Tested)"], index=0)

    rr = rows
    if dir_opt == "Demand":
        rr = [x for x in rr if x["dir"] == "Demand"]
    elif dir_opt == "Supply":
        rr = [x for x in rr if x["dir"] == "Supply"]
    if st_opt == "ताज़ा (Fresh)":
        rr = [x for x in rr if x["state"] == "Fresh"]
    elif st_opt == "परीक्षित (Tested)":
        rr = [x for x in rr if x["state"] == "Tested"]
    if sort_opt == "स्कोर ↓":
        rr = sorted(rr, key=lambda x: -x["score"])
    elif sort_opt == "एससेट":
        rr = sorted(rr, key=lambda x: (x["symbol"], x["tf"]))
    else:
        rr = sorted(rr, key=lambda x: abs(x["last"] - x["entry"]) / x["entry"] if x["last"] else 0)
    render_zone_table(rr, "सभी NSE फ्यूचर स्टॉक्स — सभी टाइमफ्रेम",
                      f'{len(tf_tuple)} TF · {len(sel_universe)} स्टॉक')
else:
    # single-stock scan rows -> same Hindi table (EOD band filter, default ON)
    try:
        zones, df, extra = load_scan(symbol, timeframe, min_score, strict,
                                     lookback_months, recommended)
        last = float(df["close"].iloc[-1]) if df is not None and len(df) else None
    except Exception as ex:
        st.error(f"स्कैन नहीं हो सका: {ex}")
        zones, df, extra = [], None, None
        last = None

    import tv as _tv
    import options as _opt
    import zscan as _zs
    _links = _opt.deep_links(symbol)
    _lc = "".join(f'<a class="chip" href="{l["url"]}" target="_blank" '
                  f'style="text-decoration:none;">↗ {l["label"]}</a>' for l in _links)
    _tvchip = (f'<a class="chip t" href="{_tv.chart_url(symbol, timeframe)}" '
               f'target="_blank" style="text-decoration:none;">📈 TradingView चार्ट</a>')
    st.markdown(f'<div class="chips">{_tvchip}{_lc}</div>', unsafe_allow_html=True)

    band = None
    if eod_filter:
        zones, band = _zs.eod_zone_filter(zones, symbol)
    if band:
        st.markdown(
            f'<div class="sumbar" style="margin-top:4px;">'
            f'<span class="it"><span class="lbl">EOD band (आज)</span> '
            f'low {band["lo"]:,.2f}−10% = {band["eod_lo"]:,.2f} … '
            f'high {band["hi"]:,.2f}+10% = {band["eod_hi"]:,.2f}</span>'
            f'</div>', unsafe_allow_html=True)

    rows = []
    for z in zones:
        rows.append({
            "symbol": symbol, "tf": timeframe,
            "pattern": z.patternType,
            "dir": "Demand" if z.isDemand else "Supply",
            "cat": z.zoneCategory,
            "entry": round(z.proxVal, 2),
            "sl": round(z.slVal, 2),
            "tp": round(z.tpVal, 2),
            "score": z.densityScore,
            "hq": bool(z.isHQ),
            "state": z.state,
            "touches": z.touchCount,
            "last": last,
            "chain": _links[0]["url"] if _links else "",
            "tv": _tv.chart_url(symbol, timeframe),
            "oi": _zs.oi_bias(symbol, z.isDemand),
        })
    render_zone_table(rows, f"{symbol.replace('.NS','')} · {timeframe}",
                      "सिंगल स्टॉक",
                      lookback_hi=lookback if isinstance(lookback, str) else lookback)

    if isinstance(extra, dict) and extra.get("roi") and extra["roi"].get("n_trades"):
        roi, rec = extra["roi"], extra["recommended"]
        st.success(f"**सुझाव ROI** (DBD · mid · RR 1:{rec['targetRR']:.1f}): "
                   f"{roi['n_trades']} ट्रेड · win {roi['win_pct']:.0f}% · "
                   f"**{roi['net_roi_pct']:+.2f}%**")


# ── News + Events (हिंदी हेडलाइन) ─────────────────────────────────────────
st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
nc1, nc2 = st.columns([1.15, 1.0], gap="small")

with nc1:
    st.markdown("## 📰 महत्वपूर्ण समाचार <span class='s'>हिंदी हेडलाइन · tap = खोलें</span>",
                unsafe_allow_html=True)
    ns = load_news()
    if not ns:
        st.info("अभी headlinés उपलब्ध नहीं।")
    for it in ns[:12]:
        hi_title = _hi(it["title"])
        tags = "".join(f'<span class="chip t">{t}</span>' for t in it["tags"])
        tm = it["published"]
        tms = tm.strftime("%H:%M") if hasattr(tm, "strftime") else str(tm)[:5]
        st.markdown(
            f'<div class="news-item"><div class="news-time">{tms}</div>'
            f'<div class="news-body"><a class="news-title" href="{it["link"]}" '
            f'target="_blank">{hi_title}</a>'
            f'<div>{tags}<span class="news-src"> · {it["source"]} · '
            f'<a href="{it["link"]}" target="_blank" style="color:#8ba1c0;">'
            f'मूल देखें ↗</a></span></div></div></div>', unsafe_allow_html=True)
        with st.expander("📖 पूरा पढ़ें"):
            body = load_news_body(it["link"]) or it.get("summary") or "पूरा text उपलब्ध नहीं।"
            st.markdown(f'<div style="font-size:12.5px;color:#cdd9ec;line-height:1.6;'
                        f'white-space:pre-line;max-height:330px;overflow:auto;">{body}</div>',
                        unsafe_allow_html=True)
            st.markdown(f'<div style="margin-top:4px;"><a href="{it["link"]}" '
                        f'target="_blank">original ↗</a></div>', unsafe_allow_html=True)

with nc2:
    st.markdown("## ⚡ NSE & फ्यूचर इवेंट <span class='s'>हिंदी · tap = खोलें</span>",
                unsafe_allow_html=True)
    ev = load_events()
    if ev:
        for it in ev[:12]:
            hi_title = _hi(it["title"])
            stamps = "".join(f'<span class="chip">{s}</span>' for s in it["stocks"])
            tick = (f'<span class="chip t">{it["tick"]}</span>' if it["tick"] and not it["stocks"] else "")
            tm = it["published"]
            tms = tm.strftime("%H:%M") if hasattr(tm, "strftime") else str(tm)[:5]
            st.markdown(
                f'<div class="news-item"><div class="news-time">{tms}</div>'
                f'<div class="news-body">{stamps}{tick}'
                f'<div style="margin-top:2px;color:#cfe0ff;font-size:12.5px;">'
                f'<a href="{it["link"]}" target="_blank" style="color:#dbe7fb;'
                f'text-decoration:none;">{hi_title}</a></div>'
                f'<div class="news-src">{it["source"]}</div></div></div>', unsafe_allow_html=True)
            with st.expander("📖 और पढ़ें"):
                bd = load_news_body(it["link"])
                st.markdown(f'<div style="font-size:12.5px;color:#cdd9ec;line-height:1.6;'
                            f'white-space:pre-line;max-height:330px;overflow:auto;">'
                            f'{bd or "पूरा text उपलब्ध नहीं।"}</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="margin-top:4px;"><a href="{it["link"]}" '
                            f'target="_blank">original ↗</a></div>', unsafe_allow_html=True)
    else:
        st.info("अभी इवेंट उपलब्ध नहीं।")


st.markdown("---")
st.caption("MarketHub · Zone Screener (हिंदी) + Live Terminal. Quotes: Yahoo/TradingView; "
           "flows: NSE/niftytrader; news & events: RSS. निवेश सलाह नहीं। "
           f"आज: {datetime.datetime.now().strftime('%d-%b-%Y %H:%M')} IST")
