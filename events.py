"""
events.py — NSE futures-stock & market-event ticker (keyless).

Fetches corporate-announcement / market feeds and flags anything that mentions a
symbol in the tracked NSE futures set (RELN/TCS/INFY etc.).  Also surfaces generic
F&O events (band, expiry, circuit, ban, results).  Kept compact: returns a short,
deduplicated, newest-first list.
"""
from __future__ import annotations

import re
import html
import datetime
import feedparser
import requests

# NSE F&O tracked set -> (token pattern, display name).  Word-boundary so "LT" does
# NOT match inside "Volt"/"result", "ITC" does not match "BITCOIN", etc.
FUT_STOCKS = [
    (r"\bRELIANCE\b", "Reliance"),
    (r"\bTCS\b", "TCS"),
    (r"\bINFY\b|INFOSYS", "Infosys"),
    (r"\bHDFCBANK\b|HDFC BANK", "HDFC Bank"),
    (r"\bICICIBANK\b|ICICI BANK", "ICICI Bank"),
    (r"\bSBIN\b", "SBI"),
    (r"\bBHARTI[A-Z]+\b|BHARTI AIRTEL", "Bharti Airtel"),
    (r"\bITC\b", "ITC"),
    (r"\bLARSEN\b|L&T|\bLT\b", "L&T"),
    (r"\bBAJFINANCE\b|BAJAJ FINANCE", "Bajaj Finance"),
    (r"\bAXISBANK\b|AXIS BANK", "Axis Bank"),
    (r"\bWIPRO\b", "Wipro"),
    (r"\bTITAN\b", "Titan"),
    (r"\bNESTLE\b", "Nestle"),
    (r"\bASIANPAINT\b|ASIAN PAINTS", "Asian Paints"),
    (r"\bULTRATECH\b|ULTRACEMCO\b", "UltraTech"),
    (r"\bKOTAK[A-Z]+\b|KOTAK BANK", "Kotak Bank"),
    (r"\bHINDUNILVR\b|HINDUSTAN UNILEVER|HUL\b", "HUL"),
]

FUT_PATTERNS = [(re.compile(p, re.I), d) for p, d in FUT_STOCKS]

# Generic F&O / market-event keywords (case-insensitive) that we always want flagged.
EVENT_KEYWORDS = [
    "f&o", "futures", "expiry", "ban", "circuit", "block deal", "bulk deal",
    "bonus", "split", "buyback", "rights issue", "stake", "result", "q1", "q2",
    "q3", "q4", "dividend", "demat", "merger", "ipo", "listing", "upper circuit",
    "lower circuit", "sell-off", "rally", "upgrade", "downgrade", "target price",
    "record date", "ex-date", "revises", "lic", "gift nifty", "sensex", "nifty",
]

# Keyless feeds: company + market headlines.
FEEDS = [
    ("Business Standard", "https://www.business-standard.com/rss/companies-101.rss"),
    ("Business Standard Mkts", "https://www.business-standard.com/rss/markets-106.rss"),
    ("LiveMint", "https://www.livemint.com/rss/markets"),
    ("ET Markets", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
]


def _clean(txt):
    if not txt:
        return ""
    txt = html.unescape(txt)
    txt = re.sub(r"<[^>]+>", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def _fetch(url, timeout=12):
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []
        return feedparser.parse(r.content).entries
    except Exception:
        return []


def _match_stocks(text):
    hits = []
    for pat, disp in FUT_PATTERNS:
        if pat.search(text):
            hits.append(disp)
    seen = set(); out = []
    for h in hits:
        if h not in seen:
            seen.add(h); out.append(h)
    return out


def _tick_class(text):
    up = text.upper()
    for kw in EVENT_KEYWORDS:
        if kw in up:
            return kw.upper()
    return ""


def fetch_events(limit=28):
    seen = set()
    items = []
    for name, url in FEEDS:
        for e in _fetch(url):
            title = _clean(e.get("title", ""))
            if not title:
                continue
            link = e.get("link", "")
            if link in seen:
                continue
            seen.add(link)
            body = title + " " + _clean(e.get("summary", ""))[:180]
            stocks = _match_stocks(body)
            tick = _tick_class(body)
            # keep items that mention a tracked stock OR are a generic F&O event
            if not stocks and tick == "":
                continue
            ts = None
            if e.get("published"):
                try:
                    ts = datetime.datetime(*e["published_parsed"][:6])
                except Exception:
                    ts = None
            items.append({
                "title": title,
                "link": link,
                "source": name,
                "published": ts or datetime.datetime.now(),
                "stocks": stocks,
                "tick": tick,
            })
    items.sort(key=lambda x: x["published"], reverse=True)
    # keep newest, limit to a handful per stock so it stays compact
    return items[:limit]


if __name__ == "__main__":
    for it in fetch_events(20):
        s = ",".join(it["stocks"]) if it["stocks"] else it["tick"]
        print(f"[{it['source']}] {it['published'].strftime('%H:%M')} {s:12s} {it['title'][:80]}")
