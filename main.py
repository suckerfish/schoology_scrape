#!/usr/bin/env python3
"""
Schoology Grade Scraper - Main Entry Point

Supports two modes:
  - Single run (default): Run once and exit
  - Daemon mode (--daemon): Run continuously at scheduled times
"""
import argparse
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from pipeline.orchestrator_v2 import GradePipelineV2
from shared.config import get_config


def setup_logging(daemon_mode: bool = False) -> None:
    """Setup logging configuration"""
    # Ensure logs directory exists
    Path('logs').mkdir(exist_ok=True)

    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    if daemon_mode:
        log_format = '%(asctime)s - DAEMON - %(levelname)s - %(message)s'

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/grade_scraper.log')
        ]
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Schoology Grade Scraper - Monitor grades via API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py              # Run once and exit
  python main.py --daemon     # Run continuously at scheduled times
  python main.py --daemon --times "08:00,20:00"  # Custom schedule
        """
    )
    parser.add_argument(
        '--daemon', '-d',
        action='store_true',
        help='Run in daemon mode (continuously at scheduled times)'
    )
    parser.add_argument(
        '--times', '-t',
        type=str,
        default=None,
        help='Comma-separated run times in 24h format (e.g., "08:00,20:00"). '
             'Overrides SCRAPE_TIMES env var. Only used with --daemon.'
    )
    return parser.parse_args()


def parse_scrape_times(times_str: str) -> list[tuple[int, int]]:
    """
    Parse comma-separated time strings into hour/minute tuples.

    Args:
        times_str: String like "08:00,20:00"

    Returns:
        List of (hour, minute) tuples
    """
    logger = logging.getLogger(__name__)
    times = []

    for time_str in times_str.split(','):
        time_str = time_str.strip()
        try:
            hour, minute = map(int, time_str.split(':'))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                times.append((hour, minute))
            else:
                logger.warning(f"Invalid time value: {time_str}")
        except ValueError as e:
            logger.warning(f"Error parsing time '{time_str}': {e}")

    return times


def get_next_run_time(scrape_times: list[tuple[int, int]]) -> tuple[datetime, int]:
    """
    Calculate next scheduled run time.

    Args:
        scrape_times: List of (hour, minute) tuples

    Returns:
        Tuple of (next_run_datetime, seconds_to_sleep)
    """
    if not scrape_times:
        scrape_times = [(21, 0)]  # Default: 9 PM

    now = datetime.now()
    target_times = []

    for hour, minute in scrape_times:
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        target_times.append(target)

    next_run = min(target_times)
    sleep_seconds = int((next_run - now).total_seconds())

    return next_run, sleep_seconds


def run_pipeline() -> bool:
    """
    Execute the grade scraping pipeline.

    Returns:
        True if pipeline completed successfully
    """
    logger = logging.getLogger(__name__)

    try:
        pipeline = GradePipelineV2()
        success = pipeline.run_full_pipeline(download_path='.')

        if success:
            logger.info("Grade scraping pipeline completed successfully")
        else:
            logger.error("Grade scraping pipeline failed")

        return success

    except Exception as e:
        logger.critical(f"Unexpected error in pipeline: {e}")

        # Try to send critical error notification
        try:
            from pipeline.notifier import GradeNotifier
            notifier = GradeNotifier()
            notifier.send_error_notification(
                "Critical error in grade scraper",
                f"Unexpected error: {str(e)}"
            )
        except Exception:
            pass  # Don't fail if notification fails

        return False


def run_daemon(scrape_times: list[tuple[int, int]]) -> None:
    """
    Run in daemon mode - continuously execute at scheduled times.

    Args:
        scrape_times: List of (hour, minute) tuples for scheduled runs
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Starting daemon mode with schedule: {scrape_times}")

    while True:
        # Run the pipeline
        run_pipeline()

        # Calculate next run time
        next_run, sleep_seconds = get_next_run_time(scrape_times)
        logger.info(f"Next run scheduled for: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Sleeping for {sleep_seconds} seconds ({sleep_seconds/3600:.1f} hours)")

        # Sleep until next scheduled time
        time.sleep(sleep_seconds)


def main() -> None:
    """Main entry point for the grade scraper"""
    args = parse_args()

    setup_logging(daemon_mode=args.daemon)
    logger = logging.getLogger(__name__)

    if args.daemon:
        logger.info("Starting Schoology Grade Scraper (Daemon Mode)")

        # Determine schedule
        if args.times:
            times_str = args.times
        else:
            config = get_config()
            times_str = config.app.scrape_times

        scrape_times = parse_scrape_times(times_str)
        if not scrape_times:
            logger.error("No valid scrape times configured. Exiting.")
            sys.exit(1)

        logger.info(f"Configured schedule: {times_str} -> {scrape_times}")

        try:
            run_daemon(scrape_times)
        except KeyboardInterrupt:
            logger.info("Daemon interrupted by user")
            sys.exit(0)

    else:
        logger.info("Starting Schoology Grade Scraper (Single Run Mode)")

        try:
            success = run_pipeline()
            sys.exit(0 if success else 1)

        except KeyboardInterrupt:
            logger.info("Grade scraper interrupted by user")
            sys.exit(0)


if __name__ == "__main__":
    main()