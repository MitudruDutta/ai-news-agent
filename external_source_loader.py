"""
External RSS Source Loader
Loads RSS sources from external files, URLs, or databases
Eliminates hardcoded sources from the codebase
"""

import os
import json
import requests
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse


class ExternalSourceLoader:
    """Load RSS sources from external configuration files or APIs"""

    def __init__(self):
        self.sources = {}

    def load_from_file(self, filepath: str) -> Dict[str, str]:
        """Load sources from a simple text file (source_id: url format)"""
        sources = {}
        filepath = Path(filepath)

        if not filepath.exists():
            print(f"⚠️ Source file not found: {filepath}")
            return sources

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue

                    # Parse "source_id: url" format
                    if ':' in line:
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            source_id = parts[0].strip()
                            url = parts[1].strip()

                            # Validate URL format
                            if url.startswith(('http://', 'https://')):
                                sources[source_id] = url
                            else:
                                print(f"⚠️ Invalid URL on line {line_num}: {url}")

            print(f"✓ Loaded {len(sources)} sources from {filepath.name}")
            return sources
        except Exception as e:
            print(f"❌ Error loading sources from file: {e}")
            return sources

    def load_from_json(self, filepath: str) -> Dict[str, str]:
        """Load sources from a JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Support different JSON formats
            if isinstance(data, dict):
                # Format 1: {"source_id": "url", ...}
                if all(isinstance(v, str) for v in data.values()):
                    print(f"✓ Loaded {len(data)} sources from JSON")
                    return data

                # Format 2: {"sources": {"id": "url", ...}}
                elif 'sources' in data:
                    sources = data['sources']
                    print(f"✓ Loaded {len(sources)} sources from JSON")
                    return sources

            print(f"⚠️ Unsupported JSON format in {filepath}")
            return {}
        except Exception as e:
            print(f"❌ Error loading JSON sources: {e}")
            return {}

    def load_from_url(self, url: str) -> Dict[str, str]:
        """Load sources from a remote URL (JSON or text format)"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Try JSON first
            try:
                data = response.json()
                if isinstance(data, dict):
                    print(f"✓ Loaded {len(data)} sources from remote URL")
                    return data
            except:
                pass

            # Try text format
            sources = {}
            for line in response.text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        sources[parts[0].strip()] = parts[1].strip()

            print(f"✓ Loaded {len(sources)} sources from remote URL")
            return sources
        except Exception as e:
            print(f"❌ Error loading from URL: {e}")
            return {}

    def load_from_github_gist(self, gist_id: str) -> Dict[str, str]:
        """Load sources from a GitHub Gist (for easy cloud updates)"""
        url = f"https://gist.githubusercontent.com/raw/{gist_id}"
        return self.load_from_url(url)

    def load_from_opml(self, filepath_or_url: str) -> Dict[str, str]:
        """Load sources from OPML file (standard RSS subscription format)"""
        import xml.etree.ElementTree as ET
        sources = {}

        try:
            # Check if it's a URL or file
            if filepath_or_url.startswith(('http://', 'https://')):
                response = requests.get(filepath_or_url, timeout=10)
                content = response.content
            else:
                with open(filepath_or_url, 'rb') as f:
                    content = f.read()

            root = ET.fromstring(content)

            # Parse OPML outline elements
            for outline in root.findall('.//outline[@xmlUrl]'):
                title = outline.get('title') or outline.get('text', 'unknown')
                xml_url = outline.get('xmlUrl')

                if xml_url:
                    # Create a clean source ID from title
                    source_id = title.lower().replace(' ', '_').replace('-', '_')
                    source_id = ''.join(c for c in source_id if c.isalnum() or c == '_')
                    sources[source_id] = xml_url

            print(f"✓ Loaded {len(sources)} sources from OPML")
            return sources
        except Exception as e:
            print(f"❌ Error loading OPML: {e}")
            return {}

    def load_all(self, config_priority: List[str] = None) -> Dict[str, str]:
        """Load sources from multiple locations with priority order"""
        all_sources = {}

        if config_priority is None:
            config_priority = [
                'sources.txt',           # Local text file
                'sources.json',          # Local JSON file
                'sources.opml',          # OPML file
                os.getenv('RSS_SOURCES_URL'),  # Remote URL from env
            ]

        for config in config_priority:
            if not config:
                continue

            sources = {}

            # Determine type and load
            if config.startswith(('http://', 'https://')):
                if config.endswith('.opml'):
                    sources = self.load_from_opml(config)
                elif config.endswith('.json'):
                    sources = self.load_from_url(config)
                else:
                    sources = self.load_from_url(config)
            elif Path(config).exists():
                if config.endswith('.json'):
                    sources = self.load_from_json(config)
                elif config.endswith('.opml'):
                    sources = self.load_from_opml(config)
                else:
                    sources = self.load_from_file(config)

            # Merge sources (later configs override earlier ones)
            all_sources.update(sources)

        print(f"\n✅ Total sources loaded: {len(all_sources)}")
        return all_sources


def get_external_sources() -> Dict[str, str]:
    """Main function to get sources from external configuration"""
    loader = ExternalSourceLoader()

    # Priority order: env var > local files
    config_sources = [
        os.getenv('RSS_SOURCES_FILE', 'sources.txt'),
        'sources.json',
        'sources.opml',
        os.getenv('RSS_SOURCES_URL'),  # Remote URL if provided
    ]

    return loader.load_all(config_sources)


if __name__ == '__main__':
    print("=== External RSS Source Loader Test ===\n")
    sources = get_external_sources()

    print(f"\nLoaded Sources ({len(sources)}):")
    for i, (source_id, url) in enumerate(list(sources.items())[:10], 1):
        print(f"  {i}. {source_id}: {url[:60]}...")

    if len(sources) > 10:
        print(f"  ... and {len(sources) - 10} more")
