# file: news_fetcher.py
"""
Enhanced news fetcher with multi-source support, real-time search, and intelligent caching.
Supports RSS, APIs, web scraping, and real-time search engines.
"""

import feedparser
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time
from urllib.parse import urlparse
import hashlib
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import re
import warnings
import sys  # added for stdout encoding detection

try:
    from sources_config import (
        get_sources_by_profile,
        API_CONFIGS,
        REALTIME_SEARCH_CONFIG,
        CACHE_CONFIG,
        FILTER_CONFIG
    )
except ImportError:
    # Fallback configuration
    def get_sources_by_profile(profile='balanced'):
        return {}


    API_CONFIGS = {}
    REALTIME_SEARCH_CONFIG = {'enabled': False}
    CACHE_CONFIG = {'enabled': False, 'ttl_seconds': 1800}
    FILTER_CONFIG = {
        'min_article_length': 100,
        'max_articles_per_source': 5,
        'lookback_hours': 24
    }

# Cache directory
CACHE_DIR = Path('.cache/news')
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_cache_key(source_id: str) -> str:
    """Generate cache key for a source."""
    return hashlib.md5(source_id.encode()).hexdigest()


def load_from_cache(cache_key: str) -> Optional[List[Dict]]:
    """Load cached articles if still valid."""
    if not CACHE_CONFIG.get('enabled', True):
        return None

    cache_file = CACHE_DIR / f"{cache_key}.json"
    if not cache_file.exists():
        return None

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cached_time = datetime.fromisoformat(data.get('timestamp', '2000-01-01'))
        ttl = CACHE_CONFIG.get('ttl_seconds', 1800)

        if datetime.now() - cached_time < timedelta(seconds=ttl):
            return data.get('articles', [])
    except Exception:
        pass

    return None


def save_to_cache(cache_key: str, articles: List[Dict]):
    """Save articles to cache."""
    if not CACHE_CONFIG.get('enabled', True):
        return

    cache_file = CACHE_DIR / f"{cache_key}.json"
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'articles': articles
            }, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def parse_rss_feed(url: str, source_name: str = '') -> List[Dict[str, Any]]:
    """Parse RSS/Atom feed and return articles."""
    try:
        feed = feedparser.parse(url)
        articles = []

        for entry in feed.entries[:FILTER_CONFIG.get('max_articles_per_source', 10)]:
            try:
                published = entry.get('published_parsed') or entry.get('updated_parsed')
                if published:
                    pub_date = datetime(*published[:6])
                else:
                    pub_date = datetime.now()

                # Check if within lookback window
                hours_ago = (datetime.now() - pub_date).total_seconds() / 3600
                if hours_ago > FILTER_CONFIG.get('lookback_hours', 24):
                    continue

                article = {
                    'title': entry.get('title', '').strip(),
                    'link': entry.get('link', '').strip(),
                    'published': pub_date.isoformat(),
                    'summary': entry.get('summary', '').strip()[:500],
                    'source': source_name or urlparse(url).netloc,
                    'source_type': 'rss',
                    'fetched_at': datetime.now().isoformat()
                }

                if article['title'] and article['link']:
                    articles.append(article)
            except Exception:
                continue

        return articles
    except Exception as e:
        print(f"RSS fetch error for {url}: {e}")
        return []


def fetch_arxiv_api(url: str) -> List[Dict[str, Any]]:
    """Fetch papers from arXiv API."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        namespace = {'atom': 'http://www.w3.org/2005/Atom'}

        articles = []
        for entry in root.findall('atom:entry', namespace)[:20]:
            try:
                title_elem = entry.find('atom:title', namespace)
                link_elem = entry.find('atom:id', namespace)
                published_elem = entry.find('atom:published', namespace)
                summary_elem = entry.find('atom:summary', namespace)

                if title_elem is not None and link_elem is not None:
                    pub_date = datetime.now()
                    if published_elem is not None:
                        try:
                            pub_date = datetime.fromisoformat(published_elem.text.replace('Z', '+00:00'))
                        except:
                            pass

                    articles.append({
                        'title': title_elem.text.strip(),
                        'link': link_elem.text.strip(),
                        'published': pub_date.isoformat(),
                        'summary': summary_elem.text.strip()[:500] if summary_elem is not None else '',
                        'source': 'arXiv',
                        'source_type': 'arxiv_api',
                        'fetched_at': datetime.now().isoformat()
                    })
            except Exception:
                continue

        return articles
    except Exception as e:
        print(f"arXiv fetch error: {e}")
        return []


def fetch_hacker_news_api(url: str) -> List[Dict[str, Any]]:
    """Fetch stories from Hacker News API."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        articles = []
        for hit in data.get('hits', [])[:15]:
            try:
                created_at = datetime.fromtimestamp(hit.get('created_at_i', time.time()))

                # Check if within lookback window
                hours_ago = (datetime.now() - created_at).total_seconds() / 3600
                if hours_ago > FILTER_CONFIG.get('lookback_hours', 24):
                    continue

                url = hit.get('url') or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"

                articles.append({
                    'title': hit.get('title', '').strip(),
                    'link': url,
                    'published': created_at.isoformat(),
                    'summary': hit.get('story_text', '')[:500],
                    'source': 'Hacker News',
                    'source_type': 'hn_api',
                    'points': hit.get('points', 0),
                    'fetched_at': datetime.now().isoformat()
                })
            except Exception:
                continue

        return articles
    except Exception as e:
        print(f"HN fetch error: {e}")
        return []


def fetch_reddit_api(url: str) -> List[Dict[str, Any]]:
    """Fetch posts from Reddit JSON API."""
    try:
        headers = {'User-Agent': 'AI-News-Agent/1.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        articles = []
        for post in data.get('data', {}).get('children', [])[:15]:
            try:
                post_data = post.get('data', {})
                created_utc = datetime.fromtimestamp(post_data.get('created_utc', time.time()))

                # Check if within lookback window
                hours_ago = (datetime.now() - created_utc).total_seconds() / 3600
                if hours_ago > FILTER_CONFIG.get('lookback_hours', 24):
                    continue

                articles.append({
                    'title': post_data.get('title', '').strip(),
                    'link': post_data.get('url', '').strip(),
                    'published': created_utc.isoformat(),
                    'summary': post_data.get('selftext', '')[:500],
                    'source': f"Reddit r/{post_data.get('subreddit', 'unknown')}",
                    'source_type': 'reddit_api',
                    'score': post_data.get('score', 0),
                    'fetched_at': datetime.now().isoformat()
                })
            except Exception:
                continue

        return articles
    except Exception as e:
        print(f"Reddit fetch error: {e}")
        return []


def scrape_webpage(url: str, source_name: str = '') -> List[Dict[str, Any]]:
    """Basic web scraping for news articles."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        articles = []

        # Try to find article links (common patterns)
        for link in soup.find_all('a', href=True)[:30]:
            href = link.get('href', '')
            title = link.get_text().strip()

            if len(title) < 20 or len(title) > 200:
                continue

            # Make absolute URL
            if href.startswith('/'):
                parsed = urlparse(url)
                href = f"{parsed.scheme}://{parsed.netloc}{href}"

            if href and title:
                articles.append({
                    'title': title,
                    'link': href,
                    'published': datetime.now().isoformat(),
                    'summary': '',
                    'source': source_name or urlparse(url).netloc,
                    'source_type': 'web_scrape',
                    'fetched_at': datetime.now().isoformat()
                })

            if len(articles) >= FILTER_CONFIG.get('max_articles_per_source', 5):
                break

        return articles
    except Exception as e:
        print(f"Web scrape error for {url}: {e}")
        return []


# Unicode symbol support detection for console prints
try:
    _ENC = sys.stdout.encoding  # type: ignore
except Exception:
    _ENC = 'utf-8'

def _supports(char: str) -> bool:
    try:
        (char).encode(_ENC or 'utf-8')
        return True
    except Exception:
        return False
_CHECK = '✓' if _supports('\u2713') else 'OK'
_CROSS = '✗' if _supports('\u2717') else 'X'


def search_duckduckgo(query: str, max_results: int = 10, retries: int = 3, backoff_base: float = 1.5) -> List[Dict[str, Any]]:
    """Real-time search using DuckDuckGo (ddgs / duckduckgo_search) with backoff.

    Tries the new `ddgs` package first (recommended). Falls back to the legacy
    `duckduckgo_search` if needed. Implements simple exponential backoff for
    transient rate limit (HTTP 202 or 'Ratelimit') responses.

    Args:
        query: search query string
        max_results: maximum number of results to return
        retries: number of retry attempts on rate limiting
        backoff_base: multiplier for exponential backoff seconds

    Returns:
        List of article dictionaries
    """
    articles: List[Dict[str, Any]] = []

    # Attempt to import preferred/new package first
    DDGS_cls = None
    import_error = None
    try:
        from ddgs import DDGS as DDGS_cls  # type: ignore
    except Exception as e_new:
        import_error = e_new
        try:
            from duckduckgo_search import DDGS as DDGS_cls  # type: ignore
        except Exception as e_old:
            import_error = e_old

    if DDGS_cls is None:
        print("DuckDuckGo search unavailable (ddgs/duckduckgo_search not installed)")
        return []

    attempt = 0
    while attempt <= retries:
        attempt += 1
        try:
            with DDGS_cls() as ddgs:
                # Prefer .news if available, else .text
                results_iter = None
                if hasattr(ddgs, 'news'):
                    results_iter = ddgs.news(query, max_results=max_results)
                else:
                    # Fallback to text search
                    results_iter = ddgs.text(query, max_results=max_results)

                results = list(results_iter) if results_iter else []
                for result in results:
                    try:
                        pub_date = result.get('date') or result.get('published')
                        if isinstance(pub_date, str):
                            try:
                                pub_date_dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                            except Exception:
                                pub_date_dt = datetime.now()
                        else:
                            pub_date_dt = datetime.now()
                        articles.append({
                            'title': (result.get('title') or '').strip(),
                            'link': (result.get('url') or result.get('link') or '').strip(),
                            'published': pub_date_dt.isoformat(),
                            'summary': (result.get('body') or result.get('description') or '')[:500],
                            'source': result.get('source', 'DuckDuckGo News'),
                            'source_type': 'realtime_search',
                            'fetched_at': datetime.now().isoformat()
                        })
                    except Exception:
                        continue
            return articles
        except Exception as e:
            err_msg = str(e)
            # Detect rate limit patterns
            if any(token in err_msg for token in ['202 Ratelimit', 'rate limit', 'Too Many Requests']) and attempt <= retries:
                sleep_seconds = round((backoff_base ** (attempt - 1)), 2)
                print(f"DuckDuckGo rate limited (attempt {attempt}/{retries}). Backing off {sleep_seconds}s...")
                time.sleep(sleep_seconds)
                continue
            print(f"DuckDuckGo search error: {e}")
            break
    return articles


def fetch_from_source(source_name: str, source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch articles from a single source based on its type."""
    url = source_config['url']
    source_type = source_config['type']

    # Check cache first
    cache_key = get_cache_key(f"{source_name}_{url}")
    cached = load_from_cache(cache_key)
    if cached:
        return cached

    articles = []

    try:
        if source_type == 'rss':
            articles = parse_rss_feed(url, source_name)
        elif source_type == 'arxiv_api':
            articles = fetch_arxiv_api(url)
        elif source_type == 'hn_api':
            articles = fetch_hacker_news_api(url)
        elif source_type == 'reddit_api':
            articles = fetch_reddit_api(url)
        elif source_type == 'web_scrape':
            articles = scrape_webpage(url, source_name)

        # Save to cache
        if articles:
            save_to_cache(cache_key, articles)

    except Exception as e:
        print(f"Error fetching from {source_name}: {e}")

    return articles


def fetch_realtime_search_results() -> List[Dict[str, Any]]:
    """Fetch real-time search results from configured search engines."""
    if not REALTIME_SEARCH_CONFIG.get('enabled', False):
        return []

    all_articles = []
    queries = REALTIME_SEARCH_CONFIG.get('search_queries', ['latest AI news'])
    max_results = REALTIME_SEARCH_CONFIG.get('max_results_per_engine', 10)

    for query in queries[:3]:  # Limit to first 3 queries
        try:
            articles = search_duckduckgo(query, max_results=max_results)
            all_articles.extend(articles)
            time.sleep(1)  # Rate limiting
        except Exception as e:
            print(f"Real-time search error for '{query}': {e}")

    return all_articles


def deduplicate_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate articles based on URL and title similarity."""
    seen_urls = set()
    seen_titles = set()
    unique_articles = []

    for article in articles:
        url = article.get('link', '').strip().lower()
        title = article.get('title', '').strip().lower()

        # Normalize title for comparison
        title_norm = re.sub(r'[^\w\s]', '', title)

        if url not in seen_urls and title_norm not in seen_titles:
            seen_urls.add(url)
            seen_titles.add(title_norm)
            unique_articles.append(article)

    return unique_articles


def filter_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Apply content filters to articles."""
    filtered = []

    min_length = FILTER_CONFIG.get('min_article_length', 100)
    exclude_keywords = [k.strip().lower() for k in FILTER_CONFIG.get('exclude_keywords', []) if k.strip()]

    for article in articles:
        title = article.get('title', '').lower()
        summary = article.get('summary', '').lower()
        content = f"{title} {summary}"

        # Check minimum length
        if len(title) < 15:
            continue

        # Check exclude keywords
        if any(keyword in content for keyword in exclude_keywords):
            continue

        filtered.append(article)

    return filtered


def sort_articles_by_relevance(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort articles by relevance score (recency + source weight + engagement)."""
    now = datetime.now()

    def calculate_score(article):
        score = 0.0

        # Recency score (0-10 points)
        try:
            pub_date = datetime.fromisoformat(article.get('published', ''))
            hours_ago = (now - pub_date).total_seconds() / 3600
            recency_score = max(0, 10 - (hours_ago / 2.4))  # Decay over 24 hours
            score += recency_score
        except:
            score += 5  # Default middle score

        # Source weight (0-10 points from source config)
        score += article.get('source_weight', 5)

        # Engagement score (0-5 points)
        points = article.get('points', 0) or article.get('score', 0)
        if points > 0:
            score += min(5, points / 100)  # Cap at 5 points

        # Boost academic sources slightly
        if article.get('source_type') in ['arxiv_api', 'academic']:
            score += 2

        return score

    return sorted(articles, key=calculate_score, reverse=True)


def fetch_recent_articles(profile: str = 'balanced', max_articles: int = 100) -> List[Dict[str, Any]]:
    """
    Main function to fetch recent AI news articles from all configured sources.

    Args:
        profile: Source profile to use ('academic', 'industry', 'news', 'balanced', 'comprehensive')
        max_articles: Maximum number of articles to return

    Returns:
        List of article dictionaries sorted by relevance
    """
    print(f"\n🔍 Fetching articles with profile: {profile}")

    all_articles = []
    sources = get_sources_by_profile(profile)

    print(f"📡 Fetching from {len(sources)} sources...")

    # Fetch from all configured sources
    for source_name, source_config in sources.items():
        print(f"  - {source_name} ({source_config['type']})...", end=' ')
        try:
            articles = fetch_from_source(source_name, source_config)
            for article in articles:
                article['source_weight'] = source_config.get('weight', 5)
            all_articles.extend(articles)
            print(f"{_CHECK} {len(articles)} articles")
        except Exception as e:
            print(f"{_CROSS} Error: {e}\n")
        time.sleep(0.5)  # Rate limiting

    # Fetch real-time search results
    if REALTIME_SEARCH_CONFIG.get('enabled', False):
        print("🔎 Fetching real-time search results...")
        realtime_articles = fetch_realtime_search_results()
        all_articles.extend(realtime_articles)
        print(f"  {_CHECK} {len(realtime_articles)} real-time results")

    print(f"\n📊 Processing {len(all_articles)} total articles...")

    # Process articles
    all_articles = deduplicate_articles(all_articles)
    print(f"  - After deduplication: {len(all_articles)}")

    all_articles = filter_articles(all_articles)
    print(f"  - After filtering: {len(all_articles)}")

    all_articles = sort_articles_by_relevance(all_articles)

    # Limit to max_articles
    all_articles = all_articles[:max_articles]

    print(f"✅ Returning top {len(all_articles)} articles\n")

    return all_articles


def extract_article_text(url: str) -> str:
    """Extract main text content from article URL."""
    try:
        from newspaper import Article
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except ImportError:
        # Fallback to basic extraction
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            return text[:5000]  # Limit length
        except Exception:
            return ""
    except Exception:
        return ""


if __name__ == '__main__':
    # Test the fetcher
    print("=== Testing News Fetcher ===\n")
    articles = fetch_recent_articles(profile='balanced', max_articles=50)

    print(f"\n📰 Sample Articles:\n")
    for i, article in enumerate(articles[:10], 1):
        print(f"{i}. {article['title']}")
        print(f"   Source: {article['source']} | Type: {article['source_type']}")
        print(f"   URL: {article['link'][:80]}...")
        print()