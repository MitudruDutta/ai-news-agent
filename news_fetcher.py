# file: news_fetcher.py
"""Utility to fetch recent AI-related articles from a collection of RSS feeds.

Functions:
- fetch_recent_articles(rss_feed_urls): returns list of recent article metadata
- extract_article_text(url): downloads and extracts article full text via newspaper3k
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Dict, Any

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


def fetch_recent_articles(rss_feed_urls: List[str]) -> List[Dict[str, Any]]:
    """Fetch articles from RSS feeds published in the last 24 hours.

    Args:
        rss_feed_urls: List of RSS feed URLs.

    Returns:
        List of article dicts (title, link, published (UTC string)).
    """
    articles: List[Dict[str, Any]] = []

    # Define the timezone for UTC
    utc = pytz.UTC

    # Time window
    now = datetime.now(utc)
    twenty_four_hours_ago = now - timedelta(days=1)

    for url in rss_feed_urls:
        try:
            feed = feedparser.parse(url)
        except Exception as e:  # pragma: no cover
            print(f"Failed to parse feed {url}: {e}")
            continue

        for entry in getattr(feed, 'entries', []):
            published_struct = None
            if getattr(entry, 'published_parsed', None):
                published_struct = entry.published_parsed
            elif getattr(entry, 'updated_parsed', None):
                published_struct = entry.updated_parsed

            if not published_struct:
                continue

            try:
                published_time = datetime(*published_struct[:6], tzinfo=utc)
            except Exception:  # pragma: no cover
                continue

            if published_time >= twenty_four_hours_ago:
                articles.append({
                    'title': getattr(entry, 'title', 'No Title'),
                    'link': getattr(entry, 'link', ''),
                    'published': published_time.strftime('%Y-%m-%d %H:%M:%S %Z')
                })

    return articles


if __name__ == '__main__':  # Smoke test run
    ai_news_feeds = [
        'https://openai.com/blog/rss.xml',
        'https://deepmind.google/blog/rss.xml',
        'https://www.therundown.ai/rss',
        'https://www.kdnuggets.com/feed',
        'https://www.marktechpost.com/feed/',
        'https://pub.towardsai.net/feed',
        'http://bair.berkeley.edu/blog/feed.xml'
    ]

    recent_articles = fetch_recent_articles(ai_news_feeds)

    if recent_articles:
        print(f"Found {len(recent_articles)} new articles in the last 24 hours:")
        for article in recent_articles:
            print(f"- Title: {article['title']}")
            print(f"  Link: {article['link']}")
            print(f"  Published: {article['published']}\n")
    else:
        print("No new articles found in the last 24 hours.")
