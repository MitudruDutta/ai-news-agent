# file: main.py
"""
Enhanced Main Execution Script for AI News Agent
Supports scheduled execution, dynamic configuration, and comprehensive logging
"""

from datetime import datetime
from pathlib import Path
import os
import sys
import logging
import json
from typing import Optional, Dict, Any
import argparse

# ==================== LOGGING SETUP (UTF-8 SAFE) ====================
LOG_DIR = Path('logs')
LOG_DIR.mkdir(exist_ok=True)

# Detect whether stdout supports the unicode check/cross symbols
def _supports_symbol(char: str) -> bool:
    try:
        enc = sys.stdout.encoding or 'utf-8'
        char.encode(enc)
        return True
    except Exception:
        return False

SUPPORTS_CHECK = _supports_symbol('\u2713')  # ✓
SUPPORTS_CROSS = _supports_symbol('\u2717')  # ✗

CHECK_MARK = '✓' if SUPPORTS_CHECK else 'OK'
CROSS_MARK = '✗' if SUPPORTS_CROSS else 'X'

# Reconfigure stdout to utf-8 if possible (Python 3.7+)
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

class _SymbolSanitizer(logging.Filter):
    """Replace unsupported unicode symbols with ASCII fallbacks for terminals that can't encode them."""
    def filter(self, record: logging.LogRecord) -> bool:
        if not SUPPORTS_CHECK and isinstance(record.msg, str):
            record.msg = record.msg.replace('✓', 'OK')
        if not SUPPORTS_CROSS and isinstance(record.msg, str):
            record.msg = record.msg.replace('✗', 'X')
        return True

# Create logger manually to ensure encoding on file handler
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Avoid duplicate handlers if module reloaded
if not logger.handlers:
    fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler(LOG_DIR / f'ai_news_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8')
    file_handler.setFormatter(fmt)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)
    sanitizer = _SymbolSanitizer()
    file_handler.addFilter(sanitizer)
    stream_handler.addFilter(sanitizer)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

# ==================== IMPORTS WITH ERROR HANDLING ====================
try:
    from agent_crew import run_crew
    from news_fetcher import fetch_recent_articles
    from email_sender import send_email_briefing
    from audio_generator import generate_audio_briefing
    from dotenv import load_dotenv

    load_dotenv()
    IMPORTS_OK = True
except ImportError as e:
    logger.error(f"Import error: {e}")
    # Define safe stubs so type checkers see the names
    def run_crew():
        return ""
    def fetch_recent_articles(*args, **kwargs):
        return []
    def send_email_briefing(*args, **kwargs):
        return False
    def generate_audio_briefing(*args, **kwargs):
        return None
    IMPORTS_OK = False
    sys.exit(1)


class NewsAgentWorkflow:
    """
    Enhanced workflow manager for AI News Agent with comprehensive features
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize workflow with optional configuration

        Args:
            config: Configuration dictionary with workflow parameters
        """
        self.config = config or self._load_default_config()
        self.results = {
            'start_time': None,
            'end_time': None,
            'articles_fetched': 0,
            'briefing_generated': False,
            'audio_generated': False,
            'email_sent': False,
            'errors': []
        }

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration from environment variables"""
        return {
            # Fetching configuration
            'profile': os.getenv('FEED_PROFILE', 'balanced'),
            'max_articles': int(os.getenv('MAX_ARTICLES', '100')),
            'lookback_hours': int(os.getenv('LOOKBACK_HOURS', '24')),
            'enable_realtime_search': os.getenv('ENABLE_REALTIME_SEARCH', 'true').lower() == 'true',

            # Output configuration
            'enable_audio': os.getenv('ENABLE_AUDIO', 'false').lower() == 'true',
            'enable_email': os.getenv('ENABLE_EMAIL', 'true').lower() == 'true',
            'enable_file_export': os.getenv('ENABLE_FILE_EXPORT', 'true').lower() == 'true',

            # Email configuration
            'recipient_email': os.getenv('RECIPIENT_EMAIL') or os.getenv('TEST_RECIPIENT_EMAIL'),
            'email_subject_prefix': os.getenv('EMAIL_SUBJECT_PREFIX', 'AI Intelligence Briefing'),

            # File export configuration
            'export_dir': Path(os.getenv('EXPORT_DIR', 'exports')),
            'export_format': os.getenv('EXPORT_FORMAT', 'markdown'),  # markdown, html, json

            # Execution configuration
            'dry_run': os.getenv('DRY_RUN', 'false').lower() == 'true',
            'verbose': os.getenv('VERBOSE', 'true').lower() == 'true',

            # Error handling
            'continue_on_error': os.getenv('CONTINUE_ON_ERROR', 'true').lower() == 'true',
            'max_retries': int(os.getenv('MAX_RETRIES', '3')),
        }

    def _log_config(self):
        """Log current configuration"""
        logger.info("=" * 80)
        logger.info("AI News Agent - Enhanced Workflow")
        logger.info("=" * 80)
        logger.info(f"Profile: {self.config['profile']}")
        logger.info(f"Max Articles: {self.config['max_articles']}")
        logger.info(f"Lookback Hours: {self.config['lookback_hours']}")
        logger.info(f"Real-time Search: {self.config['enable_realtime_search']}")
        logger.info(f"Audio Generation: {self.config['enable_audio']}")
        logger.info(f"Email Delivery: {self.config['enable_email']}")
        logger.info(f"File Export: {self.config['enable_file_export']}")
        if self.config['dry_run']:
            logger.warning("DRY RUN MODE - No emails will be sent")
        logger.info("=" * 80)

    def fetch_articles(self) -> list:
        """
        Fetch articles from configured sources

        Returns:
            List of article dictionaries
        """
        logger.info("Step 1/5: Fetching articles from sources...")

        try:
            # Set environment variables for fetching
            os.environ['FEED_PROFILE'] = self.config['profile']
            os.environ['FEED_MAX_ARTICLES'] = str(self.config['max_articles'])
            os.environ['FEED_LOOKBACK_HOURS'] = str(self.config['lookback_hours'])
            os.environ['ENABLE_REALTIME_SEARCH'] = 'true' if self.config['enable_realtime_search'] else 'false'

            articles = fetch_recent_articles(
                profile=self.config['profile'],
                max_articles=self.config['max_articles']
            )

            self.results['articles_fetched'] = len(articles)
            logger.info(f"{CHECK_MARK} Successfully fetched {len(articles)} articles")

            return articles

        except Exception as e:
            error_msg = f"Failed to fetch articles: {e}"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)

            if not self.config['continue_on_error']:
                raise

            return []

    def generate_briefing(self, articles: list) -> Optional[str]:
        """
        Generate AI briefing from articles

        Args:
            articles: List of article dictionaries

        Returns:
            Generated briefing text or None
        """
        logger.info("Step 2/5: Generating AI briefing...")

        if not articles:
            logger.warning("No articles to process. Skipping briefing generation.")
            return None

        try:
            briefing = run_crew()

            if briefing and isinstance(briefing, str) and briefing.strip():
                self.results['briefing_generated'] = True
                word_count = len(briefing.split())
                logger.info(f"{CHECK_MARK} Briefing generated successfully ({word_count} words)")
                return briefing
            else:
                logger.warning("Briefing generation returned empty result")
                return None

        except Exception as e:
            error_msg = f"Failed to generate briefing: {e}"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)

            if not self.config['continue_on_error']:
                raise

            return None

    def generate_audio(self, briefing: str) -> Optional[Path]:
        """
        Generate audio version of briefing

        Args:
            briefing: Briefing text

        Returns:
            Path to audio file or None
        """
        if not self.config['enable_audio']:
            logger.info("Step 3/5: Audio generation disabled (skipping)")
            return None

        logger.info("Step 3/5: Generating audio briefing...")

        if not briefing:
            logger.warning("No briefing to convert to audio")
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ai_briefing_{timestamp}.mp3"

            audio_path = generate_audio_briefing(
                text=briefing,
                filename=filename
            )

            if audio_path and Path(audio_path).exists():
                self.results['audio_generated'] = True
                file_size = Path(audio_path).stat().st_size / 1024  # KB
                logger.info(f"{CHECK_MARK} Audio generated successfully ({file_size:.1f} KB)")
                return Path(audio_path)
            else:
                logger.warning("Audio generation failed")
                return None

        except Exception as e:
            error_msg = f"Failed to generate audio: {e}"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)

            if not self.config['continue_on_error']:
                raise

            return None

    def send_email(self, briefing: str) -> bool:
        """
        Send briefing via email

        Args:
            briefing: Briefing text

        Returns:
            True if successful, False otherwise
        """
        if not self.config['enable_email']:
            logger.info("Step 4/5: Email delivery disabled (skipping)")
            return False

        logger.info("Step 4/5: Sending email briefing...")

        if not briefing:
            logger.warning("No briefing to send via email")
            return False

        if self.config['dry_run']:
            logger.info("DRY RUN: Would send email (but skipping)")
            return False

        recipient = self.config.get('recipient_email')
        if not recipient:
            logger.warning("No recipient email configured. Skipping email.")
            return False

        try:
            today_date = datetime.now().strftime("%Y-%m-%d")
            subject = f"{self.config['email_subject_prefix']} - {today_date}"

            success = send_email_briefing(
                briefing_content=briefing,
                recipient_email=recipient,
                subject=subject
            )

            if success:
                self.results['email_sent'] = True
                logger.info(f"{CHECK_MARK} Email sent successfully to {recipient}")
            else:
                error_msg = f"Email sending failed for recipient {recipient}"
                logger.error(error_msg)
                self.results['errors'].append(error_msg)
            return success

        except Exception as e:
            error_msg = f"Failed to send email: {e}"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)

            if not self.config['continue_on_error']:
                raise

            return False

    def export_to_file(self, briefing: str, articles: list) -> Optional[Path]:
        """
        Export briefing to file

        Args:
            briefing: Briefing text
            articles: List of articles

        Returns:
            Path to exported file or None
        """
        if not self.config['enable_file_export']:
            logger.info("Step 5/5: File export disabled (skipping)")
            return None

        logger.info("Step 5/5: Exporting briefing to file...")

        if not briefing:
            logger.warning("No briefing to export")
            return None

        try:
            export_dir = self.config['export_dir']
            export_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_format = self.config['export_format']

            if export_format == 'markdown':
                filename = f"ai_briefing_{timestamp}.md"
                filepath = export_dir / filename

                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(briefing)

            elif export_format == 'html':
                filename = f"ai_briefing_{timestamp}.html"
                filepath = export_dir / filename

                # Convert markdown to HTML (basic)
                html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AI News Briefing - {datetime.now().strftime('%Y-%m-%d')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }}
        h1 {{ color: #2c3e50; }}
        h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        a {{ color: #3498db; }}
    </style>
</head>
<body>
{briefing.replace('\n', '<br>')}
</body>
</html>
"""
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(html_content)

            elif export_format == 'json':
                filename = f"ai_briefing_{timestamp}.json"
                filepath = export_dir / filename

                export_data = {
                    'timestamp': datetime.now().isoformat(),
                    'briefing': briefing,
                    'articles': articles,
                    'metadata': {
                        'profile': self.config['profile'],
                        'article_count': len(articles),
                        'generation_config': {
                            'max_articles': self.config['max_articles'],
                            'lookback_hours': self.config['lookback_hours'],
                            'realtime_search': self.config['enable_realtime_search']
                        }
                    }
                }

                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            else:
                logger.warning(f"Unknown export format: {export_format}")
                return None

            file_size = filepath.stat().st_size / 1024  # KB
            logger.info(f"{CHECK_MARK} Briefing exported successfully to {filepath} ({file_size:.1f} KB)")
            return filepath

        except Exception as e:
            error_msg = f"Failed to export briefing: {e}"
            logger.error(error_msg)
            self.results['errors'].append(error_msg)

            if not self.config['continue_on_error']:
                raise

            return None

    def execute(self) -> Dict[str, Any]:
        """
        Execute complete workflow

        Returns:
            Dictionary with execution results
        """
        self.results['start_time'] = datetime.now().isoformat()
        self._log_config()

        try:
            # Step 1: Fetch articles
            articles = self.fetch_articles()

            if not articles:
                logger.warning("No articles found. Workflow completed with no briefing.")
                self.results['end_time'] = datetime.now().isoformat()
                return self.results

            # Step 2: Generate briefing
            briefing = self.generate_briefing(articles)

            if not briefing:
                logger.warning("No briefing generated. Stopping workflow.")
                self.results['end_time'] = datetime.now().isoformat()
                return self.results

            # Step 3: Generate audio (optional)
            audio_path = self.generate_audio(briefing)
            if audio_path:
                self.results['audio_path'] = str(audio_path)

            # Step 4: Send email (optional)
            self.send_email(briefing)

            # Step 5: Export to file (optional)
            export_path = self.export_to_file(briefing, articles)
            if export_path:
                self.results['export_path'] = str(export_path)

            self.results['end_time'] = datetime.now().isoformat()
            self._log_summary()

            return self.results

        except Exception as e:
            logger.error(f"Workflow failed with error: {e}", exc_info=True)
            self.results['end_time'] = datetime.now().isoformat()
            self.results['errors'].append(str(e))
            return self.results

    def _log_summary(self):
        # Convert stored iso strings back to datetime for duration calculation
        try:
            start_dt = datetime.fromisoformat(self.results['start_time']) if self.results['start_time'] else datetime.now()
            end_dt = datetime.fromisoformat(self.results['end_time']) if self.results.get('end_time') else datetime.now()
            duration = (end_dt - start_dt).total_seconds()
        except Exception:
            duration = 0.0

        logger.info("=" * 80)
        logger.info("EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Articles Fetched: {self.results['articles_fetched']}")
        logger.info(f"Briefing Generated: {CHECK_MARK if self.results['briefing_generated'] else CROSS_MARK}")
        logger.info(f"Audio Generated: {CHECK_MARK if self.results['audio_generated'] else CROSS_MARK}")
        logger.info(f"Email Sent: {CHECK_MARK if self.results['email_sent'] else CROSS_MARK}")

        if self.results['errors']:
            logger.warning(f"Errors Encountered: {len(self.results['errors'])}")
            for error in self.results['errors']:
                logger.warning(f"  - {error}")
        else:
            logger.info("No errors encountered")

        logger.info("=" * 80)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='AI News Agent - Automated news aggregation and briefing'
    )

    parser.add_argument(
        '--profile',
        type=str,
        choices=['academic', 'industry', 'news', 'balanced', 'comprehensive', 'quick'],
        help='Source profile to use'
    )

    parser.add_argument(
        '--max-articles',
        type=int,
        help='Maximum number of articles to fetch'
    )

    parser.add_argument(
        '--no-email',
        action='store_true',
        help='Disable email delivery'
    )

    parser.add_argument(
        '--no-audio',
        action='store_true',
        help='Disable audio generation'
    )

    parser.add_argument(
        '--no-export',
        action='store_true',
        help='Disable file export'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without sending emails'
    )

    parser.add_argument(
        '--export-format',
        type=str,
        choices=['markdown', 'html', 'json'],
        help='Export file format'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    return parser.parse_args()


def main():
    """Main entry point"""

    if not IMPORTS_OK:
        logger.error("Required modules not imported. Please check dependencies.")
        sys.exit(1)

    # Parse command line arguments
    args = parse_arguments()

    # Build configuration from arguments
    config = {}

    if args.profile:
        config['profile'] = args.profile

    if args.max_articles:
        config['max_articles'] = args.max_articles

    if args.no_email:
        config['enable_email'] = False

    if args.no_audio:
        config['enable_audio'] = False

    if args.no_export:
        config['enable_file_export'] = False

    if args.dry_run:
        config['dry_run'] = True

    if args.export_format:
        config['export_format'] = args.export_format

    if args.verbose:
        config['verbose'] = True
        logging.getLogger().setLevel(logging.DEBUG)

    # Create and execute workflow
    workflow = NewsAgentWorkflow(config if config else None)
    results = workflow.execute()

    # Exit with appropriate code
    if results['briefing_generated']:
        logger.info(f"{CHECK_MARK} Workflow completed successfully")
        sys.exit(0)
    else:
        logger.warning(f"{CROSS_MARK} Workflow completed with issues")
        sys.exit(1)


if __name__ == '__main__':
    main()