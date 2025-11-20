#!.venv/bin/python
"""
Refactored main.py using the new pipeline architecture
"""
import logging
import sys
from pathlib import Path
from pipeline.orchestrator import GradePipeline
from shared.config import get_config

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('grade_scraper.log')
        ]
    )

def main():
    """Main entry point for the grade scraper"""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Schoology Grade Scraper (API Polling Mode)")
    
    try:
        # Initialize the pipeline
        pipeline = GradePipeline()

        # Run the complete pipeline
        success = pipeline.run_full_pipeline(download_path='.')
        
        if success:
            logger.info("Grade scraping pipeline completed successfully")
            sys.exit(0)
        else:
            logger.error("Grade scraping pipeline failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Grade scraper interrupted by user")
        sys.exit(0)
        
    except Exception as e:
        logger.critical(f"Unexpected error in main: {e}")
        
        # Try to send critical error notification
        try:
            from pipeline.notifier import GradeNotifier
            notifier = GradeNotifier()
            notifier.send_error_notification(
                "Critical error in grade scraper main",
                f"Unexpected error: {str(e)}"
            )
        except:
            pass  # Don't fail if notification fails
        
        sys.exit(1)

if __name__ == "__main__":
    main()