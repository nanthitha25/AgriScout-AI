import os
import sys
import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import feedparser
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.errors import APIError

from backend import database

logger = logging.getLogger(__name__)

# Constants
RSS_BASE_URL = "https://news.google.com/rss/search?q={query}+when:7d&hl=en-US&gl=US&ceid=US:en"

# Search combinations based on target keywords
KEYWORDS = [
    "agtech startup funding",
    "precision agriculture launched",
    "hydroponics startup vertical farming",
    "agricultural robotics farm automation",
    "smart irrigation agricultural AI",
    "agricultural drone startup FoodTech"
]

# Free tier rate limits for Gemini 2.5 Flash structured calls
RATE_LIMIT_DELAY = 12.5


class StartupDiscovery(BaseModel):
    startup_name: str = Field(
        description="Name of the AgTech startup identified in the news article, or 'Unknown' if no specific startup is identified."
    )
    startup_website: str = Field(
        description="The official URL/website domain of the startup if mentioned in the text, or 'Not Mentioned'."
    )
    country: str = Field(
        description="The country of origin for the startup if mentioned or inferred (e.g. 'United States', 'Finland'), or 'Unknown'."
    )
    category: str = Field(
        description="Categorize the startup into one of: 'Hydroponics', 'Vertical Farming', 'Drone Technology', 'Farm Robotics', 'FoodTech', 'ClimateTech', or 'Other'."
    )
    description: str = Field(
        description="1-2 sentences explaining what the startup does / their core technology or product."
    )
    funding_amount: str = Field(
        description="The amount of funding raised (e.g. '$10M', '5M EUR') or 'Unknown' if not a funding announcement."
    )
    funding_stage: str = Field(
        description="The funding stage (e.g. 'Seed', 'Series A', 'Grant', 'Pre-seed') or 'Unknown'."
    )
    news_type: str = Field(
        description="The category of news: 'Funding', 'Product Launch', 'Acquisition', 'Partnership', or 'Other'."
    )
    news_summary: str = Field(
        description="A short summary explaining why they are in the news (e.g. Solar Foods secured funding to scale operations)."
    )


def fetch_all_feeds() -> List[Dict[str, Any]]:
    """
    Query Google News RSS across multiple keyword combinations.
    Deduplicates URLs locally in-memory before returning.
    """
    unique_articles: Dict[str, Dict[str, Any]] = {}
    
    for kw in KEYWORDS:
        query_encoded = kw.replace(" ", "+")
        rss_url = RSS_BASE_URL.format(query=query_encoded)
        logger.info(f"Fetching RSS feed for query: '{kw}'")
        
        try:
            feed = feedparser.parse(rss_url)
            if feed.bozo:
                logger.warning(f"Bozo parser warning for '{kw}': {feed.bozo_exception}")
                
            for entry in feed.entries:
                link = getattr(entry, 'link', '')
                if link and link not in unique_articles:
                    unique_articles[link] = {
                        'title': getattr(entry, 'title', ''),
                        'link': link,
                        'summary': getattr(entry, 'summary', ''),
                        'published': getattr(entry, 'published', '')
                    }
        except Exception as e:
            logger.error(f"Error parsing feed for query '{kw}': {e}")
            
    logger.info(f"Retrieved {len(unique_articles)} unique articles from RSS feeds.")
    return list(unique_articles.values())


def extract_startup_details(client: genai.Client, title: str, summary: str, max_retries: int = 5) -> Optional[StartupDiscovery]:
    """
    Utilize Gemini 2.5 Flash with Structured Outputs to parse article title and snippet.
    Handles 429 rate limit locks using exponential backoff.
    """
    prompt = f"""
You are an expert analyst for AgriScout AI, an automated AgTech market intelligence system.
Analyze the following news article title and summary to identify if it features a specific agriculture startup company.

If a specific agriculture startup company is identified, extract the details according to the schema.
If the article is not about a specific startup (for example, it is about general farming trends, broad agricultural research, established giant corporations, or policy/governmental updates without focusing on a specific new venture), you MUST set `startup_name` to 'Unknown'.

Title: {title}
Summary/Snippet: {summary}
"""
    delay = 10.0  # Initial retry delay
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=StartupDiscovery,
                    temperature=0.1,
                ),
            )
            
            parsed_result = response.parsed
            if parsed_result:
                return parsed_result
                
            if response.text:
                return StartupDiscovery.model_validate_json(response.text)
                
            logger.warning("Empty response from Gemini API.")
            return None
            
        except APIError as api_err:
            if api_err.code == 429:
                logger.warning(
                    f"Rate limit hit (429) on attempt {attempt + 1}/{max_retries}. "
                    f"Waiting {delay}s for cooldown..."
                )
                time.sleep(delay)
                delay *= 2.0
                continue
            else:
                logger.error(f"Gemini API Error: {api_err}")
                return None
        except Exception as e:
            logger.error(f"Unexpected error in Gemini extraction: {e}")
            return None
            
    logger.error(f"Failed extraction after {max_retries} attempts.")
    return None


def run_discovery_pipeline() -> None:
    """
    Main runner executing AgriScout AI startup discovery workflow.
    """
    logger.info("Initializing AgriScout AI discovery run...")
    
    # 1. Get API Key and client
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable is not configured. Aborting scraper.")
        return
        
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize GenAI client: {e}")
        return

    # 2. Load existing startups for deduplication
    database.ensure_db_initialized()
    existing_startups = database.read_startups()
    existing_urls = {item["source_url"] for item in existing_startups if item["source_url"]}
    
    # 3. Fetch feed entries
    articles = fetch_all_feeds()
    
    logger.info("Iterating through news entries to extract insights...")
    
    for index, article in enumerate(articles, 1):
        url = article['link']
        title = article['title']
        
        # Deduplication Match 1: URL matching
        if url in existing_urls:
            logger.info(f"[{index}/{len(articles)}] Skipping duplicate URL: {title}")
            continue
            
        logger.info(f"[{index}/{len(articles)}] Extracting AgTech data from: {title}")
        
        # Call Gemini extraction pipeline
        discovery = extract_startup_details(client, title, article['summary'])
        
        # Free-tier rate limiting safety spacing
        time.sleep(RATE_LIMIT_DELAY)
        
        if not discovery:
            logger.warning(f"Could not parse content from: {title}")
            continue
            
        # Filter general articles
        if discovery.startup_name == "Unknown" or not discovery.startup_name.strip():
            logger.info(f"No specific AgTech startup found in: {title}. Skipping gracefully.")
            continue
            
        # Deduplication Match 2 & 3: Name / Website / Fuzzy matches
        # Freshly reload DB to get the absolute latest status (progressive updates)
        existing_startups = database.read_startups()
        if database.check_duplicate(discovery.startup_name, discovery.startup_website, existing_startups):
            logger.info(f"Fuzzy or exact match duplicate detected for: '{discovery.startup_name}' or site '{discovery.startup_website}'. Skipping.")
            continue
            
        logger.info(f"Discovered New AgTech Startup: '{discovery.startup_name}'! Persisting details.")
        
        # 4. Prepare row structure
        row = {
            'startup_name': discovery.startup_name,
            'startup_website': discovery.startup_website,
            'country': discovery.country,
            'category': discovery.category,
            'brief_description': discovery.description,
            'funding_amount': discovery.funding_amount,
            'funding_stage': discovery.funding_stage,
            'news_type': discovery.news_type,
            'source_url': url,
            'news_summary': discovery.news_summary,
            'date_tracked': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 5. Progressive Save
        database.add_startup(row)
        existing_urls.add(url)
        
    logger.info("AgriScout AI discovery pipeline run finished.")
