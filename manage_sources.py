"""
Source Management Utility
Manage, refresh, and inspect AI news sources
"""

import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def show_sources():
    """Display current sources and their status."""
    from sources_config import get_sources_by_profile
    from dynamic_sources import DynamicSourceManager
    
    print("\n" + "="*80)
    print("AI NEWS SOURCES STATUS")
    print("="*80)
    
    manager = DynamicSourceManager()
    
    print(f"\n📊 Total Managed Sources: {len(manager.sources)}")
    print(f"📅 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Show sources by quality
    sorted_sources = sorted(
        manager.sources.items(),
        key=lambda x: x[1].get('quality_score', 0),
        reverse=True
    )
    
    print(f"\n🏆 Top 10 Sources by Quality:")
    print("-" * 80)
    for i, (name, config) in enumerate(sorted_sources[:10], 1):
        score = config.get('quality_score', 0)
        url = config.get('url', 'N/A')
        source_type = config.get('type', 'unknown')
        print(f"{i:2}. [{score:.2f}] {name:30} ({source_type})")
        print(f"    {url[:70]}...")
    
    # Show profile statistics
    print(f"\n📋 Sources by Profile:")
    print("-" * 80)
    for profile in ['quick', 'balanced', 'comprehensive']:
        sources = get_sources_by_profile(profile)
        print(f"  {profile:15}: {len(sources):3} sources")
    
    print("\n" + "="*80)


def refresh_sources(force=False):
    """Refresh source list and validate all sources."""
    from dynamic_sources import DynamicSourceManager
    
    print("\n" + "="*80)
    print("REFRESHING AI NEWS SOURCES")
    print("="*80 + "\n")
    
    manager = DynamicSourceManager()
    
    print(f"📊 Current sources: {len(manager.sources)}")
    
    # Discover new sources
    print("\n🔍 Discovering new sources...")
    added = manager.discover_new_sources(max_new=20)
    print(f"✓ Added {added} new sources")
    
    # Refresh quality scores
    print("\n🔄 Refreshing quality scores...")
    manager.refresh_source_scores()
    
    print(f"\n✅ Refresh complete!")
    print(f"📊 Total sources: {len(manager.sources)}")
    print("="*80 + "\n")


def test_source(url: str):
    """Test a specific RSS feed URL."""
    from dynamic_sources import validate_rss_feed
    
    print(f"\n🔍 Testing source: {url}")
    print("-" * 80)
    
    metadata = validate_rss_feed(url)
    
    if metadata:
        print("✅ Valid RSS Feed")
        print(f"\n  Title: {metadata.get('title')}")
        print(f"  Description: {metadata.get('description')}")
        print(f"  Language: {metadata.get('language')}")
        print(f"  Entries: {metadata.get('entry_count')}")
        print(f"  Latest Update: {metadata.get('latest_update')}")
        print(f"\n  📊 Scores:")
        print(f"    Quality: {metadata.get('quality_score', 0):.2f}")
        print(f"    Freshness: {metadata.get('freshness_score', 0):.2f}")
        print(f"    AI Relevance: {metadata.get('ai_relevance', 0):.2f}")
    else:
        print("❌ Invalid or low-quality RSS feed")
    
    print("-" * 80 + "\n")


def clear_cache():
    """Clear the dynamic sources cache."""
    from dynamic_sources import DYNAMIC_SOURCES_CACHE
    
    if DYNAMIC_SOURCES_CACHE.exists():
        DYNAMIC_SOURCES_CACHE.unlink()
        print("✅ Cache cleared successfully")
    else:
        print("ℹ️  No cache file found")


def export_sources(output_file: str = "sources_export.json"):
    """Export current sources to JSON file."""
    from dynamic_sources import DynamicSourceManager
    import json
    
    manager = DynamicSourceManager()
    
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'exported_at': datetime.now().isoformat(),
            'total_sources': len(manager.sources),
            'sources': manager.sources
        }, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Exported {len(manager.sources)} sources to {output_path}")


def main():
    """CLI interface for source management."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="AI News Source Management Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage_sources.py show              # Display current sources
  python manage_sources.py refresh           # Refresh and discover new sources
  python manage_sources.py test URL          # Test a specific RSS feed
  python manage_sources.py clear-cache       # Clear the sources cache
  python manage_sources.py export            # Export sources to JSON
        """
    )
    
    parser.add_argument(
        'command',
        choices=['show', 'refresh', 'test', 'clear-cache', 'export'],
        help='Command to execute'
    )
    
    parser.add_argument(
        'args',
        nargs='*',
        help='Additional arguments for the command'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force operation (skip cache)'
    )
    
    args = parser.parse_args()
    
    try:
        if args.command == 'show':
            show_sources()
        
        elif args.command == 'refresh':
            refresh_sources(force=args.force)
        
        elif args.command == 'test':
            if not args.args:
                print("❌ Error: Please provide a URL to test")
                print("Usage: python manage_sources.py test <URL>")
                sys.exit(1)
            test_source(args.args[0])
        
        elif args.command == 'clear-cache':
            clear_cache()
        
        elif args.command == 'export':
            output_file = args.args[0] if args.args else 'sources_export.json'
            export_sources(output_file)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        # No arguments, show interactive menu
        print("\n" + "="*80)
        print("AI NEWS SOURCE MANAGEMENT")
        print("="*80)
        print("\nAvailable commands:")
        print("  1. show         - Display current sources and status")
        print("  2. refresh      - Refresh and discover new sources")
        print("  3. test         - Test a specific RSS feed URL")
        print("  4. clear-cache  - Clear the sources cache")
        print("  5. export       - Export sources to JSON")
        print("\nFor detailed help: python manage_sources.py --help")
        print("="*80 + "\n")
        
        choice = input("Enter command (or press Enter to show sources): ").strip().lower()
        
        if not choice or choice == '1' or choice == 'show':
            show_sources()
        elif choice == '2' or choice == 'refresh':
            refresh_sources()
        elif choice == '3' or choice == 'test':
            url = input("Enter RSS feed URL to test: ").strip()
            if url:
                test_source(url)
        elif choice == '4' or choice == 'clear-cache':
            clear_cache()
        elif choice == '5' or choice == 'export':
            export_sources()
    else:
        main()
