# file: sources_config.py
"""Centralized RSS feed configuration for AI news & research.

Feed Profiles:
- base: conservative, fewer feeds for fast runs.
- extended: broader set including academic (arXiv), MIT news, and industry sources.

Environment Override:
- FEED_PROFILE=extended|base (default: extended)
- EXTRA_FEEDS (comma separated) appended at runtime if provided.
"""
from __future__ import annotations

BASE_FEEDS = [
    # Core industry / company blogs
    "https://openai.com/blog/rss.xml",
    "https://deepmind.google/blog/rss.xml",
    "https://www.kdnuggets.com/feed",
    "https://venturebeat.com/ai/feed/",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    # General AI commentary / aggregation
    "https://www.marktechpost.com/feed/",
    "https://pub.towardsai.net/feed",
]

EXTENDED_ADDITIONAL = [
    # Academic & Research
    "http://export.arxiv.org/rss/cs.AI",
    "http://export.arxiv.org/rss/cs.LG",
    "http://export.arxiv.org/rss/cs.CL",
    "https://bair.berkeley.edu/blog/feed.xml",
    # MIT & University / Lab feeds
    "https://news.mit.edu/topic/artificial-intelligence2-rss",  # MIT AI topic
    "https://news.mit.edu/rss/topic/machine-learning",          # MIT ML topic
    # (CSAIL site feed can change; leave commented as placeholder)
    # "https://www.csail.mit.edu/rss.xml",
    # Additional reputable sources
    "https://ai.googleblog.com/atom.xml",  # Google AI Blog (Atom)
    "https://blogs.nvidia.com/feed/",      # NVIDIA AI developments
]

EXTENDED_FEEDS = BASE_FEEDS + EXTENDED_ADDITIONAL

PROFILE_MAP = {
    "base": BASE_FEEDS,
    "extended": EXTENDED_FEEDS,
}

__all__ = [
    "BASE_FEEDS",
    "EXTENDED_FEEDS",
    "PROFILE_MAP",
]

