# -*- coding: utf-8 -*-
"""
MarketHub — Zone Screener + Live Market Terminal
================================================
One-page live app:
  • Top    : 4-row global market board (DXY · USDINR · TLT · US10Y · Gold · Silver ·
             Crude · GIFT NIFTY · NIFTY50 · US30 · US500 · JP225 · SSE)
  • Row 2  : FII/DII flows (today live + last 3 days) + Options OI (Put/Call chains + links)
  • Bottom : Demand/Supply Zone screener + Live News (touch = read full) + NSE events

Deploy:  streamlit run app.py  (or push to Streamlit Cloud)
Data:    Yahoo Finance / TradingView / niftytrader / NSE — all keyless.
"""
from __future__ import annotations

import os
import sys
import datetime
import streamlit as st

# Ensure the sibling app modules (marketdata.py, zone_core.py, zscan.py, ...) are
# importable regardless of the directory Streamlit launches app.py from.  This is
# the #1 cause of "ModuleNotFoundError: No module named 'marketdata'" on
# Streamlit Cloud when the .py files are pushed but not colocated with app.py.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

st.set_page_config(page_title="MarketHub · Zone Screener + Live Market", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

# ---------------------------------------------------------------------------
# Inline theme (replaces the need for a .streamlit/config.toml on Streamlit Cloud).
# Overrides Streamlit's own theme CSS variables that drive the app chrome
# (primary colour, backgrounds, text). The card/table CSS below builds on these.
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* Streamlit theme — mirror of the removed .streamlit/config.toml */
:root{
  --primary-color:#4f8cff;
  --background-color:#0b1220;
  --secondary-background-color:#121a2b;
  --text-color:#e6edf7;
}
.stApp{background-color:#0b1220; color:#e6edf7;}
[data-testid="stSidebar"]{background-color:#121a2b;}
[data-testid="stSidebar"] *{color:#e6edf7;}
[data-testid="stHeader"]{background:rgba(11,18,32,.35);}
[data-baseweb="select"] *{background-color:#121a2b; color:#e6edf7;}
[data-baseweb="tag"]{background-color:#1d2a44;}
[data-testid="stMetricValue"]{color:#e6edf7; font-size:1.5rem;}
.accordion, [data-testid="stExpander"]{background-color:#121a2b;}
[data-testid="stExpander"] *{color:#e6edf7;}
</style>
""", unsafe_allow_html=True)


def zone_core_version():
    try:
        import zone_core
        return zone_core.settings().get("_version", "10.1")
    except Exception:
        return "10.1"


# --------------------------------------------------------------------------- #
#  CSS (inline; renders in sandboxed preview *and* full browser)                #
# --------------------------------------------------------------------------- #
st.markdown("""
<style>
:root{--bg:#0b1220; --line:#22304a; --txt:#e6edf7; --muted:#8ba1c0;
  --up:#1ecb6b; --down:#ff4b5c; --accent2:#22d3ee; --accent:#4f8cff;}
.ticker-row{display:flex; gap:10px; flex-wrap:wrap; margin-bottom:6px;}
.tile{flex:1 1 0; min-width:118px; background:linear-gradient(160deg,#141d31,#0e1626);
  border:1px solid var(--line); border-radius:12px; padding:10px 12px 9px;
  box-shadow:0 2px 10px rgba(0,0,0,.35); position:relative; overflow:hidden;}
.sector-row .tile{min-width:96px;}
@media(max-width:640px){
  .tile{min-width:100px; padding:8px 9px 7px;}
  .sector-row .tile{min-width:86px;}
  .tile .px{font-size:16px;}
  .tile .sym{font-size:11.5px;}
}
.tile::before{content:''; position:absolute; left:0; top:0; bottom:0; width:3px;}
.tile.is-up::before{background:var(--up);}
.tile.is-dn::before{background:var(--down);}
.tile .sym{font-weight:700; font-size:12.5px; letter-spacing:.4px; color:#eaf1fb;}
.tile .nm{font-size:9.5px; color:var(--muted); line-height:1.1; min-height:22px; margin-top:1px;}
.tile .px{font-size:18px; font-weight:700; margin-top:4px; color:var(--txt); font-variant-numeric:tabular-nums;}
.tile .chg{font-size:11px; font-weight:600; margin-top:1px; font-variant-numeric:tabular-nums;}
.chg.up{color:var(--up);} .chg.dn{color:var(--down);} .chg.flat{color:var(--muted);}
.grplabel{font-size:10px; text-transform:uppercase; letter-spacing:1.4px;
  color:var(--accent2); font-weight:700; margin:8px 2px 4px;}
.panel{background:#101828; border:1px solid var(--line); border-radius:14px;
  padding:12px 14px; margin-bottom:12px;}
.phead{display:flex; align-items:baseline; justify-content:space-between;}
.phead .t{font-size:17px; font-weight:800; color:#eaf1fb;}
.phead .s{font-size:11px; color:var(--muted);}
.chips{display:flex; gap:6px; flex-wrap:wrap; margin:3px 0;}
.chip{font-size:11px; background:#152036; border:1px solid var(--line);
  color:#cfe0ff; border-radius:20px; padding:2px 9px;}
.chip.t{background:#1a2740; color:var(--accent2);}
.chip.up{color:var(--up); border-color:rgba(30,203,107,.35);}
.chip.dn{color:var(--down); border-color:rgba(255,75,92,.35);}
.fdrow{display:flex; gap:16px; flex-wrap:wrap; margin-top:6px;}
.fdbox{flex:1 1 150px; background:#0e1626; border:1px solid var(--line);
  border-radius:10px; padding:8px 10px;}
.fdbox .lab{font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:.5px;}
.fdbox .val{font-size:20px; font-weight:800; margin-top:2px; font-variant-numeric:tabular-nums;}
.fdbox .sub{font-size:10.5px; color:var(--muted); margin-top:2px;}
.up{color:var(--up);} .dn{color:var(--down);} .flat{color:var(--muted);}
.news-item{display:flex; gap:10px; padding:7px 4px; border-bottom:1px solid #18233a;}
.news-item:hover{background:#131d31;}
.news-time{color:var(--muted); font-size:11px; width:50px; flex:0 0 50px;}
.news-body{flex:1;}
.news-title{color:#dbe7fb; font-size:13px; font-weight:600; text-decoration:none;}
.news-body a{color:#dbe7fb; text-decoration:none;}
.news-src{color:var(--muted); font-size:10px;}
.news-full{background:#0c1422; border:1px solid var(--line); border-radius:8px;
  padding:10px 12px; font-size:12.5px; line-height:1.6; color:#cdd9ec; white-space:pre-line;
  margin-top:4px; max-height:340px; overflow:auto;}
.news-hint{font-size:10px; color:var(--muted); margin-top:2px;}
.univ-table{width:100%; border-collapse:collapse; font-size:12px;}
.univ-table th{text-align:left; color:#8ba1c0; font-size:10.5px; text-transform:uppercase;
  letter-spacing:.4px; padding:5px 7px; border-bottom:1px solid var(--line);}
.univ-table td{padding:5px 7px; border-bottom:1px solid #18233a; color:#d9e5f6;
  font-variant-numeric:tabular-nums;}
.univ-table tr:hover{background:#131d31;}
.univ-table .sym{font-weight:700; color:#eaf1fb;}
.univ-table a{color:var(--accent2); text-decoration:none;}
.z-badge{font-size:10px; padding:1px 7px; border-radius:12px; border:1px solid var(--line);}
.z-has{color:var(--up); border-color:rgba(30,203,107,.4);}
.z-zero{color:var(--muted);}
/* compact board table */
.board-table{width:100%; border-collapse:collapse; font-size:12px;}
.board-table th{text-align:left; color:#8ba1c0; font-size:10.5px; text-transform:uppercase;
  letter-spacing:.4px; padding:5px 8px; border-bottom:1px solid var(--line);}
.board-table td{padding:5px 8px; border-bottom:1px solid #18233a; color:#d9e5f6;
  font-variant-numeric:tabular-nums;}
.board-table tr:hover{background:#131d31;}
.board-table td.sym{font-weight:700; color:#eaf1fb;}
.board-table td.nm{color:#8ba1c0; font-size:10.5px;}
.board-table .grp td{background:#0e1626; color:var(--accent2); font-size:10px;
  font-weight:800; text-transform:uppercase; letter-spacing:1.2px;}
.board-table .src{color:#5a6c8a; font-size:9px;}
/* OI bias badge */
.oi{font-size:10px; padding:1px 6px; border-radius:10px; border:1px solid var(--line);
  white-space:nowrap; font-weight:600;}
.oi.plus{color:var(--up); border-color:rgba(30,203,107,.4);}
.oi.minus{color:var(--down); border-color:rgba(255,75,92,.35);}
.oi.none{color:var(--muted);}
.stApp{background:var(--bg);}
[data-testid="stSidebar"]{background:#0d1524;}
[data-testid="stSidebar"] *{color:var(--txt);}
.stMarkdown{font-size:14px;}
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
#  Cached data helpers                                                          #
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=45, show_spinner=False)
def load_market():
    import marketdata as md
    return md.fetch_all()


@st.cache_data(ttl=60, show_spinner=False)
def load_sectors():
    import sectors as sc
    return sc.fetch_sectors()


@st.cache_data(ttl=120, show_spinner=False)
def load_news():
    import news as n
    return n.fetch_latest(30)


@st.cache_data(ttl=600, show_spinner=False)
def load_news_body(url):
    import news as n
    return n.fetch_article(url)


@st.cache_data(ttl=120, show_spinner=False)
def load_events():
    import events as e
    return e.fetch_events(28)


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
def load_universe(tf_tuple, min_score, recommended, strict, eod_filter):
    import zscan
    return zscan.scan_universe(timeframes=tf_tuple, min_score=min_score,
                               recommended=recommended, strict=strict,
                               eod_filter=eod_filter)


@st.cache_data(ttl=90, show_spinner=False)
def load_universe_zones(tf_tuple, min_score, recommended, strict, active_only, eod_filter):
    import zscan
    return zscan.scan_universe_zones(timeframes=tf_tuple, min_score=min_score,
                                     recommended=recommended, strict=strict,
                                     active_only=active_only, eod_filter=eod_filter)


# --------------------------------------------------------------------------- #
#  Small render helpers                                                         #
# --------------------------------------------------------------------------- #
GROUP_LABELS = {"dollar": "💵 Currencies", "rates": "🏛️ Rates & Bonds",
                "commodities": "🥇 Metals & Energy", "indices": "📈 Global Indices"}


def _chg_html(c):
    if c is None:
        return '<span class="chg flat">—</span>'
    cls = "up" if c > 0 else ("dn" if c < 0 else "flat")
    sign = "+" if c > 0 else ("−" if c < 0 else "")
    return f'<span class="chg {cls}">{sign}{c:.2f}%</span>'


def _tile(q):
    cls = "is-up" if q["up"] else "is-dn"
    px = f"{q['price']:,.2f}" if q["price"] is not None else "—"
    return (f'<div class="tile {cls}"><div class="sym">{q["symbol"]}</div>'
            f'<div class="nm">{q["name"]}</div><div class="px">{px}</div>'
            f'{_chg_html(q["chg_pct"])}'
            f'<div class="nm" style="min-height:0;margin-top:3px;font-size:9px;">'
            f'source: {"TV" if q["src"]=="tv" else "Y"}</div></div>')


def render_board():
    import marketdata as md
    data = load_market()
    st.markdown('<div style="font-size:20px;font-weight:800;color:#eaf1fb;">🌍 '
                'LIVE MARKET BOARD <span style="font-size:11px;color:#8ba1c0;'
                'font-weight:500;">auto-refresh · 45s</span></div>', unsafe_allow_html=True)
    # Compact single-table board (mobile friendly; one row per instrument).
    html = ['<table class="board-table"><thead><tr><th>Symbol</th><th>Name</th>'
            '<th>Last</th><th>Chg%</th><th></th></tr></thead><tbody>']
    for grp, tiles in md.TILES:
        html.append(f'<tr class="grp"><td colspan="5">{GROUP_LABELS[grp]}</td></tr>')
        for t in tiles:
            q = data[t["label"]]
            px = f"{q['price']:,.2f}" if q["price"] is not None else "—"
            chg = _chg_html(q["chg_pct"])
            src = "TV" if q["src"] == "tv" else "Y"
            html.append(
                f'<tr><td class="sym">{t["label"]}</td>'
                f'<td class="nm">{t["name"]}</td><td>{px}</td><td>{chg}</td>'
                f'<td class="src">{src}</td></tr>')
    html.append('</tbody></table>')
    st.markdown("".join(html), unsafe_allow_html=True)
    return data


def render_sectors():
    sec = load_sectors()
    if not sec:
        return
    st.markdown('<div class="phead"><span class="t">🧱 Live Sector Indices</span>'
                '<span class="s">NSE · auto-refresh · 60s</span></div>', unsafe_allow_html=True)
    tiles = []
    for s in sec:
        cls = "is-up" if s["chg_pct"] >= 0 else "is-dn"
        px = f"{s['price']:,.1f}"
        tiles.append(
            f'<div class="tile {cls}"><div class="sym">{s["label"]}</div>'
            f'<div class="nm">{s["full"]}</div><div class="px">{px}</div>'
            f'{_chg_html(s["chg_pct"])}</div>')
    # wrap in a mobile-friendly container
    st.markdown('<div class="ticker-row sector-row">' + "".join(tiles) + '</div>',
                unsafe_allow_html=True)


def fmt_cr(x):
    if x is None:
        return "—"
    x = float(x)
    cls = "up" if x > 0 else ("dn" if x < 0 else "flat")
    return f'<span class="{cls}">{x:+,.0f} Cr</span>'


def render_fiidii():
    st.markdown('<div class="phead"><span class="t">🏛️ FII / DII Flows</span>'
                '<span class="s">today live + last 3 days · 90s</span></div>',
                unsafe_allow_html=True)
    days, monthly = load_fiidii()
    if not days:
        st.caption("FII/DII data not reachable right now.")
        return
    today = days[0]
    fii = today.get("fii_net")
    dii = today.get("dii_net")
    # Today card
    st.markdown(
        f'<div class="fdrow">'
        f'<div class="fdbox"><div class="lab">FII / FPI &nbsp;{today.get("date","")}</div>'
        f'<div class="val">{fmt_cr(fii)}</div>'
        f'<div class="sub">Buy {today.get("fii_buy","—")} · Sell {today.get("fii_sell","—")} Cr</div></div>'
        f'<div class="fdbox"><div class="lab">DII &nbsp;{today.get("date","")}</div>'
        f'<div class="val">{fmt_cr(dii)}</div>'
        f'<div class="sub">Buy {today.get("dii_buy","—")} · Sell {today.get("dii_sell","—")} Cr</div></div>'
        f'<div class="fdbox"><div class="lab">NIFTY 50</div>'
        f'<div class="val">{today.get("nifty","—"):,.0f}</div>'
        f'<div class="sub">chg {fmt_cr(today.get("chg",""))} pts</div></div>'
        f'</div>', unsafe_allow_html=True)
    # Last 3 days (touchable)
    st.markdown('<div style="margin-top:6px;color:#8ba1c0;font-size:11px;">'
                '📅 Previous days — tap to expand</div>', unsafe_allow_html=True)
    for rec in days[1:4]:
        with st.expander(f"{rec['date']}   ·   FII {fmt_cr(rec['fii_net'])}   ·   "
                         f"DII {fmt_cr(rec['dii_net'])}   ·   NIFTY {rec.get('nifty','—')}"):
            st.markdown(
                f'<div class="fdrow">'
                f'<div class="fdbox"><div class="lab">FII</div>'
                f'<div class="val">{fmt_cr(rec["fii_net"])}</div></div>'
                f'<div class="fdbox"><div class="lab">DII</div>'
                f'<div class="val">{fmt_cr(rec["dii_net"])}</div></div>'
                f'<div class="fdbox"><div class="lab">NIFTY</div>'
                f'<div class="val">{rec.get("nifty","—")}</div></div>'
                f'</div>', unsafe_allow_html=True)


def render_universe(tf_tuple, min_score, recommended, strict, eod_filter=False):
    st.markdown(f'<div class="phead"><span class="t">🚀 All NSE Futures Stocks '
                f'<span style="color:#4f8cff;">({len(zdata.FUT_STOCKS)} symbols × '
                f'{" + ".join(tf_tuple)})</span></span>'
                f'<span class="s">live scan · 90s</span></div>', unsafe_allow_html=True)
    rows = load_universe(tf_tuple, min_score, recommended, strict, eod_filter)
    if not rows:
        st.caption("Nothing returned.")
        return
    has_zones = sum(1 for r in rows if r.get("zones"))
    st.caption(f"{has_zones} stock-timeframe pairs have VALID zones out of {len(rows)}.")
    # Build an HTML table
    html = ['<table class="univ-table"><thead><tr>'
            '<th>Symbol</th><th>TF</th><th>Zones</th><th>Active</th><th>Best</th>'
            '<th>Last</th><th>Trades</th><th>ROI %</th><th>Chain</th></tr></thead><tbody>']
    for r in rows:
        zc = r.get("zones", 0)
        zbad = (f'<span class="z-badge z-has">{zc}</span>' if zc else
                f'<span class="z-badge z-zero">0</span>')
        best = (f'{r["best_pat"]}@{r["best_score"]}' if r.get("best_pat") else "—")
        last = f'{r["last"]:,.2f}' if r.get("last") else "—"
        roi = (f'{r["roi_pct"]:+.2f}' if r.get("roi_pct") is not None else "—")
        chain = (f'<a href="{r["chain"]}" target="_blank">⚠ chain ↗</a>' if r.get("chain") else "")
        # base symbol (strip .NS for display)
        disp = r["symbol"].replace(".NS", "")
        html.append(
            f'<tr><td class="sym">{disp}</td><td>{r["tf"]}</td><td>{zbad}</td>'
            f'<td>{r.get("active",0)}</td><td>{best}</td><td>{last}</td>'
            f'<td>{r.get("roi_n","—")}</td><td>{roi}</td><td>{chain}</td></tr>')
    html.append('</tbody></table>')
    st.markdown("".join(html), unsafe_allow_html=True)
    st.caption("ROI % = recommended setup (DBD · mid entry · fixed target · 0.5×ATR · RR 1:3), "
               "net after Indian charges, ₹25k / 1% risk. Chain = live option chain for that stock.")


def _oi_badge(oi, is_demand):
    """Render the Put/Call OI bias badge for a zone."""
    if not oi:
        return '<span class="oi none">—</span>'
    aligned = (oi.startswith("P>") if is_demand else oi.startswith("C>"))
    cls = "plus" if aligned else "minus"
    return f'<span class="oi {cls}">{oi}</span>'


def render_universe_zones(tf_tuple, min_score, recommended, strict, eod_filter):
    st.markdown(f'<div class="phead"><span class="t">🧭 Zone Scan — All NSE Futures '
                f'Stocks <span style="color:#4f8cff;">({len(zdata.FUT_STOCKS)} × '
                f'{" · ".join(tf_tuple)})</span></span>'
                f'<span class="s">live scan · cached 90s</span></div>', unsafe_allow_html=True)

    # filters
    f1, f2, f3, f4 = st.columns([1, 1, 1, 1])
    state_opt = f1.selectbox("State", ["Active only", "All zones"], index=0)
    dir_opt = f2.selectbox("Direction", ["All", "Demand", "Supply"], index=0)
    sort_opt = f3.selectbox("Sort", ["Score ↓", "Distance", "Symbol"], index=0)
    if eod_filter:
        f4.markdown('<div style="font-size:10px;color:#8ba1c0;margin-top:6px;">📌 EOD band ON: '
                    'scan only inside day-candle <b>low−10% … high+10%</b></div>',
                    unsafe_allow_html=True)

    all_rows = load_universe_zones(tf_tuple, min_score, recommended, strict,
                                   active_only=(state_opt == "Active only"),
                                   eod_filter=eod_filter)
    rows = all_rows
    if dir_opt != "All":
        rows = [r for r in rows if r["dir"] == dir_opt]
    if sort_opt == "Score ↓":
        rows = sorted(rows, key=lambda r: -r["score"])
    elif sort_opt == "Symbol":
        rows = sorted(rows, key=lambda r: r["symbol"])
    else:  # Distance
        rows = sorted(rows, key=lambda r: abs(r["last"] - r["entry"]) / r["entry"] if r["last"] else 0)

    if not rows:
        st.warning("No zones match the filter.")
        return

    hq = sum(1 for r in rows if r["hq"])
    active = sum(1 for r in rows if r["state"] in ("Fresh", "Tested"))
    biased = sum(1 for r in rows if r.get("oi"))
    st.caption(f"{len(rows)} zones · {active} active (Fresh/Tested) · {hq} HQ (score≥90) · "
               f"{biased} with live OI bias")

    html = ['<table class="univ-table"><thead><tr>'
            '<th>Sym</th><th>TF</th><th>Ptn</th><th>Dir</th><th>Score</th>'
            '<th>Entry</th><th>SL</th><th>TP</th><th>State</th><th>Touch</th>'
            '<th>OI</th><th>Chart</th><th>Chain</th></tr></thead><tbody>']
    for r in rows:
        zbad = (f'<span class="z-badge z-has">{r["score"]}</span>' if r["score"] >= 50
                else f'<span class="z-badge z-zero">{r["score"]}</span>')
        hq_star = " ⭐" if r["hq"] else ""
        state_cls = "" if r["state"] in ("Fresh", "Tested") else " style='color:#8ba1c0;'"
        chain = (f'<a href="{r["chain"]}" target="_blank">chain ↗</a>' if r.get("chain") else "")
        tv = (f'<a href="{r["tv"]}" target="_blank" title="TradingView chart at {r["tf"]}">'
              f'chart ↗</a>' if r.get("tv") else "")
        disp = r["symbol"].replace(".NS", "")
        oi = _oi_badge(r.get("oi"), r["dir"] == "Demand")
        html.append(
            f'<tr><td class="sym">{disp}{hq_star}</td><td>{r["tf"]}</td>'
            f'<td>{r["pattern"]}</td><td>{r["dir"]}</td><td>{zbad}</td>'
            f'<td>{r["entry"]:,.2f}</td><td>{r["sl"]:,.2f}</td><td>{r["tp"]:,.2f}</td>'
            f'<td{state_cls}>{r["state"]}</td><td>{r["touches"]}</td><td>{oi}</td>'
            f'<td>{tv}</td><td>{chain}</td></tr>')
    html.append('</tbody></table>')
    st.markdown("".join(html), unsafe_allow_html=True)
    st.caption("OI = demand zones lean bullish when Put OI > Call OI (P>C); supply zones lean "
               "bearish when Call OI > Put OI (C>P). Chart = TradingView chart at that TF. "
               "Entry = zone proximal, SL = distal+buffer, TP = recommended target (RR 1:3). ⭐ = HQ.")


def render_options(symbol):
    live, strikes, links = load_options(symbol)
    st.markdown(f'<div class="phead"><span class="t">🎯 Options OI — Put / Call '
                f'<span style="color:#4f8cff;">· {symbol.upper()}</span></span>'
                f'<span class="s">live best-effort + chain links</span></div>',
                unsafe_allow_html=True)
    if live:
        st.markdown(
            f'<div class="fdrow">'
            f'<div class="fdbox"><div class="lab">CALL OI</div>'
            f'<div class="val">{live["call_oi"]:,.0f}</div></div>'
            f'<div class="fdbox"><div class="lab">PUT OI</div>'
            f'<div class="val">{live["put_oi"]:,.0f}</div></div>'
            f'<div class="fdbox"><div class="lab">PCR</div>'
            f'<div class="val">{live["pcr"]:.2f}</div></div>'
            f'</div>', unsafe_allow_html=True)
        st.caption(f"Expiry {live['expiry']} · ATM {live['atm']} · "
                   f"max Call OI {live['max_call_oi_strike']} · max Put OI {live['max_put_oi_strike']}")
        if strikes:
            import pandas as pd
            df = pd.DataFrame(strikes)
            df.columns = ["Strike", "Call OI", "Put OI", "Call LTP", "Put LTP"]
            st.dataframe(df, width="stretch", hide_index=True, height=230)
    else:
        st.caption("Live OI from NSE is rate-limited on cloud/DC IPs. Use the chain links "
                   "below to see live Put/Call OI in your browser.")
    # Links (always available)
    st.markdown('<div style="margin-top:4px;color:#8ba1c0;font-size:11px;">'
                '🔗 Open live option chain:</div>', unsafe_allow_html=True)
    links_html = "".join(
        f'<a class="chip" href="{l["url"]}" target="_blank" '
        f'style="text-decoration:none;">↗ {l["label"]}</a>' for l in links)
    st.markdown(f'<div class="chips">{links_html}</div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
#  Sidebar                                                                      #
# --------------------------------------------------------------------------- #
st.sidebar.markdown("## 🧭 Zone Screener")
import zdata  # for the universe symbol list

symbol = st.sidebar.text_input("Symbol", value="RELIANCE.NS",
                               help="Any Yahoo symbol. Use ^NSEI for index, "
                                    "^NSEBANK for Bank Nifty.")
timeframe = st.sidebar.selectbox("Timeframe", zdata.TIMEFRAMES, index=zdata.TIMEFRAMES.index("2h"))
min_score = st.sidebar.slider("Min density score", 20, 90, 40, step=5)
lookback = st.sidebar.selectbox("Scan look-back", ["All", 24, 12, 6, 3])
lookback_months = None if lookback == "All" else int(lookback)
strict = st.sidebar.toggle("Spec-strict rules", value=False)
recommended = st.sidebar.toggle("Recommended setup (DBD · mid · RR1:3)", value=True)
scan_all = st.sidebar.toggle("Scan ALL NSE futures stocks", value=False,
                             help="Scan the full F&O universe across many timeframes "
                                  "(15m → monthly) in one table.")
univ_tfs = ["2h", "4h"]
eod_filter = True
if scan_all:
    univ_tfs = st.sidebar.multiselect(
        "Timeframes to scan (universe)",
        zdata.TIMEFRAMES,
        default=list(zdata.TIMEFRAMES),
        help="Hold Ctrl/Cmd to add/remove. 15m-8h use intraday bars, 1D/1W/1M use daily bars. "
             "All 11 timeframes scan in ~20s; results cached for 90s.")
    if not univ_tfs:
        univ_tfs = ["2h", "4h"]
    eod_filter = st.sidebar.toggle(
        "Scan only in day-candle band (low−10% … high+10%)", value=True,
        help="Keep only zones whose price lies inside today's daily candle range "
             "stretched by ±10%.")
st.sidebar.markdown("---")
st.sidebar.caption("Live data: Yahoo Finance + TradingView + niftytrader + NSE (keyless). "
                   "News & events: keyless RSS.")
st.sidebar.caption(f"Updated {datetime.datetime.now().strftime('%d-%b %H:%M:%S')} IST")

# --------------------------------------------------------------------------- #
#  Market board (top) + sector indices                                         #
# --------------------------------------------------------------------------- #
render_board()
render_sectors()

# --------------------------------------------------------------------------- #
#  FII/DII + Options OI (row 2)                                                 #
# --------------------------------------------------------------------------- #
r1, r2 = st.columns([1.15, 1.0], gap="small")
with r1:
    with st.container():
        render_fiidii()
with r2:
    with st.container():
        render_options(symbol)

st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
#  NEWS + ZONE SCREENER (bottom)                                                #
# --------------------------------------------------------------------------- #
c1, c2 = st.columns([1.15, 1.0], gap="small")

with c1:
    st.markdown("## 📰 Live News <span class='tagp'>tap title = read full</span>",
                unsafe_allow_html=True)
    ns = load_news()
    if not ns:
        st.info("No headlines reachable right now.")
    for it in ns:
        tags = "".join(f'<span class="chip t">{t}</span>' for t in it["tags"])
        st.markdown(
            f'<div class="news-item"><div class="news-time">{it["published"].strftime("%H:%M")}</div>'
            f'<div class="news-body"><a class="news-title" href="{it["link"]}" target="_blank">'
            f'{it["title"]}</a>'
            f'<div>{tags}<span class="news-src"> · {it["source"]}</span></div></div></div>',
            unsafe_allow_html=True)
        with st.expander("📖 Read full article"):
            body = load_news_body(it["link"]) or it.get("summary") or "Full text not available."
            st.markdown(f'<div class="news-full">{body}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="news-hint">Read on {it["source"]}: '
                        f'<a href="{it["link"]}" target="_blank">open original ↗</a></div>',
                        unsafe_allow_html=True)

with c2:
    st.markdown("## 🎯 Zone Screener")
    if scan_all:
        # Full NSE futures universe zone scan across multiple timeframes
        tf_tuple = tuple(univ_tfs)
        render_universe_zones(tf_tuple, min_score, recommended, strict, eod_filter)
        zones, df, extra = [], None, None
    else:
        try:
            result = load_scan(symbol, timeframe, min_score, strict, lookback_months, recommended)
            zones, df, extra = result
        except Exception as ex:
            st.error(f"Could not scan {symbol}: {ex}")
            zones, df, extra = [], None, None

    last = float(df["close"].iloc[-1]) if df is not None and len(df) else None

    if zones:
        head = f"**Zones: {len(zones)}** · {symbol} · TF {timeframe}"
        if last:
            head += f" · last {last:,.2f}"
        st.markdown(head)
        # link the scanned stock to its live option chain + TradingView chart
        try:
            import options as _o
            import tv as _tv
            _links = _o.deep_links(symbol)
            _lc = "".join(f'<a class="chip" href="{l["url"]}" target="_blank" '
                          f'style="text-decoration:none;">↗ {l["label"]}</a>' for l in _links)
            _tvchip = (f'<a class="chip t" href="{_tv.chart_url(symbol, timeframe)}" '
                       f'target="_blank" style="text-decoration:none;">📈 TradingView '
                       f'chart</a>')
            st.markdown(f'<div class="news-hint" style="margin-top:2px;">Options OI · chart:'
                        f'</div><div class="chips">{_tvchip}{_lc}</div>', unsafe_allow_html=True)
        except Exception:
            pass
        if isinstance(extra, dict) and "roi" in extra:
            roi, rec = extra["roi"], extra["recommended"]
            if roi.get("n_trades"):
                st.success(f"**Recommended ROI** (DBD · mid · RR 1:{rec['targetRR']:.1f}): "
                           f"{roi['n_trades']} trades · win {roi['win_pct']:.0f}% · "
                           f"**{roi['net_roi_pct']:+.2f}%**")
            else:
                st.info("Recommended setup: no trades in this window.")
        active = [z for z in zones if z.state in ("Fresh", "Tested")]
        active.sort(key=lambda z: (-z.densityScore, abs(z.proxVal - last) / z.proxVal))
        show = active[:8] if active else zones[:8]
        import pandas as pd
        import zscan as _zs
        rows = [{"Dir": "D" if z.isDemand else "S", "Pat": z.patternType,
                 "Score": z.densityScore, "Entry": round(z.proxVal, 2),
                 "SL": round(z.slVal, 2), "TP": round(z.tpVal, 2),
                 "State": z.state, "Touches": z.touchCount,
                 "OI": (_zs.oi_bias(symbol, z.isDemand) or "—")} for z in show]
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

        if isinstance(extra, dict) and "win_1.0R_tested" in extra:
            q = extra
            st.markdown(
                f'<div class="chips">'
                f'<span class="chip">MFE(2R) {q.get("avg_mfe_tested", 0):.2f}R</span>'
                f'<span class="chip">@1R {q.get("win_1.0R_tested", 0):.0f}%</span>'
                f'<span class="chip">@2R {q.get("win_2.0R_tested", 0):.0f}%</span>'
                f'<span class="chip">@5R {q.get("win_5.0R_tested", 0):.0f}%</span>'
                f'<span class="chip">tested {q.get("tested_pct", 0):.0f}%</span>'
                f'</div>', unsafe_allow_html=True)
    else:
        st.warning("No VALID zones for this scan.")

# --------------------------------------------------------------------------- #
#  NSE events + footer                                                          #
# --------------------------------------------------------------------------- #
st.markdown("---")
st.markdown("## ⚡ NSE & Futures Events <span class='tagp'>keyless · tap = read</span>",
            unsafe_allow_html=True)
ev = load_events()
if ev:
    for it in ev:
        stamps = "".join(f'<span class="chip">{s}</span>' for s in it["stocks"])
        tick = (f'<span class="chip t">{it["tick"]}</span>' if it["tick"] and not it["stocks"] else "")
        st.markdown(
            f'<div class="news-item"><div class="news-time">{it["published"].strftime("%H:%M")}</div>'
            f'<div class="news-body">{stamps}{tick}'
            f'<div style="margin-top:2px;color:#cfe0ff;font-size:12.5px;">{it["title"]}</div>'
            f'<div class="news-src">{it["source"]}</div></div></div>', unsafe_allow_html=True)
        with st.expander("📖 Read more"):
            bd = load_news_body(it["link"])
            st.markdown(f'<div class="news-full">{bd or "Full text not available."}</div>',
                        unsafe_allow_html=True)
            st.markdown(f'<div class="news-hint">Open original: '
                        f'<a href="{it["link"]}" target="_blank">read ↗</a></div>',
                        unsafe_allow_html=True)
else:
    st.info("No tracked-stock events right now.")

st.markdown("---")
st.caption("MarketHub · Zone Screener + Live Terminal. Quotes: Yahoo/TradingView; flows: "
           "niftytrader/NSE; news & events: keyless RSS. Not investment advice. "
           f"`zone_core v{zone_core_version()}`")
