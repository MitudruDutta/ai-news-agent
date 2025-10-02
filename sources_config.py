# file: sources_config.py
"""
Dynamic news sources configuration with real-time API integration.
Supports RSS feeds, web scraping, and API-based news aggregation.
"""

from typing import Dict, List, Any
from datetime import datetime
import os

# ==================== COMPREHENSIVE AI NEWS SOURCES ====================

# Core AI Research & Academic Sources
ACADEMIC_SOURCES = {
    'arxiv': {
        'url': 'http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL+OR+cat:cs.CV&start=0&max_results=50&sortBy=submittedDate&sortOrder=descending',
        'type': 'arxiv_api',
        'weight': 10,
        'category': 'academic'
    },
    'mit_news': {
        'url': 'https://news.mit.edu/topic/artificial-intelligence2-rss',
        'type': 'rss',
        'weight': 9,
        'category': 'academic'
    },
    'stanford_hai': {
        'url': 'https://hai.stanford.edu/news/rss.xml',
        'type': 'rss',
        'weight': 9,
        'category': 'academic'
    },
    'berkeley_ai': {
        'url': 'https://bair.berkeley.edu/blog/feed.xml',
        'type': 'rss',
        'weight': 9,
        'category': 'academic'
    },
    'papers_with_code': {
        'url': 'https://paperswithcode.com/latest',
        'type': 'web_scrape',
        'weight': 8,
        'category': 'academic'
    },
    'distill_pub': {
        'url': 'https://distill.pub/rss.xml',
        'type': 'rss',
        'weight': 8,
        'category': 'academic'
    }
}

# Industry Leaders & Company Blogs
INDUSTRY_SOURCES = {
    'openai_blog': {
        'url': 'https://openai.com/blog/rss.xml',
        'type': 'rss',
        'weight': 10,
        'category': 'industry'
    },
    'deepmind_blog': {
        'url': 'https://deepmind.google/blog/rss.xml',
        'type': 'rss',
        'weight': 10,
        'category': 'industry'
    },
    'anthropic_news': {
        'url': 'https://www.anthropic.com/news',
        'type': 'web_scrape',
        'weight': 10,
        'category': 'industry'
    },
    'meta_ai': {
        'url': 'https://ai.meta.com/blog/rss/',
        'type': 'rss',
        'weight': 9,
        'category': 'industry'
    },
    'google_ai_blog': {
        'url': 'https://blog.google/technology/ai/rss/',
        'type': 'rss',
        'weight': 9,
        'category': 'industry'
    },
    'microsoft_ai': {
        'url': 'https://blogs.microsoft.com/ai/feed/',
        'type': 'rss',
        'weight': 9,
        'category': 'industry'
    },
    'nvidia_blog': {
        'url': 'https://blogs.nvidia.com/feed/',
        'type': 'rss',
        'weight': 8,
        'category': 'industry'
    },
    'cohere_blog': {
        'url': 'https://cohere.com/blog',
        'type': 'web_scrape',
        'weight': 7,
        'category': 'industry'
    },
    'huggingface_blog': {
        'url': 'https://huggingface.co/blog/feed.xml',
        'type': 'rss',
        'weight': 8,
        'category': 'industry'
    }
}

# Real-time API Sources (requires API keys)
API_SOURCES = {
    'news_api': {
        'url': 'https://newsapi.org/v2/everything?q=AI&sortBy=publishedAt&apiKey=',
        'type': 'news_api',
        'weight': 12,  # Higher weight for real-time news
        'category': 'api',
        'api_key_env': 'NEWS_API_KEY'
    },
    'serper_api': {
        'url': 'https://google.serper.dev/news?q=AI&type=news&apiKey=',
        'type': 'serper_api',
        'weight': 12,
        'category': 'api',
        'api_key_env': 'SERPER_API_KEY'
    }
}

# Curated Tech & AI News Outlets
TECH_NEWS_SOURCES = {
    'techcrunch_ai': {
        'url': 'https://techcrunch.com/category/artificial-intelligence/feed/',
        'type': 'rss',
        'weight': 8,
        'category': 'news'
    },
    'venturebeat_ai': {
        'url': 'https://venturebeat.com/category/ai/feed/',
        'type': 'rss',
        'weight': 8,
        'category': 'news'
    },
    'wired_ai': {
        'url': 'https://www.wired.com/feed/tag/ai/latest/rss',
        'type': 'rss',
        'weight': 7,
        'category': 'news'
    },
    'the_verge_ai': {
        'url': 'https://www.theverge.com/ai-artificial-intelligence/rss/index.xml',
        'type': 'rss',
        'weight': 7,
        'category': 'news'
    },
    'mit_tech_review': {
        'url': 'https://www.technologyreview.com/topic/artificial-intelligence/feed/',
        'type': 'rss',
        'weight': 9,
        'category': 'news'
    },
    'ai_news': {
        'url': 'https://artificialintelligence-news.com/feed/',
        'type': 'rss',
        'weight': 7,
        'category': 'news'
    },
    'ars_technica_ai': {
        'url': 'https://feeds.arstechnica.com/arstechnica/technology-lab',
        'type': 'rss',
        'weight': 7,
        'category': 'news'
    }
}

# Community & Aggregators
COMMUNITY_SOURCES = {
    'hacker_news_ai': {
        'url': 'https://hn.algolia.com/api/v1/search_by_date?tags=story&query=AI|artificial%20intelligence|machine%20learning|LLM|GPT',
        'type': 'hn_api',
        'weight': 7,
        'category': 'community'
    },
    'reddit_machinelearning': {
        'url': 'https://www.reddit.com/r/MachineLearning/top.json?limit=25&t=day',
        'type': 'reddit_api',
        'weight': 6,
        'category': 'community'
    },
    'reddit_artificial': {
        'url': 'https://www.reddit.com/r/artificial/top.json?limit=25&t=day',
        'type': 'reddit_api',
        'weight': 6,
        'category': 'community'
    },
    'ai_weekly': {
        'url': 'https://aiweekly.co/feed/',
        'type': 'rss',
        'weight': 7,
        'category': 'community'
    },
    'import_ai': {
        'url': 'https://jack-clark.net/feed/',
        'type': 'rss',
        'weight': 8,
        'category': 'community'
    }
}

# Developer & Tools
DEVELOPER_SOURCES = {
    'github_trending_ai': {
        'url': 'https://github.com/trending/python?since=daily',
        'type': 'web_scrape',
        'weight': 6,
        'category': 'developer'
    },
    'towards_data_science': {
        'url': 'https://towardsdatascience.com/feed',
        'type': 'rss',
        'weight': 6,
        'category': 'developer'
    },
    'kdnuggets': {
        'url': 'https://www.kdnuggets.com/feed',
        'type': 'rss',
        'weight': 6,
        'category': 'developer'
    },
    'ml_mastery': {
        'url': 'https://machinelearningmastery.com/feed/',
        'type': 'rss',
        'weight': 5,
        'category': 'developer'
    }
}

# Combine all sources
ALL_SOURCES = {
    **ACADEMIC_SOURCES,
    **INDUSTRY_SOURCES,
    **TECH_NEWS_SOURCES,
    **COMMUNITY_SOURCES,
    **DEVELOPER_SOURCES
}

# Profile definitions for different use cases
PROFILE_MAP = {
    'academic': {k: v for k, v in ALL_SOURCES.items() if v['category'] == 'academic'},
    'industry': {k: v for k, v in ALL_SOURCES.items() if v['category'] == 'industry'},
    'news': {k: v for k, v in ALL_SOURCES.items() if v['category'] == 'news'},
    'comprehensive': ALL_SOURCES,
    'balanced': {
        **{k: v for k, v in ACADEMIC_SOURCES.items() if v['weight'] >= 8},
        **{k: v for k, v in INDUSTRY_SOURCES.items() if v['weight'] >= 8},
        **{k: v for k, v in TECH_NEWS_SOURCES.items() if v['weight'] >= 7},
        **{k: v for k, v in COMMUNITY_SOURCES.items() if v['weight'] >= 7}
    },
    'quick': {
        'openai_blog': INDUSTRY_SOURCES['openai_blog'],
        'deepmind_blog': INDUSTRY_SOURCES['deepmind_blog'],
        'mit_news': ACADEMIC_SOURCES['mit_news'],
        'techcrunch_ai': TECH_NEWS_SOURCES['techcrunch_ai'],
        'hacker_news_ai': COMMUNITY_SOURCES['hacker_news_ai']
    }
}


def get_sources_by_profile(profile: str = 'balanced') -> Dict[str, Dict[str, Any]]:
    """Get news sources based on profile configuration."""
    profile = profile.lower()

    # Allow environment override
    env_profile = os.getenv('FEED_PROFILE', '').lower()
    if env_profile in PROFILE_MAP:
        profile = env_profile

    sources = PROFILE_MAP.get(profile, PROFILE_MAP['balanced'])

    # Add custom sources from environment
    custom_sources = os.getenv('CUSTOM_NEWS_SOURCES', '')
    if custom_sources:
        for idx, url in enumerate(custom_sources.split(',')):
            url = url.strip()
            if url:
                sources[f'custom_{idx}'] = {
                    'url': url,
                    'type': 'rss',
                    'weight': 5,
                    'category': 'custom'
                }

    return sources


def get_source_urls(profile: str = 'balanced', source_type: str = None) -> List[str]:
    """Extract just the URLs from sources, optionally filtered by type."""
    sources = get_sources_by_profile(profile)

    if source_type:
        return [s['url'] for s in sources.values() if s['type'] == source_type]

    return [s['url'] for s in sources.values()]


# API Configuration for external services
API_CONFIGS = {
    'newsapi': {
        'enabled': bool(os.getenv('NEWSAPI_KEY')),
        'api_key': os.getenv('NEWSAPI_KEY', ''),
        'endpoint': 'https://newsapi.org/v2/everything',
        'query': 'artificial intelligence OR machine learning OR deep learning OR LLM OR GPT',
        'sort_by': 'publishedAt'
    },
    'serpapi': {
        'enabled': bool(os.getenv('SERPAPI_KEY')),
        'api_key': os.getenv('SERPAPI_KEY', ''),
        'endpoint': 'https://serpapi.com/search',
        'engine': 'google_news',
        'query': 'AI news OR artificial intelligence news'
    },
    'bing_news': {
        'enabled': bool(os.getenv('BING_NEWS_KEY')),
        'api_key': os.getenv('BING_NEWS_KEY', ''),
        'endpoint': 'https://api.bing.microsoft.com/v7.0/news/search',
        'query': 'artificial intelligence'
    }
}

# Real-time search configuration
REALTIME_SEARCH_CONFIG = {
    'enabled': os.getenv('ENABLE_REALTIME_SEARCH', 'true').lower() == 'true',
    'search_engines': ['duckduckgo', 'google_news'],  # No API key needed for DDG
    'max_results_per_engine': int(os.getenv('REALTIME_MAX_RESULTS', '10')),
    'search_queries': [
        'latest AI news today',
        'artificial intelligence breakthrough',
        'new AI model release',
        'machine learning research',
        'LLM developments'
    ]
}

# Caching configuration
CACHE_CONFIG = {
    'enabled': os.getenv('ENABLE_CACHING', 'true').lower() == 'true',
    'ttl_seconds': int(os.getenv('CACHE_TTL', '1800')),  # 30 minutes
    'max_cache_size_mb': int(os.getenv('CACHE_MAX_SIZE', '100'))
}

# Content filtering
FILTER_CONFIG = {
    'min_article_length': int(os.getenv('MIN_ARTICLE_LENGTH', '100')),
    'max_articles_per_source': int(os.getenv('MAX_PER_SOURCE', '5')),
    'lookback_hours': int(os.getenv('LOOKBACK_HOURS', '24')),
    'exclude_keywords': os.getenv('EXCLUDE_KEYWORDS', '').split(','),
    'require_keywords': ['AI', 'artificial intelligence', 'machine learning', 'deep learning',
                         'neural network', 'LLM', 'GPT', 'model', 'algorithm'],
    'language': os.getenv('CONTENT_LANGUAGE', 'en')
}


def get_active_sources_count(profile: str = 'balanced') -> int:
    """Get count of active sources for a profile."""
    return len(get_sources_by_profile(profile))


def get_sources_by_category(profile: str = 'balanced') -> Dict[str, List[str]]:
    """Group sources by category."""
    sources = get_sources_by_profile(profile)
    categorized = {}

    for name, config in sources.items():
        category = config['category']
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(name)

    return categorized


if __name__ == '__main__':
    print("=== AI News Sources Configuration ===\n")
    print(f"Total sources available: {len(ALL_SOURCES)}")
    print(f"\nBreakdown by category:")
    print(f"  Academic: {len(ACADEMIC_SOURCES)}")
    print(f"  Industry: {len(INDUSTRY_SOURCES)}")
    print(f"  Tech News: {len(TECH_NEWS_SOURCES)}")
    print(f"  Community: {len(COMMUNITY_SOURCES)}")
    print(f"  Developer: {len(DEVELOPER_SOURCES)}")
    print(f"\nAvailable profiles: {', '.join(PROFILE_MAP.keys())}")
    print(f"\nDefault profile 'balanced' has {get_active_sources_count('balanced')} sources")