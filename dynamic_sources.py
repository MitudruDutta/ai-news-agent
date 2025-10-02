"""
Dynamic AI News Source Discovery and Management
Automatically discovers, validates, and rotates news sources based on freshness and quality
"""

import requests
import feedparser
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from pathlib import Path
import json
import hashlib
from collections import defaultdict
from dotenv import load_dotenv
import os

load_dotenv()

# ==================== CONFIGURATION ====================

DYNAMIC_SOURCES_CACHE = Path('.cache/dynamic_sources.json')
DYNAMIC_SOURCES_CACHE.parent.mkdir(parents=True, exist_ok=True)

SOURCE_REFRESH_HOURS = int(os.getenv('SOURCE_REFRESH_HOURS', '24'))
MIN_SOURCE_SCORE = float(os.getenv('MIN_SOURCE_SCORE', '0.6'))
MAX_SOURCES_PER_CATEGORY = int(os.getenv('MAX_SOURCES_PER_CATEGORY', '15'))

# ==================== SOURCE DISCOVERY ====================

# Curated RSS feed directories and discovery endpoints
DISCOVERY_ENDPOINTS = {
    'ai_feeds': [
        'https://raw.githubusercontent.com/kilimchoi/engineering-blogs/master/README.md',
        'https://github.com/topics/artificial-intelligence',
    ],
    'rss_directories': [
        'https://www.feedspot.com/infiniterss.php?_src=feed_directory&followfeedid=5014071',  # AI News
        'https://www.alltop.com/tech/artificial-intelligence',
    ],
    'trending_sources': [
        'https://trends.google.com/trends/trendingsearches/daily/rss?geo=US',
        'https://news.ycombinator.com/rss',
    ]
}

# Known high-quality AI news sources for bootstrapping
SEED_SOURCES = {
    'openai_blog': 'https://openai.com/blog/rss.xml',
    'anthropic_news': 'https://www.anthropic.com/news/rss',
    'deepmind_blog': 'https://deepmind.google/blog/rss.xml',
    'meta_ai': 'https://ai.meta.com/blog/rss/',
    'google_ai': 'https://blog.google/technology/ai/rss/',
    'microsoft_ai': 'https://blogs.microsoft.com/ai/feed/',
    'nvidia_blog': 'https://blogs.nvidia.com/feed/',
    'huggingface': 'https://huggingface.co/blog/feed.xml',
    'techcrunch_ai': 'https://techcrunch.com/category/artificial-intelligence/feed/',
    'mit_news': 'https://news.mit.edu/topic/artificial-intelligence2-rss',
    'stanford_hai': 'https://hai.stanford.edu/news/rss.xml',
    'berkeley_ai': 'https://bair.berkeley.edu/blog/feed.xml',
    'venturebeat_ai': 'https://venturebeat.com/category/ai/feed/',
    'wired_ai': 'https://www.wired.com/feed/tag/ai/latest/rss',
    'mit_tech_review': 'https://www.technologyreview.com/topic/artificial-intelligence/feed/',
    'aiweekly': 'https://aiweekly.co/feed/',
    'importai': 'https://jack-clark.net/feed/',
    'the_verge_ai': 'https://www.theverge.com/ai-artificial-intelligence/rss/index.xml',
    'towardsdatascience': 'https://towardsdatascience.com/feed',
    'kdnuggets': 'https://www.kdnuggets.com/feed',
}

# AI-related keywords for source validation
AI_KEYWORDS = {
    'artificial intelligence', 'machine learning', 'deep learning', 'neural network',
    'llm', 'gpt', 'transformer', 'ai model', 'generative ai', 'chatgpt',
    'computer vision', 'nlp', 'natural language', 'reinforcement learning',
    'ai research', 'ai development', 'ai application', 'ai ethics'
}

# ==================== SOURCE VALIDATION ====================

def validate_rss_feed(url: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """Validate an RSS feed and return metadata if valid."""
    try:
        response = requests.get(url, timeout=timeout, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code != 200:
            return None
        
        feed = feedparser.parse(response.content)
        
        if not feed.entries:
            return None
        
        # Calculate freshness score
        latest_entry = feed.entries[0] if feed.entries else None
        if not latest_entry:
            return None
        
        published = latest_entry.get('published_parsed') or latest_entry.get('updated_parsed')
        if published:
            pub_date = datetime(*published[:6])
            age_days = (datetime.now() - pub_date).days
            freshness_score = max(0, 1 - (age_days / 30))  # Decay over 30 days
        else:
            freshness_score = 0.5
        
        # Calculate AI relevance score
        ai_score = 0
        sample_text = ' '.join([
            feed.feed.get('title', '').lower(),
            feed.feed.get('description', '').lower(),
            ' '.join([e.get('title', '').lower() for e in feed.entries[:5]])
        ])
        
        for keyword in AI_KEYWORDS:
            if keyword in sample_text:
                ai_score += 1
        
        ai_relevance = min(1.0, ai_score / 5)  # Normalize to 0-1
        
        # Calculate overall quality score
        quality_score = (freshness_score * 0.6) + (ai_relevance * 0.4)
        
        if quality_score < MIN_SOURCE_SCORE:
            return None
        
        return {
            'url': url,
            'title': feed.feed.get('title', 'Unknown'),
            'description': feed.feed.get('description', '')[:200],
            'language': feed.feed.get('language', 'en'),
            'entry_count': len(feed.entries),
            'latest_update': pub_date.isoformat() if published else None,
            'quality_score': quality_score,
            'freshness_score': freshness_score,
            'ai_relevance': ai_relevance,
            'validated_at': datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"⚠️ Failed to validate {url}: {e}")
        return None


def discover_feeds_from_opml(opml_url: str) -> List[str]:
    """Extract RSS feed URLs from OPML files."""
    try:
        response = requests.get(opml_url, timeout=10)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        feeds = []
        for outline in root.findall('.//outline[@xmlUrl]'):
            feed_url = outline.get('xmlUrl')
            if feed_url:
                feeds.append(feed_url)
        
        return feeds
    except Exception:
        return []


def discover_feeds_from_aggregator(aggregator_url: str) -> List[str]:
    """Discover feeds from aggregator pages."""
    try:
        response = requests.get(aggregator_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        feeds = []
        # Look for RSS/Atom links
        for link in soup.find_all('link', type=['application/rss+xml', 'application/atom+xml']):
            href = link.get('href')
            if href:
                feeds.append(href)
        
        # Look for feed URLs in anchor tags
        for a in soup.find_all('a', href=True):
            href = a['href']
            if any(pattern in href.lower() for pattern in ['/feed', '/rss', '.xml', 'feed.xml']):
                feeds.append(href)
        
        return list(set(feeds))
    except Exception:
        return []


# ==================== DYNAMIC SOURCE MANAGEMENT ====================

class DynamicSourceManager:
    """Manages dynamic discovery and validation of AI news sources."""
    
    def __init__(self):
        self.sources: Dict[str, Dict[str, Any]] = {}
        self.load_cached_sources()
    
    def load_cached_sources(self):
        """Load previously validated sources from cache."""
        if DYNAMIC_SOURCES_CACHE.exists():
            try:
                with open(DYNAMIC_SOURCES_CACHE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                cached_time = datetime.fromisoformat(data.get('cached_at', '2000-01-01'))
                if datetime.now() - cached_time < timedelta(hours=SOURCE_REFRESH_HOURS):
                    self.sources = data.get('sources', {})
                    print(f"✓ Loaded {len(self.sources)} sources from cache")
                    return
            except Exception as e:
                print(f"⚠️ Failed to load cache: {e}")
        
        # Initialize with seed sources if no cache
        print("🔄 Initializing with seed sources...")
        self.sources = {name: {'url': url, 'quality_score': 0.8, 'type': 'seed'} 
                       for name, url in SEED_SOURCES.items()}
    
    def save_sources_cache(self):
        """Save validated sources to cache."""
        try:
            with open(DYNAMIC_SOURCES_CACHE, 'w', encoding='utf-8') as f:
                json.dump({
                    'cached_at': datetime.now().isoformat(),
                    'sources': self.sources
                }, f, indent=2, ensure_ascii=False)
            print(f"✓ Cached {len(self.sources)} sources")
        except Exception as e:
            print(f"⚠️ Failed to save cache: {e}")
    
    def discover_new_sources(self, max_new: int = 20) -> int:
        """Discover and validate new sources."""
        print("🔍 Discovering new AI news sources...")
        discovered = []
        
        # Method 1: Validate seed sources that aren't cached
        for name, url in SEED_SOURCES.items():
            if name not in self.sources:
                metadata = validate_rss_feed(url)
                if metadata:
                    discovered.append((name, metadata))
        
        # Method 2: Discover from Google News RSS (dynamic queries)
        from urllib.parse import quote_plus
        trending_queries = [
            'artificial intelligence news',
            'machine learning research',
            'AI breakthrough',
            'generative AI developments'
        ]
        
        for query in trending_queries[:2]:  # Limit to avoid rate limits
            gnews_url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
            try:
                feed = feedparser.parse(gnews_url)
                for entry in feed.entries[:5]:
                    source_name = entry.get('source', {}).get('title', 'Unknown')
                    if source_name and source_name not in self.sources:
                        # This is an article, not a feed, so we track the source name
                        source_id = hashlib.md5(source_name.encode()).hexdigest()[:12]
                        if source_id not in self.sources:
                            self.sources[source_id] = {
                                'name': source_name,
                                'url': gnews_url,
                                'type': 'google_news_dynamic',
                                'quality_score': 0.7,
                                'discovered_at': datetime.now().isoformat()
                            }
                            discovered.append((source_id, self.sources[source_id]))
            except Exception:
                pass
        
        print(f"✓ Discovered {len(discovered)} new sources")
        
        # Add discovered sources with limits
        added = 0
        for name, metadata in discovered[:max_new]:
            if name not in self.sources:
                self.sources[name] = metadata
                added += 1
        
        if added > 0:
            self.save_sources_cache()
        
        return added
    
    def refresh_source_scores(self):
        """Re-validate and update scores for existing sources."""
        print("🔄 Refreshing source quality scores...")
        updated = 0
        
        for name, config in list(self.sources.items()):
            if config.get('type') == 'google_news_dynamic':
                continue  # Skip dynamic aggregators
            
            url = config.get('url')
            if url and url.startswith('http'):
                metadata = validate_rss_feed(url)
                if metadata:
                    self.sources[name].update(metadata)
                    updated += 1
                else:
                    # Remove dead sources
                    print(f"⚠️ Removing dead source: {name}")
                    del self.sources[name]
        
        print(f"✓ Updated {updated} sources")
        self.save_sources_cache()
    
    def get_top_sources(self, category: Optional[str] = None, limit: int = 20) -> Dict[str, Dict[str, Any]]:
        """Get top-scoring sources, optionally filtered by category."""
        sorted_sources = sorted(
            self.sources.items(),
            key=lambda x: x[1].get('quality_score', 0),
            reverse=True
        )
        
        result = {}
        for name, config in sorted_sources[:limit]:
            result[name] = {
                'url': config['url'],
                'type': 'rss',
                'weight': int(config.get('quality_score', 0.5) * 10),
                'category': config.get('type', 'dynamic'),
                'quality_score': config.get('quality_score', 0.5)
            }
        
        return result
    
    def get_sources_for_profile(self, profile: str = 'balanced') -> Dict[str, Dict[str, Any]]:
        """Get sources tailored to a specific profile."""
        if profile == 'comprehensive':
            return self.get_top_sources(limit=MAX_SOURCES_PER_CATEGORY)
        elif profile == 'balanced':
            return self.get_top_sources(limit=15)
        elif profile == 'quick':
            return self.get_top_sources(limit=5)
        else:
            return self.get_top_sources(limit=10)


# ==================== PUBLIC API ====================

_manager: Optional[DynamicSourceManager] = None

def get_dynamic_sources(profile: str = 'balanced', force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
    """Get dynamically managed sources with automatic refresh."""
    global _manager
    
    if _manager is None:
        _manager = DynamicSourceManager()
    
    # Check if refresh is needed
    cache_age_hours = 0
    if DYNAMIC_SOURCES_CACHE.exists():
        try:
            with open(DYNAMIC_SOURCES_CACHE, 'r') as f:
                data = json.load(f)
            cached_time = datetime.fromisoformat(data.get('cached_at', '2000-01-01'))
            cache_age_hours = (datetime.now() - cached_time).total_seconds() / 3600
        except Exception:
            pass
    
    # Refresh if cache is old or forced
    if force_refresh or cache_age_hours > SOURCE_REFRESH_HOURS:
        print(f"🔄 Cache age: {cache_age_hours:.1f}h (refresh threshold: {SOURCE_REFRESH_HOURS}h)")
        _manager.discover_new_sources(max_new=10)
        _manager.refresh_source_scores()
    
    return _manager.get_sources_for_profile(profile)


def force_source_refresh():
    """Force immediate refresh of all sources."""
    global _manager
    if _manager is None:
        _manager = DynamicSourceManager()
    
    _manager.discover_new_sources(max_new=20)
    _manager.refresh_source_scores()
    return _manager.sources


if __name__ == '__main__':
    print("=== Dynamic AI News Source Manager ===\n")
    
    # Test source discovery
    manager = DynamicSourceManager()
    print(f"\nCached sources: {len(manager.sources)}")
    
    # Discover new sources
    added = manager.discover_new_sources(max_new=10)
    print(f"Added {added} new sources")
    
    # Get top sources
    top_sources = manager.get_top_sources(limit=10)
    print(f"\nTop 10 sources:")
    for i, (name, config) in enumerate(top_sources.items(), 1):
        score = config.get('quality_score', 0)
        print(f"  {i}. {name}: {config['url'][:60]}... (score: {score:.2f})")
    
    print(f"\n✓ Dynamic source management ready")
