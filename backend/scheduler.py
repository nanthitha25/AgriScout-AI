from apscheduler.schedulers.background import BackgroundScheduler
from backend import scraper

# Initialize the global background scheduler instance
scheduler = BackgroundScheduler()


def start_scheduler() -> None:
    """
    Register and start the periodic scraper discovery job to execute every 6 hours.
    """
    try:
        # Avoid registering duplicate job ids if start is called twice
        scheduler.add_job(
            func=scraper.run_discovery_pipeline,
            trigger="interval",
            hours=6,
            id="agriscout_news_crawler",
            replace_existing=True
        )
        
        if not scheduler.running:
            scheduler.start()
            print("AgriScout AI Background Scheduler started. Scraper job will execute every 6 hours.")
    except Exception as e:
        print(f"Error starting background scheduler: {e}")


def shutdown_scheduler() -> None:
    """
    Gracefully terminate the background scheduler threads upon server shutdown.
    """
    try:
        if scheduler.running:
            scheduler.shutdown()
            print("AgriScout AI Background Scheduler stopped gracefully.")
    except Exception as e:
        print(f"Error shutting down background scheduler: {e}")
