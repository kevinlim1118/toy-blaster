#!/usr/bin/env python3
"""
Portfolio Daily Update
======================
Fetches prices, company news, and macro/policy news for your investment portfolio.
Outputs a self-contained HTML report you can open in any browser.

Requirements:
    pip install -r requirements.txt

Usage:
    python portfolio_update.py
"""

import sys
import html
import urllib.parse
from datetime import datetime

try:
    import yfinance as yf
except ImportError:
    sys.exit("Missing dependency: pip install yfinance")

try:
    import feedparser
except ImportError:
    sys.exit("Missing dependency: pip install feedparser")

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")


# ── Portfolio Definition ───────────────────────────────────────────────────────
# Notes on tickers:
#   GC=F       — Gold futures (CME)
#   TIP        — iShares TIPS Bond ETF (proxy for TIPS)
#   LQD        — iShares IG Corporate Bond ETF (proxy for IG bonds)
#   005930.KS  — Samsung Electronics (KRX)
#   000660.KS  — SK Hynix (KRX)
#   UMG.AS     — Universal Music Group (Euronext Amsterdam)

PORTFOLIO = [
    {
        "name":     "Physical Gold",
        "ticker":   "GC=F",
        "keywords": ["gold", "XAU", "bullion", "precious metal"],
    },
    {
        "name":     "TIPS (TIP ETF)",
        "ticker":   "TIP",
        "keywords": ["TIPS", "treasury inflation", "inflation-protected", "real yield"],
    },
    {
        "name":     "IG Corporate Bonds (LQD ETF)",
        "ticker":   "LQD",
        "keywords": ["corporate bond", "investment grade", "credit spread", "LQD"],
    },
    {
        "name":     "Sweetgreen",
        "ticker":   "SG",
        "keywords": ["Sweetgreen"],
    },
    {
        "name":     "Samsung Electronics",
        "ticker":   "005930.KS",
        "keywords": ["Samsung Electronics", "Samsung"],
    },
    {
        "name":     "Baidu",
        "ticker":   "BIDU",
        "keywords": ["Baidu"],
    },
    {
        "name":     "Pinduoduo",
        "ticker":   "PDD",
        "keywords": ["Pinduoduo", "Temu", "PDD"],
    },
    {
        "name":     "Synopsys",
        "ticker":   "SNPS",
        "keywords": ["Synopsys"],
    },
    {
        "name":     "Blue Owl Capital",
        "ticker":   "OWL",
        "keywords": ["Blue Owl"],
    },
    {
        "name":     "Universal Music Group",
        "ticker":   "UMG.AS",
        "keywords": ["Universal Music", "UMG"],
    },
    {
        "name":     "SK Hynix",
        "ticker":   "000660.KS",
        "keywords": ["SK Hynix", "Hynix"],
    },
    {
        "name":     "Trip.com",
        "ticker":   "TCOM",
        "keywords": ["Trip.com", "Ctrip", "TCOM"],
    },
    {
        "name":     "JD.com",
        "ticker":   "JD",
        "keywords": ["JD.com", "JD "],
    },
    {
        "name":     "Alibaba",
        "ticker":   "BABA",
        "keywords": ["Alibaba", "BABA"],
    },
]

# ── Macro News Sources & Keywords ──────────────────────────────────────────────
MACRO_RSS_FEEDS = [
    ("Reuters Business",    "https://feeds.reuters.com/reuters/businessNews"),
    ("MarketWatch Economy", "https://feeds.marketwatch.com/marketwatch/economy-politics/"),
    ("WSJ Markets",         "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),
    ("Seeking Alpha Macro", "https://seekingalpha.com/market_currents.xml"),
]

MACRO_KEYWORDS = [
    "federal reserve", "fed rate", "interest rate", "inflation", "cpi", "pce",
    "treasury yield", "bond yield", "10-year", "2-year", "yield curve",
    "recession", "gdp", "employment", "jobs report", "nonfarm",
    "tariff", "trade war", "sanctions", "export control",
    "china economy", "china gdp", "pboc", "yuan",
    "monetary policy", "fiscal policy", "debt ceiling",
    "ecb", "bank of japan", "boj", "rate cut", "rate hike",
    "semiconductor", "chip", "ai regulation",
]

# ── International ticker routing ──────────────────────────────────────────────
# Yahoo Finance RSS returns 0 results for KRX and Euronext tickers.
# These will use Google News RSS (by company name) as their primary source.
GOOGLE_NEWS_PRIMARY = {"005930.KS", "000660.KS", "UMG.AS"}

# ── ANSI terminal colors (auto-disabled when stdout is piped) ──────────────────
_IS_TTY     = sys.stdout.isatty()
ANSI_GREEN  = "\033[92m" if _IS_TTY else ""
ANSI_RED    = "\033[91m" if _IS_TTY else ""
ANSI_YELLOW = "\033[93m" if _IS_TTY else ""
ANSI_RESET  = "\033[0m"  if _IS_TTY else ""

# ── Currency symbol map ────────────────────────────────────────────────────────
CURRENCY_SYMBOLS = {
    "USD": "$",
    "KRW": "₩",
    "EUR": "€",
    "GBP": "£",
    "HKD": "HK$",
    "CNY": "¥",
    "JPY": "¥",
    "AUD": "A$",
    "CAD": "C$",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def fmt_price(price, currency="USD"):
    sym = CURRENCY_SYMBOLS.get(currency, currency + " ")
    if currency == "KRW":
        return f"{sym}{price:,.0f}"
    return f"{sym}{price:,.2f}"


def fmt_change(chg, pct):
    sign = "+" if chg >= 0 else ""
    return f"{sign}{chg:.2f} ({sign}{pct:.2f}%)"


def color_class(pct):
    if pct > 0.05:
        return "up"
    if pct < -0.05:
        return "down"
    return "flat"


# ── Price Fetching ─────────────────────────────────────────────────────────────

def fetch_price(ticker):
    """
    Returns dict with keys: price, change, pct, volume, low_52w, high_52w, currency
    or {"error": "..."} on failure.
    """
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")         # 5 days gives buffer for weekends/holidays

        if hist.empty:
            return {"error": "No price history returned"}

        # Latest close and previous close for daily change
        closes = hist["Close"].dropna()
        if len(closes) < 1:
            return {"error": "Insufficient price data"}

        price = float(closes.iloc[-1])
        prev  = float(closes.iloc[-2]) if len(closes) >= 2 else price
        change = price - prev
        pct    = (change / prev * 100) if prev else 0.0
        volume = float(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else 0

        # 52-week range
        hist_yr = t.history(period="1y")
        low_52w  = float(hist_yr["Low"].min())  if not hist_yr.empty else None
        high_52w = float(hist_yr["High"].max()) if not hist_yr.empty else None

        # Currency
        try:
            info     = t.fast_info
            currency = getattr(info, "currency", "USD") or "USD"
        except Exception:
            currency = "USD"

        return {
            "price":    price,
            "change":   change,
            "pct":      pct,
            "volume":   volume,
            "low_52w":  low_52w,
            "high_52w": high_52w,
            "currency": currency,
        }

    except Exception as exc:
        return {"error": str(exc)}


# ── News Fetching ──────────────────────────────────────────────────────────────

_RSS_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; portfolio-update/1.0)"}


def _parse_rss(url):
    """Fetch and parse an RSS feed with a 10-second timeout. Returns feedparser result or None."""
    try:
        resp = requests.get(url, timeout=10, headers=_RSS_HEADERS)
        resp.raise_for_status()
        return feedparser.parse(resp.content)
    except requests.exceptions.RequestException:
        return None


def _rss_entry_to_item(entry):
    return {
        "title":     entry.get("title", "").strip(),
        "link":      entry.get("link", "#"),
        "published": entry.get("published", "")[:25],
        "summary":   entry.get("summary", ""),
    }


def fetch_yahoo_rss(ticker, max_items=6):
    """Fetch headline RSS from Yahoo Finance for a given ticker."""
    url  = f"https://finance.yahoo.com/rss/headline?s={ticker}"
    feed = _parse_rss(url)
    if not feed:
        return []
    return [_rss_entry_to_item(e) for e in feed.entries[:max_items]]


def fetch_google_news_rss(company_name, max_items=6):
    """Fetch news from Google News RSS by company name — works for global companies."""
    query = urllib.parse.quote_plus(company_name)
    url   = f"https://news.google.com/rss/search?q={query}&hl=en&gl=US&ceid=US:en"
    feed  = _parse_rss(url)
    if not feed:
        return []
    return [_rss_entry_to_item(e) for e in feed.entries[:max_items]]


def fetch_macro_news(max_items=15):
    """Aggregate macro/policy news from multiple RSS feeds, filtered by keywords."""
    seen   = set()
    result = []

    for source_name, url in MACRO_RSS_FEEDS:
        feed = _parse_rss(url)
        if not feed:
            continue

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            if not title or title in seen:
                continue

            title_lower = title.lower()
            summary_lower = entry.get("summary", "").lower()
            combined = title_lower + " " + summary_lower

            if any(kw in combined for kw in MACRO_KEYWORDS):
                seen.add(title)
                result.append({
                    "source":    source_name,
                    "title":     title,
                    "link":      entry.get("link", "#"),
                    "published": entry.get("published", "")[:25],
                })

    return result[:max_items]


# ── HTML Report Builder ────────────────────────────────────────────────────────

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #0d1117; color: #e6edf3;
  padding: 28px 32px; max-width: 1100px; margin: 0 auto;
  font-size: 14px; line-height: 1.5;
}
h1 { font-size: 1.45rem; font-weight: 700; }
.timestamp { color: #8b949e; font-size: 0.82rem; margin-top: 4px; margin-bottom: 32px; }
h2 {
  font-size: 1rem; color: #58a6ff; font-weight: 600;
  margin: 32px 0 12px;
  border-bottom: 1px solid #21262d; padding-bottom: 6px; letter-spacing: .03em;
}
/* Price table */
table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
th {
  background: #161b22; color: #8b949e; text-align: left;
  padding: 8px 12px; font-weight: 600; border-bottom: 2px solid #21262d;
  white-space: nowrap;
}
td { padding: 9px 12px; border-bottom: 1px solid #161b22; vertical-align: middle; }
tr:hover td { background: #161b22; }
td:first-child { font-weight: 600; }
.up   { color: #3fb950; }
.down { color: #f85149; }
.flat { color: #8b949e; }
.mono { font-family: "SF Mono", "Cascadia Code", monospace; }
/* News */
.news-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
@media (max-width: 720px) { .news-grid { grid-template-columns: 1fr; } }
.news-card {
  background: #161b22; border: 1px solid #21262d; border-radius: 8px;
  padding: 14px 16px;
}
.news-card h3 { font-size: 0.88rem; margin-bottom: 10px; color: #e6edf3; }
.ticker-badge {
  background: #21262d; color: #8b949e; font-size: 0.72rem;
  padding: 1px 6px; border-radius: 4px; font-weight: normal;
  font-family: "SF Mono", monospace;
}
.news-card ul { list-style: none; }
.news-card li {
  padding: 5px 0; border-bottom: 1px solid #21262d;
  font-size: 0.83rem;
}
.news-card li:last-child { border-bottom: none; }
.news-card a { color: #58a6ff; text-decoration: none; }
.news-card a:hover { text-decoration: underline; }
.pub { color: #8b949e; font-size: 0.76rem; display: block; margin-top: 2px; }
/* Macro */
.macro-card {
  background: #0f1f35; border: 1px solid #1f3a5f; border-radius: 8px;
  padding: 16px 18px; margin-bottom: 6px;
}
.macro-card ul { list-style: none; }
.macro-card li {
  padding: 6px 0; border-bottom: 1px solid #1a2d45; font-size: 0.84rem;
}
.macro-card li:last-child { border-bottom: none; }
.macro-card a { color: #79c0ff; text-decoration: none; }
.macro-card a:hover { text-decoration: underline; }
.src-badge {
  background: #1f3a5f; color: #79c0ff; font-size: 0.72rem;
  padding: 1px 6px; border-radius: 4px; margin-right: 6px;
}
.empty { color: #8b949e; font-size: 0.84rem; }
"""

def build_price_table(prices):
    rows = ""
    for asset in PORTFOLIO:
        name   = asset["name"]
        ticker = asset["ticker"]
        d      = prices.get(ticker)

        if not d or "error" in d:
            err_msg = html.escape((d or {}).get("error", "N/A")[:80])
            rows += (
                f"<tr>"
                f"<td>{html.escape(name)}</td>"
                f"<td class='mono'>{html.escape(ticker)}</td>"
                f"<td colspan='4' class='flat'>⚠ {err_msg}</td>"
                f"</tr>"
            )
            continue

        cur = d["currency"]
        cls = color_class(d["pct"])
        lo  = fmt_price(d["low_52w"], cur)  if d["low_52w"]  else "—"
        hi  = fmt_price(d["high_52w"], cur) if d["high_52w"] else "—"
        vol = f'{d["volume"]:,.0f}'          if d["volume"]   else "—"

        rows += (
            f"<tr>"
            f"<td>{html.escape(name)}</td>"
            f"<td class='mono'>{html.escape(ticker)}</td>"
            f"<td class='{cls} mono'>{fmt_price(d['price'], cur)}</td>"
            f"<td class='{cls} mono'>{fmt_change(d['change'], d['pct'])}</td>"
            f"<td class='mono'>{lo} – {hi}</td>"
            f"<td class='mono'>{vol}</td>"
            f"</tr>"
        )

    return f"""
<table>
  <thead>
    <tr>
      <th>Asset</th>
      <th>Ticker</th>
      <th>Price</th>
      <th>Day Change</th>
      <th>52-Week Range</th>
      <th>Volume</th>
    </tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>"""


def build_news_grid(news_by_ticker):
    cards = ""
    for asset in PORTFOLIO:
        name   = asset["name"]
        ticker = asset["ticker"]
        items  = news_by_ticker.get(ticker, [])
        if not items:
            continue

        lis = ""
        for item in items:
            title = html.escape(item["title"])
            link  = html.escape(item["link"])
            pub   = html.escape(item["published"])
            lis += (
                f"<li>"
                f"<a href='{link}' target='_blank' rel='noopener'>{title}</a>"
                f"<span class='pub'>{pub}</span>"
                f"</li>"
            )

        cards += (
            f"<div class='news-card'>"
            f"<h3>{html.escape(name)} "
            f"<span class='ticker-badge'>{html.escape(ticker)}</span></h3>"
            f"<ul>{lis}</ul>"
            f"</div>"
        )

    return f"<div class='news-grid'>{cards}</div>" if cards else "<p class='empty'>No company news fetched.</p>"


def build_macro_section(macro_news):
    if not macro_news:
        return "<p class='empty'>No macro news matched filters.</p>"

    lis = ""
    for item in macro_news:
        src   = html.escape(item["source"])
        title = html.escape(item["title"])
        link  = html.escape(item["link"])
        pub   = html.escape(item["published"])
        lis += (
            f"<li>"
            f"<span class='src-badge'>{src}</span>"
            f"<a href='{link}' target='_blank' rel='noopener'>{title}</a>"
            f"<span class='pub'>{pub}</span>"
            f"</li>"
        )

    return f"<div class='macro-card'><ul>{lis}</ul></div>"


def build_html_report(prices, news_by_ticker, macro_news):
    now_str = datetime.now().strftime("%A, %B %d, %Y — %H:%M")

    price_table   = build_price_table(prices)
    news_grid     = build_news_grid(news_by_ticker)
    macro_section = build_macro_section(macro_news)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Portfolio Update — {now_str}</title>
  <style>{CSS}</style>
</head>
<body>

<h1>Portfolio Daily Update</h1>
<p class="timestamp">Generated: {now_str}</p>

<h2>PRICE SUMMARY</h2>
{price_table}

<h2>MACRO &amp; POLICY NEWS</h2>
{macro_section}

<h2>COMPANY NEWS</h2>
{news_grid}

</body>
</html>"""


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Portfolio Daily Update")
    print(f"  {datetime.now().strftime('%A, %B %d, %Y  %H:%M')}")
    print("=" * 60)

    # 1. Prices
    print("\n[1/3] Fetching prices...")
    prices = {}
    for asset in PORTFOLIO:
        ticker = asset["ticker"]
        name   = asset["name"]
        sys.stdout.write(f"  {name:<35} ")
        sys.stdout.flush()
        d = fetch_price(ticker)
        prices[ticker] = d
        if d and "error" not in d:
            sign    = "+" if d["pct"] >= 0 else ""
            pct_str = f"{sign}{d['pct']:.2f}%"
            color   = ANSI_GREEN if d["pct"] > 0.05 else (ANSI_RED if d["pct"] < -0.05 else ANSI_YELLOW)
            print(f"{fmt_price(d['price'], d['currency']):>14}   {color}{pct_str}{ANSI_RESET}")
        else:
            err = (d or {}).get("error", "unknown error")[:50]
            print(f"  {ANSI_RED}ERROR:{ANSI_RESET} {err}")

    # 2. Company news
    print("\n[2/3] Fetching company news...")
    news_by_ticker = {}
    for asset in PORTFOLIO:
        ticker = asset["ticker"]
        name   = asset["name"]

        if ticker in GOOGLE_NEWS_PRIMARY:
            items        = fetch_google_news_rss(name)
            source_label = "Google News"
        else:
            items        = fetch_yahoo_rss(ticker)
            source_label = "Yahoo RSS"
            if not items:
                items        = fetch_google_news_rss(name)
                source_label = "Google News (fallback)"

        news_by_ticker[ticker] = items
        print(f"  [{ticker:<12}]  {len(items):>2} articles  ({source_label})")

    # 3. Macro news
    print("\n[3/3] Fetching macro & policy news...")
    macro_news = fetch_macro_news(max_items=20)
    # Deduplicate: drop macro articles already covered in company news sections
    company_titles = {
        item["title"].strip().lower()
        for items in news_by_ticker.values()
        for item in items
    }
    macro_news = [m for m in macro_news if m["title"].strip().lower() not in company_titles]
    print(f"  {len(macro_news)} macro articles matched")

    # 4. Generate report
    report_html = build_html_report(prices, news_by_ticker, macro_news)
    filename    = f"portfolio_{datetime.now().strftime('%Y%m%d_%H%M')}.html"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(report_html)

    print(f"\n{'=' * 60}")
    print(f"  Report saved → {filename}")
    print(f"  Open it in a browser to read your daily briefing.")
    print(f"{'=' * 60}\n")

    # Auto-open on Windows
    try:
        import subprocess
        subprocess.Popen(["start", filename], shell=True)
    except Exception:
        pass


if __name__ == "__main__":
    main()
