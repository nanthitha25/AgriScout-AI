import os
import pandas as pd
from typing import List, Dict, Any
from rapidfuzz import fuzz

DB_FILE = "agtech_startups.xlsx"
HEADERS = [
    'Startup Name', 
    'Startup Website', 
    'Country', 
    'Category',
    'Brief Description', 
    'Funding Amount', 
    'Funding Stage', 
    'News Type', 
    'Source URL', 
    'News Summary', 
    'Date Tracked'
]


def ensure_db_initialized() -> None:
    """
    Ensure the Excel database is initialized with correct headers.
    If the file exists but has outdated/different columns, it preserves data but merges structure.
    """
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=HEADERS)
        df.to_excel(DB_FILE, index=False)
    else:
        try:
            df = pd.read_excel(DB_FILE)
            # Verify if headers match. If columns are missing, add them.
            missing_headers = [h for h in HEADERS if h not in df.columns]
            if missing_headers:
                for h in missing_headers:
                    df[h] = ""
                # Reorder columns to match HEADERS
                df = df[HEADERS]
                df.to_excel(DB_FILE, index=False)
        except Exception as e:
            print(f"Error checking/repairing database file columns: {e}")
            # If corrupted, re-initialize
            df = pd.DataFrame(columns=HEADERS)
            df.to_excel(DB_FILE, index=False)


def read_startups() -> List[Dict[str, Any]]:
    """
    Read tracked startups from the Excel file database.
    Returns a list of startup dictionaries with standardized field mappings.
    """
    ensure_db_initialized()
    try:
        df = pd.read_excel(DB_FILE)
        # Convert NaN values to empty strings or default placeholders to ensure JSON compliance
        df = df.fillna("")
        
        startups = []
        for index, row in df.iterrows():
            startup = {
                "id": int(index),
                "startup_name": str(row.get("Startup Name", "")).strip(),
                "startup_website": str(row.get("Startup Website", "")).strip(),
                "country": str(row.get("Country", "Unknown")).strip(),
                "category": str(row.get("Category", "Other")).strip(),
                "brief_description": str(row.get("Brief Description", "")).strip(),
                "funding_amount": str(row.get("Funding Amount", "Unknown")).strip(),
                "funding_stage": str(row.get("Funding Stage", "Unknown")).strip(),
                "news_type": str(row.get("News Type", "Other")).strip(),
                "source_url": str(row.get("Source URL", "")).strip(),
                "news_summary": str(row.get("News Summary", "")).strip(),
                "date_tracked": str(row.get("Date Tracked", ""))
            }
            startups.append(startup)
        return startups
    except Exception as e:
        print(f"Error reading Excel database: {e}")
        return []


def clean_domain(url: str) -> str:
    """
    Extract a clean domain name from a URL/website string for accurate duplicate checking.
    e.g., 'https://www.solarfoods.com/path' -> 'solarfoods.com'
    """
    domain = url.strip().lower()
    if not domain or domain in ["not mentioned", "unknown", "nan", ""]:
        return ""
    # Strip protocols and www
    domain = domain.replace("https://", "").replace("http://", "").replace("www.", "")
    # Strip trailing paths or slashes
    domain = domain.split("/")[0]
    return domain


def check_duplicate(new_name: str, new_website: str, existing_startups: List[Dict[str, Any]]) -> bool:
    """
    Check if a startup already exists in the database.
    Detects duplicates using three rules:
    1. Normalized website domain matching.
    2. Case-insensitive exact name matching.
    3. Fuzzy name matching using RapidFuzz (threshold of 85%).
    """
    new_name_clean = new_name.strip().lower()
    new_domain_clean = clean_domain(new_website)
    
    for startup in existing_startups:
        # Match 1: Normalized website domain check
        existing_website = startup.get("startup_website", "")
        existing_domain_clean = clean_domain(existing_website)
        if new_domain_clean and existing_domain_clean and new_domain_clean == existing_domain_clean:
            return True
            
        # Match 2: Case-insensitive name check
        existing_name_clean = startup.get("startup_name", "").strip().lower()
        if new_name_clean == existing_name_clean:
            return True
            
        # Match 3: Fuzzy matching on names using RapidFuzz
        # Token set ratio or ratio can handle variations like "GreenFarm AI" and "Green Farm AI"
        if fuzz.token_sort_ratio(new_name_clean, existing_name_clean) > 85.0:
            return True
            
    return False


def delete_startup(row_index: int) -> bool:
    """
    Delete a startup from the database by its 0-indexed row position.
    """
    ensure_db_initialized()
    try:
        df = pd.read_excel(DB_FILE)
        if 0 <= row_index < len(df):
            # Drop the row by index and reset index
            df = df.drop(df.index[row_index]).reset_index(drop=True)
            df.to_excel(DB_FILE, index=False)
            return True
        return False
    except Exception as e:
        print(f"Error deleting row {row_index} from Excel database: {e}")
        return False


def add_startup(startup_data: Dict[str, Any]) -> bool:
    """
    Manually add a startup discovery to the database.
    """
    ensure_db_initialized()
    try:
        row = {
            'Startup Name': startup_data.get('startup_name', 'Unknown'),
            'Startup Website': startup_data.get('startup_website', 'Not Mentioned'),
            'Country': startup_data.get('country', 'Unknown'),
            'Category': startup_data.get('category', 'Other'),
            'Brief Description': startup_data.get('brief_description', ''),
            'Funding Amount': startup_data.get('funding_amount', 'Unknown'),
            'Funding Stage': startup_data.get('funding_stage', 'Unknown'),
            'News Type': startup_data.get('news_type', 'Other'),
            'Source URL': startup_data.get('source_url', 'Manual Entry'),
            'News Summary': startup_data.get('news_summary', ''),
            'Date Tracked': startup_data.get('date_tracked', '')
        }
        
        new_df = pd.DataFrame([row])
        existing_df = pd.read_excel(DB_FILE)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df.to_excel(DB_FILE, index=False)
        return True
    except Exception as e:
        print(f"Error adding manual startup row: {e}")
        return False
