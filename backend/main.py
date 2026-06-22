import os
import sys
import re
import threading
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure project root is in system path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from backend import database, scraper, similarity, chat, pdf_generator, scheduler

app = FastAPI(title="AgriScout AI Market Intelligence API")

# Enable CORS for Next.js dev server on port 3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Start background job scheduler when application starts
@app.on_event("startup")
def startup_event():
    scheduler.start_scheduler()

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown_scheduler()

# Global tracking run lock
tracker_lock = threading.Lock()
is_tracker_running = False
last_run_status = "Not Run Yet"
last_run_time = "Never"


class StartupManualInput(BaseModel):
    startup_name: str = Field(..., description="Name of the startup")
    startup_website: str = Field("Not Mentioned", description="Website of the startup")
    country: str = Field("Unknown", description="Country of origin")
    category: str = Field("Other", description="AgTech sector category")
    brief_description: str = Field(..., description="Brief description")
    funding_amount: str = Field("Unknown", description="Funding amount raised")
    funding_stage: str = Field("Unknown", description="Funding stage")
    news_type: str = Field("Other", description="Type of news event")
    source_url: str = Field("Manual Entry", description="URL source link")
    news_summary: str = Field(..., description="News summary")


class ChatQueryInput(BaseModel):
    query: str = Field(..., description="The user query for the AI Chat Assistant")


def run_tracker_pipeline_wrapper():
    """
    Runs the scraper pipeline and updates global tracking status.
    """
    global is_tracker_running, last_run_status, last_run_time
    
    with tracker_lock:
        is_tracker_running = True
        last_run_status = "Running"
        
    try:
        print("Starting AgriScout AI Scraper background task...")
        scraper.run_discovery_pipeline()
        last_run_status = "Success"
    except Exception as e:
        print(f"Error during scraper run: {e}")
        last_run_status = f"Error: {str(e)}"
    finally:
        with tracker_lock:
            is_tracker_running = False
            last_run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"AgriScout AI Scraper run finished with status: {last_run_status}")


def parse_funding_to_float(amount_str: str) -> float:
    """
    Parse funding amount strings like '$12.5M' or '500K' to float USD value.
    """
    amount_str = amount_str.lower().strip()
    if not amount_str or amount_str in ["unknown", "not mentioned", "nan", "n/a", "-"]:
        return 0.0
        
    # Extract numeric part and scale based on standard units (M, B, K)
    match = re.search(r'([0-9.,]+)\s*(m|b|k)?', amount_str)
    if not match:
        return 0.0
        
    val_str = match.group(1).replace(",", "")
    try:
        val = float(val_str)
    except ValueError:
        return 0.0
        
    unit = match.group(2)
    if unit == 'm':
        val *= 1_000_000
    elif unit == 'b':
        val *= 1_000_000_000
    elif unit == 'k':
        val *= 1_000
    return val


@app.get("/api/startups")
def get_startups():
    """
    Retrieve all discovered startups from database.
    """
    return database.read_startups()


@app.post("/api/startups", status_code=status.HTTP_201_CREATED)
def add_startup_manually(startup: StartupManualInput):
    """
    Add a manual discovery row to the Excel database.
    """
    data = startup.model_dump()
    data["date_tracked"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    success = database.add_startup(data)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to append manual entry to Excel sheet."
        )
    return {"message": "Startup discovery recorded successfully.", "data": data}


@app.delete("/api/startups/{row_index}")
def delete_startup(row_index: int):
    """
    Remove a startup from Excel logs by index.
    """
    success = database.delete_startup(row_index)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Startup at index {row_index} not found."
        )
    return {"message": f"Startup index {row_index} removed successfully."}


@app.post("/api/tracker/run", status_code=status.HTTP_202_ACCEPTED)
def trigger_tracker(background_tasks: BackgroundTasks):
    """
    Manually trigger an asynchronous Scraper crawl run.
    """
    global is_tracker_running
    
    # Check if key is available
    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GEMINI_API_KEY is not configured on the server."
        )
        
    if is_tracker_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scraper run is already executing."
        )
        
    background_tasks.add_task(run_tracker_pipeline_wrapper)
    return {
        "status": "Accepted",
        "message": "Scraper run queued in the background."
    }


@app.get("/api/tracker/status")
def get_tracker_status():
    """
    Get scheduler/pipeline state.
    """
    global is_tracker_running, last_run_status, last_run_time
    return {
        "is_running": is_tracker_running,
        "last_run_status": last_run_status,
        "last_run_time": last_run_time
    }


@app.get("/api/startups/{row_id}/similar")
def get_similar_companies(row_id: int):
    """
    Suggest similar startups using Gemini text embeddings and local cosine similarity.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GEMINI_API_KEY environment variable is not configured."
        )
        
    client = genai.Client(api_key=api_key)
    startups = database.read_startups()
    
    target_startup = next((s for s in startups if s["id"] == row_id), None)
    if not target_startup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Startup with ID {row_id} not found."
        )
        
    similar_list = similarity.get_similar_startups(client, target_startup["startup_name"], startups, top_k=3)
    return {
        "target": target_startup["startup_name"],
        "similar_companies": similar_list
    }


@app.post("/api/chat")
def run_chat_query(chat_input: ChatQueryInput):
    """
    AI Chat Assistant to query Excel logs.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GEMINI_API_KEY environment variable is not configured."
        )
        
    client = genai.Client(api_key=api_key)
    startups = database.read_startups()
    
    response_text = chat.handle_chat_query(client, chat_input.query, startups)
    return {"reply": response_text}


@app.get("/api/report/weekly")
def download_pdf_report():
    """
    Generate and stream the Weekly Market Intelligence report PDF.
    """
    startups = database.read_startups()
    if not startups:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No startups available to generate report."
        )
        
    pdf_stream = pdf_generator.generate_weekly_report_pdf(startups)
    return StreamingResponse(
        pdf_stream,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=AgriScout_Weekly_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
        }
    )


@app.get("/api/analytics")
def get_dashboard_analytics():
    """
    Compile aggregates of funding trends, categories, and growth for Next.js charts.
    """
    startups = database.read_startups()
    
    # 1. Category Distribution
    category_counts = {}
    # 2. News Type Distribution
    type_counts = {}
    # 3. Country Breakdown
    country_funding = {}
    
    # 4. Monthly/Time Series Funding
    monthly_funding = {}
    
    # Initialize categories
    for cat in ["Hydroponics", "Vertical Farming", "Drone Technology", "Farm Robotics", "FoodTech", "ClimateTech", "Other"]:
        category_counts[cat] = 0
        
    for item in startups:
        # Category
        cat = item.get("category", "Other")
        if cat not in category_counts:
            category_counts[cat] = 0
        category_counts[cat] += 1
        
        # News Type
        ntype = item.get("news_type", "Other")
        if ntype not in type_counts:
            type_counts[ntype] = 0
        type_counts[ntype] += 1
        
        # Funding parsing
        fund_str = item.get("funding_amount", "Unknown")
        fund_val = parse_funding_to_float(fund_str)
        
        # Country Funding
        country = item.get("country", "Unknown")
        if country not in country_funding:
            country_funding[country] = 0.0
        country_funding[country] += fund_val
        
        # Monthly Funding
        date_str = item.get("date_tracked", "")
        if date_str:
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                month_key = date_obj.strftime("%b %Y")
            except Exception:
                month_key = datetime.now().strftime("%b %Y")
        else:
            month_key = datetime.now().strftime("%b %Y")
            
        if month_key not in monthly_funding:
            monthly_funding[month_key] = 0.0
        monthly_funding[month_key] += fund_val

    # Convert to Next.js chart format
    categories_data = [{"name": k, "value": v} for k, v in category_counts.items() if v > 0]
    types_data = [{"name": k, "value": v} for k, v in type_counts.items()]
    
    # Funding by country (top 8)
    country_data = [{"country": k, "amount": round(v / 1_000_000, 2)} for k, v in country_funding.items() if v > 0]
    country_data.sort(key=lambda x: x["amount"], reverse=True)
    country_data = country_data[:8]
    
    # Funding by month
    monthly_data = [{"month": k, "amount": round(v / 1_000_000, 2)} for k, v in monthly_funding.items()]
    
    return {
        "category_distribution": categories_data,
        "news_type_distribution": types_data,
        "funding_by_country": country_data,
        "funding_by_month": monthly_data,
        "total_startups": len(startups)
    }
