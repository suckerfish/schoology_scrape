#!/usr/bin/env python3
"""
Timestamp-based scheduler for Schoology grade scraper.
Runs at specific times defined in SCRAPE_TIMES environment variable.
"""
import os
import sys
import time
import logging
import subprocess
from datetime import datetime, timedelta
from typing import List

def setup_logging():
    """Setup logging for the scheduler"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - SCHEDULER - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/scheduler.log', mode='a')
        ]
    )

def parse_scrape_times(times_str: str) -> List[tuple]:
    """
    Parse comma-separated time strings into hour/minute tuples

    Args:
        times_str: String like "08:00,20:00"

    Returns:
        List of (hour, minute) tuples
    """
    times = []
    for time_str in times_str.split(','):
        time_str = time_str.strip()
        try:
            hour, minute = map(int, time_str.split(':'))
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                times.append((hour, minute))
            else:
                raise ValueError(f"Invalid time: {time_str}")
        except ValueError as e:
            logging.error(f"Error parsing time '{time_str}': {e}")
            continue

    return times

def get_next_sleep_duration(scrape_times: List[tuple]) -> int:
    """
    Calculate seconds until next scheduled scrape time

    Args:
        scrape_times: List of (hour, minute) tuples

    Returns:
        Number of seconds to sleep until next run
    """
    if not scrape_times:
        # Fallback to daily at 21:00 if no valid times
        scrape_times = [(21, 0)]

    now = datetime.now()
    target_times = []

    # Convert times to today's timestamps
    for hour, minute in scrape_times:
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If time already passed today, schedule for tomorrow
        if target <= now:
            target += timedelta(days=1)
        target_times.append(target)

    # Get the next upcoming time
    next_run = min(target_times)
    sleep_seconds = int((next_run - now).total_seconds())

    logging.info(f"Next scrape scheduled for: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"Sleeping for: {sleep_seconds} seconds ({sleep_seconds/3600:.1f} hours)")

    return sleep_seconds

def run_scraper() -> bool:
    """
    Execute the main scraper process

    Returns:
        True if scraper completed successfully
    """
    logging.info("Starting grade scraper...")

    try:
        # Run the main scraper
        result = subprocess.run([sys.executable, 'main.py'],
                              capture_output=True,
                              text=True,
                              timeout=1800)  # 30 minute timeout

        # Forward stdout/stderr to scheduler logs
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    logging.info(f"PIPELINE: {line}")

        if result.stderr:
            for line in result.stderr.strip().split('\n'):
                if line.strip():
                    logging.error(f"PIPELINE ERROR: {line}")

        if result.returncode == 0:
            logging.info("Grade scraper completed successfully")
            return True
        else:
            logging.error(f"Grade scraper failed with exit code {result.returncode}")
            return False

    except subprocess.TimeoutExpired:
        logging.error("Grade scraper timed out after 30 minutes")
        return False
    except Exception as e:
        logging.error(f"Error running grade scraper: {e}")
        return False

def main():
    """Main scheduler loop"""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting timestamp-based grade scraper scheduler")

    # Get scrape times from environment
    scrape_times_str = os.getenv('SCRAPE_TIMES', '21:00')
    logger.info(f"Configured scrape times: {scrape_times_str}")

    # Parse scrape times
    scrape_times = parse_scrape_times(scrape_times_str)
    if not scrape_times:
        logger.error("No valid scrape times found, exiting")
        sys.exit(1)

    logger.info(f"Parsed scrape times: {scrape_times}")

    # Main scheduling loop
    try:
        while True:
            # Run the scraper
            success = run_scraper()

            if not success:
                logger.warning("Scraper failed, but continuing with schedule")

            # Calculate next sleep duration
            sleep_seconds = get_next_sleep_duration(scrape_times)

            # Sleep until next scheduled time
            logger.info(f"Sleeping until next scheduled run...")
            time.sleep(sleep_seconds)

    except KeyboardInterrupt:
        logger.info("Scheduler interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unexpected error in scheduler: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()