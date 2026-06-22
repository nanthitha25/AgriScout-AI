#!/usr/bin/env python3
"""
CLI wrapper to execute the AgriScout AI startup discovery crawler.
"""
import os
import sys
import logging

# Ensure project root is in system path to import backend modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend import scraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def main() -> None:
    """
    Validate environment configurations and launch the crawler.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.critical(
            "GEMINI_API_KEY environment variable is not configured. "
            "Please export your Gemini API key to run this crawler."
        )
        sys.exit(1)
        
    logger.info("Running AgriScout AI Scraper discovery crawler...")
    try:
        scraper.run_discovery_pipeline()
        logger.info("Crawler execution completed successfully.")
    except Exception as e:
        logger.error(f"Error during crawler execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
