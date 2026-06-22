#!/usr/bin/env python3
"""
AI-Powered Agriculture Startup Discovery Tracker

This script:
1. Loads existing tracked startup data from a local Excel file database to prevent duplicates.
2. Fetches recent AgTech news via Google News RSS.
3. Filters out articles that have already been tracked.
4. Uses Google Gemini 2.5 Flash with Structured Outputs to parse new articles and extract startup details.
5. Appends newly discovered startups to the Excel file progressively during execution.
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import List, Set, Optional

import feedparser
import pandas as pd
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.errors import APIError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Constants
DB_FILE = "agtech_startups.xlsx"
RSS_URL = "https://news.google.com/rss/search?q=agriculture+startup+funding+OR+launched+when:7d&hl=en-US&gl=US&ceid=US:en"
HEADERS = [
    'Startup Name', 
    'Startup Website', 
    'Source URL', 
    'Brief Description', 
    'News Summary', 
    'Date Tracked'
]
# Free tier of Gemini API is limited to 5 requests per minute (RPM) for 2.5 Flash.
# A delay of 12.5 seconds between requests ensures we stay comfortably under this limit.
RATE_LIMIT_DELAY = 12.5

# Define the Pydantic schema for Structured Outputs with Gemini
class StartupDiscovery(BaseModel):
    startup_name: str = Field(
        description="Name of the AgTech company identified in the news article, or 'Unknown' if no specific startup is identified."
    )
    startup_website: str = Field(
        description="The official URL/website of the startup if mentioned in the text, or 'Not Mentioned'."
    )
    brief_description: str = Field(
        description="1-2 sentences explaining what the startup does or their core product/technology."
    )
    news_summary: str = Field(
        description="A short summary explaining why they are in the news (e.g., raised funding, launched a new product, opened a new facility)."
    )


def initialize_database(file_path: str = DB_FILE) -> None:
    """
    Check if the database Excel file exists. If it does not, initialize it with the required headers.
    """
    if not os.path.exists(file_path):
        logger.info(f"Database file '{file_path}' not found. Initializing new file.")
        df = pd.DataFrame(columns=HEADERS)
        df.to_excel(file_path, index=False)
        logger.info(f"Initialized database successfully with columns: {HEADERS}")
    else:
        logger.info(f"Database file '{file_path}' already exists.")


def load_existing_urls(file_path: str = DB_FILE) -> Set[str]:
    """
    Load the Excel database and return a set of all URLs in the 'Source URL' column
    to facilitate duplicate checks.
    """
    try:
        df = pd.read_excel(file_path)
        if 'Source URL' in df.columns:
            # Drop empty or NaN values and convert to string set
            existing_urls = set(df['Source URL'].dropna().astype(str).tolist())
            logger.info(f"Loaded {len(existing_urls)} existing URLs from the database.")
            return existing_urls
        else:
            logger.warning("'Source URL' column not found in database. Treating as empty.")
            return set()
    except Exception as e:
        logger.error(f"Error loading existing URLs from database: {e}")
        return set()


def fetch_news_feed(rss_url: str = RSS_URL) -> List[dict]:
    """
    Fetch and parse the Google News RSS feed.
    Returns a list of articles, each represented as a dictionary.
    """
    logger.info(f"Fetching RSS feed from: {rss_url}")
    feed = feedparser.parse(rss_url)
    
    if feed.bozo:
        logger.warning(f"Feed parser reported a bozo error (malformed XML), but will attempt parsing: {feed.bozo_exception}")
        
    entries = feed.entries
    logger.info(f"Successfully retrieved {len(entries)} articles from the RSS feed.")
    
    articles = []
    for entry in entries:
        articles.append({
            'title': getattr(entry, 'title', ''),
            'link': getattr(entry, 'link', ''),
            'summary': getattr(entry, 'summary', ''),
            'published': getattr(entry, 'published', '')
        })
    return articles


def extract_startup_info(client: genai.Client, title: str, summary: str, max_retries: int = 5) -> Optional[StartupDiscovery]:
    """
    Use Google Gemini 2.5 Flash via Structured Outputs to parse article title and summary
    to extract startup info. Returns a StartupDiscovery instance if successful, else None.
    Handles rate limits (429 RESOURCE_EXHAUSTED) using exponential backoff.
    """
    prompt = f"""
You are an expert analyst monitoring AgTech (Agriculture Technology) news.
Your task is to analyze the following news article title and summary to identify if it features a specific agriculture startup company.

If a specific agriculture startup company is identified, extract the details according to the schema.
If the article is not about a specific startup (for example, it is about general farming trends, broad agricultural research, established giant corporations, or policy/governmental updates without focusing on a specific new venture), you MUST set `startup_name` to 'Unknown'.

Title: {title}
Summary/Snippet: {summary}
"""
    delay = 10.0  # Initial retry delay if we hit a 429
    for attempt in range(max_retries):
        try:
            # Call Gemini model with structured output configuration
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=StartupDiscovery,
                    temperature=0.1,  # Keep it deterministic and structured
                ),
            )
            
            # The modern google-genai SDK handles parsing directly when response_schema is provided.
            # It is accessible on response.parsed if Pydantic model is supplied.
            parsed_result = response.parsed
            if parsed_result:
                return parsed_result
                
            # Fallback to response.text parsing if response.parsed is empty
            if response.text:
                return StartupDiscovery.model_validate_json(response.text)
                
            logger.warning("Empty response from Gemini API.")
            return None
            
        except APIError as api_err:
            # Catch rate limit / resource exhausted errors (HTTP status 429)
            if api_err.code == 429:
                logger.warning(
                    f"Rate limit exceeded (429 RESOURCE_EXHAUSTED) on attempt {attempt + 1}/{max_retries}. "
                    f"Retrying in {delay} seconds..."
                )
                time.sleep(delay)
                delay *= 2.0  # Exponential backoff
                continue
            else:
                logger.error(f"Gemini API Error occurred: {api_err}")
                return None
        except Exception as e:
            logger.error(f"Unexpected error extracting startup info: {e}")
            return None
            
    logger.error(f"Failed to extract startup info after {max_retries} attempts due to rate limit/quota issues.")
    return None


def append_single_discovery(file_path: str, row: dict) -> None:
    """
    Safely append a single new discovered startup row to the Excel database.
    Saving progressively prevents data loss in case of script interruption.
    """
    try:
        new_df = pd.DataFrame([row])
        # Reorder to match headers
        new_df = new_df[HEADERS]
        
        # Load current data, append, and save
        if os.path.exists(file_path):
            existing_df = pd.read_excel(file_path)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df
            
        combined_df.to_excel(file_path, index=False)
        logger.info(f"Progressively saved discovery to Excel database: '{row['Startup Name']}'")
    except Exception as e:
        logger.error(f"Failed to progressively append discovery to Excel: {e}")


def main() -> None:
    """
    Main orchestration function to run the tracking pipeline.
    """
    logger.info("Starting AI-Powered Agriculture Startup Discovery Tracker pipeline...")
    
    # 1. Check/Get API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.critical(
            "GEMINI_API_KEY environment variable is not set. "
            "Please configure the environment variable to run this script."
        )
        sys.exit(1)
        
    # Initialize the Gemini GenAI Client
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        logger.critical(f"Failed to initialize Gemini GenAI Client: {e}")
        sys.exit(1)

    # 2. Initialize and Load DB URL list
    initialize_database(DB_FILE)
    existing_urls = load_existing_urls(DB_FILE)

    # 3. Fetch feed articles
    articles = fetch_news_feed(RSS_URL)
    
    # 4. Iterate and filter
    for index, article in enumerate(articles, 1):
        url = article['link']
        title = article['title']
        
        # Deduplication engine
        if url in existing_urls:
            logger.info(f"[{index}/{len(articles)}] Skipping duplicate article: {title}")
            continue
            
        logger.info(f"[{index}/{len(articles)}] Processing new article: {title}")
        
        # Extract startup details using Gemini API
        discovery = extract_startup_info(client, title, article['summary'])
        
        # Free-tier rate limiting safety delay (e.g., maximum 5 requests per minute for 2.5 Flash free tier)
        time.sleep(RATE_LIMIT_DELAY)
        
        if not discovery:
            logger.warning(f"Failed to extract info from article: {title}")
            continue
            
        # Gracefully handle articles that aren't about a specific startup
        if discovery.startup_name == "Unknown" or not discovery.startup_name.strip():
            logger.info(f"No agriculture startup identified in article: {title}. Skipping gracefully.")
            continue
            
        logger.info(f"Discovered Startup: '{discovery.startup_name}' from {url}")
        
        # Prepare row for database
        row = {
            'Startup Name': discovery.startup_name,
            'Startup Website': discovery.startup_website,
            'Source URL': url,
            'Brief Description': discovery.brief_description,
            'News Summary': discovery.news_summary,
            'Date Tracked': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save progressively to avoid losing progress
        append_single_discovery(DB_FILE, row)
        
        # Add the URL to our memory set so we don't process it again if it appears twice in the same RSS run
        existing_urls.add(url)

    logger.info("Pipeline run completed successfully.")


if __name__ == "__main__":
    main()
