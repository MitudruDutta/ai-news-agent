# file: news_fetcher.py
"""Utility to fetch recent AI-related articles from a collection of RSS feeds.

Functions:
- fetch_recent_articles(rss_feed_urls, *, max_articles=None, max_per_domain=3, hours=24)
- extract_article_text(url)
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Dict, Any
from urllib.parse import urlparse

# Import guards to give helpful messages if dependencies are missing
try:  # feedparser for RSS parsing
    import feedparser  # type: ignore
except ImportError as e:  # pragma: no cover
    raise ImportError("Missing dependency 'feedparser'. Install with: pip install feedparser") from e

try:  # pytz for timezone aware comparisons
    import pytz  # type: ignore
except ImportError as e:  # pragma: no cover
    raise ImportError("Missing dependency 'pytz'. Install with: pip install pytz") from e

# (newspaper3k imported lazily inside extract_article_text)


def extract_article_text(url: str) -> str:
    """Extract full text from a news article URL using newspaper3k.

    Args:
        url: Article URL.

    Returns:
        Clean article text or empty string if extraction fails or dependency missing.
    """
    try:
        from newspaper import Article, Config  # type: ignore
    except ImportError:
        print("newspaper3k not installed. Skipping full text extraction.")
        return ""

    try:
        user_agent = (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        )
        config = Config()
        config.browser_user_agent = user_agent
        config.request_timeout = 10

        article = Article(url, config=config)
        article.download()
        article.parse()
        return article.text or ""
    except Exception as e:  # pragma: no cover - network variability
        print(f"Error extracting article from {url}: {e}")
        return ""

# --- NEW HELPERS -----------------------------------------------------------

def _normalize_title(t: str) -> str:
    return (t or "").strip().lower()

def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""

# --- ENHANCED FETCH --------------------------------------------------------

def fetch_recent_articles(
    rss_feed_urls: List[str],
    *,
    max_articles: int | None = None,
    max_per_domain: int = 3,
    hours: int = 24,
) -> List[Dict[str, Any]]:
    """Fetch articles from RSS feeds within a recent time window with domain balancing.

    Args:
        rss_feed_urls: List of RSS feed URLs.
        max_articles: Optional cap on total returned articles after balancing.
        max_per_domain: Limit of articles per domain (post-dedup).
        hours: Lookback window (default 24).

    Returns:
        List of article dicts (title, link, published (UTC string)).
    """
    articles_raw: List[Dict[str, Any]] = []
    utc = pytz.UTC
    now = datetime.now(utc)
    window_start = now - timedelta(hours=hours)

    for url in rss_feed_urls:
        try:
            feed = feedparser.parse(url)
        except Exception as e:  # pragma: no cover
            print(f"Failed to parse feed {url}: {e}")
            continue
        for entry in getattr(feed, 'entries', []):
            published_struct = getattr(entry, 'published_parsed', None) or getattr(entry, 'updated_parsed', None)
            if not published_struct:
                continue
            try:
                published_time = datetime(*published_struct[:6], tzinfo=utc)
            except Exception:
                continue
            if published_time < window_start:
                continue
            articles_raw.append({
                'title': getattr(entry, 'title', 'No Title'),
                'link': getattr(entry, 'link', ''),
                'published': published_time.strftime('%Y-%m-%d %H:%M:%S %Z')
            })

    if not articles_raw:
        return []

    # De-duplicate by link then by title
    dedup_by_link: Dict[str, Dict[str, Any]] = {}
    for a in articles_raw:
        link_key = a['link'].strip()
        if link_key and link_key not in dedup_by_link:
            dedup_by_link[link_key] = a
    # Fallback: if link missing, use title hash
    title_based: Dict[str, Dict[str, Any]] = {}
    for a in articles_raw:
        if not a['link']:
            tk = _normalize_title(a['title'])
            if tk and tk not in title_based:
                title_based[tk] = a
    combined = list(dedup_by_link.values()) + list(title_based.values())

    # Sort newest first
    def _parsed_dt(a: Dict[str, Any]):
        try:
            return datetime.strptime(a['published'], '%Y-%m-%d %H:%M:%S %Z')
        except Exception:
            return datetime.min.replace(tzinfo=utc)
    combined.sort(key=_parsed_dt, reverse=True)

    # Domain balancing
    domain_counts: Dict[str, int] = {}
    balanced: List[Dict[str, Any]] = []
    for a in combined:
        dom = _domain(a['link'])
        if dom:
            cnt = domain_counts.get(dom, 0)
            if cnt >= max_per_domain:
                continue
            domain_counts[dom] = cnt + 1
        balanced.append(a)
        if max_articles and len(balanced) >= max_articles:
            break

    return balanced


if __name__ == '__main__':  # Smoke test run
    ai_news_feeds = [
        'https://openai.com/blog/rss.xml',
        'https://deepmind.google/blog/rss.xml',
        'https://www.kdnuggets.com/feed',
        'https://www.marktechpost.com/feed/',
        'https://pub.towardsai.net/feed',
        'http://bair.berkeley.edu/blog/feed.xml'
    ]
    recent_articles = fetch_recent_articles(ai_news_feeds, max_articles=25, max_per_domain=3)
    if recent_articles:
        print(f"Found {len(recent_articles)} balanced articles in the last 24 hours:")
        for article in recent_articles:
            print(f"- [{_domain(article['link'])}] {article['title']}")
    else:
        print("No new articles found in the last 24 hours.")
