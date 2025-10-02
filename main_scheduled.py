# file: main_scheduled.py
"""
Scheduled Execution Manager for AI News Agent
Supports cron-like scheduling, timezone handling, and automated daily briefings
"""

import schedule
import time
from datetime import datetime, timedelta
import pytz
import os
import sys
from pathlib import Path
import logging
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
LOG_DIR = Path('logs')
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f'scheduled_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Imports
try:
    from main import NewsAgentWorkflow

    MAIN_AVAILABLE = True
except ImportError:
    logger.error("main.py not found. Please ensure main.py is in the same directory.")
    MAIN_AVAILABLE = False
    sys.exit(1)

# ==================== CONFIGURATION ====================

# Schedule Configuration
SCHEDULE_ENABLED = os.getenv('SCHEDULE_ENABLED', 'true').lower() == 'true'
SCHEDULE_TIME = os.getenv('SCHEDULE_TIME', '08:00')  # HH:MM format (24-hour)
SCHEDULE_TIMEZONE = os.getenv('SCHEDULE_TIMEZONE', 'UTC')  # e.g., 'America/New_York', 'Europe/London'
SCHEDULE_DAYS = os.getenv('SCHEDULE_DAYS', 'monday,tuesday,wednesday,thursday,friday').lower()  # Comma-separated

# Multiple schedule times (comma-separated)
SCHEDULE_TIMES = os.getenv('SCHEDULE_TIMES', SCHEDULE_TIME).split(',')

# Weekend schedule (optional)
WEEKEND_ENABLED = os.getenv('WEEKEND_ENABLED', 'false').lower() == 'true'
WEEKEND_TIME = os.getenv('WEEKEND_TIME', '10:00')

# Execution Configuration
RETRY_ON_FAILURE = os.getenv('RETRY_ON_FAILURE', 'true').lower() == 'true'
RETRY_DELAY_MINUTES = int(os.getenv('RETRY_DELAY_MINUTES', '30'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))

# Profile rotation (different profiles on different days)
PROFILE_ROTATION_ENABLED = os.getenv('PROFILE_ROTATION_ENABLED', 'false').lower() == 'true'
PROFILE_ROTATION = {
    'monday': os.getenv('MONDAY_PROFILE', 'balanced'),
    'tuesday': os.getenv('TUESDAY_PROFILE', 'industry'),
    'wednesday': os.getenv('WEDNESDAY_PROFILE', 'academic'),
    'thursday': os.getenv('THURSDAY_PROFILE', 'comprehensive'),
    'friday': os.getenv('FRIDAY_PROFILE', 'balanced'),
    'saturday': os.getenv('SATURDAY_PROFILE', 'quick'),
    'sunday': os.getenv('SUNDAY_PROFILE', 'quick'),
}

# Health check
HEALTH_CHECK_ENABLED = os.getenv('HEALTH_CHECK_ENABLED', 'true').lower() == 'true'
HEALTH_CHECK_INTERVAL_HOURS = int(os.getenv('HEALTH_CHECK_INTERVAL_HOURS', '1'))

# Notification on failure
NOTIFY_ON_FAILURE = os.getenv('NOTIFY_ON_FAILURE', 'true').lower() == 'true'
FAILURE_NOTIFICATION_EMAIL = os.getenv('FAILURE_NOTIFICATION_EMAIL', os.getenv('RECIPIENT_EMAIL', ''))


# ==================== TIMEZONE HANDLING ====================

def get_timezone():
    """Get configured timezone object"""
    try:
        return pytz.timezone(SCHEDULE_TIMEZONE)
    except pytz.exceptions.UnknownTimeZoneError:
        logger.warning(f"Unknown timezone: {SCHEDULE_TIMEZONE}. Using UTC.")
        return pytz.UTC


def get_current_time():
    """Get current time in configured timezone"""
    tz = get_timezone()
    return datetime.now(tz)


def is_scheduled_day(day_name: str) -> bool:
    """Check if today is a scheduled day"""
    scheduled_days = [d.strip() for d in SCHEDULE_DAYS.split(',')]
    return day_name.lower() in scheduled_days


# ==================== EXECUTION TRACKING ====================

class ExecutionTracker:
    """Track execution history and statistics"""

    def __init__(self):
        self.history = []
        self.stats_file = LOG_DIR / 'execution_stats.json'
        self.load_history()

    def load_history(self):
        """Load execution history from file"""
        if self.stats_file.exists():
            try:
                import json
                with open(self.stats_file, 'r') as f:
                    self.history = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load execution history: {e}")
                self.history = []

    def save_history(self):
        """Save execution history to file"""
        try:
            import json
            # Keep only last 30 days
            cutoff = (datetime.now() - timedelta(days=30)).isoformat()
            self.history = [h for h in self.history if h.get('timestamp', '') >= cutoff]

            with open(self.stats_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save execution history: {e}")

    def record_execution(self, results: dict):
        """Record execution results"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'success': results.get('briefing_generated', False),
            'articles_fetched': results.get('articles_fetched', 0),
            'errors': len(results.get('errors', [])),
            'duration_seconds': (
                (results.get('end_time') - results.get('start_time')).total_seconds()
                if results.get('end_time') and results.get('start_time') else 0
            )
        }

        self.history.append(record)
        self.save_history()

    def get_statistics(self):
        """Get execution statistics"""
        if not self.history:
            return None

        total = len(self.history)
        successful = sum(1 for h in self.history if h.get('success'))
        failed = total - successful

        avg_articles = sum(h.get('articles_fetched', 0) for h in self.history) / total
        avg_duration = sum(h.get('duration_seconds', 0) for h in self.history) / total

        return {
            'total_executions': total,
            'successful': successful,
            'failed': failed,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'avg_articles_fetched': avg_articles,
            'avg_duration_seconds': avg_duration
        }


# Initialize tracker
tracker = ExecutionTracker()


# ==================== WORKFLOW EXECUTION ====================

def execute_briefing_workflow(config: Optional[dict] = None, retry_count: int = 0):
    """
    Execute the news briefing workflow

    Args:
        config: Optional configuration dictionary
        retry_count: Current retry attempt number
    """
    logger.info("=" * 80)
    logger.info(f"🚀 Starting scheduled briefing workflow")
    logger.info(f"⏰ Time: {get_current_time().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    if retry_count > 0:
        logger.info(f"🔄 Retry attempt: {retry_count}/{MAX_RETRIES}")
    logger.info("=" * 80)

    try:
        # Determine profile (rotation if enabled)
        profile = config.get('profile') if config else None

        if PROFILE_ROTATION_ENABLED and not profile:
            day_name = get_current_time().strftime('%A').lower()
            profile = PROFILE_ROTATION.get(day_name, 'balanced')
            logger.info(f"📅 Using profile rotation: {day_name} → {profile}")

        # Build configuration
        workflow_config = config or {}
        if profile:
            workflow_config['profile'] = profile

        # Execute workflow
        workflow = NewsAgentWorkflow(workflow_config)
        results = workflow.execute()

        # Track execution
        tracker.record_execution(results)

        # Check if successful
        if results.get('briefing_generated'):
            logger.info("✅ Workflow completed successfully")

            # Log statistics
            stats = tracker.get_statistics()
            if stats:
                logger.info(f"📊 Success rate: {stats['success_rate']:.1f}% "
                            f"({stats['successful']}/{stats['total_executions']} executions)")

            return True
        else:
            logger.warning("⚠️ Workflow completed but no briefing generated")

            # Retry if enabled
            if RETRY_ON_FAILURE and retry_count < MAX_RETRIES:
                logger.info(f"🔄 Retrying in {RETRY_DELAY_MINUTES} minutes...")
                time.sleep(RETRY_DELAY_MINUTES * 60)
                return execute_briefing_workflow(config, retry_count + 1)

            # Send failure notification
            if NOTIFY_ON_FAILURE and FAILURE_NOTIFICATION_EMAIL:
                send_failure_notification(results)

            return False

    except Exception as e:
        logger.error(f"❌ Workflow failed with error: {e}", exc_info=True)

        # Retry if enabled
        if RETRY_ON_FAILURE and retry_count < MAX_RETRIES:
            logger.info(f"🔄 Retrying in {RETRY_DELAY_MINUTES} minutes...")
            time.sleep(RETRY_DELAY_MINUTES * 60)
            return execute_briefing_workflow(config, retry_count + 1)

        # Send failure notification
        if NOTIFY_ON_FAILURE and FAILURE_NOTIFICATION_EMAIL:
            send_failure_notification({'errors': [str(e)]})

        return False


def send_failure_notification(results: dict):
    """Send email notification on failure"""
    try:
        from email_sender import send_email_briefing

        errors = results.get('errors', ['Unknown error'])
        error_message = '\n'.join(f"- {e}" for e in errors)

        subject = f"AI News Agent - Execution Failed - {datetime.now().strftime('%Y-%m-%d')}"
        content = f"""
# AI News Agent - Execution Failure Report

**Time:** {get_current_time().strftime('%Y-%m-%d %H:%M:%S %Z')}

## Errors Encountered:

{error_message}

## Execution Summary:

- Articles Fetched: {results.get('articles_fetched', 0)}
- Briefing Generated: {'Yes' if results.get('briefing_generated') else 'No'}
- Email Sent: {'Yes' if results.get('email_sent') else 'No'}

Please check the logs for more details.

---
*This is an automated notification from AI News Agent*
"""

        send_email_briefing(
            recipient=FAILURE_NOTIFICATION_EMAIL,
            subject=subject,
            content=content
        )

        logger.info(f"📧 Failure notification sent to {FAILURE_NOTIFICATION_EMAIL}")

    except Exception as e:
        logger.error(f"Failed to send failure notification: {e}")


# ==================== HEALTH CHECK ====================

def health_check():
    """Perform health check and log system status"""
    logger.info("🏥 Performing health check...")

    checks = {
        'imports': MAIN_AVAILABLE,
        'schedule_enabled': SCHEDULE_ENABLED,
        'timezone': SCHEDULE_TIMEZONE,
        'current_time': get_current_time().strftime('%Y-%m-%d %H:%M:%S %Z')
    }

    # Check last execution
    stats = tracker.get_statistics()
    if stats:
        checks['last_execution_success_rate'] = f"{stats['success_rate']:.1f}%"
        checks['total_executions'] = stats['total_executions']

    logger.info(f"Health check results: {checks}")

    return all([checks['imports'], checks['schedule_enabled']])


# ==================== SCHEDULE SETUP ====================

def setup_schedule():
    """Setup scheduled jobs"""

    if not SCHEDULE_ENABLED:
        logger.warning("⚠️ Scheduling is disabled. Set SCHEDULE_ENABLED=true to enable.")
        return False

    logger.info("📅 Setting up schedule...")

    # Get scheduled days list
    scheduled_days = [d.strip().lower() for d in SCHEDULE_DAYS.split(',')]

    # Schedule for each specified time
    for schedule_time in SCHEDULE_TIMES:
        schedule_time = schedule_time.strip()

        # Schedule for weekdays
        if any(day in scheduled_days for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']):
            for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
                if day in scheduled_days:
                    getattr(schedule.every(), day).at(schedule_time).do(execute_briefing_workflow)
                    logger.info(f"  ✓ Scheduled for {day.capitalize()} at {schedule_time}")

        # Schedule for weekends if enabled
        if WEEKEND_ENABLED:
            if 'saturday' in scheduled_days:
                schedule.every().saturday.at(WEEKEND_TIME).do(execute_briefing_workflow)
                logger.info(f"  ✓ Scheduled for Saturday at {WEEKEND_TIME}")

            if 'sunday' in scheduled_days:
                schedule.every().sunday.at(WEEKEND_TIME).do(execute_briefing_workflow)
                logger.info(f"  ✓ Scheduled for Sunday at {WEEKEND_TIME}")

    # Setup health check
    if HEALTH_CHECK_ENABLED:
        schedule.every(HEALTH_CHECK_INTERVAL_HOURS).hours.do(health_check)
        logger.info(f"  ✓ Health check scheduled every {HEALTH_CHECK_INTERVAL_HOURS} hour(s)")

    logger.info(f"✅ Schedule setup complete. Timezone: {SCHEDULE_TIMEZONE}")
    logger.info(f"📍 Current time: {get_current_time().strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # Display statistics
    stats = tracker.get_statistics()
    if stats:
        logger.info(f"\n📊 Historical Statistics:")
        logger.info(f"  Total Executions: {stats['total_executions']}")
        logger.info(f"  Success Rate: {stats['success_rate']:.1f}%")
        logger.info(f"  Avg Articles: {stats['avg_articles_fetched']:.0f}")
        logger.info(f"  Avg Duration: {stats['avg_duration_seconds']:.1f}s")

    return True


# ==================== MAIN EXECUTION ====================

def main():
    """Main entry point for scheduled execution"""

    logger.info("=" * 80)
    logger.info("AI NEWS AGENT - SCHEDULED EXECUTION MANAGER")
    logger.info("=" * 80)
    logger.info(f"Start Time: {get_current_time().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info(f"Schedule: {SCHEDULE_DAYS} at {', '.join(SCHEDULE_TIMES)}")
    logger.info(f"Profile Rotation: {'Enabled' if PROFILE_ROTATION_ENABLED else 'Disabled'}")
    logger.info(f"Retry on Failure: {'Enabled' if RETRY_ON_FAILURE else 'Disabled'}")
    logger.info("=" * 80)

    if not MAIN_AVAILABLE:
        logger.error("❌ main.py module not available. Exiting.")
        sys.exit(1)

    # Setup schedule
    if not setup_schedule():
        logger.error("❌ Failed to setup schedule. Exiting.")
        sys.exit(1)

    # Initial health check
    if not health_check():
        logger.warning("⚠️ Health check failed but continuing...")

    # Run scheduler loop
    logger.info("\n🔄 Scheduler running. Press Ctrl+C to stop.\n")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    except KeyboardInterrupt:
        logger.info("\n✋ Scheduler stopped by user")
        logger.info("=" * 80)

        # Final statistics
        stats = tracker.get_statistics()
        if stats:
            logger.info("\n📊 Final Statistics:")
            logger.info(f"  Total Executions: {stats['total_executions']}")
            logger.info(f"  Successful: {stats['successful']}")
            logger.info(f"  Failed: {stats['failed']}")
            logger.info(f"  Success Rate: {stats['success_rate']:.1f}%")

        logger.info("\nGoodbye! 👋")
        sys.exit(0)

    except Exception as e:
        logger.error(f"❌ Scheduler crashed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()