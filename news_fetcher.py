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
import sys

try:
    from sources_config import (
        get_sources_by_profile,
        API_CONFIGS,
        REALTIME_SEARCH_CONFIG,
        CACHE_CONFIG,
        FILTER_CONFIG
    )
except ImportError:
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

# ==================== API KEY LOADING ====================
def get_env_clean(key: str, default: str = "") -> str:
    """Get environment variable and strip quotes if present"""
    value = os.getenv(key, default)
    if value and isinstance(value, str):
        value = value.strip("'\"")
    return value

NEWSAPI_KEY = get_env_clean("NEWSAPI_KEY")
SERPAPI_KEY = get_env_clean("SERPAPI_KEY")

print(f"🔑 NewsAPI Key: {'✓ Found' if NEWSAPI_KEY else '❌ Missing'}")
print(f"🔑 SerpAPI Key: {'✓ Found' if SERPAPI_KEY else '❌ Missing'}")

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

# ==================== NEWS API INTEGRATION ====================
def fetch_from_newsapi(query: str = "artificial intelligence", max_results: int = 20) -> List[Dict[str, Any]]:
    """Fetch articles from NewsAPI"""
    if not NEWSAPI_KEY:
        print("⚠️ NewsAPI key not configured")
        return []

    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': query,
            'apiKey': NEWSAPI_KEY,
            'language': 'en',
            'sortBy': 'publishedAt',
            'pageSize': min(max_results, 100),
            'from': (datetime.now() - timedelta(hours=24)).isoformat()
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        articles = []
        for article in data.get('articles', []):
            articles.append({
                'title': article.get('title', ''),
                'url': article.get('url', ''),
                'source': article.get('source', {}).get('name', 'Unknown'),
                'published': article.get('publishedAt', ''),
                'description': article.get('description', ''),
                'content': article.get('content', ''),
                'author': article.get('author', 'Unknown'),
                'api_source': 'NewsAPI'  # Add metadata for tracking
            })

        print(f"✓ Fetched {len(articles)} articles from NewsAPI")
        return articles
    except requests.exceptions.RequestException as e:
        if "Failed to resolve" in str(e) or "Name or service not known" in str(e):
            print(f"⚠️ NewsAPI unreachable (DNS/network issue). Continuing with other sources...")
        else:
            print(f"❌ Error fetching from NewsAPI: {e}")
        return []
    except Exception as e:
        print(f"❌ Error fetching from NewsAPI: {e}")
        return []

def fetch_from_serpapi(query: str = "artificial intelligence news", max_results: int = 20) -> List[Dict[str, Any]]:
    """Fetch articles from SerpAPI (Google News)"""
    if not SERPAPI_KEY:
        print("⚠️ SerpAPI key not configured")
        return []

    try:
        url = "https://serpapi.com/search"
        params = {
            'q': query,
            'api_key': SERPAPI_KEY,
            'engine': 'google_news',
            'gl': 'us',
            'hl': 'en',
            'num': min(max_results, 100)
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        articles = []
        for item in data.get('news_results', []):
            source_name = item.get('source', {})
            if isinstance(source_name, dict):
                source_name = source_name.get('name', 'Unknown')
            else:
                source_name = str(source_name) if source_name else 'Unknown'
            
            articles.append({
                'title': item.get('title', ''),
                'url': item.get('link', ''),
                'source': source_name,
                'published': item.get('date', ''),
                'description': item.get('snippet', ''),
                'content': item.get('snippet', ''),
                'thumbnail': item.get('thumbnail', ''),
                'api_source': 'SerpAPI'  # Add metadata for tracking
            })

        print(f"✓ Fetched {len(articles)} articles from SerpAPI")
        return articles
    except requests.exceptions.RequestException as e:
        if "Failed to resolve" in str(e) or "Name or service not known" in str(e):
            print(f"⚠️ SerpAPI unreachable (DNS/network issue). Continuing with other sources...")
        else:
            print(f"❌ Error fetching from SerpAPI: {e}")
        return []
    except Exception as e:
        print(f"❌ Error fetching from SerpAPI: {e}")
        return []



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

                hours_ago = (datetime.now() - pub_date).total_seconds() / 3600
                if hours_ago > FILTER_CONFIG.get('lookback_hours', 24):
                    continue

                article = {
                    'title': entry.get('title', 'No Title'),
                    'url': entry.get('link', ''),
                    'source': source_name or entry.get('source', {}).get('title', 'Unknown'),
                    'published': pub_date.isoformat(),
                    'description': entry.get('summary', '')[:500]
                }
                articles.append(article)
            except Exception:
                continue

        return articles
    except Exception as e:
        print(f"❌ Error parsing RSS feed {url}: {e}")
        return []

# FIXED: Now fetches from ALL sources
def fetch_recent_articles(profile: str = 'balanced', max_articles: int = 50) -> List[Dict[str, Any]]:
    """Fetch recent articles from multiple sources including RSS and APIs"""
    all_articles = []

    # 1. FETCH FROM RSS SOURCES (sources_config.py)
    print("📡 Fetching from RSS sources...")
    sources = get_sources_by_profile(profile)
    for source_id, source_config in sources.items():
        cache_key = get_cache_key(source_id)
        cached = load_from_cache(cache_key)

        if cached:
            all_articles.extend(cached)
            print(f"  ✓ {source_id}: {len(cached)} articles (cached)")
            continue

        if source_config['type'] == 'rss':
            articles = parse_rss_feed(source_config['url'], source_id)
            if articles:
                save_to_cache(cache_key, articles)
                all_articles.extend(articles)
                print(f"  ✓ {source_id}: {len(articles)} articles")

        time.sleep(0.5)  # Rate limiting

    # 2. FETCH FROM NEWSAPI
    if NEWSAPI_KEY:
        print("📡 Fetching from NewsAPI...")
        newsapi_articles = fetch_from_newsapi(
            query="artificial intelligence OR machine learning OR AI OR deep learning",
            max_results=30
        )
        all_articles.extend(newsapi_articles)

    # 3. FETCH FROM SERPAPI
    if SERPAPI_KEY:
        print("📡 Fetching from SerpAPI...")
        serpapi_articles = fetch_from_serpapi(
            query="artificial intelligence news OR AI developments",
            max_results=30
        )
        all_articles.extend(serpapi_articles)

    # 5. REMOVE DUPLICATES
    seen_urls = set()
    unique_articles = []
    for article in all_articles:
        if article['url'] and article['url'] not in seen_urls:
            seen_urls.add(article['url'])
            unique_articles.append(article)

    # 6. SORT BY DATE
    try:
        unique_articles.sort(key=lambda x: x.get('published', ''), reverse=True)
    except:
        pass

    # Count articles by source
    newsapi_count = len([a for a in unique_articles if a.get('api_source') == 'NewsAPI'])
    serpapi_count = len([a for a in unique_articles if a.get('api_source') == 'SerpAPI'])
    rss_count = len([a for a in unique_articles if not a.get('api_source')])
    
    print(f"\n✅ Total unique articles fetched: {len(unique_articles)}")
    print(f"   └─ From RSS sources: {rss_count} articles")
    print(f"   └─ From NewsAPI: {newsapi_count} articles")
    print(f"   └─ From SerpAPI: {serpapi_count} articles")

    return unique_articles[:max_articles]

def extract_article_text(url: str) -> str:
    """Extract main text content from article URL"""
    try:
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.content, 'html.parser')

        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        return text[:5000]
    except Exception as e:
        return f"Error extracting text: {str(e)}"